"""骑手端配送流程测试：接单即进入配送中、归属唯一、送达闭环。"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from common.auth import make_rider_token
from delivery.models import Rider
from merchant.models import MerchantInfo
from order.models import OrderInfo
from user.models import UserInfo


class RiderDeliveryFlowTest(TestCase):
    def setUp(self):
        customer_user = User.objects.create_user(username='rd_c', password='pw123456')
        self.customer = UserInfo.objects.create(
            auth_user=customer_user, nickname='顾客', phone='13700000001',
        )
        shop_user = User.objects.create_user(username='rd_shop', password='pw123456')
        self.merchant = MerchantInfo.objects.create(
            auth_user=shop_user, name='测试商户', status=20,
        )

        self.rider_auth = User.objects.create_user(username='rd_r1', password='pw123456')
        self.rider = Rider.objects.create(
            auth_user=self.rider_auth, name='骑手甲', phone='13700000002',
        )
        self.other_rider_auth = User.objects.create_user(username='rd_r2', password='pw123456')
        self.other_rider = Rider.objects.create(
            auth_user=self.other_rider_auth, name='骑手乙', phone='13700000003',
        )

        self.token = make_rider_token(self.rider_auth)
        self.order = OrderInfo.objects.create(
            order_no='RIDERORDER0001', user=self.customer, merchant=self.merchant,
            address_snapshot='示例路1号', total_amount=10, delivery_fee=2, pay_amount=12,
            status=OrderInfo.STATUS_PENDING_ACCEPT,
        )

    def _post(self, url, payload=None, token=None):
        return self.client.post(
            url, data=json.dumps(payload or {}), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token or self.token}',
        )

    def test_accept_moves_order_to_delivering(self):
        resp = self._post(f'/api/v1/delivery/tasks/{self.order.id}/accept')
        self.assertEqual(resp.json()['code'], '00000')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderInfo.STATUS_DELIVERING)
        self.assertEqual(self.order.rider_id, self.rider.id)

    def test_accept_rejected_when_taken_by_other_rider(self):
        self.order.rider = self.other_rider
        self.order.save()
        resp = self._post(f'/api/v1/delivery/tasks/{self.order.id}/accept')
        self.assertIn('其他骑手接单', resp.json()['info'])
        self.order.refresh_from_db()
        self.assertEqual(self.order.rider_id, self.other_rider.id)

    def test_deliver_finishes_order(self):
        self._post(f'/api/v1/delivery/tasks/{self.order.id}/accept')
        resp = self._post(f'/api/v1/delivery/tasks/{self.order.id}/status', {'status': 6})
        self.assertEqual(resp.json()['code'], '00000')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderInfo.STATUS_FINISHED)
        self.assertIsNotNone(self.order.deliver_time)
        self.assertIsNotNone(self.order.finish_time)

    def test_intermediate_status_is_rejected(self):
        self._post(f'/api/v1/delivery/tasks/{self.order.id}/accept')
        resp = self._post(f'/api/v1/delivery/tasks/{self.order.id}/status', {'status': 5})
        self.assertIn('未知的配送状态', resp.json()['info'])

    def test_rider_info_has_no_fabricated_fields(self):
        resp = self.client.get(
            f'/api/v1/delivery/riders/{self.rider.id}', HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        data = resp.json()['data']
        self.assertNotIn('rating', data)
        self.assertNotIn('todayEarnings', data)
        self.assertNotIn('location', data)
        self.assertEqual(data['todayDeliveryCount'], 0)
