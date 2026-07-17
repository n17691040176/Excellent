#!/usr/bin/env python3
"""
全链路测试脚本
从注册登录 → 后台发布商品 → 上架 → 移动端购买 → 收藏/足迹 → 订单/支付 → 资产记录
"""
import random
import time

import requests

BASE_URL = "http://localhost:8000/api/v1"


def gen_phone():
    return f"138{random.randint(10000000, 99999999)}"


def get_headers(token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def print_step(title):
    print(f"\n{'='*60}")
    print(f"STEP: {title}")
    print('='*60)


def print_result(label, data):
    try:
        print(f"  [{label}] {data}")
    except UnicodeEncodeError:
        print(f"  [{label}] {data.encode('utf-8', errors='replace').decode('utf-8')}")


def assert_result(resp, expected_code=0):
    try:
        data = resp.json()
    except Exception as exc:
        # Handle non-JSON response
        text = resp.text
        try:
            text = text.encode('utf-8', errors='replace').decode('utf-8')
        except Exception:
            text = repr(text)
        print(f"  [FAIL] {resp.status_code} Response: {text[:500]}")
        raise Exception(f"API returned non-JSON response: {text[:200]}") from exc
    if resp.status_code != 200 or data.get("code") != expected_code:
        msg = data.get('message', 'Unknown error')
        try:
            print(f"  [FAIL] {resp.status_code} {msg}")
        except UnicodeEncodeError:
            print(f"  [FAIL] {resp.status_code}")
        raise Exception(f"API failed: {msg}")
    return data


class ChainTest:
    def __init__(self):
        self.admin_token = None
        self.user_token = None
        self.admin_phone = "18800000000"
        self.admin_password = "Admin@123"
        self.test_user_phone = None
        self.test_product_id = None
        self.test_order_id = None

    def run(self):
        print("\n" + "=" * 50)
        print("开始全链路测试")
        print("=" * 50)

        try:
            self.test_1_admin_login()
            self.test_2_create_product()
            self.test_3_submit_review()
            self.test_4_audit_product()
            self.test_5_onshelf_product()
            self.test_6_user_register()
            self.test_7_user_login()
            self.test_8_add_favorite()
            self.test_9_add_footprint()
            self.test_10_list_favorites()
            self.test_11_list_footprints()
            self.test_12_check_asset_summary()
            self.test_13_create_order()
            self.test_14_preview_order()
            self.test_15_pay_order()
            self.test_16_check_order_status()
            self.test_17_admin_ship_order()
            self.test_18_admin_confirm_order()
            self.test_19_user_confirm_order()
            self.test_20_check_all_assets()
            self.test_21_asset_ledgers()
            self.test_22_sign_in()

            print("\n" + "=" * 50)
            print("全部链路测试通过!")
            print("=" * 50)
        except Exception as e:
            print(f"\n测试失败: {e}")
            raise

    # ==================== 管理员流程 ====================

    def test_1_admin_login(self):
        """管理员登录"""
        print_step("1. 管理员登录")
        resp = requests.post(
            f"{BASE_URL}/auth/admin-login",
            json={"phone": self.admin_phone, "password": self.admin_password},
            headers=get_headers()
        )
        data = assert_result(resp)
        self.admin_token = data["data"]["access_token"]
        print_result("管理员登录成功", f"Token: {self.admin_token[:20]}...")

    def test_2_create_product(self):
        """创建商品（DRAFT 状态）"""
        print_step("2. 创建商品（草稿状态）")
        product_name = f"测试商品_{int(time.time())}"
        resp = requests.post(
            f"{BASE_URL}/admin/products",
            json={
                "product_name": product_name,
                "product_type": "PHYSICAL",
                "zone_type": "SELF_OPERATED",
                "owner_type": "SELF_OPERATED",
                "owner_id": None,
                "sale_price": 99.99,
                "market_price": 199.99,
                "cost_price": 50.00,
                "stock": 100,
                "brand": "测试品牌",
                "profile": "这是一个测试商品的简介",
                "feature": "热销爆款 支持发货",
                "requires_shipping": True,
                "drop_shipping_enabled": False,
            },
            headers=get_headers(self.admin_token)
        )
        data = assert_result(resp)
        self.test_product_id = data["data"]["id"]
        print_result("商品创建成功", f"ID: {self.test_product_id}, 名称: {product_name}")
        print_result("当前状态", data["data"]["status"])

    def test_3_submit_review(self):
        """提交审核"""
        print_step("3. 提交商品审核")
        resp = requests.patch(
            f"{BASE_URL}/admin/products/{self.test_product_id}/submit-review",
            headers=get_headers(self.admin_token)
        )
        data = assert_result(resp)
        print_result("提交审核成功", f"状态: {data['data']['status']}")

    def test_4_audit_product(self):
        """审核通过"""
        print_step("4. 审核通过商品")
        resp = requests.patch(
            f"{BASE_URL}/admin/products/{self.test_product_id}/audit",
            json={"audit_status": "APPROVED"},
            headers=get_headers(self.admin_token)
        )
        data = assert_result(resp)
        print_result("审核通过", f"状态: {data['data']['status']}")

    def test_5_onshelf_product(self):
        """上架商品"""
        print_step("5. 上架商品")
        resp = requests.patch(
            f"{BASE_URL}/admin/products/{self.test_product_id}/status",
            json={"status": "ON_SHELF"},
            headers=get_headers(self.admin_token)
        )
        data = assert_result(resp)
        print_result("上架成功", f"状态: {data['data']['status']}")

    # ==================== 用户流程 ====================

    def test_6_user_register(self):
        """用户注册"""
        print_step("6. 用户注册")
        self.test_user_phone = gen_phone()
        # 获取管理员的邀请码
        resp = requests.get(
            f"{BASE_URL}/users/me",
            headers=get_headers(self.admin_token)
        )
        admin_data = resp.json()
        invite_code = admin_data.get("data", {}).get("invite_code", "")

        resp = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "phone": self.test_user_phone,
                "password": "test123456",
                "nickname": f"测试用户_{self.test_user_phone[-4:]}",
                "invite_code": invite_code
            },
            headers=get_headers()
        )
        data = assert_result(resp)
        self.user_token = data["data"]["access_token"]
        print_result("注册成功", f"手机: {self.test_user_phone}")
        print_result("用户Token", f"{self.user_token[:20]}...")

    def test_7_user_login(self):
        """用户登录"""
        print_step("7. 用户登录")
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"phone": self.test_user_phone, "password": "test123456"},
            headers=get_headers()
        )
        data = assert_result(resp)
        self.user_token = data["data"]["access_token"]
        print_result("登录成功", f"Token: {self.user_token[:20]}...")

    def test_8_add_favorite(self):
        """添加收藏"""
        print_step("8. 添加商品收藏")
        resp = requests.post(
            f"{BASE_URL}/app/commerce/products/{self.test_product_id}/favorite",
            headers=get_headers(self.user_token)
        )
        data = assert_result(resp)
        print_result("收藏成功", f"商品ID: {data['data']['product_id']}")

    def test_9_add_footprint(self):
        """添加足迹"""
        print_step("9. 添加商品足迹")
        resp = requests.post(
            f"{BASE_URL}/app/commerce/products/{self.test_product_id}/footprint",
            headers=get_headers(self.user_token)
        )
        data = assert_result(resp)
        print_result("足迹记录成功", f"商品ID: {data['data']['product_id']}")

    def test_10_list_favorites(self):
        """查看收藏列表"""
        print_step("10. 查看收藏列表")
        resp = requests.get(
            f"{BASE_URL}/app/commerce/favorites",
            headers=get_headers(self.user_token)
        )
        data = assert_result(resp)
        favorites = data["data"]
        print_result("收藏数量", len(favorites))
        for item in favorites[:3]:
            print_result("  -", f"商品: {item['product_name']}, 价格: RMB{item['sale_price']}")

    def test_11_list_footprints(self):
        """查看足迹列表"""
        print_step("11. 查看足迹列表")
        resp = requests.get(
            f"{BASE_URL}/app/commerce/footprints",
            headers=get_headers(self.user_token)
        )
        data = assert_result(resp)
        footprints = data["data"]
        print_result("足迹数量", len(footprints))
        for item in footprints[:3]:
            print_result("  -", f"商品: {item['product_name']}, 价格: RMB{item['sale_price']}")

    def test_12_check_asset_summary(self):
        """查看资产总览"""
        print_step("12. 查看用户资产总览")
        resp = requests.get(
            f"{BASE_URL}/app/assets/summary",
            headers=get_headers(self.user_token)
        )
        data = assert_result(resp)
        assets = data["data"]
        print_result("余额", f"RMB{assets.get('balance', 0)}")
        print_result("积分", assets.get('points', 0))
        print_result("消费金", assets.get('voucher', 0))
        print_result("AI券", assets.get('ai_coupon', 0))
        print_result("充电宝", assets.get('power_bank', 0))

    def test_13_create_order(self):
        """创建订单"""
        print_step("13. 创建订单")
        resp = requests.post(
            f"{BASE_URL}/app/orders",
            json={
                "order_type": "SELF_OPERATED_ORDER",
                "zone_type": "SELF_OPERATED",
                "items": [{"product_id": self.test_product_id, "quantity": 1}],
                "pay_channel": "WECHAT",
                "asset_deductions": []
            },
            headers=get_headers(self.user_token)
        )
        data = assert_result(resp)
        order = data["data"]
        self.test_order_id = order["id"]
        print_result("订单创建成功", f"订单ID: {self.test_order_id}, 订单号: {order['order_no']}")
        print_result("订单状态", order['order_status'])
        print_result("应付金额", f"RMB{order['payable_amount']}")
        print_result("支付状态", order['pay_status'])

    def test_14_preview_order(self):
        """预览订单支付"""
        print_step("14. 预览订单支付方案")
        resp = requests.post(
            f"{BASE_URL}/app/orders/preview",
            json={
                "order_type": "SELF_OPERATED_ORDER",
                "zone_type": "SELF_OPERATED",
                "items": [{"product_id": self.test_product_id, "quantity": 1}],
                "pay_channel": "WECHAT",
                "asset_deductions": []
            },
            headers=get_headers(self.user_token)
        )
        data = assert_result(resp)
        preview = data["data"]
        print_result("支付预览", f"总金额: RMB{preview['total_amount']}, 应付: RMB{preview['cash_due']}")
        print_result("支付方式", preview.get('pay_channel'))
        print_result("支付选项", preview.get('pay_channel_options'))

    def test_15_pay_order(self):
        """支付订单（Demo 模拟支付）"""
        print_step("15. 支付订单（Demo 模拟支付）")
        resp = requests.post(
            f"{BASE_URL}/app/orders/{self.test_order_id}/pay-demo",
            headers=get_headers(self.user_token)
        )
        data = assert_result(resp)
        order = data["data"]
        print_result("支付结果", "success")
        print_result("订单状态", order['order_status'])
        print_result("支付状态", order['pay_status'])

    def test_16_check_order_status(self):
        """查看订单状态"""
        print_step("16. 查看订单状态")
        resp = requests.get(
            f"{BASE_URL}/app/orders/{self.test_order_id}",
            headers=get_headers(self.user_token)
        )
        data = assert_result(resp)
        order = data["data"]
        print_result("订单号", order['order_no'])
        print_result("订单状态", order['order_status'])
        print_result("支付状态", order['pay_status'])
        print_result("物流状态", order.get('delivery_status', 'N/A'))

    def test_17_admin_ship_order(self):
        """后台发货（如果订单还不是已发货状态才执行）"""
        print_step("17. 后台发货")
        # 先检查订单状态
        resp = requests.get(
            f"{BASE_URL}/app/orders/{self.test_order_id}",
            headers=get_headers(self.user_token)
        )
        data = resp.json()
        current_status = data.get("data", {}).get("order_status", "")

        if current_status == "SHIPPED":
            print_result("跳过", f"订单已发货 (状态: {current_status})")
            return

        resp = requests.post(
            f"{BASE_URL}/admin/orders/{self.test_order_id}/ship",
            params={"tracking_no": "SF1234567890", "tracking_company": "顺丰速运"},
            headers=get_headers(self.admin_token)
        )
        data = assert_result(resp)
        order = data["data"]
        print_result("发货成功", f"状态: {order['order_status']}, 物流: {order.get('tracking_no')}")

    def test_18_admin_confirm_order(self):
        """后台确认收货（如果订单还不是已完成状态才执行）"""
        print_step("18. 后台确认收货")
        resp = requests.get(
            f"{BASE_URL}/app/orders/{self.test_order_id}",
            headers=get_headers(self.user_token)
        )
        data = resp.json()
        current_status = data.get("data", {}).get("order_status", "")

        if current_status == "COMPLETED":
            print_result("跳过", f"订单已完成 (状态: {current_status})")
            return

        resp = requests.post(
            f"{BASE_URL}/admin/orders/{self.test_order_id}/confirm",
            headers=get_headers(self.admin_token)
        )
        data = assert_result(resp)
        order = data["data"]
        print_result("确认收货成功", f"状态: {order['order_status']}")

    def test_19_user_confirm_order(self):
        """用户确认收货（如果订单还不是已完成状态才执行）"""
        print_step("19. 用户确认收货")
        resp = requests.get(
            f"{BASE_URL}/app/orders/{self.test_order_id}",
            headers=get_headers(self.user_token)
        )
        data = resp.json()
        current_status = data.get("data", {}).get("order_status", "")

        if current_status == "COMPLETED":
            print_result("跳过", f"订单已完成 (状态: {current_status})")
            return

        resp = requests.post(
            f"{BASE_URL}/app/orders/{self.test_order_id}/confirm",
            headers=get_headers(self.user_token)
        )
        data = assert_result(resp)
        order = data["data"]
        print_result("用户确认收货成功", f"状态: {order['order_status']}")

    def test_20_check_all_assets(self):
        """查看所有资产账户"""
        print_step("20. 查看所有资产账户")
        asset_types = ["balance", "points", "voucher", "ai_coupon", "power_bank"]
        for asset_type in asset_types:
            resp = requests.get(
                f"{BASE_URL}/app/assets/{asset_type}",
                headers=get_headers(self.user_token)
            )
            data = assert_result(resp)
            account = data["data"]
            total = account.get("total_amount", 0)
            available = account.get("available_amount", 0)
            print_result(f"{asset_type}", f"总额: {total}, 可用: {available}")

    def test_21_asset_ledgers(self):
        """查看资产流水记录"""
        print_step("21. 查看各类型资产流水记录")
        asset_types = ["balance", "points", "voucher", "ai_coupon"]
        for asset_type in asset_types:
            resp = requests.get(
                f"{BASE_URL}/app/assets/{asset_type}/ledgers",
                params={"page_size": 5},
                headers=get_headers(self.user_token)
            )
            data = assert_result(resp)
            ledgers = data["data"]
            print_result(f"{asset_type} 流水", f"共 {len(ledgers)} 条记录")
            for ledger in ledgers[:3]:
                action = ledger.get('action_type', ledger.get('action'))
                amount = ledger.get('amount', 0)
                print_result("  -", f"{action}: {amount}")

    def test_22_sign_in(self):
        """签到测试"""
        print_step("22. 每日签到")
        resp = requests.post(
            f"{BASE_URL}/app/assets/signin",
            headers=get_headers(self.user_token)
        )
        data = assert_result(resp)
        sign_result = data["data"]
        print_result("签到成功", f"获得: {sign_result.get('points', 0)} 积分")
        print_result("连续签到", f"{sign_result.get('consecutive_days', 1)} 天")


if __name__ == "__main__":
    test = ChainTest()
    test.run()
