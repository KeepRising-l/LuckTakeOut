"""AI 点餐助手的作用域与审计测试。

覆盖：四个接口的登录要求、会话以登录顾客为归属、跨顾客访问会话与草稿被拒、
审计记录的操作者非空。
"""

import json
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from common.auth import make_token
from merchant.models import MerchantInfo
from order.models import OrderInfo, OrderItem
from platform_ops.models import OperationLog
from product.models import ProductInfo
from review.models import Review
from user.models import UserInfo

from .models import ChatSession, OrderDraft, OrderDraftItem
from .recommend import build_profile, build_reorder, recommend_dishes
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


class AiToolGuardTest(TestCase):
    """工具参数异常时的兜底：草稿过滤不可售/非法数量，评价查重与评分钳制。"""

    def setUp(self):
        self.auth_user, self.customer = make_customer('ai_guard', '守卫顾客', '13800000021')
        self.session = ChatSession.objects.create(customer=self.customer, status=10)
        self.merchant = make_merchant('ai_guard_shop', '测试商户')
        self.p_ok = ProductInfo.objects.create(
            merchant=self.merchant, name='可点菜品', price=Decimal('10.00'), stock=5, status=10,
        )
        self.p_off = ProductInfo.objects.create(
            merchant=self.merchant, name='下架菜品', price=Decimal('10.00'), stock=5, status=20,
        )

    def test_create_draft_skips_offline_and_bad_quantity(self):
        result = execute_tool('create_draft', {
            'merchant_id': self.merchant.id,
            'items': [
                {'product_id': self.p_ok.id, 'quantity': 2},
                {'product_id': self.p_off.id, 'quantity': 1},
                {'product_id': self.p_ok.id, 'quantity': -3},
                {'product_id': self.p_ok.id, 'quantity': 'abc'},
            ],
        }, self.session)
        draft = OrderDraft.objects.get(id=result['draftId'])
        self.assertEqual(list(draft.items.values_list('quantity', flat=True)), [2])

    def test_create_draft_all_invalid_returns_error(self):
        result = execute_tool('create_draft', {
            'merchant_id': self.merchant.id,
            'items': [{'product_id': self.p_off.id, 'quantity': 1}],
        }, self.session)
        self.assertIn('error', result)
        self.assertEqual(OrderDraft.objects.count(), 0)

    def test_confirm_rejects_negative_quantity_draft(self):
        draft = OrderDraft.objects.create(
            session=self.session, customer=self.customer, merchant=self.merchant,
            total_amount=Decimal('-10'), status=OrderDraft.STATUS_PENDING,
        )
        OrderDraftItem.objects.create(
            draft=draft, product=self.p_ok, quantity=-1, price_snapshot=self.p_ok.price,
        )
        resp = self.client.post(
            f'/api/v1/ai/drafts/{draft.id}/confirm', data='{}', content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {make_token(self.auth_user)}',
        )
        self.assertIn('数量非法', resp.json()['info'])

    def test_submit_review_clamps_rating_and_rejects_duplicate(self):
        order = OrderInfo.objects.create(
            order_no='AIGUARD01', user=self.customer, merchant=self.merchant,
            address_snapshot='测试地址', total_amount=10, delivery_fee=Decimal('2.00'),
            pay_amount=12, status=OrderInfo.STATUS_FINISHED,
        )
        first = execute_tool('submit_review', {'order_id': order.id, 'rating': 99}, self.session)
        self.assertTrue(first['ok'])
        review = Review.objects.get(order=order)
        self.assertEqual(review.rating, 5)
        second = execute_tool('submit_review', {'order_id': order.id, 'rating': 3}, self.session)
        self.assertFalse(second['ok'])
        self.assertIn('已评价过', second['message'])
        self.assertEqual(Review.objects.filter(order=order).count(), 1)


