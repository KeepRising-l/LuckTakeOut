"""商品（菜品）域接口。"""

from django.views.decorators.http import require_http_methods

from common.response import fail, ok

from .models import ProductInfo


def product_to_dict(p):
    return {
        'id': p.id,
        'productId': p.id,
        'merchantId': p.merchant_id,
        'categoryId': p.category_id,
        'name': p.name,
        'productName': p.name,
        'description': p.description,
        'productDescription': p.description,
        'price': float(p.price),
        'productPrice': float(p.price),
        'mainImage': p.image,
        'productImage': p.image,
        'stock': p.stock,
        'categoryName': p.category.name if p.category else '',
    }


@require_http_methods(['GET'])
def merchant_products(request, pk):
    qs = ProductInfo.objects.filter(merchant_id=pk, status=10).order_by('id')
    category_id = request.GET.get('categoryId')
    if category_id and category_id not in ('0', ''):
        qs = qs.filter(category_id=category_id)
    return ok([product_to_dict(p) for p in qs])


@require_http_methods(['GET'])
def product_detail(request, pk):
    p = ProductInfo.objects.filter(id=pk).first()
    if not p:
        return fail('商品不存在')
    return ok(product_to_dict(p))


@require_http_methods(['GET'])
def product_search(request):
    keyword = (request.GET.get('keyword') or '').strip()
    qs = ProductInfo.objects.filter(status=10)
    if keyword:
        qs = qs.filter(name__icontains=keyword)
    return ok([product_to_dict(p) for p in qs.order_by('id')[:50]])
