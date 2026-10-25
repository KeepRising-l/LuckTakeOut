"""生成演示数据：python manage.py seed_demo"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from delivery.models import Rider
from merchant.models import MerchantCategory, MerchantInfo
from product.models import ProductCategory, ProductInfo
from user.models import UserAddress, UserInfo


class Command(BaseCommand):
    help = '生成演示数据（商户、菜品、骑手、顾客）'

    def handle(self, *args, **options):
        cat_fast, _ = MerchantCategory.objects.get_or_create(name='快餐便当')
        cat_drink, _ = MerchantCategory.objects.get_or_create(name='奶茶饮品')

        merchants = [
            ('川香小馆', cat_fast, [
                ('招牌川菜套餐', '32.80', '麻婆豆腐+宫保鸡丁+米饭'),
                ('水煮肉片', '28.00', '经典川味'),
            ]),
            ('快乐奶茶', cat_drink, [
                ('珍珠奶茶', '12.00', '经典珍珠'),
                ('柠檬茶', '14.00', '清爽柠檬'),
            ]),
        ]
        for idx, (mname, mcat, products) in enumerate(merchants, start=1):
            auth_user, created = User.objects.get_or_create(username=f'merchant{idx}')
            if created:
                auth_user.set_password('merchant123')
                auth_user.save()
            m, _ = MerchantInfo.objects.get_or_create(
                auth_user=auth_user,
                defaults=dict(
                    name=mname, category=mcat, phone=f'1380000000{idx}',
                    address=f'示例路{idx}号', description=f'{mname}，欢迎光临', status=20,
                ),
            )
            if m.status != 20:
                m.status = 20
                m.save()
            pc, _ = ProductCategory.objects.get_or_create(merchant=m, name='热销')
            for pname, price, desc in products:
                ProductInfo.objects.get_or_create(
                    merchant=m, name=pname,
                    defaults=dict(category=pc, price=Decimal(price), stock=100,
                                  description=desc, status=10),
                )

        # 平台运营演示账号（/admin/ 登录，公开演示凭据见 README）
        p_auth, created = User.objects.get_or_create(
            username='platform',
            defaults=dict(is_staff=True, is_superuser=True),
        )
        if created:
            p_auth.set_password('platform123')
            p_auth.save()

        r_auth, created = User.objects.get_or_create(username='rider1')
        if created:
            r_auth.set_password('rider123')
            r_auth.save()
        Rider.objects.get_or_create(
            auth_user=r_auth, defaults=dict(name='骑手小李', phone='13900000001'),
        )

        c_auth, created = User.objects.get_or_create(username='customer1')
        if created:
            c_auth.set_password('customer123')
            c_auth.save()
        info, _ = UserInfo.objects.get_or_create(
            auth_user=c_auth, defaults=dict(nickname='测试顾客', phone='13700000001'),
        )
        UserAddress.objects.get_or_create(
            user=info, detail='示例小区1号楼101',
            defaults=dict(receiver='测试顾客', phone='13700000001', city='示例市', is_default=True),
        )

        self.stdout.write(self.style.SUCCESS('演示数据已生成'))
