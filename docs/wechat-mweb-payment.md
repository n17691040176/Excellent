# 微信支付 H5 MWEB 联调说明

本文只针对普通手机浏览器或 App WebView 中的微信 H5/MWEB 支付。它与
原生 App Pay、微信小程序/公众号 JSAPI 是不同的产品和接口，不能只替换
一个 AppID 就互相通用。

## 适用场景

H5 MWEB 的服务端下单接口是微信支付 API v3 的
`POST /v3/pay/transactions/h5`。服务端应提交订单金额、商户订单号、
回调地址，以及 `scene_info.payer_client_ip` 和 `scene_info.h5_info.type`
（本项目默认使用 `WAP`，对应配置 `WECHAT_PAY_H5_TYPE`）。微信返回短时有效的
`h5_url` 后，浏览器跳转到
该地址完成支付。

H5 页面不要调用 `uni.requestPayment({ provider: 'wxpay' })`；该调用属于
编译后的原生 App 宿主能力。微信内网页需要 JSAPI 流程和用户 `openid`，
小程序需要小程序支付流程，均应另行设计。

## 开发阶段配置

开发或尚未拿到商户资料时，保持微信关闭并留空敏感参数：

```dotenv
APP_ENV=development
PAYMENT_MOCK_EXTERNAL_PAYMENT=true

WECHAT_PAY_ENABLED=false
WECHAT_PAY_APP_ID=
WECHAT_PAY_MCHID=
WECHAT_PAY_API_V3_KEY=
WECHAT_PAY_MERCHANT_SERIAL_NO=
WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH=
WECHAT_PAY_PLATFORM_CERT_PATH=
WECHAT_PAY_NOTIFY_URL=
WECHAT_PAY_REFUND_NOTIFY_URL=
WECHAT_PAY_H5_TYPE=WAP
WECHAT_PAY_H5_RETURN_URL=
WECHAT_PAY_APP_SUBJECT_PREFIX=Excellent
```

本地开发请使用这份开发配置，或把它放进后端实际会读取的 `server/.env` /
`server/.env.alipay.local`（这两个运行时文件均不应提交）；不要直接把生产支付
模板覆盖到本地环境文件。若两个文件同时存在，当前设置加载顺序是
`.env.alipay.local` 覆盖 `.env`，因此必须在后者也保持开发值，或在启动进程前显式
设置 `APP_ENV`、`PAYMENT_MOCK_EXTERNAL_PAYMENT`、`ALIPAY_ENABLED` 和
`WECHAT_PAY_ENABLED` 环境变量。

`PAYMENT_MOCK_EXTERNAL_PAYMENT=true` 只用于本地演示和自动化测试，不会访问
微信接口。不要把 API v3 Key、商户私钥或平台证书放进前端环境变量、镜像或
Git。生产 Compose 通过 `PAYMENT_ENV_FILE`（兼容旧的 `ALIPAY_ENV_FILE`）
将运行时 env 文件注入后端；密钥目录通过 `PAYMENT_SECRETS_DIR` 只读挂载到
容器的 `/run/secrets`。使用 `./deploy.sh` 时脚本会把两个解析后的路径导出给
Compose；若直接运行 `docker compose`，必须把 `PAYMENT_ENV_FILE`（或兼容的
`ALIPAY_ENV_FILE`）和
`PAYMENT_SECRETS_DIR` 放在根 `.env` 中，因为 Compose 不会从 `env_file` 内容
反向插值宿主机挂载路径。

如果要在没有商户资料时预览微信支付选项，可以只把开发环境的
`WECHAT_PAY_ENABLED` 临时改为 `true`，继续保持 `PAYMENT_MOCK_EXTERNAL_PAYMENT=true`
以及其余微信参数为空；此时请求不会访问微信，订单会走模拟支付，不代表真实
商户配置已经就绪。

## 生产参数清单

只有在目标端、回调验签和查单流程都完成后，才将微信开关改为 `true`。以下
示例故意使用占位符，不要原样部署：

