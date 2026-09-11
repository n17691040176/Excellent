> 状态更新（2026-09-10）：下列九项问题已完成代码修复和本地验证，详见 [修复与验收记录](fix_20260910_city_partner.md)。本文保留修复前的证据与行号，不代表当前代码仍有相同行为；历史异常账务不自动调整。

本次检查覆盖 2026-09-09 的 `4c38e65`（城市合伙人分润模式），以及 2026-09-10 的 `b9d9f9b`（公司、运维内部账户），对比基线为 `79c012b`。

结论：新功能尚未形成完整的业务闭环，建议修复下列问题后再启用真实资金结算。这是基于代码及隔离复现作出的验收判断，不代表已经发现线上资金损失。

验证结果：后端 `python -m pytest tests -q --disable-warnings --tb=short` 为 230 passed、2 subtests passed；后台 `npm run build` 成功，有资源包体积提示。现有测试中未发现覆盖城市合伙人或模式切换的测试。额外复现使用内存 SQLite、真实 ORM 和服务方法；退款案例替换了库存、支付渠道和附属奖励操作，因此验证的是本地退款状态与席位的一致性，不是支付渠道实际退钱。未执行线上数据库操作，也未验证 MySQL 并发锁或真实支付回调。

**1. [P1] 普通商品订单可用于获取席位，同一订单还能跨城市重复使用。已复现。**

位置：[city_partner_service.py:142](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/city_partner_service.py:142)。这里只检查订单归属、已支付和金额相等；重复校验限定为 `(seat_id, order_id)`，数据库唯一约束也是这个组合，没有专用席位订单及全局订单消费约束。

实测：一笔 1,000 元的 `NORMAL_PRODUCT` 订单成功取得两个初始价格同为 1,000 元的城市席位，上级佣金累计增加 200 元。商品履约和席位权益共享了同一笔支付，重复处理还会放大实际负债。

建议：建立明确绑定席位、报价版本的专用购买订单，验证支付用途，并对席位结算的 `order_id` 单独实施唯一约束。

**2. [P1] 席位购买订单退款后，席位和轮换奖励未冲正。已复现。**

位置：[city_partner_service.py:218](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/city_partner_service.py:218)、[order_service.py:630](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/order_service.py:630)。席位购买只记录当前用户及轮换流水，通用退款流程未检查或处理席位结算。

实测：取得席位后调用本地退款流程，订单变为 `REFUND`，席位持有人仍是原买家，轮换流水仍为 `SUCCESS`。这会允许本地退款状态与继续持有席位、已获奖励并存。

建议：将席位订单纳入独立退款规则；若普通退款不允许，应在发起支付渠道退款前拒绝；特殊退款需要完整冲正本金、奖励、账户和席位状态。设计文档对此仍有待确认项，不能直接套用商品退款。

**3. [P1] CITY_PARTNER 订单仍会支付旧市级代理奖励。已复现。**

位置：[order_service.py:713](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/order_service.py:713)、[region_dividend_service.py:28](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/region_dividend_service.py:28)。新分支只隔离了 `CommissionService.freeze_for_order`，完成订单时的区域代理奖励入口仍无模式判断。

实测：给新模式已完成订单配置旧市代理固定奖励 5 元及有效市代理后，真实区域奖励服务仍生成并结算一笔 5 元流水。触发条件是商品保留旧区域代理规则；这恰好是模式切换兼容场景。

建议：区域代理发奖入口按订单已锁定模式隔离；历史原模式订单保留现有结算与退款行为。

**4. [P1] 公司、运维收入只有轮换流水数字，没有实际账户入账。已复现。**

位置：[city_partner_service.py:123](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/city_partner_service.py:123)、[city_partner_service.py:177](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/city_partner_service.py:177)。今天新增的 `_credit_system_account` 没有调用点，购买逻辑只给上一任和新买家上级入账。

实测：预先配置 COMPANY 和 OPERATIONS 用户及佣金账户；席位从 1,000 元轮换到 1,200 元时，流水记公司 60 元、运维 40 元，两者账户余额仍为 0。首购公司的分配也有同类缺口。

建议：在同一事务中完成分配入账及可追溯账本；明确内部账户缺失时的处理，避免成功流水掩盖未入账金额。

