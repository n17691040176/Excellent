# Alipay H5 Payment

This project is embedded as H5 inside a host App, so the payment flow uses
`alipay.trade.wap.pay`. It does not depend on `uni.requestPayment`, which is a
native App capability.

## Backend configuration

Set these variables in the server environment. Do not commit private keys or
Alipay certificates to Git. Certificate mode is the only supported mode.

```dotenv
APP_ENV=production
PAYMENT_MOCK_EXTERNAL_PAYMENT=false

ALIPAY_ENABLED=true
ALIPAY_APP_ID=your_app_id
ALIPAY_PRIVATE_KEY_PATH=/run/secrets/alipay-merchant-private-key.pem
ALIPAY_APP_CERT_PATH=/run/secrets/alipay-app-cert.crt
ALIPAY_PUBLIC_CERT_PATH=/run/secrets/alipay-public-cert.crt
ALIPAY_ROOT_CERT_PATH=/run/secrets/alipay-root-cert.crt
ALIPAY_NOTIFY_URL=https://your-domain.example/api/v1/payments/alipay/notify
ALIPAY_RETURN_URL=https://your-domain.example/#/subpackages/order/detail
ALIPAY_GATEWAY_URL=https://openapi.alipay.com/gateway.do
ALIPAY_PAYMENT_METHOD=alipay.trade.wap.pay
ALIPAY_SIGN_TYPE=RSA2
ALIPAY_SANDBOX_ALLOW_UNVERIFIED_QUERY_RESPONSE=false
ALIPAY_SELLER_ID=
```

For sandbox testing, use the sandbox gateway provided by Alipay and a sandbox
APP-ID/key pair. The notify URL must still be publicly reachable over HTTPS.
The current sandbox template uses:

```dotenv
ALIPAY_GATEWAY_URL=https://openapi-sandbox.dl.alipaydev.com/gateway.do
```

If the Alipay sandbox returns a response signed by a key that does not match
its downloaded sandbox platform certificate, the server-side trade query can
use this temporary fallback:

```dotenv
ALIPAY_SANDBOX_ALLOW_UNVERIFIED_QUERY_RESPONSE=true
```

The fallback is accepted only with the exact sandbox gateway URL above. It
applies only to the server-initiated HTTPS trade query; production responses
and inbound notifications still require RSA2 verification. The query result
must still match the local transaction number, amount, and status; the signed
outbound query remains bound to the configured APP-ID.

## Runtime flow

1. The backend creates a unique `out_trade_no` and signs the WAP order with
   the merchant private key. The signed Alipay request includes
   `timeout_express=30m`, matching the backend unpaid-order expiration window.
2. The API returns `payment_form` to the H5 client.
3. H5 creates a POST form in the current WebView and submits it to the Alipay
   gateway.
4. Alipay calls `ALIPAY_NOTIFY_URL`. The backend verifies RSA2, APP-ID,
   seller ID when configured, amount, status, and transaction number before
   marking the order paid.
5. Alipay redirects the browser to `ALIPAY_RETURN_URL`. H5 sends the complete
   signed Alipay return fields to the backend. The backend verifies RSA2,
   APP-ID, seller ID when configured, amount, and the exact local transaction
   before reconciling the order. It never trusts unsigned return fields.
6. If the signed return is unavailable, the order page falls back to
   `alipay.trade.query` and reloads the current order state.

`ALIPAY_PUBLIC_CERT_PATH` must contain the Alipay platform public certificate
downloaded for the same sandbox/production environment. It
must not contain the merchant application certificate or a stale certificate
from another Alipay application. After replacing a mounted certificate,
recreate the backend container so the running process reloads it.

Keep one Alipay runtime configuration file. Set `ALIPAY_ENV_FILE` in the root
`.env` to that file and let Compose load it through `env_file`; do not append a
second sandbox or production block to the root `.env`.

## Unpaid orders

Unpaid non-local-life orders expire after 30 minutes. Expiration currently runs
when the user or admin queries order lists/details. When an order expires, the
backend cancels the local order, closes pending payment transactions, refunds
reserved asset deductions, and restores inventory.

Because Alipay WAP orders now also use `timeout_express=30m`, the provider-side
payment page should stop accepting payment at the same window. If a late notify
arrives for a locally canceled order, the backend will not mark that order paid.

The host App must allow navigation to the Alipay HTTPS domain. If the host
WebView blocks external navigation, the host App needs to intercept the
Alipay gateway URL and open it in its supported browser or native bridge.

## Refunds

The current integration is for collection only. The existing refund API does
not call Alipay's refund API for external payments and will keep rejecting
such refunds until a provider refund flow is implemented. Confirm whether
real Alipay refunds are required before enabling that capability; it should be
implemented with the required certificate-mode credentials and idempotency.