```dotenv
APP_ENV=production
PAYMENT_MOCK_EXTERNAL_PAYMENT=false
PAYMENT_DEFAULT_CURRENCY=CNY

WECHAT_PAY_ENABLED=true
WECHAT_PAY_APP_ID=填写与商户产品绑定的应用或公众号 AppID
WECHAT_PAY_MCHID=填写微信支付商户号
WECHAT_PAY_API_V3_KEY=填写 32 字节 API v3 Key
WECHAT_PAY_MERCHANT_SERIAL_NO=填写商户证书序列号
WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH=/run/secrets/wechat-merchant-private-key.pem
WECHAT_PAY_PLATFORM_CERT_PATH=/run/secrets/wechat-platform-cert.pem
WECHAT_PAY_NOTIFY_URL=https://pay.example.com/api/v1/payments/wechat/notify
WECHAT_PAY_REFUND_NOTIFY_URL=https://pay.example.com/api/v1/payments/wechat/refund-notify
WECHAT_PAY_H5_TYPE=WAP
WECHAT_PAY_H5_RETURN_URL=https://pay.example.com/#/subpackages/order/detail
WECHAT_PAY_APP_SUBJECT_PREFIX=Excellent
```

旧部署若仍使用 `WECHAT_PAY_H5_INFO_TYPE` 或
`WECHAT_PAY_H5_REDIRECT_URL` 可以暂时保留；新配置应使用上面的主变量。

其中 API v3 Key 必须是微信商户平台生成的 32 字节密钥，不是商户证书序列号，
也不是 AppSecret。商户私钥和微信支付平台证书应放在宿主机的
`PAYMENT_SECRETS_DIR` 中，再以 `/run/secrets/<filename>` 的容器路径填写。

## 商户平台设置

1. 在微信支付商户平台完成 H5 支付产品开通，并绑定实际使用的应用/公众号
   与商户号。
2. 在商户平台的 H5 支付域名配置中登记最终用户访问的公网域名。填写域名，
   不要填写 `localhost`、内网地址、IP、端口或带路径的 URL；域名必须与实际
   H5 页面访问域名一致，并满足微信平台的备案和安全要求。
3. 下载当前环境对应的商户 API 证书、商户私钥和微信支付平台证书，核对商户
   证书序列号后再放入只读密钥目录。平台证书轮换后要同步替换并重建后端容器。
4. 确认 H5 域名和通知域名都能从公网通过有效 TLS 证书访问。仓库内 Nginx
   只负责 HTTP 转发，生产 HTTPS 终止需要由宿主机 Nginx、网关或负载均衡器
   提供。

## 回调与回跳

支付通知地址固定为：

```text
https://<公网域名>/api/v1/payments/wechat/notify
```

网关必须原样转发 `POST` 请求体和以下请求头：
`Wechatpay-Timestamp`、`Wechatpay-Nonce`、`Wechatpay-Signature`、
`Wechatpay-Serial`。服务端要先用对应平台证书验证签名和时间窗口，再使用
API v3 Key 解密 `resource`，并校验商户号、AppID、订单号、金额、币种和支付
状态。重复通知应幂等处理；不能用浏览器回跳参数直接判定已支付。

H5 `h5_url` 可按微信接口要求追加经过 URL 编码的 `redirect_url`，将用户带回
订单详情页，例如：

```text
https://pay.example.com/#/subpackages/order/detail?id=123
```

回跳只负责展示和触发一次状态刷新，支付结果以服务端通知或服务端查单为准。
回跳地址必须使用 HTTPS，并在微信平台允许的域名范围内；不要把商户私钥、
API v3 Key 或未签名的金额字段放进 URL。

## 退款闭环

当前实现只支持对一笔已完成微信支付做全额退款，金额由服务端支付流水决定，
客户端不能传入退款金额。用户和管理端均通过订单退款接口发起请求；可在请求头
中传入 `Idempotency-Key`，同一笔微信支付始终复用同一个 `out_refund_no`，不会
因网络超时创建第二笔微信退款。

