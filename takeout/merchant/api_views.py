"""商户端接口：注册入驻、登录、资料、营业状态。

未通过入驻审核的商户可以登录并查看审核状态，但只能使用 login 与 current 两个接口，
经营类接口由 merchant_approved_required 拦下（R3）。
"""

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.views.decorators.http import require_http_methods

from common.auth import make_merchant_token, merchant_approved_required, merchant_login_required
from common.response import fail_m, ok_m
from common.utils import get_json

from .models import MerchantInfo

# 注册时必填的字段：(请求字段名, 提示用名称)；店铺简介为选填
REQUIRED_REGISTER_FIELDS = (
    ('username', '账号'),
    ('password', '密码'),
    ('name', '店铺名称'),
    ('phone', '联系电话'),
    ('address', '店铺地址'),
)


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
        'open': bool(m.is_open),
        'openTime': m.open_time.strftime('%H:%M') if m.open_time else '09:00',
        'closeTime': m.close_time.strftime('%H:%M') if m.close_time else '21:00',
        'createTime': m.create_time.strftime('%Y-%m-%d %H:%M:%S') if m.create_time else '',
    }


@require_http_methods(['POST'])
def register(request):
    """商户注册与入驻申请：注册账号的同时提交入驻资料，生成「待审核」商户记录。"""
    data = get_json(request)
    values = {key: (data.get(key) or '').strip() for key, _ in REQUIRED_REGISTER_FIELDS}
    values['name'] = values['name'] or (data.get('merchantName') or '').strip()

    missing = [label for key, label in REQUIRED_REGISTER_FIELDS if not values.get(key)]
    if missing:
        return fail_m(f'请填写：{"、".join(missing)}')
    if len(values['password']) < 6:
        return fail_m('密码长度不能少于 6 位')
    if User.objects.filter(username=values['username']).exists():
        return fail_m('该账号已被占用，请更换')

    with transaction.atomic():
        auth_user = User.objects.create_user(
            username=values['username'], password=values['password'],
        )
        merchant = MerchantInfo.objects.create(
            auth_user=auth_user,
            name=values['name'],
            phone=values['phone'],
            address=values['address'],
            description=(data.get('description') or '').strip(),
            status=MerchantInfo.STATUS_PENDING,
        )

    return ok_m({
        'token': make_merchant_token(auth_user),
        'merchantId': merchant.id,
        'merchantName': merchant.name,
        'avatar': merchant.logo or '',
        'status': merchant.status,
    }, message='入驻申请已提交，请等待平台审核')


@require_http_methods(['POST'])
def login(request):
    """商户登录：账号密码校验通过即可登录，未过审商户登录后只能查看审核状态（R3）。"""
    data = get_json(request)
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    user = authenticate(username=username, password=password)
    if user is None:
        return fail_m('用户名或密码错误')
    merchant = MerchantInfo.objects.filter(auth_user=user).first()
    if merchant is None:
        return fail_m('该账号不是商户账号')
    token = make_merchant_token(user)
    return ok_m({
        'token': token,
        'merchantId': merchant.id,
        'merchantName': merchant.name,
        'avatar': merchant.logo or '',
        'status': merchant.status,
    })


@require_http_methods(['GET'])
@merchant_login_required
def current(request):
    return ok_m(merchant_to_dict(request.merchant))


@require_http_methods(['PUT', 'POST'])
@merchant_approved_required
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
@merchant_approved_required
def update_status(request):
    """营业状态：{open: true/false} 落库。"""
    data = get_json(request)
    open_value = data.get('open', data.get('status'))
    if isinstance(open_value, str):
        open_value = open_value.lower() in ('1', 'true', 'open')
    if not isinstance(open_value, bool):
        return fail_m('营业状态格式不正确')
    request.merchant.is_open = open_value
    request.merchant.save()
    return ok_m({'open': request.merchant.is_open}, message='营业状态已更新')


@require_http_methods(['POST'])
@merchant_approved_required
def upload_avatar(request):
    """商户头像/Logo 上传：multipart 字段 file，存 media/ 并更新 logo。"""
    import os
    import uuid

    from django.conf import settings
    from django.core.files.storage import default_storage

    f = request.FILES.get('file')
    if not f:
        return fail_m('请选择图片文件')
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        return fail_m('仅支持 jpg/png/webp/gif 图片')
    if f.size > 5 * 1024 * 1024:
        return fail_m('图片不能超过 5MB')

    name = f'avatar/{uuid.uuid4().hex}{ext}'
    saved = default_storage.save(name, f)
    url = f'{settings.MEDIA_URL}{saved}'
    request.merchant.logo = url
    request.merchant.save()
    return ok_m({'logo': url}, message='头像已更新')
