"""用户域接口测试：登录链路、资料、收货地址。

覆盖：验证码登录（演示万能码）、同号复登不重复建档、资料与地址的作用域隔离、
删除地址仅接受 DELETE 方法。
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from common.auth import make_token
from user.models import UserInfo, UserAddress


class AuthLoginTest(TestCase):
    """手机号 + 验证码登录（演示环境固定万能码 123456）。"""

    PHONE = '13900000081'

    def _code(self, phone=PHONE):
        return self.client.post(
            '/api/v1/auth/code', data=json.dumps({'phone': phone}),
            content_type='application/json',
        )

    def _login(self, phone=PHONE, code='123456'):
        return self.client.post(
            '/api/v1/auth/login', data=json.dumps({'phone': phone, 'code': code}),
            content_type='application/json',
        )

    def test_send_code_returns_demo_code(self):
        body = self._code().json()
        self.assertEqual(body['code'], '00000')
        self.assertEqual(body['data']['code'], '123456')

    def test_login_creates_user_and_token(self):
        body = self._login().json()
        self.assertEqual(body['code'], '00000')
        self.assertTrue(body['data']['accessToken'])
        self.assertEqual(body['data']['user']['phone'], self.PHONE)
        self.assertTrue(UserInfo.objects.filter(phone=self.PHONE).exists())

    def test_relogin_reuses_same_user(self):
        first = self._login().json()['data']['user']['id']
        second = self._login().json()['data']['user']['id']
        self.assertEqual(first, second)
        self.assertEqual(UserInfo.objects.filter(phone=self.PHONE).count(), 1)

    def test_wrong_code_rejected(self):
        body = self._login(code='000000').json()
        self.assertIn('验证码错误', body['info'])
        self.assertEqual(UserInfo.objects.filter(phone=self.PHONE).count(), 0)

    def test_missing_phone_rejected(self):
        body = self._login(phone='').json()
        self.assertIn('手机号不能为空', body['info'])

    def test_profile_requires_auth(self):
        resp = self.client.get('/api/v1/users/profile')
        self.assertEqual(resp.status_code, 401)

    def test_profile_returns_login_user(self):
        token = self._login().json()['data']['accessToken']
        resp = self.client.get('/api/v1/users/profile', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(resp.json()['data']['phone'], self.PHONE)


class AddressScopeTest(TestCase):
    """地址的归属过滤与删除方法限制。"""

    def setUp(self):
        self.auth_user, self.info = self._customer('ad_a', '顾客A', '13900000091')
        self.other_auth, self.other_info = self._customer('ad_b', '顾客B', '13900000092')
        self.token = make_token(self.auth_user)
        self.address = UserAddress.objects.create(
            user=self.info, receiver='顾客A', phone='13900000091', detail='示例路1号',
        )
        self.other_address = UserAddress.objects.create(
            user=self.other_info, receiver='顾客B', phone='13900000092', detail='示例路2号',
        )

    @staticmethod
    def _customer(username, nickname, phone):
        auth_user = User.objects.create_user(username=username, password='pw123456')
        info = UserInfo.objects.create(auth_user=auth_user, nickname=nickname, phone=phone)
        return auth_user, info

    def test_list_only_own_addresses(self):
        resp = self.client.get('/api/v1/addresses', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        ids = [a['id'] for a in resp.json()['data']]
        self.assertIn(self.address.id, ids)
        self.assertNotIn(self.other_address.id, ids)

    def test_create_address(self):
        resp = self.client.post(
            '/api/v1/addresses',
            data=json.dumps({'name': '张三', 'phone': '13900000093', 'detail': '新地址9号'}),
            content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        self.assertEqual(resp.json()['code'], '00000')
        self.assertTrue(UserAddress.objects.filter(user=self.info, detail='新地址9号').exists())

    def test_delete_own_address(self):
        resp = self.client.delete(
            f'/api/v1/addresses/{self.address.id}', HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        self.assertEqual(resp.json()['code'], '00000')
        self.assertFalse(UserAddress.objects.filter(id=self.address.id).exists())

    def test_delete_other_customers_address_is_noop(self):
        resp = self.client.delete(
            f'/api/v1/addresses/{self.other_address.id}', HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        self.assertEqual(resp.json()['code'], '00000')
        self.assertTrue(UserAddress.objects.filter(id=self.other_address.id).exists())

    def test_get_delete_is_not_allowed(self):
        """删除地址只接受 DELETE，GET 不再触发删除。"""
        resp = self.client.get(
            f'/api/v1/addresses/{self.address.id}', HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(UserAddress.objects.filter(id=self.address.id).exists())
