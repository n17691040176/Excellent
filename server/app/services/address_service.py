from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.address import UserAddress


class AddressService:
    @staticmethod
    def list_addresses(db: Session, user_id: int) -> list[UserAddress]:
        return db.query(UserAddress).filter(UserAddress.user_id == user_id).order_by(UserAddress.id.desc()).all()

    @staticmethod
    def create_address(db: Session, user_id: int, payload: dict) -> UserAddress:
        if payload.get('is_default'):
            db.query(UserAddress).filter(UserAddress.user_id == user_id).update({UserAddress.is_default: False})
        address = UserAddress(user_id=user_id, **payload)
        db.add(address)
        db.commit()
        db.refresh(address)
        return address

    @staticmethod
    def update_address(db: Session, user_id: int, address_id: int, payload: dict) -> UserAddress:
        address = db.query(UserAddress).filter(UserAddress.id == address_id, UserAddress.user_id == user_id).first()
        if not address:
            raise NotFoundError('Address not found')
        if payload.get('is_default'):
            db.query(UserAddress).filter(UserAddress.user_id == user_id).update({UserAddress.is_default: False})
        for field, value in payload.items():
            if value is not None:
                setattr(address, field, value)
        db.commit()
        db.refresh(address)
        return address

    @staticmethod
    def delete_address(db: Session, user_id: int, address_id: int) -> None:
        address = db.query(UserAddress).filter(UserAddress.id == address_id, UserAddress.user_id == user_id).first()
        if not address:
            raise NotFoundError('Address not found')
        db.delete(address)
        db.commit()

    @staticmethod
    def set_default(db: Session, user_id: int, address_id: int) -> UserAddress:
        address = db.query(UserAddress).filter(UserAddress.id == address_id, UserAddress.user_id == user_id).first()
        if not address:
            raise NotFoundError('Address not found')
        db.query(UserAddress).filter(UserAddress.user_id == user_id).update({UserAddress.is_default: False})
        address.is_default = True
        db.commit()
        db.refresh(address)
        return address
