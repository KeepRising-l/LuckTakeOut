"""运营端（平台）接口测试。

覆盖：运营登录的 is_staff 门槛、商户审核的通过与驳回、非法审核动作拦截、
审核操作写操作日志，以及商户列表的状态筛选。
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from merchant.models import MerchantInfo

from .models import OperationLog


class PlatformAuditTest(TestCase):
    """商户审核是平台唯一的写操作，这里覆盖它的完整行为。"""

    def setUp(self):
        self.staff = User.objects.create_user(
            username='ops_admin', password='pw123456', is_staff=True,
        )
        self.normal = User.objects.create_user(username='ops_user', password='pw123456')
        self.merchant = MerchantInfo.objects.create(
            auth_user=User.objects.create_user(username='pa_shop', password='pw123456'),
            name='待审核商户', status=10,
        )

    def _login(self, username, password):
        resp = self.client.post(
            '/api/v1/platform/login', data=json.dumps({'username': username, 'password': password}),
            content_type='application/json',
        )
        return resp.json()

    def _audit(self, merchant_id, payload, token):
        return self.client.post(
            f'/api/v1/platform/merchants/{merchant_id}/audit',
            data=json.dumps(payload), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )

    def test_login_requires_staff(self):
        body = self._login('ops_user', 'pw123456')
        self.assertNotEqual(body['code'], '00000')
        body = self._login('ops_admin', 'pw123456')
        self.assertEqual(body['code'], '00000')
        self.assertTrue(body['data']['token'])

    def test_login_rejects_bad_password(self):
        body = self._login('ops_admin', 'wrong')
        self.assertNotEqual(body['code'], '00000')

    def test_audit_approve_writes_log(self):
        token = self._login('ops_admin', 'pw123456')['data']['token']
        resp = self._audit(self.merchant.id, {'action': 'approve'}, token)
        self.assertEqual(resp.json()['code'], '00000')
        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.status, 20)
        log = OperationLog.objects.latest('id')
        self.assertEqual(log.actor_role, 'platform')
        self.assertEqual(log.target_id, self.merchant.id)
        self.assertIn('10 -> 20', log.detail)

    def test_audit_reject_sets_status_30(self):
        token = self._login('ops_admin', 'pw123456')['data']['token']
        resp = self._audit(self.merchant.id, {'action': 'reject'}, token)
        self.assertEqual(resp.json()['code'], '00000')
        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.status, 30)

    def test_audit_unknown_action_rejected(self):
        token = self._login('ops_admin', 'pw123456')['data']['token']
        resp = self._audit(self.merchant.id, {'action': 'freeze'}, token)
        self.assertIn('未知的审核动作', resp.json()['info'])
        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.status, 10)
        self.assertEqual(OperationLog.objects.count(), 0)

    def test_audit_missing_merchant_rejected(self):
        token = self._login('ops_admin', 'pw123456')['data']['token']
        resp = self._audit(99999, {'action': 'approve'}, token)
        self.assertIn('商户不存在', resp.json()['info'])

    def test_audit_requires_platform_token(self):
        resp = self.client.post(
            f'/api/v1/platform/merchants/{self.merchant.id}/audit',
            data=json.dumps({'action': 'approve'}), content_type='application/json',
        )
        self.assertEqual(resp.status_code, 401)

    def test_merchant_list_status_filter(self):
        MerchantInfo.objects.create(
            auth_user=User.objects.create_user(username='pa_shop2', password='pw123456'),
            name='已过审商户', status=20,
        )
        token = self._login('ops_admin', 'pw123456')['data']['token']
        resp = self.client.get(
            '/api/v1/platform/merchants?status=pending', HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        data = resp.json()['data']
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['list'][0]['name'], '待审核商户')
