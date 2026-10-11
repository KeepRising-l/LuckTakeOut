"""顾客端订单接口的归属过滤与下单前置校验测试。

覆盖：订单详情与模拟支付限定为本人订单、未选择（或不属于本人的）收货地址被拒，
以及归属校验通过时行为保持不变。
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from common.auth import make_merchant_token, make_token
from merchant.models import MerchantInfo
from product.models import ProductInfo
from user.models import UserAddress, UserInfo

from .models import OrderInfo


def make_customer(username, nickname, phone):
    auth_user = User.objects.create_user(username=username, password='pw123456')
    info = UserInfo.objects.create(auth_user=auth_user, nickname=nickname, phone=phone)
    return auth_user, info


class OrderScopeTest(TestCase):
    """订单详情与模拟支付只能作用在本人订单上。"""

    def setUp(self):
        self.a_user, self.a_info = make_customer('ord_a', '顾客A', '13900000001')
        self.b_user, self.b_info = make_customer('ord_b', '顾客B', '13900000002')
        self.token_a = make_token(self.a_user)
        self.token_b = make_token(self.b_user)

        shop_user = User.objects.create_user(username='ord_shop', password='pw123456')
        self.merchant = MerchantInfo.objects.create(
            auth_user=shop_user, name='测试商户', status=20,
        )
        self.order = OrderInfo.objects.create(
            order_no='TESTORDER0001', user=self.a_info, merchant=self.merchant,
            address_snapshot='示例路1号', total_amount=10, pay_amount=12,
            status=OrderInfo.STATUS_PENDING_PAY,
        )

    def test_detail_rejects_other_customer(self):
        resp = self.client.get(
            f'/api/v1/orders/{self.order.id}', HTTP_AUTHORIZATION=f'Bearer {self.token_b}',
        )
        self.assertIn('订单不存在', resp.json()['info'])

    def test_detail_allows_owner(self):
        resp = self.client.get(
            f'/api/v1/orders/{self.order.id}', HTTP_AUTHORIZATION=f'Bearer {self.token_a}',
        )
        self.assertEqual(resp.json()['code'], '00000')

    def test_pay_rejects_other_customer(self):
        resp = self.client.post(
            f'/api/v1/orders/{self.order.id}/pay', HTTP_AUTHORIZATION=f'Bearer {self.token_b}',
        )
        self.assertIn('订单不存在', resp.json()['info'])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderInfo.STATUS_PENDING_PAY)

    def test_pay_allows_owner(self):
        resp = self.client.post(
            f'/api/v1/orders/{self.order.id}/pay', HTTP_AUTHORIZATION=f'Bearer {self.token_a}',
        )
        self.assertEqual(resp.json()['code'], '00000')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderInfo.STATUS_PAID)


class CreateOrderPreconditionTest(TestCase):
    """下单必须指定属于本人的收货地址。"""

    def setUp(self):
        self.user, self.info = make_customer('co_a', '顾客A', '13900000011')
        self.other_user, self.other_info = make_customer('co_b', '顾客B', '13900000012')
        self.token = make_token(self.user)

        shop_user = User.objects.create_user(username='co_shop', password='pw123456')
        self.merchant = MerchantInfo.objects.create(
            auth_user=shop_user, name='测试商户', status=20,
        )
        self.product = ProductInfo.objects.create(
            merchant=self.merchant, name='测试菜品', price=10, stock=50, status=10,
        )
        self.address = UserAddress.objects.create(
            user=self.info, receiver='顾客A', phone='13900000011', detail='示例路1号',
        )
        self.other_address = UserAddress.objects.create(
            user=self.other_info, receiver='顾客B', phone='13900000012', detail='示例路2号',
        )

    def _create(self, payload):
        return self.client.post(
            '/api/v1/orders', data=json.dumps(payload), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )

    def _payload(self, **overrides):
        data = {
            'merchantId': self.merchant.id,
            'items': [{'productId': self.product.id, 'quantity': 1}],
            'deliveryFee': 2,
            'remark': '',
            'addressId': self.address.id,
        }
        data.update(overrides)
        return data

    def test_missing_address_is_rejected(self):
        resp = self._create(self._payload(addressId=None))
        self.assertIn('请选择收货地址', resp.json()['info'])
        self.assertEqual(OrderInfo.objects.count(), 0)

    def test_other_customers_address_is_rejected(self):
        resp = self._create(self._payload(addressId=self.other_address.id))
        self.assertIn('请选择收货地址', resp.json()['info'])
        self.assertEqual(OrderInfo.objects.count(), 0)

    def test_order_created_with_own_address(self):
        resp = self._create(self._payload())
        self.assertEqual(resp.json()['code'], '00000')
        order = OrderInfo.objects.latest('id')
        self.assertEqual(order.user_id, self.info.id)
        self.assertEqual(order.address_snapshot, '示例路1号')

    def test_platform_delivery_fee_is_persisted(self):
        self._create(self._payload())
        order = OrderInfo.objects.latest('id')
        self.assertEqual(float(order.delivery_fee), 2.0)
        self.assertEqual(float(order.pay_amount), float(order.total_amount) + 2.0)

    def test_client_supplied_delivery_fee_is_ignored(self):
        self._create(self._payload(deliveryFee=99))
        order = OrderInfo.objects.latest('id')
        self.assertEqual(float(order.delivery_fee), 2.0)


class MerchantStatusTransitionTest(TestCase):
    """商户端的状态更新受状态机约束（R2）。"""

    def setUp(self):
        self.merchant_auth = User.objects.create_user(username='mt_shop', password='pw123456')
        self.merchant = MerchantInfo.objects.create(
            auth_user=self.merchant_auth, name='测试商户', status=20,
        )
        self.customer = UserInfo.objects.create(
            auth_user=User.objects.create_user(username='mt_c', password='pw123456'),
            nickname='顾客', phone='13900000021',
        )
        self.token = make_merchant_token(self.merchant_auth)

    def _order_with(self, status):
        return OrderInfo.objects.create(
            order_no=f'TRANS{status}0001', user=self.customer, merchant=self.merchant,
            address_snapshot='示例路1号', total_amount=10, delivery_fee=2, pay_amount=12,
            status=status,
        )

    def _put(self, order, target):
        return self.client.put(
            f'/api/order/{order.id}/status',
            data=json.dumps({'status': target}), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )

    def test_paid_order_can_be_accepted(self):
        order = self._order_with(OrderInfo.STATUS_PAID)
        resp = self._put(order, OrderInfo.STATUS_PENDING_ACCEPT)
        self.assertEqual(resp.json()['code'], '00000')
        order.refresh_from_db()
        self.assertEqual(order.status, OrderInfo.STATUS_PENDING_ACCEPT)

    def test_delivering_order_cannot_go_back(self):
        order = self._order_with(OrderInfo.STATUS_DELIVERING)
        resp = self._put(order, OrderInfo.STATUS_PENDING_ACCEPT)
        self.assertIn('不允许该操作', resp.json()['info'])
        order.refresh_from_db()
        self.assertEqual(order.status, OrderInfo.STATUS_DELIVERING)

    def test_delivering_order_cannot_be_cancelled(self):
        order = self._order_with(OrderInfo.STATUS_DELIVERING)
        resp = self.client.put(
            f'/api/order/{order.id}/cancel', HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        self.assertIn('不允许该操作', resp.json()['info'])
        order.refresh_from_db()
        self.assertEqual(order.status, OrderInfo.STATUS_DELIVERING)

    def test_unknown_target_is_rejected(self):
        order = self._order_with(OrderInfo.STATUS_PAID)
        resp = self._put(order, 999)
        self.assertIn('未知的订单状态', resp.json()['info'])
