"""
商品购买和分销系统测试脚本 - 独立版本

直接使用 SQLAlchemy 创建数据库连接，不依赖应用模块导入
"""

import sys
import time
from decimal import Decimal

sys.path.insert(0, '.')

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, create_engine
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


# ========== 定义模型（匹配实际数据库结构）==========

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=False)
    nickname = Column(String(100))
    password_hash = Column(String(255))
    global_role = Column(String(20), default='USER')
    status = Column(String(20), default='ENABLED')
    member_level = Column(String(20))
    invite_code = Column(String(20), unique=True)
    parent_id = Column(Integer, ForeignKey('users.id'))
    grandparent_id = Column(Integer, ForeignKey('users.id'))
    last_login_at = Column(DATETIME(fsp=6))
    created_at = Column(DATETIME(fsp=6))
    updated_at = Column(DATETIME(fsp=6))


class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    product_name = Column(String(150), nullable=False)
    product_type = Column(String(20))
    sale_price = Column(Numeric(18, 2), nullable=False)
    cost_price = Column(Numeric(18, 2))
    stock = Column(Integer, default=0)
    status = Column(String(20), default='ON_SHELF')
    created_at = Column(DATETIME(fsp=6))
    updated_at = Column(DATETIME(fsp=6))


class ShoppingCartItem(Base):
    __tablename__ = 'shopping_cart_items'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, default=1)
    selected = Column(Boolean, default=True)
    created_at = Column(DATETIME(fsp=6))
    updated_at = Column(DATETIME(fsp=6))


class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    order_no = Column(String(64), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    order_type = Column(String(50), default='NORMAL_PRODUCT')
    zone_type = Column(String(50))
    total_amount = Column(Numeric(18, 2), nullable=False)
    discount_amount = Column(Numeric(18, 2), default=0)
    payable_amount = Column(Numeric(18, 2), nullable=False)
    paid_amount = Column(Numeric(18, 2), nullable=False)
    pay_status = Column(String(20), default='UNPAID')
    order_status = Column(String(32), default='PENDING_PAYMENT')
    paid_at = Column(DATETIME(fsp=6))
    confirmed_at = Column(DATETIME(fsp=6))
    created_at = Column(DATETIME(fsp=6))
    updated_at = Column(DATETIME(fsp=6))


class OrderItem(Base):
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    sku_id = Column(Integer)
    product_name = Column(String(150), nullable=False)
    sku_name = Column(String(100))
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(18, 2), nullable=False)
    total_amount = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DATETIME(fsp=6))


class CommissionFlow(Base):
    __tablename__ = 'commission_flows'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    source_user_id = Column(Integer, ForeignKey('users.id'))
    beneficiary_user_id = Column(Integer, ForeignKey('users.id'))
    level = Column(Integer)
    base_amount = Column(Numeric(18, 2))
    rate = Column(Numeric(10, 2))
    commission_amount = Column(Numeric(18, 2))
    status = Column(String(20), default='FROZEN')
    created_at = Column(DATETIME(fsp=6))
    settled_at = Column(DATETIME(fsp=6))


class UserCommission(Base):
    __tablename__ = 'user_commissions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    total_amount = Column(Numeric(18, 2), default=0)
    frozen_amount = Column(Numeric(18, 2), default=0)
    available_amount = Column(Numeric(18, 2), default=0)
    withdrawn_amount = Column(Numeric(18, 2), default=0)
    updated_at = Column(DATETIME(fsp=6))


# ========== 分销佣金计算（复制业务逻辑）==========

def rate_for_commission_level(level: int) -> Decimal:
    """获取指定分销级别的佣金比例"""
    if level == 1:
        return Decimal('0.15')  # 15%
    elif level == 2:
        return Decimal('0.05')  # 5%
    return Decimal('0')


def quantize_amount(amount: Decimal) -> Decimal:
    """量化金额到2位小数"""
    return amount.quantize(Decimal('0.01'))


def now_str():
    """返回当前时间字符串"""
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


# ========== 数据库连接 ==========

DATABASE_URL = 'mysql+pymysql://excellent:excellent123@127.0.0.1:3306/excellent_app?charset=utf8mb4'
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()