**5. [P1] 保存的新模式商品规则回显为默认值，再次保存会覆盖原配置。已复现回显错误。**

位置：[catalog_service.py:746](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/catalog_service.py:746)。序列化先遍历旧配置默认字段，再对新字段直接 `setdefault`；新字段没有从数据库对象读取。

实测：数据库中 `city_partner_commission_enabled=True`、`city_partner_amount=100`，接口使用的序列化结果返回 `False` 和 `0.0`。前端重新打开表单会读取这些默认值，再保存时发送回服务端，因此会覆盖已配置的新模式规则。

建议：将新字段纳入真实配置序列化，并验证保存、重新读取、再次保存的往返一致性。

**6. [P1] 后端保存规则没有新模式金额和范围校验，错误规则会进入支付结算路径。已复现校验缺失。**

位置：[schemas/product.py:97](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/schemas/product.py:97)、[catalog_service.py:1430](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/catalog_service.py:1430)。金额、层数、递减比例字段缺少范围约束，业务校验仍只覆盖旧分润规则。前端的预计分润校验不能替代服务端约束。

实测：利润池 900 元的商品，配置城市合伙人奖励 999,999 元、递减比例 -50，仍通过服务校验。新结算器直到付款处理时才检查实际分配是否超过利润池，有对应受益人时会抛错，导致支付确认不能正常完成；这里未模拟外部渠道实际扣款。

建议：服务端保存时校验所有数值范围、最大配置分配与利润池，成本或价格变化也应纳入校验。

**7. [P2] 公司尾差流水既不释放，也不随退款取消。已复现。**

位置：[commission_service.py:142](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/commission_service.py:142)、[commission_service.py:187](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/commission_service.py:187)。尾差生成时 `beneficiary_user_id=None`，结算和取消查询却都排除了这一类流水。

实测：200 元公司尾差在订单结算后仍为 `FROZEN`，调用佣金取消后仍为 `FROZEN`。模式状态页的冻结总额会持续包含该金额，公司收益也无法完成生命周期对账。

建议：无用户受益人的内部账户流水也必须执行结算、取消与审计；不要用是否存在用户 ID 决定流水是否需要转换状态。

**8. [P2] 新模式查询与后台模式显示未接通。流水缺失已复现，其余为静态核对。**

位置：[commission_service.py:92](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/commission_service.py:92)、[commission_service.py:363](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/commission_service.py:363)、[CommissionView.vue:256](/D:/Users/admin/Documents/ChatGPT/Excellent/admin-web/src/views/commission/CommissionView.vue:256)。

实测：用户有 3 条城市合伙人商品分润流水，移动端查询使用的 `Commissions.flows` 返回 0 条，因为只查旧 `CommissionFlow`。后台流水查询同样只查旧表；商品规则列表只筛选 `custom_commission_enabled`，没有新规则数据。后台全局模式标签则由商品列表首行推断，未调用已经新增的 `/admin/commission/mode` 接口，因此实际切换后仍会显示原模式。也未发现后台席位管理或移动端席位购买的页面调用。

建议：先接通模式读取和新旧流水查询，再完善模式切换、席位管理和购买入口；全局模式应使用配置接口，不能由商品列表推断。

**9. [P2] 配置递减比例为 0%，后端按 50%执行。已复现。**

位置：[commission_service.py:760](/D:/Users/admin/Documents/ChatGPT/Excellent/server/app/services/commission_service.py:760)。`value or 50` 将合法的零值当作缺失值，而后台允许输入 0，预览也按零计算。

实测：上级起始金额 100 元、两层、比例 0%，实际分出第 1 层 100 元和第 2 层 50 元。按前端预览和当前公式，第 2 层应为 0，存在额外发放或触发利润池超额检查的风险。

建议：仅在值为 `None` 时补默认值，并使前后端计算及舍入规则一致。

修复次序建议：先封住席位支付重复消费和退款缺口，再修模式隔离、账户入账、配置往返和服务端校验，最后补流水查询及页面入口。验收需增加新模式正常结算、缺少上级、模式切换、退款和同城/跨城并发案例；现有测试通过不能证明以上新路径正确。
