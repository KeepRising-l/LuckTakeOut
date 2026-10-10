"""评价接口：商户评价列表 + 顾客按单评价。"""

from django.views.decorators.http import require_http_methods

from common.auth import api_login_required
from common.response import fail, ok
from common.utils import get_json
from order.models import OrderInfo
from user.models import UserInfo

from .models import Review


def review_to_dict(r):
    u = r.user
    return {
        'id': r.id,
        'orderId': r.order_id,
        'nickname': u.nickname if u else '',
        'rating': r.rating,
        'content': r.content,
        'targetType': r.target_type,
        'productId': r.product_id,
        'productName': r.product.name if r.product else '',
        'createTime': r.create_time.strftime('%Y-%m-%d %H:%M') if r.create_time else '',
    }


@require_http_methods(['GET'])
def merchant_reviews(request, pk):
    """某商户的评价列表。"""
    qs = Review.objects.filter(merchant_id=pk).order_by('-id')[:50]
    items = [review_to_dict(r) for r in qs]
    count = len(items)
    avg = round(sum(i['rating'] for i in items) / count, 1) if count else 5.0
    return ok({'list': items, 'total': count, 'avgRating': avg})


@require_http_methods(['POST'])
@api_login_required
def create_review(request, pk):
    """顾客评价已完成订单：一单一评，默认评商户，可指定菜品。"""
    info = UserInfo.objects.filter(auth_user=request.user).first()
    if not info:
        return fail('用户不存在', status=401)
    o = OrderInfo.objects.filter(id=pk, user=info).first()
    if not o:
        return fail('订单不存在')
    if o.status != OrderInfo.STATUS_FINISHED:
        return fail('订单完成后才能评价')
    if Review.objects.filter(order=o).exists():
        return fail('该订单已评价过')

    data = get_json(request)
    try:
        rating = int(data.get('rating') or 5)
    except (TypeError, ValueError):
        return fail('评分格式不正确')
    rating = min(5, max(1, rating))

    product = None
    product_id = data.get('productId')
    if product_id:
        product = o.items.filter(product_id=product_id).first()
        if not product:
            return fail('该订单中不存在此商品')

    target_type = Review.TARGET_PRODUCT if product else Review.TARGET_MERCHANT
    r = Review.objects.create(
        order=o,
        user=info,
        merchant=o.merchant,
        product=product.product if product else None,
        target_type=target_type,
        rating=rating,
        content=(data.get('content') or '')[:255],
    )
    return ok(review_to_dict(r), info='评价成功')