def create_order_no():
    """生成订单号"""
    return f"ORD{int(time.time()*1000)}"


def test_distribution_system():
    """测试分销系统"""
    print("=" * 60)
    print("[TEST] Start Distribution System Test")
    print("=" * 60)

    try:
        # 获取测试商品
        product = db.query(Product).filter(Product.status == 'ON_SHELF').first()
        if not product:
            print("[ERROR] No test product found, please add product data first")
            return

        print(f"\n[PRODUCT] Test Product: {product.product_name} (ID: {product.id})")
        print(f"   Sale Price: {product.sale_price}, Cost Price: {product.cost_price}")

        # 计算预期佣金
        sale_price = Decimal(str(product.sale_price))
        cost_price = Decimal(str(product.cost_price)) if product.cost_price else sale_price * Decimal('0.7')
        profit = sale_price - cost_price
        level1_rate = rate_for_commission_level(1)
        level2_rate = rate_for_commission_level(2)
        expected_level1 = profit * level1_rate
        expected_level2 = profit * level2_rate

        print("\n[CALC] Expected Commission:")
        print(f"   Profit: {profit}")
        print(f"   Level 1 Rate: {level1_rate*100}%, Amount: {expected_level1}")
        print(f"   Level 2 Rate: {level2_rate*100}%, Amount: {expected_level2}")

        # ========== 创建测试用户 ==========
        print("\n[USERS] Creating test users...")

        # 用户A - 顶级用户
        user_a = db.query(User).filter(User.phone == '13800000011').first()
        if not user_a:
            user_a = User(
                phone='13800000011',
                nickname='Test User A (Top)',
                password_hash='test',
                global_role='USER',
                status='ENABLED',
                member_level='DEALER',
                invite_code='TESTA011',
                created_at=now_str(),
                updated_at=now_str(),
            )
            db.add(user_a)
            db.flush()

        # 用户B - A的下级
        user_b = db.query(User).filter(User.phone == '13800000012').first()
        if not user_b:
            user_b = User(
                phone='13800000012',
                nickname='Test User B (Middle)',
                password_hash='test',
                global_role='USER',
                status='ENABLED',
                member_level='DEALER',
                invite_code='TESTB012',
                parent_id=user_a.id,
                created_at=now_str(),
                updated_at=now_str(),
            )
            db.add(user_b)
            db.flush()

        # 用户C - B的下级（买家）
        user_c = db.query(User).filter(User.phone == '13800000013').first()
        if not user_c:
            user_c = User(
                phone='13800000013',
                nickname='Test User C (Buyer)',
                password_hash='test',
                global_role='USER',
                status='ENABLED',
                member_level='NORMAL_MEMBER',
                invite_code='TESTC013',
                parent_id=user_b.id,
                grandparent_id=user_a.id,
                created_at=now_str(),
                updated_at=now_str(),
            )
            db.add(user_c)
            db.flush()

        # 初始化用户的佣金账户
        for user in [user_a, user_b, user_c]:
            comm = db.query(UserCommission).filter(UserCommission.user_id == user.id).first()
            if not comm:
                comm = UserCommission(
                    user_id=user.id,
                    total_amount=Decimal('0'),
                    frozen_amount=Decimal('0'),
                    available_amount=Decimal('0'),
                    withdrawn_amount=Decimal('0'),
                    updated_at=now_str()
                )
                db.add(comm)

        db.commit()

        print(f"   [OK] User A (ID:{user_a.id}) - Top Level")
        print(f"   [OK] User B (ID:{user_b.id}) - A's Downline")
        print(f"   [OK] User C (ID:{user_c.id}) - B's Downline (Buyer)")
        print("   Relationship: A -> B -> C")

        # ========== 清理旧测试数据 ==========
        print("\n[CLEAN] Cleaning old test orders...")

        # 删除用户C的测试订单和佣金流水
        db.query(CommissionFlow).filter(CommissionFlow.source_user_id == user_c.id).delete(synchronize_session=False)
        db.query(OrderItem).filter(
            OrderItem.order_id.in_(
                db.query(Order.id).filter(Order.user_id == user_c.id)
            )
        ).delete(synchronize_session=False)
        db.query(Order).filter(Order.user_id == user_c.id).delete(synchronize_session=False)
        db.query(ShoppingCartItem).filter(ShoppingCartItem.user_id == user_c.id).delete(synchronize_session=False)
        db.commit()
        print("   [OK] Cleanup complete")

        # ========== 第一步：添加商品到购物车 ==========
        print("\n[STEP 1] User C adds product to cart...")

        cart_item = db.query(ShoppingCartItem).filter(
            ShoppingCartItem.user_id == user_c.id,
            ShoppingCartItem.product_id == product.id
        ).first()

        if not cart_item:
            cart_item = ShoppingCartItem(
                user_id=user_c.id,
                product_id=product.id,
                quantity=1,
                selected=True,
                created_at=now_str(),
                updated_at=now_str(),
            )
            db.add(cart_item)
            db.commit()
            db.refresh(cart_item)

        print(f"   [OK] Cart: Product ID={product.id}, Quantity={cart_item.quantity}")

        # ========== 第二步：创建订单 ==========
        print("\n[STEP 2] User C creates order...")

        total_amount = sale_price * cart_item.quantity
        discount_amount = Decimal('0')
        pay_amount = total_amount - discount_amount

        order = Order(
            order_no=create_order_no(),
            user_id=user_c.id,
            order_type='NORMAL_PRODUCT',
            total_amount=quantize_amount(total_amount),
            discount_amount=quantize_amount(discount_amount),
            payable_amount=quantize_amount(pay_amount),
            paid_amount=quantize_amount(pay_amount),
            pay_status='PAID',
            order_status='PENDING_PAYMENT',
            paid_at=now_str(),
            created_at=now_str(),
            updated_at=now_str(),
        )
        db.add(order)
        db.flush()

        # 创建订单项
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.product_name,
            sku_id=None,
            quantity=cart_item.quantity,
            unit_price=sale_price,
            total_amount=total_amount,
            created_at=now_str(),
        )
        db.add(order_item)
        db.commit()
        db.refresh(order)

        print("   [OK] Order created:")
        print(f"      Order No: {order.order_no}")
        print(f"      Order Amount: {order.total_amount}")
        print(f"      Pay Status: {order.pay_status}")
        print(f"      Order Status: {order.order_status}")

        # ========== 第三步：冻结分销佣金 ==========
        print("\n[STEP 3] Freezing distribution commissions...")

        # 获取用户的上级关系
        ancestors = []
        if user_c.parent_id:
            parent = db.query(User).filter(User.id == user_c.parent_id).first()
            if parent:
                ancestors.append((parent, 1))
        if user_c.grandparent_id:
            grandparent = db.query(User).filter(User.id == user_c.grandparent_id).first()
            if grandparent:
                ancestors.append((grandparent, 2))

        print(f"   Found {len(ancestors)} uplines:")

        # 计算每个上级的佣金
        flows = []
        for ancestor, level in ancestors:
            rate = rate_for_commission_level(level)
            commission_amount = profit * rate

            flow = CommissionFlow(
                order_id=order.id,
                source_user_id=user_c.id,
                beneficiary_user_id=ancestor.id,
                level=level,
                base_amount=quantize_amount(profit),
                rate=quantize_amount(rate * 100),  # 存储为百分比
                commission_amount=quantize_amount(commission_amount),
                status='FROZEN',
                created_at=now_str(),
            )
            db.add(flow)
            flows.append(flow)

            # 更新佣金账户（冻结金额）
            user_comm = db.query(UserCommission).filter(UserCommission.user_id == ancestor.id).first()
            if user_comm:
                user_comm.frozen_amount = quantize_amount(Decimal(str(user_comm.frozen_amount or 0)) + commission_amount)
                user_comm.updated_at = now_str()

            level_str = "Level 1" if level == 1 else "Level 2"
            print(f"      {ancestor.nickname} (ID:{ancestor.id}) -> {level_str}")
            print(f"         Base: {profit}, Rate: {rate*100}%, Commission: {commission_amount}")

        db.commit()
        print(f"   [OK] Frozen {len(flows)} commission flows")

        # ========== 第四步：确认订单并结算佣金 ==========
        print("\n[STEP 4] Confirming order and settling commissions...")

        # 更新订单状态为已完成
        order.order_status = 'COMPLETED'
        order.confirmed_at = now_str()
        order.updated_at = now_str()

        # 结算佣金（从冻结转为可用）
        for flow in flows:
            flow.status = 'SETTLED'
            flow.settled_at = now_str()

            # 更新用户佣金账户
            user_comm = db.query(UserCommission).filter(UserCommission.user_id == flow.beneficiary_user_id).first()
            if user_comm:
                user_comm.frozen_amount = quantize_amount(Decimal(str(user_comm.frozen_amount or 0)) - flow.commission_amount)
                user_comm.available_amount = quantize_amount(Decimal(str(user_comm.available_amount or 0)) + flow.commission_amount)
                user_comm.total_amount = quantize_amount(Decimal(str(user_comm.total_amount or 0)) + flow.commission_amount)
                user_comm.updated_at = now_str()

        db.commit()
        print("   [OK] Order confirmed, commissions settled")

        # ========== 第五步：验证佣金状态 ==========
        print("\n[STEP 5] Verifying commission status...")

        flows_after = db.query(CommissionFlow).filter(
            CommissionFlow.order_id == order.id
        ).all()

        print("   Commission flows:")
        for flow in flows_after:
            level_str = "Level 1" if flow.level == 1 else "Level 2"
            status_str = "FROZEN" if flow.status == "FROZEN" else "SETTLED"
            print(f"      User {flow.beneficiary_user_id} -> {level_str}: {flow.commission_amount} ({status_str})")

        # ========== 第六步：验证用户佣金账户 ==========
        print("\n[STEP 6] Verifying user commission accounts...")

        for user_id, user_name, expected_commission in [
            (user_a.id, 'User A', expected_level2),
            (user_b.id, 'User B', expected_level1),
            (user_c.id, 'User C', Decimal('0')),
        ]:
            comm = db.query(UserCommission).filter(UserCommission.user_id == user_id).first()
            if comm:
                print(f"   {user_name} (ID:{user_id}):")
                print(f"      Total: {comm.total_amount}")
                print(f"      Frozen: {comm.frozen_amount}")
                print(f"      Available: {comm.available_amount}")

                # 验证准确性
                actual_total = Decimal(str(comm.total_amount or 0))
                diff = abs(actual_total - expected_commission)
                status = "[OK]" if diff < 0.01 else "[FAIL]"
                print(f"      Verify: {status} (Expected: {expected_commission})")

        # ========== 第七步：验证订单统计 ==========
        print("\n[STEP 7] Verifying order statistics...")

        buyer_orders = db.query(Order).filter(Order.user_id == user_c.id).all()
        total_spent = sum(Decimal(str(o.total_amount or 0)) for o in buyer_orders if o.pay_status == 'PAID')

        print("   User C Order Stats:")
        print(f"      Total Orders: {len(buyer_orders)}")
        print(f"      Paid Orders: {len([o for o in buyer_orders if o.pay_status == 'PAID'])}")
        print(f"      Total Spent: {total_spent}")

        # ========== 最终验证 ==========
        print("\n" + "=" * 60)
        print("[RESULT] Final Verification")
        print("=" * 60)

        # 检查佣金计算准确性
        level1_correct = False
        level2_correct = False

        for flow in flows_after:
            actual = Decimal(str(flow.commission_amount))
            if flow.beneficiary_user_id == user_b.id:
                diff = abs(actual - expected_level1)
                level1_correct = diff < 0.01
                print(f"   {'[OK]' if level1_correct else '[FAIL]'} Level 1 Commission: Expected {expected_level1}, Actual {actual}")
            elif flow.beneficiary_user_id == user_a.id:
                diff = abs(actual - expected_level2)
                level2_correct = diff < 0.01
                print(f"   {'[OK]' if level2_correct else '[FAIL]'} Level 2 Commission: Expected {expected_level2}, Actual {actual}")

        print("\n" + "=" * 60)
        if level1_correct and level2_correct:
            print("[PASS] Distribution System Test PASSED!")
        else:
            print("[FAIL] Distribution System Test FAILED!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    test_distribution_system()
