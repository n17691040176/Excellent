from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.bank_card import UserBankCard
from app.models.commission import WithdrawRequest
from app.models.enums import WithdrawStatus
from app.utils.sensitive_data import encrypt_sensitive, mask_bank_card


class BankCardService:
    @staticmethod
    def serialize(card: UserBankCard) -> dict:
        return {
            'id': card.id,
            'holder_name': card.holder_name,
            'bank_name': card.bank_name,
            'branch_name': card.branch_name,
            'card_last_four': card.card_last_four,
            'masked_card_number': mask_bank_card(card.card_last_four),
            'is_default': bool(card.is_default),
            'created_at': card.created_at.isoformat() if card.created_at else None,
            'updated_at': card.updated_at.isoformat() if card.updated_at else None,
        }

    @staticmethod
    def list_cards(db: Session, user_id: int) -> list[UserBankCard]:
        return db.query(UserBankCard).filter(UserBankCard.user_id == user_id).order_by(
            UserBankCard.is_default.desc(), UserBankCard.id.desc()
        ).all()

    @staticmethod
    def get_owned(db: Session, user_id: int, card_id: int, *, lock: bool = False) -> UserBankCard:
        query = db.query(UserBankCard).filter(UserBankCard.id == card_id, UserBankCard.user_id == user_id)
        if lock:
            query = query.with_for_update()
        card = query.first()
        if not card:
            raise NotFoundError('Bank card not found')
        return card

    @staticmethod
    def create(db: Session, user_id: int, payload: dict) -> UserBankCard:
        card_number = payload.pop('card_number', None)
        existing = db.query(UserBankCard.id).filter(UserBankCard.user_id == user_id).first()
        if not existing:
            payload['is_default'] = True
        if payload.get('is_default'):
            db.query(UserBankCard).filter(UserBankCard.user_id == user_id).update({UserBankCard.is_default: False})
        card = UserBankCard(
            user_id=user_id,
            card_number_encrypted=encrypt_sensitive(card_number),
            card_last_four=card_number[-4:],
            **payload,
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        return card

    @staticmethod
    def update(db: Session, user_id: int, card_id: int, payload: dict) -> UserBankCard:
        card = BankCardService.get_owned(db, user_id, card_id, lock=True)
        card_number = payload.pop('card_number', None)
        if payload.get('is_default'):
            db.query(UserBankCard).filter(UserBankCard.user_id == user_id).update({UserBankCard.is_default: False})
        elif payload.get('is_default') is False and card.is_default:
            payload['is_default'] = True
        for key, value in payload.items():
            setattr(card, key, value)
        if card_number:
            card.card_number_encrypted = encrypt_sensitive(card_number)
            card.card_last_four = card_number[-4:]
        db.commit()
        db.refresh(card)
        return card

    @staticmethod
    def set_default(db: Session, user_id: int, card_id: int) -> UserBankCard:
        card = BankCardService.get_owned(db, user_id, card_id, lock=True)
        db.query(UserBankCard).filter(UserBankCard.user_id == user_id).update({UserBankCard.is_default: False})
        card.is_default = True
        db.commit()
        db.refresh(card)
        return card

    @staticmethod
    def delete(db: Session, user_id: int, card_id: int) -> None:
        card = BankCardService.get_owned(db, user_id, card_id, lock=True)
        pending = db.query(WithdrawRequest.id).filter(
            WithdrawRequest.bank_card_id == card.id,
            WithdrawRequest.status.in_([WithdrawStatus.PENDING, WithdrawStatus.APPROVED]),
        ).first()
        if pending:
            raise ConflictError('Bank card is used by an active withdraw request')
        was_default = card.is_default
        db.delete(card)
        db.flush()
        if was_default:
            replacement = db.query(UserBankCard).filter(UserBankCard.user_id == user_id).order_by(UserBankCard.id.desc()).first()
            if replacement:
                replacement.is_default = True
        db.commit()
