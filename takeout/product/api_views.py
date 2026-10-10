"""商户端菜品与分类管理接口。"""

from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods

from common.auth import merchant_login_required
from common.response import fail_m, ok_m
from common.utils import get_json

from .models import ProductCategory, ProductInfo

PRODUCT_STATUS_MAP = {10: 'ACTIVE', 20: 'INACTIVE'}
PRODUCT_STATUS_REV = {'ACTIVE': 10, 'INACTIVE': 20}


def product_to_dict(p):
    return {
        'id': p.id,
        'name': p.name,
        'description': p.description or '',
        'image': p.image or '',
        'price': float(p.price),
        'stock': p.stock,
        'status': PRODUCT_STATUS_MAP.get(p.status, 'ACTIVE'),
        'categoryId': p.category_id,
        'categoryName': p.category.name if p.category else '',
        'createTime': p.create_time.strftime('%Y-%m-%d %H:%M:%S') if p.create_time else '',
    }


def category_to_dict(c):
    return {
        'id': c.id,
        'name': c.name,
        'description': '',
        'sortOrder': c.sort,
        'status': 'ACTIVE',
        'productCount': c.products.count(),
        'createTime': c.create_time.strftime('%Y-%m-%d %H:%M:%S') if c.create_time else '',
    }


# ---- 分类 ----

@require_http_methods(['GET'])
@merchant_login_required
def category_list(request):
    qs = ProductCategory.objects.filter(merchant=request.merchant).order_by('sort', 'id')
    return ok_m([category_to_dict(c) for c in qs])


@require_http_methods(['POST'])
@merchant_login_required
def category_create(request):
    data = get_json(request)
    name = (data.get('name') or '').strip()
    if not name:
        return fail_m('分类名称不能为空')
    c = ProductCategory.objects.create(
        merchant=request.merchant,
        name=name,
        sort=int(data.get('sortOrder') or 0),
    )
    return ok_m(category_to_dict(c), message='分类创建成功')


@require_http_methods(['PUT', 'POST'])
@merchant_login_required
def category_update(request, pk):
    c = ProductCategory.objects.filter(id=pk, merchant=request.merchant).first()
    if not c:
        return fail_m('分类不存在')
    data = get_json(request)
    if data.get('name'):
        c.name = data['name']
    if 'sortOrder' in data:
        c.sort = int(data.get('sortOrder') or 0)
    c.save()
    return ok_m(category_to_dict(c), message='分类更新成功')


@require_http_methods(['DELETE', 'POST'])
@merchant_login_required
def category_delete(request, pk):
    ProductCategory.objects.filter(id=pk, merchant=request.merchant).delete()
    return ok_m(True, message='分类已删除')


# ---- 菜品 ----

@require_http_methods(['GET'])
@merchant_login_required
def product_list(request):
    qs = ProductInfo.objects.filter(merchant=request.merchant).order_by('-id')

    search = request.GET.get('search')
    if search:
        qs = qs.filter(name__icontains=search)
    category = request.GET.get('category')
    if category:
        qs = qs.filter(category_id=category)
    status = request.GET.get('status')
    if status in PRODUCT_STATUS_REV:
        qs = qs.filter(status=PRODUCT_STATUS_REV[status])

    try:
        page = int(request.GET.get('page') or 1)
        size = int(request.GET.get('size') or 12)
    except ValueError:
        page, size = 1, 12
    paginator = Paginator(qs, size)
    page_obj = paginator.get_page(page)
    return ok_m({
        'items': [product_to_dict(p) for p in page_obj.object_list],
        'total': paginator.count,
        'totalPages': paginator.num_pages,
        'page': page,
        'size': size,
    })


@require_http_methods(['POST'])
@merchant_login_required
def product_create(request):
    data = get_json(request)
    name = (data.get('name') or '').strip()
    if not name:
        return fail_m('菜品名称不能为空')
    try:
        price = Decimal(str(data.get('price') or 0))
    except (InvalidOperation, ValueError):
        return fail_m('价格格式不正确')
    p = ProductInfo.objects.create(
        merchant=request.merchant,
        category_id=data.get('categoryId') or None,
        name=name,
        description=data.get('description') or '',
        image=data.get('image') or '',
        price=price,
        stock=int(data.get('stock') or 0),
        status=PRODUCT_STATUS_REV.get(data.get('status'), 10),
    )
    return ok_m(product_to_dict(p), message='菜品添加成功')


@require_http_methods(['GET'])
@merchant_login_required
def product_detail(request, pk):
    p = ProductInfo.objects.filter(id=pk, merchant=request.merchant).first()
    if not p:
        return fail_m('菜品不存在')
    return ok_m(product_to_dict(p))


@require_http_methods(['PUT', 'POST'])
@merchant_login_required
def product_update(request, pk):
    p = ProductInfo.objects.filter(id=pk, merchant=request.merchant).first()
    if not p:
        return fail_m('菜品不存在')
    data = get_json(request)
    if data.get('name'):
        p.name = data['name']
    if 'categoryId' in data:
        p.category_id = data.get('categoryId') or None
    if 'price' in data:
        try:
            p.price = Decimal(str(data.get('price') or 0))
        except (InvalidOperation, ValueError):
            return fail_m('价格格式不正确')
    if 'stock' in data:
        p.stock = int(data.get('stock') or 0)
    if 'description' in data:
        p.description = data.get('description') or ''
    if 'image' in data and data.get('image'):
        p.image = data['image']
    p.save()
    return ok_m(product_to_dict(p), message='菜品更新成功')


@require_http_methods(['DELETE', 'POST'])
@merchant_login_required
def product_delete(request, pk):
    ProductInfo.objects.filter(id=pk, merchant=request.merchant).delete()
    return ok_m(True, message='菜品已删除')


@require_http_methods(['PUT', 'POST'])
@merchant_login_required
def product_update_status(request, pk):
    p = ProductInfo.objects.filter(id=pk, merchant=request.merchant).first()
    if not p:
        return fail_m('菜品不存在')
    data = get_json(request)
    status = data.get('status')
    if status in PRODUCT_STATUS_REV:
        p.status = PRODUCT_STATUS_REV[status]
        p.save()
    return ok_m(product_to_dict(p), message='状态已更新')


@require_http_methods(['PUT', 'POST'])
@merchant_login_required
def product_update_stock(request, pk):
    p = ProductInfo.objects.filter(id=pk, merchant=request.merchant).first()
    if not p:
        return fail_m('菜品不存在')
    data = get_json(request)
    try:
        p.stock = int(data.get('stock') or 0)
    except ValueError:
        return fail_m('库存格式不正确')
    p.save()
    return ok_m(product_to_dict(p), message='库存已更新')
