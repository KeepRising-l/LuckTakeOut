"""评价接口测试。

覆盖：一单一评约束、评分钳制 1–5、仅已完成订单可评价、订单归属校验，
以及商户评价列表的全量均分统计。
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from common.auth import make_token
from merchant.models import MerchantInfo
from order.models import OrderInfo, OrderItem
from product.models import ProductInfo
from user.models import UserInfo

from .models import Review


def make_customer(username, nickname, phone):
    auth_user = User.objects.create_user(username=username, password='pw123456')
    info = UserInfo.objects.create(auth_user=auth_user, nickname=nickname, phone=phone)
    return auth_user, info


class CreateReviewTest(TestCase):
    """顾客按单评价的核心约束。"""

    def setUp(self):
        self.auth_user, self.info = make_customer('rv_c1', '顾客A', '13900000061')
        self.other_auth, self.other_info = make_customer('rv_c2', '顾客B', '13900000062')
        self.token = make_token(self.auth_user)
        self.merchant = MerchantInfo.objects.create(
            auth_user=User.objects.create_user(username='rv_shop', password='pw123456'),
            name='测试商户', status=20,
        )
        self.product = ProductInfo.objects.create(
            merchant=self.merchant, name='测试菜品', price=10, stock=5, status=10,
        )
        self.order = OrderInfo.objects.create(
            order_no='RV0001', user=self.info, merchant=self.merchant,
            address_snapshot='示例路1号', total_amount=10, delivery_fee=2, pay_amount=12,
            status=OrderInfo.STATUS_FINISHED,
        )
        OrderItem.objects.create(
            order=self.order, product=self.product, product_name=self.product.name,
            price=self.product.price, quantity=1, amount=10,
        )

    def _review(self, payload, token=None, order_id=None):
        return self.client.post(
            f'/api/v1/orders/{order_id or self.order.id}/review',
            data=json.dumps(payload), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token or self.token}',
        )

    def test_review_finished_order(self):
        resp = self._review({'rating': 5, 'content': '好吃'})
        self.assertEqual(resp.json()['code'], '00000')
        self.assertEqual(Review.objects.count(), 1)
        review = Review.objects.first()
        self.assertEqual(review.target_type, Review.TARGET_MERCHANT)

    def test_unfinished_order_rejected(self):
        self.order.status = OrderInfo.STATUS_DELIVERING
        self.order.save()
        resp = self._review({'rating': 5})
        self.assertIn('订单完成后才能评价', resp.json()['info'])

    def test_duplicate_review_rejected(self):
        self._review({'rating': 5})
        resp = self._review({'rating': 4})
        self.assertIn('已评价过', resp.json()['info'])
        self.assertEqual(Review.objects.count(), 1)

    def test_rating_clamped_to_1_5(self):
        self._review({'rating': 99})
        self.assertEqual(Review.objects.first().rating, 5)

    def test_rating_floor_clamped_to_1(self):
        self._review({'rating': -3})
        self.assertEqual(Review.objects.first().rating, 1)

    def test_other_customers_order_rejected(self):
        resp = self._review({'rating': 5}, token=make_token(self.other_auth))
        self.assertIn('订单不存在', resp.json()['info'])

    def test_review_with_order_product_targets_product(self):
        resp = self._review({'rating': 4, 'productId': self.product.id})
        self.assertEqual(resp.json()['code'], '00000')
        review = Review.objects.first()
        self.assertEqual(review.target_type, Review.TARGET_PRODUCT)
        self.assertEqual(review.product, self.product)

    def test_product_not_in_order_rejected(self):
        stray = ProductInfo.objects.create(
            merchant=self.merchant, name='别的菜', price=5, stock=5, status=10,
        )
        resp = self._review({'rating': 4, 'productId': stray.id})
        self.assertIn('不存在此商品', resp.json()['info'])


class MerchantReviewsStatsTest(TestCase):
    """商户评价列表：均分统计全量评价，而非仅最近 50 条。"""

    def setUp(self):
        _, info = make_customer('rv_s1', '顾客S', '13900000071')
        self.merchant = MerchantInfo.objects.create(
            auth_user=User.objects.create_user(username='rv_sshop', password='pw123456'),
            name='统计商户', status=20,
        )
        for i in range(3):
            order = OrderInfo.objects.create(
                order_no=f'RVSTAT{i:02d}', user=info, merchant=self.merchant,
                address_snapshot='示例路1号', total_amount=10, delivery_fee=2, pay_amount=12,
                status=OrderInfo.STATUS_FINISHED,
            )
            Review.objects.create(
                order=order, user=info, merchant=self.merchant,
                target_type=Review.TARGET_MERCHANT, rating=5 if i < 2 else 1,
            )

    def test_avg_over_all_reviews(self):
        resp = self.client.get(f'/api/v1/merchants/{self.merchant.id}/reviews')
        data = resp.json()['data']
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['avgRating'], round((5 + 5 + 1) / 3, 1))
