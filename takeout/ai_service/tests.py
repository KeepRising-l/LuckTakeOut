"""AI 点餐助手的作用域与审计测试。

覆盖：四个接口的登录要求、会话以登录顾客为归属、跨顾客访问会话与草稿被拒、
审计记录的操作者非空。
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from common.auth import make_token
from merchant.models import MerchantInfo
from platform_ops.models import OperationLog
from user.models import UserInfo

from .models import ChatSession, OrderDraft
from .tools import execute_tool


def make_customer(username, nickname, phone):
    auth_user = User.objects.create_user(username=username, password='pw123456')
    info = UserInfo.objects.create(auth_user=auth_user, nickname=nickname, phone=phone)
    return auth_user, info


def make_merchant(username, name):
    auth_user = User.objects.create_user(username=username, password='pw123456')
    return MerchantInfo.objects.create(auth_user=auth_user, name=name, status=20)


class AiEndpointAuthTest(TestCase):
    """四个接口都必须要求登录。"""

    def setUp(self):
        self.auth_user, self.customer = make_customer('ai_c1', '顾客一', '13800000001')

    def test_endpoints_reject_anonymous(self):
        cases = [
            ('post', '/api/v1/ai/session', {}),
            ('post', '/api/v1/ai/chat', {'sessionId': 1, 'message': '你好'}),
            ('get', '/api/v1/ai/drafts/1', None),
            ('post', '/api/v1/ai/drafts/1/confirm', {}),
        ]
        for method, url, payload in cases:
            with self.subTest(url=url):
                client_method = getattr(self.client, method)
                resp = client_method(url, data=payload)
                self.assertEqual(resp.status_code, 401)
                self.assertEqual(resp.json()['code'], 'A0401')
        self.assertEqual(ChatSession.objects.count(), 0)

    def test_authorized_request_passes(self):
        token = make_token(self.auth_user)
        resp = self.client.post(
            '/api/v1/ai/session', data={},
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['code'], '00000')
        self.assertEqual(ChatSession.objects.count(), 1)


class AiSessionScopeTest(TestCase):
    """会话与草稿的作用域是当前登录的顾客。"""

    def setUp(self):
        self.a_user, self.a_info = make_customer('ai_a', '顾客A', '13800000002')
        self.b_user, self.b_info = make_customer('ai_b', '顾客B', '13800000003')
        self.merchant = make_merchant('ai_shop', '测试商户')
        self.token_a = make_token(self.a_user)
        self.token_b = make_token(self.b_user)

    def _post(self, url, payload, token):
        return self.client.post(
            url, data=json.dumps(payload), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )

    def test_session_belongs_to_logged_in_customer(self):
        resp = self._post('/api/v1/ai/session', {'customerId': self.b_info.id}, self.token_a)
        self.assertEqual(resp.json()['code'], '00000')
        session = ChatSession.objects.latest('id')
        self.assertEqual(session.customer_id, self.a_info.id)

    def test_chat_rejects_other_customers_session(self):
        session = ChatSession.objects.create(customer=self.a_info, status=10)
        resp = self._post('/api/v1/ai/chat', {'sessionId': session.id, 'message': '你好'}, self.token_b)
        body = resp.json()
        self.assertNotEqual(body['code'], '00000')
        self.assertIn('会话不存在', body['info'])

    def test_draft_detail_rejects_other_customers_draft(self):
        draft = OrderDraft.objects.create(
            customer=self.a_info, merchant=self.merchant, total_amount=0,
        )
        resp = self.client.get(
            f'/api/v1/ai/drafts/{draft.id}', HTTP_AUTHORIZATION=f'Bearer {self.token_b}',
        )
        body = resp.json()
        self.assertNotEqual(body['code'], '00000')
        self.assertIn('草稿不存在', body['info'])

    def test_draft_confirm_rejects_other_customers_draft(self):
        draft = OrderDraft.objects.create(
            customer=self.a_info, merchant=self.merchant, total_amount=0,
        )
        resp = self._post(f'/api/v1/ai/drafts/{draft.id}/confirm', {}, self.token_b)
        body = resp.json()
        self.assertNotEqual(body['code'], '00000')
        self.assertIn('草稿不存在', body['info'])
        draft.refresh_from_db()
        self.assertEqual(draft.status, OrderDraft.STATUS_PENDING)


class AiAuditTest(TestCase):
    """工具调用的审计记录里，操作者标识不再是空的。"""

    def setUp(self):
        _, self.customer = make_customer('ai_audit', '顾客审计', '13800000004')
        self.session = ChatSession.objects.create(customer=self.customer, status=10)

    def test_audit_records_customer_as_actor(self):
        execute_tool('search_merchant', {'keyword': ''}, self.session)
        log = OperationLog.objects.latest('id')
        self.assertEqual(log.actor_id, self.customer.id)
        self.assertEqual(log.actor_role, 'ai')
        self.assertEqual(log.action, 'search_merchant')
