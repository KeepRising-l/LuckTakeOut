"""生成多品类商家与菜品（炒菜/奶茶/面条/快餐/寿司/甜品等）。

前置：先跑 scripts/fetch_food_images.py 准备图片，否则菜品图留空走占位图标。

用法：
    cd takeout && .venv/Scripts/python.exe manage.py seed_shops

幂等：重复执行只会补齐/更新，不会产生重复商家或菜品。
"""

from datetime import time
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from merchant.models import MerchantCategory, MerchantInfo
from product.models import ProductCategory, ProductInfo

# (账号, 商户名, 商户分类, 门店图, 电话, 地址, 简介, 营业时间)
SHOPS = [
    (
        'merchant1', '川香小馆', '炒菜', 'sichuan',
        '13800000001', '示例路1号', '地道川味，麻辣鲜香',
        (time(10, 0), time(21, 0)),
    ),
    (
        'coffee1', '晨光咖啡', '咖啡烘焙', 'coffee',
        '13800000011', '梧桐路 18 号 1 层', '手冲与意式，每日现烤可颂',
        (time(7, 30), time(21, 0)),
    ),
    (
        'merchant2', '快乐奶茶', '奶茶饮品', 'milktea',
        '13800000002', '示例路2号', '现煮茶底，鲜果现切',
        (time(10, 0), time(22, 30)),
    ),
    (
        'noodle1', '面面俱到', '面食', 'noodle',
        '13800000013', '老城巷 6 号', '一碗热汤面，抚平一天的疲惫',
        (time(10, 30), time(21, 30)),
    ),
    (
        'fastfood1', '快意小厨', '快餐便当', 'fastfood',
        '13800000014', '科技园 B 座 1 层', '现炸现做，出餐 5 分钟',
        (time(9, 0), time(23, 0)),
    ),
    (
        'sushi1', '江户寿司', '寿司日料', 'sushi',
        '13800000015', '滨江路 88 号', '当日直送食材，师傅现握',
        (time(11, 0), time(22, 0)),
    ),
    (
        'dessert1', '甜心甜品屋', '甜品烘焙', 'dessert',
        '13800000021', '甜水巷 3 号', '现做甜品，杨枝甘露与双皮奶',
        (time(11, 0), time(22, 0)),
    ),
    (
        'bbq1', '老王烧烤', '烧烤炸串', 'bbq',
        '13800000022', '夜市街 12 号', '炭火烧烤，深夜烟火气',
        (time(17, 0), time(23, 59)),
    ),
    (
        'fruit1', '鲜果多多', '水果生鲜', 'fruit',
        '13800000023', '便民路 7 号', '当季鲜果，现切现卖',
        (time(8, 0), time(21, 30)),
    ),
    (
        'breakfast1', '晨光早点铺', '早餐粥点', 'breakfast',
        '13800000024', '梧桐路 22 号', '现蒸包子，现磨豆浆',
        (time(5, 30), time(10, 30)),
    ),
    (
        'supper1', '深夜食堂', '夜宵小吃', 'supper',
        '13800000025', '夜市街 15 号', '炒粉卤味，深夜慰藉',
        (time(20, 0), time(23, 59)),
    ),
]

