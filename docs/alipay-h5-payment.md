# Alipay H5 Payment

This project is embedded as H5 inside a host App, so the payment flow uses
`alipay.trade.wap.pay`. It does not depend on `uni.requestPayment`, which is a
native App capability.

## Backend configuration

Set these variables in the server environment. Do not commit private keys or
the Alipay public key to Git.

```dotenv
APP_ENV=production
PAYMENT_MOCK_EXTERNAL_PAYMENT=false

ALIPAY_ENABLED=true
ALIPAY_APP_ID=your_app_id
ALIPAY_PRIVATE_KEY_PATH=/run/secrets/alipay-merchant-private-key.pem
ALIPAY_PUBLIC_KEY_PATH=/run/secrets/alipay-public-key.pem
ALIPAY_NOTIFY_URL=https://your-domain.example/api/v1/payments/alipay/notify
ALIPAY_RETURN_URL=https://your-domain.example/#/subpackages/order/detail
ALIPAY_GATEWAY_URL=https://openapi.alipay.com/gateway.do
ALIPAY_PAYMENT_METHOD=alipay.trade.wap.pay
ALIPAY_SIGN_TYPE=RSA2
ALIPAY_SELLER_ID=
```

For sandbox testing, use the sandbox gateway provided by Alipay and a sandbox
APP-ID/key pair. The notify URL must still be publicly reachable over HTTPS.
The current sandbox template uses:

```dotenv
ALIPAY_GATEWAY_URL=https://openapi-sandbox.dl.alipaydev.com/gateway.do
```

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
5. Alipay redirects the browser to `ALIPAY_RETURN_URL`. This is only a page
   return; the H5 page must reload the order from the backend instead of
   trusting the return query parameters.

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
