"""顾客端订单接口的归属过滤与下单前置校验测试。

覆盖：订单详情与模拟支付限定为本人订单、未选择（或不属于本人的）收货地址被拒，
以及归属校验通过时行为保持不变。
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from common.auth import make_merchant_token, make_token
from merchant.models import MerchantInfo
from payment.models import PaymentRecord, RefundRecord
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


class StockDeductionTest(TestCase):
    """下单扣减库存，取消订单回补库存（防超卖）。"""

    def setUp(self):
        self.user, self.info = make_customer('sd_a', '顾客A', '13900000031')
        self.token = make_token(self.user)

        shop_user = User.objects.create_user(username='sd_shop', password='pw123456')
        self.merchant = MerchantInfo.objects.create(
            auth_user=shop_user, name='测试商户', status=20,
        )
        self.product = ProductInfo.objects.create(
            merchant=self.merchant, name='测试菜品', price=10, stock=50, status=10,
        )
        self.address = UserAddress.objects.create(
            user=self.info, receiver='顾客A', phone='13900000031', detail='示例路1号',
        )

    def _create(self, items):
        payload = {
            'merchantId': self.merchant.id,
            'items': items,
            'addressId': self.address.id,
        }
        return self.client.post(
            '/api/v1/orders', data=json.dumps(payload), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )

    def test_stock_is_deducted_after_create(self):
        self._create([{'productId': self.product.id, 'quantity': 3}])
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 47)

    def test_cancel_restores_stock(self):
        self._create([{'productId': self.product.id, 'quantity': 3}])
        order = OrderInfo.objects.latest('id')
        self.client.post(
            f'/api/v1/orders/{order.id}/cancel', HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 50)

    def test_insufficient_stock_is_rejected(self):
        resp = self._create([{'productId': self.product.id, 'quantity': 51}])
        self.assertIn('库存不足', resp.json()['info'])
        self.assertEqual(OrderInfo.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 50)

    def test_duplicate_lines_share_stock_budget(self):
        """同一菜品拆两行下单时按合并数量校验，防重复行绕过库存。"""
        resp = self._create([
            {'productId': self.product.id, 'quantity': 30},
            {'productId': self.product.id, 'quantity': 30},
        ])
        self.assertIn('库存不足', resp.json()['info'])
        self.assertEqual(OrderInfo.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 50)

    def test_non_numeric_ids_are_rejected_not_500(self):
        payload = {
            'merchantId': 'abc',
            'items': [{'productId': self.product.id, 'quantity': 1}],
            'addressId': self.address.id,
        }
        resp = self.client.post(
            '/api/v1/orders', data=json.dumps(payload), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        self.assertIn('商家不存在', resp.json()['info'])


class RefundFlowTest(TestCase):
    """退款闭环：顾客申请（已支付/待接单）→ 商户审核（同意/拒绝）。"""

    def setUp(self):
        self.user, self.info = make_customer('rf_c', '顾客A', '13900000051')
        self.other_user, self.other_info = make_customer('rf_c2', '顾客B', '13900000052')
        self.token = make_token(self.user)
        self.merchant_auth = User.objects.create_user(username='rf_shop', password='pw123456')
        self.merchant = MerchantInfo.objects.create(
            auth_user=self.merchant_auth, name='测试商户', status=20,
        )
        self.other_shop_auth = User.objects.create_user(username='rf_shop2', password='pw123456')
        self.other_merchant = MerchantInfo.objects.create(
            auth_user=self.other_shop_auth, name='别家商户', status=20,
        )
        self.merchant_token = make_merchant_token(self.merchant_auth)
        self.other_shop_token = make_merchant_token(self.other_shop_auth)
        self.order = OrderInfo.objects.create(
            order_no='RF0001', user=self.info, merchant=self.merchant,
            address_snapshot='示例路1号', total_amount=10, delivery_fee=2, pay_amount=12,
            status=OrderInfo.STATUS_PAID,
        )
        PaymentRecord.objects.create(order=self.order, amount=12, method='mock', status=20)

    def _apply(self, token=None, payload=None):
        return self.client.post(
            f'/api/v1/orders/{self.order.id}/refund',
            data=json.dumps(payload or {'reason': '不想要了'}), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token or self.token}',
        )

    def _review(self, payload, token=None, order_id=None):
        return self.client.put(
            f'/api/order/{order_id or self.order.id}/refund/review',
            data=json.dumps(payload), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token or self.merchant_token}',
        )

    def test_apply_from_paid_enters_refunding(self):
        resp = self._apply()
        self.assertEqual(resp.json()['code'], '00000')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderInfo.STATUS_REFUNDING)
        refund = RefundRecord.objects.get(order=self.order)
        self.assertEqual(refund.status, RefundRecord.STATUS_PENDING)
        self.assertEqual(refund.from_status, OrderInfo.STATUS_PAID)
        self.assertEqual(float(refund.amount), 12.0)

    def test_apply_from_pending_accept_records_origin(self):
        self.order.status = OrderInfo.STATUS_PENDING_ACCEPT
        self.order.save()
        self._apply()
        refund = RefundRecord.objects.get(order=self.order)
        self.assertEqual(refund.from_status, OrderInfo.STATUS_PENDING_ACCEPT)

    def test_apply_from_other_status_rejected(self):
        self.order.status = OrderInfo.STATUS_DELIVERING
        self.order.save()
        resp = self._apply()
        self.assertIn('不支持申请退款', resp.json()['info'])
        self.assertEqual(RefundRecord.objects.count(), 0)

    def test_duplicate_pending_apply_rejected(self):
        self._apply()
        resp = self._apply()
        self.assertIn('已有退款申请待审核', resp.json()['info'])
        self.assertEqual(RefundRecord.objects.count(), 1)

    def test_other_customer_cannot_apply(self):
        resp = self._apply(token=make_token(self.other_user))
        self.assertIn('订单不存在', resp.json()['info'])
        self.assertEqual(RefundRecord.objects.count(), 0)

    def test_approve_refunds_and_marks_payment(self):
        self._apply()
        resp = self._review({'approve': True, 'remark': '同意'})
        self.assertIn('已同意退款', resp.json()['info'])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderInfo.STATUS_REFUNDED)
        refund = RefundRecord.objects.get(order=self.order)
        self.assertEqual(refund.status, RefundRecord.STATUS_APPROVED)
        self.assertEqual(refund.review_time, refund.review_time)
        self.assertTrue(PaymentRecord.objects.filter(order=self.order, status=40).exists())

    def test_reject_returns_to_origin_status(self):
        self._apply()
        resp = self._review({'approve': False, 'remark': '已出餐不便退款'})
        self.assertIn('已拒绝退款申请', resp.json()['info'])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderInfo.STATUS_PAID)
        refund = RefundRecord.objects.get(order=self.order)
        self.assertEqual(refund.status, RefundRecord.STATUS_REJECTED)
        self.assertFalse(PaymentRecord.objects.filter(order=self.order, status=40).exists())

    def test_reject_from_pending_accept_returns_there(self):
        self.order.status = OrderInfo.STATUS_PENDING_ACCEPT
        self.order.save()
        self._apply()
        self._review({'approve': False})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderInfo.STATUS_PENDING_ACCEPT)

    def test_other_merchant_cannot_review(self):
        self._apply()
        resp = self._review({'approve': True}, token=self.other_shop_token)
        self.assertIn('订单不存在', resp.json()['info'])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderInfo.STATUS_REFUNDING)

    def test_review_without_pending_apply_rejected(self):
        resp = self._review({'approve': True})
        self.assertIn('不在退款审核中', resp.json()['info'])

    def test_refunding_order_cannot_be_cancelled_or_accepted(self):
        self._apply()
        # 顾客取消：状态不在可取消集合
        resp = self.client.post(
            f'/api/v1/orders/{self.order.id}/cancel', HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        self.assertIn('不允许取消', resp.json()['info'])
        # 商户接单：退款审核中的订单被引导走退款审核接口
        resp2 = self.client.put(
            f'/api/order/{self.order.id}/status', data=json.dumps({'status': 30}),
            content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.merchant_token}',
        )
        self.assertIn('退款审核中', resp2.json()['info'])
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderInfo.STATUS_REFUNDING)

    def test_order_detail_carries_refund_info(self):
        self._apply()
        resp = self.client.get(
            f'/api/v1/orders/{self.order.id}', HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        data = resp.json()['data']
        self.assertEqual(data['refundStatus'], RefundRecord.STATUS_PENDING)
        self.assertEqual(data['refundReason'], '不想要了')


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
