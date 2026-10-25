"""商户端菜品接口回归测试。

覆盖：有订单引用的菜品删除被拒（引导改为下架）、无引用菜品可正常删除、
价格与库存的非法入参校验。
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from common.auth import make_merchant_token
from merchant.models import MerchantInfo
from order.models import OrderInfo, OrderItem
from user.models import UserInfo

from .models import ProductInfo


class ProductDeleteGuardTest(TestCase):
    """删除菜品遇到订单引用（PROTECT）时返回业务提示而不是 500。"""

    def setUp(self):
        self.merchant_auth = User.objects.create_user(username='pd_shop', password='pw123456')
        self.merchant = MerchantInfo.objects.create(
            auth_user=self.merchant_auth, name='测试商户', status=20,
        )
        self.token = make_merchant_token(self.merchant_auth)
        self.customer = UserInfo.objects.create(
            auth_user=User.objects.create_user(username='pd_c', password='pw123456'),
            nickname='顾客', phone='13900000041',
        )
        self.product = ProductInfo.objects.create(
            merchant=self.merchant, name='引用菜品', price=10, stock=5, status=10,
        )
        order = OrderInfo.objects.create(
            order_no='PD0001', user=self.customer, merchant=self.merchant,
            address_snapshot='示例路1号', total_amount=10, delivery_fee=2, pay_amount=12,
            status=OrderInfo.STATUS_FINISHED,
        )
        OrderItem.objects.create(
            order=order, product=self.product, product_name=self.product.name,
            price=self.product.price, quantity=1, amount=10,
        )

    def _delete(self, product_id):
        return self.client.delete(
            f'/api/product/{product_id}', HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )

    def test_referenced_product_delete_is_rejected(self):
        resp = self._delete(self.product.id)
        self.assertIn('改为下架', resp.json()['info'])
        self.assertTrue(ProductInfo.objects.filter(id=self.product.id).exists())

    def test_unreferenced_product_delete_succeeds(self):
        free = ProductInfo.objects.create(
            merchant=self.merchant, name='无引用菜品', price=5, stock=5, status=10,
        )
        resp = self._delete(free.id)
        self.assertEqual(resp.json()['code'], '00000')
        self.assertFalse(ProductInfo.objects.filter(id=free.id).exists())


class ProductValidationTest(TestCase):
    """价格/库存的非法入参返回业务提示，不再 500 或落库脏数据。"""

    def setUp(self):
        self.merchant_auth = User.objects.create_user(username='pv_shop', password='pw123456')
        self.merchant = MerchantInfo.objects.create(
            auth_user=self.merchant_auth, name='测试商户', status=20,
        )
        self.token = make_merchant_token(self.merchant_auth)

    def _create(self, payload):
        return self.client.post(
            '/api/product', data=json.dumps(payload), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )

    def test_negative_price_rejected(self):
        resp = self._create({'name': '负价菜', 'price': -1, 'stock': 5})
        self.assertIn('价格必须为大于 0', resp.json()['info'])

    def test_zero_price_rejected(self):
        resp = self._create({'name': '零价菜', 'price': 0, 'stock': 5})
        self.assertIn('价格必须为大于 0', resp.json()['info'])

    def test_nan_price_rejected(self):
        resp = self._create({'name': 'NaN菜', 'price': 'NaN', 'stock': 5})
        self.assertIn('价格必须为大于 0', resp.json()['info'])

    def test_negative_stock_rejected(self):
        resp = self._create({'name': '负库存菜', 'price': 10, 'stock': -3})
        self.assertIn('库存必须为不小于 0', resp.json()['info'])