class RecommendTest(TestCase):
    """历史推荐与一键复购：画像口径、推荐理由、下架/缺货过滤。"""

    def setUp(self):
        self.auth_user, self.customer = make_customer('ai_rec1', '常客', '13800000011')
        self.merchant = make_merchant('ai_shop1', '测试川菜馆')
        self.p_hot = ProductInfo.objects.create(
            merchant=self.merchant, name='招牌套餐', price=Decimal('30.00'), stock=10, status=10,
        )
        self.p_side = ProductInfo.objects.create(
            merchant=self.merchant, name='配菜', price=Decimal('10.00'), stock=10, status=10,
        )
        self.p_off = ProductInfo.objects.create(
            merchant=self.merchant, name='已下架菜', price=Decimal('20.00'), stock=10, status=20,
        )
        self._make_order([(self.p_hot, 1), (self.p_side, 2)])
        self._make_order([(self.p_hot, 1)])

    def _make_order(self, pairs, status=OrderInfo.STATUS_FINISHED):
        total = sum((p.price * q for p, q in pairs), Decimal('0'))
        order = OrderInfo.objects.create(
            order_no=uuid.uuid4().hex[:20], user=self.customer, merchant=self.merchant,
            address_snapshot='测试地址', total_amount=total, delivery_fee=Decimal('2.00'),
            pay_amount=total + Decimal('2.00'), status=status,
        )
        for p, q in pairs:
            OrderItem.objects.create(
                order=order, product=p, product_name=p.name,
                price=p.price, quantity=q, amount=p.price * q,
            )
        return order

    def test_profile_counts_orders_not_items(self):
        """商户维度按订单数统计：两笔订单即使含 3 条明细也只算 2 单。"""
        profile = build_profile(self.customer)
        self.assertEqual(profile['orderCount'], 2)
        self.assertEqual(profile['topMerchants'][0]['orders'], 2)
        # 招牌套餐出现在两笔订单中
        self.assertEqual(profile['topDishes'][0]['name'], '招牌套餐')
        self.assertEqual(profile['topDishes'][0]['times'], 2)

    def test_recommend_prefers_history_and_explains(self):
        dishes = recommend_dishes(self.customer, limit=6)
        self.assertTrue(dishes)
        self.assertEqual(dishes[0]['name'], '招牌套餐')
        self.assertIn('你点过', dishes[0]['reason'])

    def test_recommend_excludes_offline(self):
        names = [d['name'] for d in recommend_dishes(self.customer, limit=10)]
        self.assertNotIn('已下架菜', names)

    def test_recommend_cold_start(self):
        """无历史顾客也能拿到推荐（走全站热销兜底）。"""
        _, stranger = make_customer('ai_new1', '新客', '13800000012')
        dishes = recommend_dishes(stranger, limit=3)
        self.assertTrue(dishes)
        self.assertTrue(all(d['reason'] for d in dishes))

    def test_reorder_skips_offline(self):
        """最近订单含下架菜时，复购草稿应跳过并记录 skipped。"""
        self._make_order([(self.p_hot, 1), (self.p_off, 1)])
        order, items, missing = build_reorder(self.customer)
        self.assertIsNotNone(order)
        self.assertEqual([p.name for p, _ in items], ['招牌套餐'])
        self.assertTrue(any('已下架菜' in m for m in missing))

    def test_reorder_skips_out_of_stock(self):
        self.p_hot.stock = 0
        self.p_hot.save()
        _, items, missing = build_reorder(self.customer)
        self.assertNotIn('招牌套餐', [p.name for p, _ in items])
        self.assertTrue(any('库存不足' in m for m in missing))

    def test_reorder_without_history(self):
        _, stranger = make_customer('ai_new2', '新客二', '13800000013')
        order, items, missing = build_reorder(stranger)
        self.assertIsNone(order)
        self.assertEqual(items, [])

    def test_recommend_endpoint_scope(self):
        """推荐接口返回的是当前登录顾客的画像。"""
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {make_token(self.auth_user)}'
        res = self.client.get('/api/v1/ai/recommend')
        self.assertEqual(res.status_code, 200)
        data = res.json()['data']
        self.assertEqual(data['profile']['orderCount'], 2)
        self.assertTrue(data['dishes'])

    def test_reorder_endpoint_creates_draft(self):
        """复购取最近一笔订单：最近一单只有 1 个菜，草稿也应为 1 条明细。"""
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {make_token(self.auth_user)}'
        res = self.client.post('/api/v1/ai/reorder', data='{}', content_type='application/json')
        self.assertEqual(res.status_code, 200)
        payload = res.json()['data']
        self.assertTrue(payload['draftId'])
        draft = OrderDraft.objects.get(id=payload['draftId'])
        self.assertEqual(draft.customer, self.customer)
        self.assertEqual(draft.merchant, self.merchant)
        self.assertEqual(draft.items.count(), 1)
        self.assertEqual(draft.items.first().product.name, '招牌套餐')