```text
POST /api/v1/app/orders/{order_id}/refund
POST /api/v1/admin/orders/{order_id}/refund
POST /api/v1/app/orders/{order_id}/refund-status
POST /api/v1/admin/orders/{order_id}/refund-status
```

退款提交和状态查询都会返回订单与退款单。`completed=false`、退款单状态为
`PROCESSING` 时，微信侧结果尚未确定，本地订单仍保持已支付状态，不能发货或
确认收货；使用 `refund-status` 按原退款号查单即可继续同步。只有微信返回
`SUCCESS` 后，系统才会一次性更新订单、退回库存和资产抵扣，并撤销佣金、奖励
与区域分红。重复请求、重复通知和重复查单不会重复执行这些副作用。

真实微信支付启用时，服务进程还会每 60 秒扫描已到重试时间的 `PENDING` 和
`PROCESSING` 退款：前者使用原 `out_refund_no` 重新提交，后者向微信查单。因而
退款通知丢失或短暂网络失败会自行收敛，无需依赖单独部署的任务队列；模拟支付和
关闭微信支付时不会发起外部请求。

退款通知地址固定为：

```text
https://<公网域名>/api/v1/payments/wechat/refund-notify
```

将此地址填入 `WECHAT_PAY_REFUND_NOTIFY_URL`。它不能带 query 或 fragment；
生产环境必须使用 HTTPS。网关同样必须原样转发支付通知所列的四个
`Wechatpay-*` 验签头和请求体。服务端只接受 `REFUND.SUCCESS`、
`REFUND.ABNORMAL`、`REFUND.CLOSED`，验签、解密、退款号、支付流水号、金额和
币种任一不匹配时不会确认通知，以便微信重试。

对于订单取消后才到达、或另一笔支付已经完成订单后才到达的已验证微信成功通知，
系统会先保留该支付流水，再自动创建并提交同一笔全额原路退款。若微信暂时返回
`PROCESSING`，退款通知和原退款号查单会继续收敛状态；退款成功只校正这笔迟到
流水，不会重复退库存、资产或改变已由另一笔支付完成的订单。

支付宝的真实退款 API 仍不在本次范围内，真实支付宝支付的退款会继续被拒绝，
不能把它当作微信退款能力的一部分。

## 联调顺序

1. 用 `PAYMENT_MOCK_EXTERNAL_PAYMENT=true` 验证订单创建、支付选项和前端
   状态展示，确认不会触发真实微信请求。
2. 准备测试商户资料后，将参数放入 `PAYMENT_ENV_FILE` 指向的运行时文件，
   私钥/平台证书放入 `PAYMENT_SECRETS_DIR`，重建后端容器。
3. 先用小额订单验证 H5 域名、`h5_url` 跳转和 HTTPS 通知，再验证重复通知、
   延迟通知、订单超时和查单恢复。
4. 最后再在管理后台打开商品级微信支付开关，并观察支付流水、订单状态和
   退款/售后流程。任何一个环节未完成，都应保持 `WECHAT_PAY_ENABLED=false`。

当前代码已覆盖收款、支付通知验签、支付查单、全额退款、退款查单和退款通知
幂等。上线前仍应先用小额订单演练 `PROCESSING`、超时、重复通知、订单取消后
晚到支付和退款成功后的订单副作用，再打开商品级微信支付开关。

## 常见配置错误

- 把原生 App Pay 的 `requestPayment` 参数用于 H5，导致页面没有可跳转的
  `h5_url`。
- 把商户号、证书序列号或 AppSecret 当作 API v3 Key；API v3 Key 必须是 32
  字节。
- 回调 URL 使用 IP、HTTP、内网地址或带错路径，微信无法通知。
- 只修改根目录 `.env`，却没有把变量放入 Compose 的 `PAYMENT_ENV_FILE`，
  导致容器仍读取旧配置。
- 仅依据前端回跳显示“支付成功”，没有等待服务端通知或查单确认。
