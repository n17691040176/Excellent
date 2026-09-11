# 城市合伙人支付异常与席位报价恢复修复

> 后续增加了固定七层、禁止自我接替及新旧模式隔离修复；最新验证见 [新旧分润隔离报告](isolation_verification_20260910_city_partner.md)。本文所述支付异常处理和报价恢复能力继续保留。

日期：2026-09-10。对应上一轮逻辑核验的两个明确问题。

**支付确认修复**

旧订单售价 1600，商品调为售价 2000、成本 1000 后，新商品规则虽然有效，但旧订单按支付时成本计算仅有 600 元分润池。以前分润校验失败会使支付确认事务失败，订单和渠道交易不能正确记为已付款。

现在先保留付款事实；城市合伙人商品分润在数据库保存点内计算。遇到规则或账户的业务冲突时，全部分润写入回滚，付款记录保留为 PAID，订单进入“已付款，待平台处理”。保留当时的订单售价、商品成本、完整商品规则、城市、持有人、上级关系和失败原因，禁止发货、确认完成以及重新计算分润。重复支付回调不会重复入账，也不读取后续修改的规则。

后台分润页新增“商品订单待处理”表，超级管理员可以查看原因并申请全额退款。退款复用现有订单/渠道流程；只有完成退款的订单才退出待处理列表。移动端显示付款成功、待平台处理和申请退款入口，退款完成后提示清除。无需配送商品发生该异常时，也会暂停自动完成和释放。

本次没有通过降低成本、减少奖励或超发来让冲突订单强行成交。当前处理办法是退款，不提供按新规则补算历史异常订单。使用原有 JSON 快照保存异常证据，无需新增数据库字段；之前未留下的渠道收款记录仍需单独对账，不能由本次代码自动推断。

**席位报价恢复修复**

对报价已经不高于上一笔成交价的席位，在管理员调整增长比例或价格上限后，以上一笔实际成交价重新计算未来报价：

```text
新报价 = 上一笔成交价 × (1 + 调整后的增长比例)
按分向下取整；有上限时取 min(新报价, 上限)
```

例如 1000 首购、1100 封顶接替后，提高上限到 2000，增长率仍为 20%，新报价恢复为 1320。0% 增长成交后改为 20%，也能恢复报价。取消上限同样有效。

正常可购买的已有报价仍保持不变；状态开关不会单独改变报价。报价仍受上限和分精度约束，没有正增值时依然不能同价接替。更新使旧报价版本失效，审计记录保留更新前后的报价、参数和管理员；历史成交价、持有人及资金流水不改动。

**验证**

| 项目 | 结果 |
|---|---|
| 后端完整回归 | 278 passed，2 subtests passed |
| 文档与边界专项 | 29 passed |
| 新增专项回归 | 10 个测试，已计入后端总数 |
| 后台 lint | 通过 |
| Docker 后端、后台、移动端镜像构建 | 通过 |
| Docker 五服务健康检查 | 全部 healthy |
| 本地 MySQL/浏览器交易验证 | 待处理订单 35 退款成功；恢复报价的席位 19，通过订单 38 支付 1320 并完成接替 |
| 权限 | 普通用户、团队管理员不能访问待处理分润列表；浏览器实际请求普通用户返回 403 |

新增回归覆盖配送/无需配送、渠道付款记录、付款快照、重复回调、混合商品校验失败、部分入账回滚、履约限制、退款幂等、退款后列表退出、权限、封顶恢复、取消上限、历史本金不变和审计。

本地页面流程没有出现页面异常或意外 HTTP 错误。仍使用模拟支付，未验证真实微信/支付宝出入金。测试保留带标识的本地记录。

证据文件：

- `logs/local-test/recovery-regression.xml`
- `logs/local-test/recovery-acceptance.xml`
- `logs/local-test/recovery-docker-build.log`
- `logs/local-test/recovery-browser-results.json`
- `logs/local-test/recovery-admin-pending.png`
- `logs/local-test/recovery-mobile-pending.png`

**业务口径边界**

此次没有改变原模式是否允许席位交易、售后等待期、自定义递减取整方式、自己接替自己、积分抵扣的利润口径等规则。成功席位特殊退款仍不支持；其他已结算订单余额不足的冲正问题也不在本次两项修复内。这些内容仍按上一轮报告区分“实现差异”和“文档待定”，不能宣称整份设计已全部达标。

主要文件：[支付与报价回归](/D:/Users/admin/Documents/ChatGPT/Excellent/server/tests/test_city_partner_recovery.py)、[订单服务](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/order_service.py)、[分润服务](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/commission_service.py)、[席位服务](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/city_partner_service.py)、[后台待处理组件](/D:/Users/admin/Documents/ChatGPT/Excellent/admin-web/src/views/commission/FailedSettlementsPanel.vue)。
