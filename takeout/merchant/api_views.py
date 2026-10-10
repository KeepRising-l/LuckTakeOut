"""商户端接口：登录、资料、营业状态。"""

from django.contrib.auth import authenticate
from django.views.decorators.http import require_http_methods

from common.auth import make_merchant_token, merchant_login_required
from common.response import fail_m, ok_m
from common.utils import get_json

from .models import MerchantInfo


def merchant_to_dict(m):
    return {
        'id': m.id,
        'merchantId': m.id,
        'name': m.name,
        'merchantName': m.name,
        'avatar': m.logo or '',
        'logo': m.logo or '',
        'description': m.description or '',
        'phone': m.phone or '',
        'address': m.address or '',
        'categoryId': m.category_id,
        'status': m.status,
        'open': True,
        'openTime': m.open_time.strftime('%H:%M') if m.open_time else '09:00',
        'closeTime': m.close_time.strftime('%H:%M') if m.close_time else '21:00',
        'createTime': m.create_time.strftime('%Y-%m-%d %H:%M:%S') if m.create_time else '',
    }


@require_http_methods(['POST'])
def login(request):
    data = get_json(request)
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    user = authenticate(username=username, password=password)
    if user is None:
        return fail_m('用户名或密码错误')
    merchant = MerchantInfo.objects.filter(auth_user=user).first()
    if merchant is None:
        return fail_m('该账号不是商户账号')
    if merchant.status != 20:
        return fail_m('商户尚未通过审核，无法登录')
    token = make_merchant_token(user)
    return ok_m({
        'token': token,
        'merchantId': merchant.id,
        'merchantName': merchant.name,
        'avatar': merchant.logo or '',
    })


@require_http_methods(['GET'])
@merchant_login_required
def current(request):
    return ok_m(merchant_to_dict(request.merchant))


@require_http_methods(['PUT', 'POST'])
@merchant_login_required
def update_info(request):
    data = get_json(request)
    m = request.merchant
    if data.get('name'):
        m.name = data['name']
    if 'description' in data:
        m.description = data.get('description') or ''
    if 'phone' in data:
        m.phone = data.get('phone') or ''
    if 'address' in data:
        m.address = data.get('address') or ''
    if 'logo' in data and data.get('logo'):
        m.logo = data['logo']
    m.save()
    return ok_m(merchant_to_dict(m))


@require_http_methods(['PUT', 'POST'])
@merchant_login_required
def update_status(request):
    data = get_json(request)
    # 营业状态为演示占位：直接回显
    return ok_m({'status': data.get('status', 1)})
