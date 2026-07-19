import base64
import tempfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from app.core.exceptions import ConflictError
from app.core.payment_config import AlipayConfig, PaymentConfig, validate_payment_config
from app.models.enums import OrderType, PaymentChannel, PaymentStatus, PayStatus
from app.services import payment_service as payment_module
from app.services.payment_service import PaymentService


class AlipayH5PaymentTest(TestCase):
    def setUp(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.private_path = root / 'merchant-private.pem'
        self.public_path = root / 'alipay-public.pem'
        self.private_path.write_bytes(
            self.private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        self.public_path.write_bytes(
            self.public_key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        self.config = AlipayConfig(
            enabled=True,
            app_id='2026000000000000',
            private_key_path=str(self.private_path),
            public_key_path=str(self.public_path),
            notify_url='https://pay.example.com/api/v1/payments/alipay/notify',
            return_url='https://pay.example.com/#/subpackages/order/detail',
            gateway_url='https://openapi.alipay.com/gateway.do',
            payment_method='alipay.trade.wap.pay',
            sign_type='RSA2',
            seller_id='2088000000000000',
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def build_order():
        return SimpleNamespace(
            id=12,
            order_no='ORD-20260716-0012',
            order_type=OrderType.SELF_OPERATED_ORDER,
            pay_status=PayStatus.UNPAID,
            payable_amount=Decimal('9.90'),
        )

    @staticmethod
    def build_transaction():
        return SimpleNamespace(
            id=9,
            order_id=12,
            order_no='ORD-20260716-0012',
            channel=PaymentChannel.ALIPAY,
            status=PaymentStatus.PENDING,
            amount=Decimal('9.90'),
            currency='CNY',
            out_trade_no='PAYAL0012ABCDEF',
            provider_app_id='2026000000000000',
        )

    def test_builds_signed_h5_form(self):
        payment = PaymentService._alipay_build_request_payment(
            self.build_order(),
            self.build_transaction(),
            self.config,
        )

        self.assertEqual(payment['payment_method'], 'alipay.trade.wap.pay')
        self.assertEqual(payment['payment_form']['action'], f'{self.config.gateway_url}?charset=utf-8')
        self.assertNotIn('charset', payment['payment_form']['params'])
        params = dict(payment['payment_form']['params'], charset=self.config.charset)
        signature = base64.b64decode(params.pop('sign'))
        message = PaymentService._alipay_sign_string(params)
        self.assertIn('sign_type=RSA2', message)
        self.public_key.verify(signature, message.encode('utf-8'), padding.PKCS1v15(), hashes.SHA256())
        self.assertIn('#/subpackages/order/detail?order_id=12&out_trade_no=PAYAL0012ABCDEF', payment['return_url'])
        self.assertEqual(payment['provider_payload']['biz_content']['product_code'], 'QUICK_WAP_WAP')

    def test_loads_public_key_from_x509_certificate(self):
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Alipay Test')])
        now_utc = datetime.now(UTC)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(self.public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now_utc - timedelta(days=1))
            .not_valid_after(now_utc + timedelta(days=1))
            .sign(self.private_key, hashes.SHA256())
        )
        certificate_path = Path(self.temp_dir.name) / 'alipay-public-cert.pem'
        certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))

        loaded_key = PaymentService._load_public_key(str(certificate_path))

        self.assertEqual(loaded_key.public_numbers(), self.public_key.public_numbers())

    def test_notify_requires_valid_signature_and_amount(self):
        tx = self.build_transaction()
        order = self.build_order()
        payload = {
            'app_id': self.config.app_id,
            'seller_id': self.config.seller_id,
            'trade_status': 'TRADE_SUCCESS',
            'out_trade_no': tx.out_trade_no,
            'total_amount': '9.90',
            'trade_no': '20260716000000000001',
            'sign_type': 'RSA2',
        }
        payload['sign'] = PaymentService._rsa_sign(
            self.private_key,
            PaymentService._alipay_sign_string(payload, exclude_sign_type=True),
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = tx

        with (
            patch.object(payment_module, 'payment_config', PaymentConfig(mock_external_payment=False, alipay=self.config)),
            patch.object(PaymentService, 'confirm_paid_order', return_value=order) as confirm_paid,
        ):
            result = PaymentService.handle_notify(db, PaymentChannel.ALIPAY.value, payload)

        self.assertEqual(result['provider_trade_no'], '20260716000000000001')
        confirm_paid.assert_called_once()

        payload['total_amount'] = '9.91'
        payload['sign'] = PaymentService._rsa_sign(
            self.private_key,
            PaymentService._alipay_sign_string(payload, exclude_sign_type=True),
        )
        with (
            patch.object(payment_module, 'payment_config', PaymentConfig(mock_external_payment=False, alipay=self.config)),
            patch.object(PaymentService, 'confirm_paid_order', return_value=order) as confirm_paid,
            self.assertRaises(ConflictError),
        ):
            PaymentService.handle_notify(db, PaymentChannel.ALIPAY.value, payload)
        confirm_paid.assert_not_called()

    def test_production_rejects_mock_payment(self):
        with self.assertRaisesRegex(RuntimeError, 'PAYMENT_MOCK_EXTERNAL_PAYMENT'):
            validate_payment_config('production', PaymentConfig(mock_external_payment=True))

    def test_disabled_provider_does_not_fall_back_to_mock(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        order = self.build_order()
        with (
            patch.object(
                payment_module,
                'payment_config',
                PaymentConfig(mock_external_payment=False, alipay=AlipayConfig(enabled=False)),
            ),
            self.assertRaisesRegex(ConflictError, 'not enabled'),
        ):
            PaymentService.prepare_external_payment(db, order, PaymentChannel.ALIPAY.value)

    def test_rejects_invalid_alipay_key_material(self):
        self.private_path.write_text('not a private key', encoding='utf-8')
        self.public_path.write_text('not a public key', encoding='utf-8')

        with self.assertRaisesRegex(RuntimeError, 'valid unencrypted PEM private key'):
            validate_payment_config(
                'production',
                PaymentConfig(mock_external_payment=False, alipay=self.config),
            )
