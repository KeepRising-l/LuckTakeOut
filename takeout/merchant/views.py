"""商户域接口：附近商户、详情、分类。"""

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from django.views.decorators.http import require_http_methods

from common.response import fail, ok

from .models import MerchantInfo


def merchant_to_dict(m):
    """顾客端展示口径：名称、简介、评分（评价均值）、配送费；不含销量与距离。"""
    rating = getattr(m, 'rating_avg', None)
    return {
        'id': m.id,
        'name': m.name,
        'avatar': m.logo or '',
        'logo': m.logo or '',
        'description': m.description or '',
        'merchantDescription': m.description or '',
        'rating': round(float(rating), 1) if rating is not None else None,
        'deliveryFee': float(settings.DELIVERY_FEE),
        'address': m.address or '',
        'phone': m.phone or '',
        'status': m.status,
        'categoryId': m.category_id,
    }


@require_http_methods(['GET'])
def nearby(request):
    keyword = (request.GET.get('keyword') or '').strip()
    qs = MerchantInfo.objects.filter(status=20).annotate(rating_avg=Avg('reviews__rating')).order_by('id')
    if keyword:
        # 分类入口/搜索词同时匹配：商户名、所属分类、简介、在售菜品名
        qs = qs.filter(
            Q(name__icontains=keyword)
            | Q(category__name__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(products__name__icontains=keyword)
        ).distinct()
    try:
        page = int(request.GET.get('page') or 1)
        size = int(request.GET.get('size') or 10)
    except ValueError:
        page, size = 1, 10
    page_obj = Paginator(qs, size).get_page(page)
    return ok([merchant_to_dict(m) for m in page_obj.object_list])


@require_http_methods(['GET'])
def detail(request, pk):
    # 顾客端只展示已过审商户（与 nearby 列表口径一致）
    m = MerchantInfo.objects.filter(id=pk, status=20).annotate(
        rating_avg=Avg('reviews__rating')
    ).first()
    if not m:
        return fail('商家不存在或未通过审核')
    return ok(merchant_to_dict(m))


@require_http_methods(['GET'])
def categories(request, pk):
    m = MerchantInfo.objects.filter(id=pk).first()
    if not m:
        return fail('商家不存在')
    data = [
        {'id': c.id, 'name': c.name, 'sort': c.sort}
        for c in m.categories.all().order_by('sort', 'id')
    ]
    if not data:
        data = [{'id': 0, 'name': '全部', 'sort': 0}]
    return ok(data)