# 账号 -> [(菜品分类, [(菜名, 价格, 描述, 图片名)])]
MENU = {
    'merchant1': [
        ('招牌川菜', [
            ('招牌川菜套餐', '32.80', '麻婆豆腐+宫保鸡丁+米饭', 'mapo_tofu'),
            ('水煮肉片', '28.00', '经典川味，麻辣鲜香', 'shuizhu_pork'),
            ('宫保鸡丁', '26.00', '鸡丁花生，甜辣适口', 'kung_pao'),
        ]),
        ('特色湘菜', [
            ('剁椒鱼头', '58.00', '湘菜头牌，鲜辣下饭', 'duojiao_fish'),
            ('辣椒炒肉', '32.00', '农家小炒，锅气十足', 'chili_pork'),
        ]),
    ],
    'coffee1': [
        ('咖啡', [
            ('拿铁', '22.00', '意式浓缩与丝滑牛奶，拉花现做', 'latte'),
            ('美式咖啡', '18.00', '深烘豆，清爽回甘', 'americano'),
            ('卡布奇诺', '24.00', '绵密奶泡，撒可可粉', 'cappuccino'),
        ]),
        ('烘焙甜点', [
            ('黄油可颂', '16.00', '每日现烤，层次酥脆', 'croissant'),
            ('提拉米苏', '26.00', '马斯卡彭芝士与浓缩咖啡', 'tiramisu'),
        ]),
    ],
    'merchant2': [
        ('招牌奶茶', [
            ('珍珠奶茶', '12.00', '经典黑糖珍珠，现煮 Q 弹', 'bubble_tea'),
            ('芝士奶盖茶', '17.00', '海盐芝士奶盖，茶底清爽', 'cheese_foam_tea'),
            ('抹茶拿铁', '15.00', '宇治抹茶配鲜奶', 'matcha_latte'),
        ]),
        ('鲜果茶', [
            ('杨枝甘露', '16.00', '芒果西柚西米，果肉满满', 'mango_sago'),
            ('柠檬茶', '14.00', '手打香水柠檬，冰爽解腻', 'lemon_tea'),
        ]),
    ],
    'noodle1': [
        ('汤面', [
            ('红烧牛肉面', '26.00', '慢炖牛腩，汤头浓郁', 'beef_noodle'),
            ('兰州拉面', '22.00', '一清二白三红四绿', 'lanzhou_noodle'),
            ('鲜虾云吞面', '24.00', '手工云吞，虾仁饱满', 'wonton_noodle'),
        ]),
        ('拌面小吃', [
            ('老北京炸酱面', '20.00', '六必居黄酱，配八样菜码', 'zhajiang_noodle'),
            ('酸辣粉', '16.00', '红薯粉爽滑，酸辣开胃', 'spicy_noodle'),
        ]),
    ],
    'fastfood1': [
        ('主食', [
            ('香辣鸡腿堡', '18.00', '整块鸡腿排，现炸酥脆', 'chicken_burger'),
            ('招牌炸鸡（2块）', '22.00', '秘制腌料，外酥里嫩', 'fried_chicken'),
        ]),
        ('小食饮品', [
            ('黄金薯条', '10.00', '现炸粗薯，配番茄酱', 'fries'),
            ('鸡米花', '13.00', '一口一个，追剧必备', 'popcorn_chicken'),
            ('冰镇可乐', '7.00', '加冰更爽', 'cola'),
        ]),
    ],
    'sushi1': [
        ('寿司卷物', [
            ('三文鱼寿司（4贯）', '28.00', '挪威三文鱼，现握', 'salmon_sushi'),
            ('加州卷（6件）', '26.00', '蟹柳牛油果，反卷', 'california_roll'),
        ]),
        ('主食汤品', [
            ('鳗鱼饭', '38.00', '蒲烧鳗鱼，酱汁浓郁', 'unagi_don'),
            ('刺身拼盘', '58.00', '三文鱼/金枪鱼/甜虾', 'sashimi'),
            ('味增汤', '8.00', '白味增配豆腐海带', 'miso_soup'),
        ]),
    ],
    'dessert1': [
        ('招牌甜品', [
            ('杨枝甘露', '13.00', '芒果西柚西米，经典甜品', ''),
            ('芒果双皮奶', '12.00', '顺德风味，奶香嫩滑', ''),
        ]),
    ],
    'bbq1': [
        ('炭火烤串', [
            ('烤羊肉串（5串）', '20.00', '炭火现烤，孜然够味', ''),
            ('烤茄子', '8.00', '蒜蓉铺满，软糯入味', ''),
        ]),
    ],
    'fruit1': [
        ('鲜果现切', [
            ('鲜切水果捞', '15.00', '当季水果，酸奶拌制', ''),
            ('冰镇西瓜盒', '9.00', '冷藏现切，清甜多汁', ''),
        ]),
    ],
    'breakfast1': [
        ('早点', [
            ('鲜肉包子', '3.00', '现蒸现卖，皮薄馅大', ''),
            ('现磨豆浆', '4.00', '黄豆现磨，浓香微甜', ''),
        ]),
    ],
    'supper1': [
        ('夜宵', [
            ('炒河粉', '16.00', '锅气十足，镬香扑鼻', ''),
            ('麻辣小龙虾', '58.00', '十三香入味，宵夜首选', ''),
        ]),
    ],
}


class Command(BaseCommand):
    help = '生成多品类商家（咖啡/奶茶/面条/快餐/寿司）与菜品，含图片'

    def handle(self, *args, **options):
        created_merchants = created_products = 0

        for username, name, cat_name, slug, phone, address, desc, hours in SHOPS:
            mcat, _ = MerchantCategory.objects.get_or_create(name=cat_name)

            auth_user, user_created = User.objects.get_or_create(username=username)
            if user_created:
                auth_user.set_password('merchant123')
                auth_user.save()

            merchant, m_created = MerchantInfo.objects.update_or_create(
                auth_user=auth_user,
                defaults=dict(
                    name=name,
                    category=mcat,
                    logo=f'/media/products/{slug}/logo.jpg',
                    phone=phone,
                    address=address,
                    description=desc,
                    status=MerchantInfo.STATUS_APPROVED,
                    is_open=True,
                    open_time=hours[0],
                    close_time=hours[1],
                ),
            )
            created_merchants += 1 if m_created else 0

            for sort, (pcat_name, items) in enumerate(MENU[username]):
                pcat, _ = ProductCategory.objects.get_or_create(
                    merchant=merchant, name=pcat_name, defaults=dict(sort=sort),
                )
                for idx, (pname, price, pdesc, img) in enumerate(items):
                    _, p_created = ProductInfo.objects.update_or_create(
                        merchant=merchant, name=pname,
                        defaults=dict(
                            category=pcat,
                            image=(f'/media/products/{slug}/{img}.jpg' if img else ''),
                            price=Decimal(price),
                            stock=100,
                            description=pdesc,
                            status=10,
                        ),
                    )
                    created_products += 1 if p_created else 0

            self.stdout.write(
                f'  {name}（{username}）：{len(MENU[username])} 个分类，'
                f'{sum(len(i) for _, i in MENU[username])} 道菜'
            )

        # 清掉遗留的空分类（如旧种子数据的「热销」），避免前台出现空分组
        usernames = [s[0] for s in SHOPS]
        removed = ProductCategory.objects.filter(
            merchant__auth_user__username__in=usernames, products__isnull=True,
        ).delete()[0]

        self.stdout.write(self.style.SUCCESS(
            f'完成：{len(SHOPS)} 家商户（新增 {created_merchants}），'
            f'菜品新增 {created_products} 道，清理空分类 {removed} 个。统一密码 merchant123'
        ))
