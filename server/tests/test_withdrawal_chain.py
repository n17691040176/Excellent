from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import app.main  # noqa: F401
from app.core.exceptions import ConflictError
from app.models.commission import CommissionAccountLedger, WithdrawRequest
from app.models.enums import GlobalRole, WithdrawStatus, WithdrawType
from app.schemas.commission import WithdrawCreateRequest
from app.services.bank_card_service import BankCardService
from app.services.commission_service import CommissionService
from app.utils.sensitive_data import decrypt_sensitive, encrypt_sensitive
from app.utils.spreadsheet import build_xlsx, load_tabular_rows


def first_query(value):
    query = MagicMock()
    query.filter.return_value.with_for_update.return_value.first.return_value = value
    return query


class WithdrawalChainTest(TestCase):
    def test_request_schema_only_accepts_commission(self):
        with self.assertRaises(ValueError):
            WithdrawCreateRequest(withdraw_type='BALANCE', amount=10, bank_card_id=1)

    def test_sensitive_bank_card_round_trip(self):
        encrypted = encrypt_sensitive('6222020000001234')
        self.assertNotIn('6222020000001234', encrypted)
        self.assertEqual(decrypt_sensitive(encrypted), '6222020000001234')

    def test_bank_card_metadata_can_update_without_reentering_card_number(self):
        encrypted = encrypt_sensitive('6222020000001234')
        card = SimpleNamespace(
            id=3,
            user_id=10,
            holder_name='张三',
            bank_name='测试银行',
            branch_name=None,
            card_number_encrypted=encrypted,
            card_last_four='1234',
            is_default=True,
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = card
        BankCardService.update(db, 10, 3, {'branch_name': '新支行', 'is_default': False})
        self.assertEqual(card.branch_name, '新支行')
        self.assertTrue(card.is_default)
        self.assertEqual(card.card_number_encrypted, encrypted)

    def test_apply_approve_and_pay_move_commission_at_correct_stages(self):
        db = MagicMock()
        db.get.return_value = SimpleNamespace(id=10, team_id=8)
        card = SimpleNamespace(
            id=3,
            holder_name='张三',
            bank_name='测试银行',
            branch_name='测试支行',
            card_number_encrypted=encrypt_sensitive('6222020000001234'),
            card_last_four='1234',
        )
        summary = SimpleNamespace(
            user_id=10,
            available_amount=Decimal('100.00'),
            frozen_amount=Decimal('5.00'),
            withdrawn_amount=Decimal('20.00'),
            updated_at=None,
        )
        added = []

        def add(item):
            if isinstance(item, WithdrawRequest):
                item.id = 99
            added.append(item)

        db.add.side_effect = add
        db.query.side_effect = [first_query(card), first_query(summary)]
        with patch.object(CommissionService, 'withdraw_config', return_value={'fee_rate': 2, 'min_amount': 1, 'max_amount': 50000}):
            record = CommissionService.create_withdraw(db, 10, WithdrawType.COMMISSION, 50, 3)

        self.assertEqual(record.fee_amount, Decimal('1.00'))
        self.assertEqual(record.net_amount, Decimal('49.00'))
        self.assertEqual(summary.available_amount, Decimal('50.00'))
        self.assertEqual(summary.frozen_amount, Decimal('55.00'))
        self.assertTrue(any(isinstance(item, CommissionAccountLedger) and item.action == 'APPLY' for item in added))

        admin = SimpleNamespace(id=1, global_role=GlobalRole.SUPER_ADMIN)
        db.query.side_effect = [first_query(record)]
        CommissionService.approve_withdraw(db, record.id, admin, '资料无误')
        self.assertEqual(record.status, WithdrawStatus.APPROVED)
        self.assertEqual(summary.frozen_amount, Decimal('55.00'))
        self.assertEqual(summary.withdrawn_amount, Decimal('20.00'))

        db.query.side_effect = [first_query(record), first_query(summary)]
        CommissionService.pay_withdraw(db, record.id, admin)
        self.assertEqual(record.status, WithdrawStatus.PAID)
        self.assertEqual(summary.frozen_amount, Decimal('5.00'))
        self.assertEqual(summary.withdrawn_amount, Decimal('70.00'))
        self.assertTrue(any(isinstance(item, CommissionAccountLedger) and item.action == 'PAY' for item in added))

    def test_service_rejects_non_commission_withdraw(self):
        with self.assertRaisesRegex(ConflictError, 'Only commission'):
            CommissionService.create_withdraw(MagicMock(), 1, WithdrawType.POINTS, 10, 1)

    def test_finance_xlsx_can_be_read_back(self):
        content = build_xlsx(['提现单号', '银行卡号'], [['WD-1', '6222020000001234']], '提现打款清单')
        self.assertEqual(
            load_tabular_rows('withdraws.xlsx', content),
            [{'提现单号': 'WD-1', '银行卡号': '6222020000001234'}],
        )
