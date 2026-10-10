"""运营端（平台）接口：商户管理/审核、统计、订单与用户。契约见前端 admin/js/admin.js。"""

from django.db.models import Sum
from django.views.decorators.http import require_http_methods

from common.auth import make_platform_token, platform_login_required
from common.response import fail, ok
from common.utils import get_json
from merchant.models import MerchantInfo
from order.models import OrderInfo
from user.models import UserInfo

MERCHANT_STATUS_TEXT = {10: '待审核', 20: '营业中', 30: '已停业'}


def merchant_to_dict(m):
    return {
        'id': m.id,
        'name': m.name,
        'phone': m.phone or '',
        'address': m.address or '',
        'category': m.category.name if m.category else '',
        'status': m.status,
        'statusText': MERCHANT_STATUS_TEXT.get(m.status, ''),
        'createTime': m.create_time.strftime('%Y-%m-%d %H:%M:%S') if m.create_time else '',
    }


@require_http_methods(['GET'])
@platform_login_required
def merchants(request):
    qs = MerchantInfo.objects.all().order_by('-id')
    status = request.GET.get('status')
    if status == 'pending':
        qs = qs.filter(status=10)
    elif status in ('active', 'approve'):
        qs = qs.filter(status=20)
    elif status in ('blocked', 'reject'):
        qs = qs.filter(status=30)
    keyword = request.GET.get('keyword')
    if keyword:
        qs = qs.filter(name__icontains=keyword)
    return ok({'list': [merchant_to_dict(m) for m in qs[:100]], 'total': qs.count()})


@require_http_methods(['POST', 'PUT'])
@platform_login_required
def merchant_audit(request, pk):
    m = MerchantInfo.objects.filter(id=pk).first()
    if not m:
        return fail('商户不存在')
    data = get_json(request)
    action = data.get('action') or data.get('status')
    if action in ('approve', 'active', 20, '20'):
        m.status = 20
    elif action in ('reject', 'blocked', 30, '30'):
        m.status = 30
    else:
        return fail('未知的审核动作')
    m.save()
    return ok(merchant_to_dict(m), info='审核完成')


@require_http_methods(['GET'])
@platform_login_required
def statistics(request):
    revenue = OrderInfo.objects.filter(
        status__in=[20, 30, 40, 50]
    ).aggregate(s=Sum('pay_amount'))['s'] or 0
    return ok({
        'merchantCount': MerchantInfo.objects.count(),
        'pendingMerchantCount': MerchantInfo.objects.filter(status=10).count(),
        'userCount': UserInfo.objects.count(),
        'orderCount': OrderInfo.objects.count(),
        'revenue': float(revenue),
    })


@require_http_methods(['GET'])
@platform_login_required
def orders(request):
    qs = OrderInfo.objects.all().order_by('-id')[:100]
    data = [
        {
            'id': o.id,
            'orderNumber': o.order_no,
            'merchantName': o.merchant.name if o.merchant else '',
            'customerName': o.user.nickname if o.user else '',
            'totalAmount': float(o.pay_amount),
            'status': o.status,
            'createTime': o.create_time.strftime('%Y-%m-%d %H:%M:%S') if o.create_time else '',
        }
        for o in qs
    ]
    return ok(data)


@require_http_methods(['GET'])
@platform_login_required
def users(request):
    qs = UserInfo.objects.all().order_by('-id')[:100]
    data = [
        {
            'id': u.id,
            'nickname': u.nickname,
            'phone': u.phone,
            'createTime': u.create_time.strftime('%Y-%m-%d %H:%M:%S') if u.create_time else '',
        }
        for u in qs
    ]
    return ok(data)


@require_http_methods(['POST'])
def login(request):
    """平台运营登录：账号密码，要求 is_staff。"""
    from django.contrib.auth import authenticate

    data = get_json(request)
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    user = authenticate(username=username, password=password)
    if user is None or not user.is_staff:
        return fail('用户名或密码错误，或无运营权限')
    return ok({
        'token': make_platform_token(user),
        'username': user.username,
    })
