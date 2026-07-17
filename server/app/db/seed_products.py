"""
商品测试数据脚本
运行方式: python -m app.db.seed_products
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import ProductOwnerType, ProductStatus, ProductType, ZoneType
from app.models.product import Product

# 测试商品数据 - 使用品牌名称作为分类
TEST_PRODUCTS = [
    # 数码电子类
    {
        'product_name': '无线蓝牙耳机 Pro',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('299.00'),
        'market_price': Decimal('399.00'),
        'cost_price': Decimal('180.00'),
        'stock': 100,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '数码电子',
        'profile': '高品质无线蓝牙耳机，支持降噪功能',
        'detail': '采用最新蓝牙5.0技术，续航长达30小时',
        'feature': '降噪 | 续航30小时 | 防水防汗',
        'order_by': 100,
        'is_hot': 1,
    },
    {
        'product_name': '智能手环运动版',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('199.00'),
        'market_price': Decimal('259.00'),
        'cost_price': Decimal('120.00'),
        'stock': 80,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '数码电子',
        'profile': '多功能智能手环，支持心率监测',
        'detail': '24小时心率监测，睡眠追踪，防水50米',
        'feature': '心率监测 | 睡眠追踪 | 防水50米',
        'order_by': 99,
        'is_hot': 1,
    },
    {
        'product_name': '便携式移动电源 20000mAh',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('129.00'),
        'market_price': Decimal('169.00'),
        'cost_price': Decimal('75.00'),
        'stock': 200,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '数码电子',
        'profile': '大容量移动电源，双向快充',
        'detail': '20000mAh大容量，支持双向快充，可同时充三台设备',
        'feature': '20000mAh | 双向快充 | 三口输出',
        'order_by': 98,
        'is_hot': 0,
    },

    # 服饰鞋包类
    {
        'product_name': '休闲运动T恤 男款',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('89.00'),
        'market_price': Decimal('129.00'),
        'cost_price': Decimal('45.00'),
        'stock': 300,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '服饰鞋包',
        'profile': '纯棉透气运动T恤，舒适休闲',
        'detail': '精选纯棉面料，透气舒适，多色可选',
        'feature': '纯棉面料 | 透气舒适 | 多色可选',
        'order_by': 100,
        'is_hot': 1,
    },
    {
        'product_name': '时尚女士手提包',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('259.00'),
        'market_price': Decimal('399.00'),
        'cost_price': Decimal('130.00'),
        'stock': 50,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '服饰鞋包',
        'profile': '简约时尚手提包，适合上班通勤',
        'detail': '优质PU皮面料，经典款式，大容量设计',
        'feature': 'PU皮面料 | 大容量 | 经典款式',
        'order_by': 99,
        'is_hot': 1,
    },
    {
        'product_name': '轻便运动跑鞋',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('199.00'),
        'market_price': Decimal('299.00'),
        'cost_price': Decimal('110.00'),
        'stock': 120,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '服饰鞋包',
        'profile': '轻便透气跑鞋，适合日常运动',
        'detail': 'EVA缓震中底，透气网面设计，防滑耐磨',
        'feature': 'EVA缓震 | 透气网面 | 防滑耐磨',
        'order_by': 98,
        'is_hot': 0,
    },

    # 食品生鲜类
    {
        'product_name': '有机新疆红枣 500g',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('39.00'),
        'market_price': Decimal('59.00'),
        'cost_price': Decimal('20.00'),
        'stock': 500,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '食品生鲜',
        'profile': '正宗新疆若羌红枣，个大饱满',
        'detail': '产地直发，精选特级红枣，营养丰富',
        'feature': '产地直发 | 特级品质 | 营养丰富',
        'order_by': 100,
        'is_hot': 1,
    },
    {
        'product_name': '进口坚果礼盒 1.2kg',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('128.00'),
        'market_price': Decimal('188.00'),
        'cost_price': Decimal('70.00'),
        'stock': 200,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '食品生鲜',
        'profile': '精选六种进口坚果，健康零食',
        'detail': '开心果、碧根果、腰果、夏威夷果、核桃、榛子',
        'feature': '六种坚果 | 健康零食 | 精美礼盒',
        'order_by': 99,
        'is_hot': 1,
    },
    {
        'product_name': '有机五常大米 5kg',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('68.00'),
        'market_price': Decimal('98.00'),
        'cost_price': Decimal('38.00'),
        'stock': 300,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '食品生鲜',
        'profile': '正宗五常大米，有机种植',
        'detail': '东北优质稻米，米粒晶莹，口感软糯',
        'feature': '有机种植 | 东北稻米 | 口感软糯',
        'order_by': 98,
        'is_hot': 0,
    },

    # 美妆护肤类
    {
        'product_name': '保湿滋养面膜 10片装',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('69.00'),
        'market_price': Decimal('99.00'),
        'cost_price': Decimal('35.00'),
        'stock': 400,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '美妆护肤',
        'profile': '深层保湿滋养面膜，补水急救',
        'detail': '蕴含玻尿酸精华，深层补水，修护肌肤',
        'feature': '玻尿酸 | 深层补水 | 修护肌肤',
        'order_by': 100,
        'is_hot': 1,
    },
    {
        'product_name': '控油洁面乳 150ml',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('49.00'),
        'market_price': Decimal('69.00'),
        'cost_price': Decimal('25.00'),
        'stock': 250,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '美妆护肤',
        'profile': '温和控油洁面，清洁毛孔',
        'detail': '氨基酸配方，温和不刺激，有效控油',
        'feature': '氨基酸配方 | 温和控油 | 清洁毛孔',
        'order_by': 99,
        'is_hot': 0,
    },
    {
        'product_name': '遮瑕保湿气垫BB霜',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('159.00'),
        'market_price': Decimal('229.00'),
        'cost_price': Decimal('80.00'),
        'stock': 150,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '美妆护肤',
        'profile': '水润遮瑕，自然裸妆感',
        'detail': '轻薄服帖，长效持妆，打造自然裸妆',
        'feature': '轻薄服帖 | 长效持妆 | 自然裸妆',
        'order_by': 98,
        'is_hot': 1,
    },

    # 家居日用类
    {
        'product_name': '智能电饭煲 4L',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('299.00'),
        'market_price': Decimal('399.00'),
        'cost_price': Decimal('160.00'),
        'stock': 80,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '家居日用',
        'profile': '智能多功能电饭煲，一机多用',
        'detail': '24小时预约，柴火饭功能，微压烹饪',
        'feature': '24小时预约 | 柴火饭功能 | 微压烹饪',
        'order_by': 100,
        'is_hot': 1,
    },
    {
        'product_name': '静音加湿器 3.5L',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('129.00'),
        'market_price': Decimal('179.00'),
        'cost_price': Decimal('65.00'),
        'stock': 120,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '家居日用',
        'profile': '大容量静音加湿器，滋润生活',
        'detail': '超大雾量，缺水自动断电，静音设计',
        'feature': '超大雾量 | 自动断电 | 静音设计',
        'order_by': 99,
        'is_hot': 0,
    },
    {
        'product_name': '不锈钢保温杯 500ml',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.SELF_OPERATED,
        'sale_price': Decimal('79.00'),
        'market_price': Decimal('109.00'),
        'cost_price': Decimal('40.00'),
        'stock': 300,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '家居日用',
        'profile': '304不锈钢真空保温，保冷保热',
        'detail': '12小时保温，24小时保冷，食品级材质',
        'feature': '304不锈钢 | 12h保温 | 食品级材质',
        'order_by': 98,
        'is_hot': 1,
    },

    # 爆款专区
    {
        'product_name': '爆款限量运动鞋',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.HOT_SALE,
        'sale_price': Decimal('399.00'),
        'market_price': Decimal('599.00'),
        'cost_price': Decimal('200.00'),
        'stock': 50,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '精选爆款',
        'profile': '限量发售，先到先得',
        'detail': '时尚潮流款式，舒适脚感',
        'feature': '限量发售 | 时尚潮流 | 舒适脚感',
        'order_by': 100,
        'is_hot': 1,
    },
    {
        'product_name': '爆款智能手表',
        'product_type': ProductType.PHYSICAL,
        'owner_type': ProductOwnerType.SELF_OPERATED,
        'zone_type': ZoneType.HOT_SALE,
        'sale_price': Decimal('599.00'),
        'market_price': Decimal('899.00'),
        'cost_price': Decimal('320.00'),
        'stock': 30,
        'main_image': 'https://img.yzcdn.cn/vant/cat.jpeg',
        'brand': '精选爆款',
        'profile': '多功能智能手表，限时特惠',
        'detail': '心率血氧监测，GPS定位，支付功能',
        'feature': '心率血氧 | GPS定位 | 支付功能',
        'order_by': 99,
        'is_hot': 1,
    },
]


def seed_test_products(db: Session) -> None:
    """添加测试商品数据"""
    print("开始添加测试商品数据...")

    # 检查是否已有测试数据
    existing_count = db.query(Product).filter(
        Product.brand.in_(['数码电子', '服饰鞋包', '食品生鲜', '美妆护肤', '家居日用', '精选爆款'])
    ).count()

    if existing_count > 0:
        print(f"已存在 {existing_count} 条测试商品数据，跳过添加。")
        return

    created_count = 0
    for product_data in TEST_PRODUCTS:
        product = Product(
            product_name=product_data['product_name'],
            product_type=product_data['product_type'],
            owner_type=product_data['owner_type'],
            owner_id=1,  # 归属超级管理员
            zone_type=product_data['zone_type'],
            market_price=product_data.get('market_price'),
            sale_price=product_data['sale_price'],
            cost_price=product_data.get('cost_price'),
            stock=product_data['stock'],
            sold_count=0,
            main_image=product_data.get('main_image'),
            status=ProductStatus.ON_SHELF,
            requires_shipping=True,
            drop_shipping_enabled=False,
            brand=product_data.get('brand'),
            profile=product_data.get('profile'),
            detail=product_data.get('detail'),
            feature=product_data.get('feature'),
            order_by=product_data.get('order_by', 0),
            is_hot=product_data.get('is_hot', 0),
        )
        db.add(product)
        created_count += 1

    db.commit()
    print(f"成功添加 {created_count} 条测试商品数据！")
    print("\n分类统计:")
    print("  - 数码电子: 3件商品")
    print("  - 服饰鞋包: 3件商品")
    print("  - 食品生鲜: 3件商品")
    print("  - 美妆护肤: 3件商品")
    print("  - 家居日用: 3件商品")
    print("  - 精选爆款: 2件商品")


if __name__ == '__main__':
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        seed_test_products(db)
    finally:
        db.close()
