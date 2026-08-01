import base64
import json
import tempfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import md5
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from app.core.exceptions import ConflictError, ForbiddenError
from app.core.payment_config import AlipayConfig, PaymentConfig, validate_payment_config
from app.models.enums import OrderType, PaymentChannel, PaymentStatus, PayStatus
from app.services import payment_service as payment_module
from app.services.payment_service import PaymentService


class AlipayH5PaymentTest(TestCase):
    @staticmethod
    def build_certificate(private_key, common_name: str, serial_number: int | None = None):
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
        now_utc = datetime.now(UTC)
        return (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(private_key.public_key())
            .serial_number(serial_number or x509.random_serial_number())
            .not_valid_before(now_utc - timedelta(days=1))
            .not_valid_after(now_utc + timedelta(days=1))
            .sign(private_key, hashes.SHA256())
        )

    def setUp(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        self.alipay_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.alipay_public_key = self.alipay_private_key.public_key()
        self.root_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.private_path = root / 'merchant-private.pem'
        self.app_cert_path = root / 'app-cert.crt'
        self.alipay_cert_path = root / 'alipay-public-cert.crt'
        self.root_cert_path = root / 'alipay-root-cert.crt'
        self.private_path.write_bytes(
            self.private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        self.app_certificate = self.build_certificate(self.private_key, 'Merchant App', 123456789)
        self.alipay_certificate = self.build_certificate(self.alipay_private_key, 'Alipay Platform', 234567890)
        self.root_certificate = self.build_certificate(self.root_private_key, 'Alipay Root', 345678901)
        self.app_cert_path.write_bytes(self.app_certificate.public_bytes(serialization.Encoding.PEM))
        self.alipay_cert_path.write_bytes(self.alipay_certificate.public_bytes(serialization.Encoding.PEM))
        self.root_cert_path.write_bytes(self.root_certificate.public_bytes(serialization.Encoding.PEM))
        self.config = AlipayConfig(
            enabled=True,
            app_id='2026000000000000',
            private_key_path=str(self.private_path),
            app_cert_path=str(self.app_cert_path),
            alipay_public_cert_path=str(self.alipay_cert_path),
            root_cert_path=str(self.root_cert_path),
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
        self.assertIn('#/subpackages/order/detail?order_id=12', payment['return_url'])
        self.assertNotIn('out_trade_no=', payment['return_url'])
        self.assertEqual(payment['provider_payload']['biz_content']['product_code'], 'QUICK_WAP_WAP')
        self.assertEqual(payment['provider_payload']['biz_content']['timeout_express'], '30m')

    def test_verifies_signed_trade_query_response(self):
        response = {
            'code': '10000',
            'msg': 'Success',
            'out_trade_no': 'PAYAL0012ABCDEF',
            'trade_no': '20260720000000000001',
            'trade_status': 'TRADE_SUCCESS',
            'total_amount': '9.90',
        }
        response_body = json.dumps(response, ensure_ascii=False, separators=(',', ':'))
        signature = PaymentService._rsa_sign(self.alipay_private_key, response_body)
        raw_body = f'{{"alipay_trade_query_response":{response_body},"sign":"{signature}"}}'

        result = PaymentService._alipay_verify_api_response(
            raw_body,
            'alipay_trade_query_response',
            self.config,
        )

        self.assertEqual(result, response)

    def test_trade_query_sends_charset_in_gateway_url(self):
        response = {
            'code': '10000',
            'msg': 'Success',
            'out_trade_no': 'PAYAL0012ABCDEF',
            'trade_no': '20260720000000000001',
            'trade_status': 'TRADE_SUCCESS',
            'total_amount': '9.90',
        }
        response_body = json.dumps(response, ensure_ascii=False, separators=(',', ':'))
        signature = PaymentService._rsa_sign(self.alipay_private_key, response_body)
        raw_body = f'{{"alipay_trade_query_response":{response_body},"sign":"{signature}"}}'
        provider_response = MagicMock()
        provider_response.read.return_value = raw_body.encode(self.config.charset)

        with patch.object(payment_module.urlrequest, 'urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value = provider_response
            result = PaymentService._alipay_query_trade('PAYAL0012ABCDEF', self.config)

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, f'{self.config.gateway_url}?charset=utf-8')
        self.assertEqual(result, response)

    def test_reconciles_successful_trade_query(self):
        tx = self.build_transaction()
        order = self.build_order()
        paid_order = SimpleNamespace(**vars(order), order_status='PENDING_SHIP')
        query_result = {
            'code': '10000',
            'msg': 'Success',
            'out_trade_no': tx.out_trade_no,
            'trade_no': '20260720000000000001',
            'trade_status': 'TRADE_SUCCESS',
            'total_amount': '9.90',
        }
        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.first.return_value = tx

        with (
            patch.object(payment_module, 'payment_config', PaymentConfig(mock_external_payment=False, alipay=self.config)),
            patch.object(PaymentService, '_alipay_query_trade', return_value=query_result),
            patch.object(PaymentService, 'confirm_paid_order', return_value=paid_order) as confirm_paid,
        ):
            result = PaymentService.reconcile_alipay_payment(db, order, tx.out_trade_no)

        self.assertIs(result['order'], paid_order)
        self.assertEqual(result['provider_status'], 'TRADE_SUCCESS')
        confirm_paid.assert_called_once_with(
            db,
            tx,
            notify_payload={'source': 'trade_query', **query_result},
            provider_trade_no='20260720000000000001',
        )

    def test_reconciles_latest_transaction_when_return_trade_no_does_not_match(self):
        tx = self.build_transaction()
        order = self.build_order()
        db = MagicMock()
        base_query = db.query.return_value.filter.return_value
        base_query.filter.return_value.first.return_value = None
        base_query.filter.return_value.order_by.return_value.first.return_value = tx

        with patch.object(
            payment_module,
            'payment_config',
            PaymentConfig(mock_external_payment=True, alipay=self.config),
        ):
            result = PaymentService.reconcile_alipay_payment(
                db,
                order,
                'ALIPAY_RETURN_VALUE_WITHOUT_LOCAL_TRANSACTION',
            )

        self.assertIs(result['transaction'], tx)
        self.assertEqual(result['provider_status'], 'WAIT_BUYER_PAY')

    def test_rejects_trade_query_amount_mismatch(self):
        tx = self.build_transaction()
        order = self.build_order()
        query_result = {
            'code': '10000',
            'out_trade_no': tx.out_trade_no,
            'trade_no': '20260720000000000001',
            'trade_status': 'TRADE_SUCCESS',
            'total_amount': '10.00',
        }
        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.first.return_value = tx

        with (
            patch.object(payment_module, 'payment_config', PaymentConfig(mock_external_payment=False, alipay=self.config)),
            patch.object(PaymentService, '_alipay_query_trade', return_value=query_result),
            self.assertRaisesRegex(ConflictError, 'amount mismatch'),
        ):
            PaymentService.reconcile_alipay_payment(db, order, tx.out_trade_no)

    def test_reconciles_valid_signed_return(self):
        tx = self.build_transaction()
        order = self.build_order()
        paid_order = SimpleNamespace(**vars(order), order_status='PENDING_SHIP')
        payload = {
            'app_id': self.config.app_id,
            'auth_app_id': self.config.app_id,
            'seller_id': self.config.seller_id,
            'method': 'alipay.trade.wap.pay.return',
            'out_trade_no': tx.out_trade_no,
            'total_amount': '9.90',
            'trade_no': '20260722000000000001',
            'charset': 'utf-8',
            'sign_type': 'RSA2',
            'timestamp': '2026-07-22 13:53:19',
            'version': '1.0',
        }
        payload['sign'] = PaymentService._rsa_sign(
            self.alipay_private_key,
            PaymentService._alipay_sign_string(payload, exclude_sign_type=True),
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = tx

        with (
            patch.object(payment_module, 'payment_config', PaymentConfig(mock_external_payment=False, alipay=self.config)),
            patch.object(PaymentService, 'confirm_paid_order', return_value=paid_order) as confirm_paid,
        ):
            result = PaymentService.reconcile_alipay_return(db, order, payload)

        self.assertIs(result['order'], paid_order)
        self.assertEqual(result['provider_status'], 'TRADE_SUCCESS')
        confirm_paid.assert_called_once_with(
            db,
            tx,
            notify_payload={'source': 'signed_return', **payload},
            provider_trade_no='20260722000000000001',
        )

    def test_rejects_invalid_signed_return(self):
        tx = self.build_transaction()
        payload = {
            'app_id': self.config.app_id,
            'seller_id': self.config.seller_id,
            'method': 'alipay.trade.wap.pay.return',
            'out_trade_no': tx.out_trade_no,
            'total_amount': '9.90',
            'trade_no': '20260722000000000001',
            'sign_type': 'RSA2',
            'sign': base64.b64encode(b'invalid-signature').decode(),
        }
        db = MagicMock()

        with (
            patch.object(payment_module, 'payment_config', PaymentConfig(mock_external_payment=False, alipay=self.config)),
            patch.object(PaymentService, 'confirm_paid_order') as confirm_paid,
            self.assertRaises(ForbiddenError),
        ):
            PaymentService.reconcile_alipay_return(db, self.build_order(), payload)
        confirm_paid.assert_not_called()

    def test_loads_public_key_only_from_x509_certificate(self):
        loaded_key = PaymentService._load_certificate_public_key(str(self.alipay_cert_path))

        self.assertEqual(loaded_key.public_numbers(), self.alipay_public_key.public_numbers())

    def test_rejects_raw_public_key_as_alipay_certificate(self):
        public_key_path = Path(self.temp_dir.name) / 'raw-alipay-public-key.pem'
        public_key_path.write_bytes(
            self.alipay_public_key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        with self.assertRaisesRegex(ConflictError, 'certificate format is invalid'):
            PaymentService._load_certificate_public_key(str(public_key_path))

    def test_builds_request_with_certificate_serial_numbers(self):

        payment = PaymentService._alipay_build_request_payment(
            self.build_order(),
            self.build_transaction(),
            self.config,
        )

        params = dict(payment['payment_form']['params'], charset=self.config.charset)
        expected_app_sn = md5(
            f'{self.app_certificate.issuer.rfc4514_string()}{self.app_certificate.serial_number}'.encode(),
            usedforsecurity=False,
        ).hexdigest()
        expected_root_sn = md5(
            f'{self.root_certificate.issuer.rfc4514_string()}{self.root_certificate.serial_number}'.encode(),
            usedforsecurity=False,
        ).hexdigest()
        self.assertEqual(params['app_cert_sn'], expected_app_sn)
        self.assertEqual(params['alipay_root_cert_sn'], expected_root_sn)
        signature = base64.b64decode(params.pop('sign'))
        message = PaymentService._alipay_sign_string(params)
        self.public_key.verify(signature, message.encode(), padding.PKCS1v15(), hashes.SHA256())

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
            self.alipay_private_key,
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
            self.alipay_private_key,
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

        with self.assertRaisesRegex(RuntimeError, 'valid unencrypted PEM private key'):
            validate_payment_config(
                'production',
                PaymentConfig(mock_external_payment=False, alipay=self.config),
            )

    def test_requires_alipay_certificate_paths(self):
        config = AlipayConfig(**{**self.config.__dict__, 'alipay_public_cert_path': ''})

        with self.assertRaisesRegex(RuntimeError, 'ALIPAY_PUBLIC_CERT_PATH is required'):
            validate_payment_config(
                'production',
                PaymentConfig(mock_external_payment=False, alipay=config),
            )
