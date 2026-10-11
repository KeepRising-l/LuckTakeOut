"""商户端测试：展示口径与入驻链路（注册、审核状态、经营门槛）。"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from merchant.models import MerchantInfo
from order.models import OrderInfo
from review.models import Review
from user.models import UserInfo


class MerchantDisplayTest(TestCase):
    def setUp(self):
        shop_user = User.objects.create_user(username='md_shop', password='pw123456')
        self.merchant = MerchantInfo.objects.create(
            auth_user=shop_user, name='测试商户', description='简介', status=20,
        )
        self.listed = MerchantInfo.objects.create(
            auth_user=User.objects.create_user(username='md_shop2', password='pw123456'),
            name='未通过商户', status=10,
        )
        self.customer = UserInfo.objects.create(
            auth_user=User.objects.create_user(username='md_c', password='pw123456'),
            nickname='顾客', phone='13600000001',
        )
        self.order = OrderInfo.objects.create(
            order_no='DISPLAYORDER0001', user=self.customer, merchant=self.merchant,
            address_snapshot='示例路1号', total_amount=10, delivery_fee=2, pay_amount=12,
            status=OrderInfo.STATUS_FINISHED,
        )

    def _add_review(self, rating):
        return Review.objects.create(
            order=self.order, user=self.customer, merchant=self.merchant,
            target_type=Review.TARGET_MERCHANT, rating=rating, content='',
        )

    def test_list_excludes_unapproved_and_fabricated_fields(self):
        resp = self.client.get('/api/v1/merchants/nearby')
        rows = resp.json()['data']
        names = [r['name'] for r in rows]
        self.assertIn('测试商户', names)
        self.assertNotIn('未通过商户', names)
        for row in rows:
            self.assertNotIn('monthlySales', row)
            self.assertNotIn('distance', row)

    def test_rating_is_average_of_reviews(self):
        self._add_review(4)
        self._add_review(5)
        resp = self.client.get(f'/api/v1/merchants/{self.merchant.id}')
        self.assertEqual(resp.json()['data']['rating'], 4.5)

    def test_rating_is_null_without_reviews(self):
        resp = self.client.get(f'/api/v1/merchants/{self.merchant.id}')
        self.assertIsNone(resp.json()['data']['rating'])

    def test_delivery_fee_is_platform_constant(self):
        resp = self.client.get(f'/api/v1/merchants/{self.merchant.id}')
        self.assertEqual(resp.json()['data']['deliveryFee'], 2.0)


class MerchantOnboardingTest(TestCase):
    """商户注册与入驻申请、查看审核状态、未过审商户的经营门槛（F-B-01/F-B-03/R3）。"""

    def _register(self, **overrides):
        payload = {
            'username': 'newshop',
            'password': 'pw123456',
            'name': '新店',
            'phone': '13500000001',
            'address': '示例路9号',
            'description': '家常菜',
        }
        payload.update(overrides)
        return self.client.post(
            '/api/merchant/register', data=json.dumps(payload),
            content_type='application/json',
        )

    def _login(self, username='newshop', password='pw123456'):
        return self.client.post(
            '/api/merchant/login',
            data=json.dumps({'username': username, 'password': password}),
            content_type='application/json',
        )

    def test_register_creates_pending_merchant(self):
        resp = self._register()
        body = resp.json()
        self.assertEqual(body['code'], '00000')
        self.assertEqual(body['data']['status'], MerchantInfo.STATUS_PENDING)
        merchant = MerchantInfo.objects.get(name='新店')
        self.assertEqual(merchant.status, MerchantInfo.STATUS_PENDING)
        self.assertEqual(merchant.phone, '13500000001')
        self.assertEqual(merchant.address, '示例路9号')
        # 注册后即可凭该账号登录
        self.assertEqual(self._login().json()['code'], '00000')

    def test_register_rejects_taken_username(self):
        self._register()
        resp = self._register(name='另一家店')
        self.assertIn('已被占用', resp.json()['info'])
        self.assertEqual(MerchantInfo.objects.filter(name='另一家店').count(), 0)

    def test_register_rejects_missing_required_fields(self):
        resp = self._register(name='', phone='')
        info = resp.json()['info']
        self.assertIn('店铺名称', info)
        self.assertIn('联系电话', info)

    def test_register_rejects_short_password(self):
        resp = self._register(password='123')
        self.assertIn('密码长度', resp.json()['info'])

    def _pending_token(self):
        self._register()
        return self._login().json()['data']['token']

    def test_pending_merchant_can_login_and_view_status(self):
        token = self._pending_token()
        resp = self.client.get(
            '/api/merchant/current', HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        body = resp.json()
        self.assertEqual(body['code'], '00000')
        self.assertEqual(body['data']['status'], MerchantInfo.STATUS_PENDING)

    def test_pending_merchant_is_blocked_from_business_endpoints(self):
        token = self._pending_token()
        cases = [
            ('get', '/api/product/categories'),
            ('get', '/api/product/merchant'),
            ('get', '/api/order/merchant'),
            ('get', '/api/stats/overview'),
            ('put', '/api/merchant/info'),
        ]
        for method, url in cases:
            with self.subTest(url=url):
                resp = getattr(self.client, method)(
                    url, data={}, content_type='application/json',
                    HTTP_AUTHORIZATION=f'Bearer {token}',
                )
                self.assertEqual(resp.status_code, 403)
                self.assertIn('尚未通过入驻审核', resp.json()['info'])

    def test_approved_merchant_passes_the_gate(self):
        self._register()
        merchant = MerchantInfo.objects.get(name='新店')
        merchant.status = MerchantInfo.STATUS_APPROVED
        merchant.save()
        token = self._login().json()['data']['token']
        resp = self.client.get(
            '/api/product/categories', HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.json()['code'], '00000')
