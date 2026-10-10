"""商户域接口：附近商户、详情、分类。"""

from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods

from common.response import fail, ok

from .models import MerchantInfo


def merchant_to_dict(m):
    return {
        'id': m.id,
        'name': m.name,
        'avatar': m.logo or '',
        'logo': m.logo or '',
        'description': m.description or '',
        'merchantDescription': m.description or '',
        'rating': 4.5,
        'monthlySales': 0,
        'sales': 0,
        'tags': [],
        'deliveryFee': 3.0,
        'deliveryTime': 30,
        'distance': 1.2,
        'address': m.address or '',
        'phone': m.phone or '',
        'status': m.status,
        'categoryId': m.category_id,
    }


@require_http_methods(['GET'])
def nearby(request):
    keyword = (request.GET.get('keyword') or '').strip()
    qs = MerchantInfo.objects.filter(status=20).order_by('id')
    if keyword:
        qs = qs.filter(name__icontains=keyword)
    try:
        page = int(request.GET.get('page') or 1)
        size = int(request.GET.get('size') or 10)
    except ValueError:
        page, size = 1, 10
    page_obj = Paginator(qs, size).get_page(page)
    return ok([merchant_to_dict(m) for m in page_obj.object_list])


@require_http_methods(['GET'])
def detail(request, pk):
    m = MerchantInfo.objects.filter(id=pk).first()
    if not m:
        return fail('商家不存在')
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
