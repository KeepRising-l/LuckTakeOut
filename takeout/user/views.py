"""用户域接口：登录、资料、收货地址。"""

import random

from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods

from common.auth import api_login_required, make_token
from common.response import fail, ok
from common.utils import get_json

from .models import UserAddress, UserInfo

# 演示用验证码存储（内存），并固定提供一个万能验证码
_CODE_STORE = {}
DEV_CODE = '123456'


def _user_to_dict(info):
    return {
        'id': info.id,
        'userId': info.auth_user_id,
        'nickname': info.nickname,
        'phone': info.phone,
        'gender': info.gender,
        'avatar': info.avatar,
    }


def _addr_to_dict(a):
    return {
        'id': a.id,
        'name': a.receiver,
        'phone': a.phone,
        'province': a.province,
        'city': a.city,
        'district': a.district,
        'detail': a.detail,
        'tag': '',
        'isDefault': a.is_default,
    }


def _find_or_create_user(phone):
    info = UserInfo.objects.filter(phone=phone).first()
    if info:
        return info
    auth_user, created = User.objects.get_or_create(username=f'user_{phone}')
    if created:
        auth_user.set_unusable_password()
        auth_user.save()
    return UserInfo.objects.create(
        auth_user=auth_user,
        nickname=f'用户{phone[-4:]}',
        phone=phone,
    )


@require_http_methods(['POST'])
def auth_code(request):
    data = get_json(request)
    phone = (data.get('phone') or '').strip()
    if not phone:
        return fail('手机号不能为空')
    code = DEV_CODE or f'{random.randint(0, 999999):06d}'
    _CODE_STORE[phone] = code
    # 演示环境直接把验证码返回，方便测试
    return ok({'phone': phone, 'code': code})


@require_http_methods(['POST'])
def auth_login(request):
    data = get_json(request)
    phone = (data.get('phone') or '').strip()
    code = (data.get('code') or '').strip()
    if not phone:
        return fail('手机号不能为空')
    if not code:
        return fail('验证码不能为空')
    expected = _CODE_STORE.get(phone)
    if code != DEV_CODE and code != expected:
        return fail('验证码错误')
    info = _find_or_create_user(phone)
    token = make_token(info.auth_user)
    return ok({'accessToken': token, 'refreshToken': token, 'user': _user_to_dict(info)})


@require_http_methods(['POST'])
def auth_callback(request):
    data = get_json(request)
    phone = (data.get('phone') or '').strip() or '13800000000'
    info = _find_or_create_user(phone)
    token = make_token(info.auth_user)
    return ok({'accessToken': token, 'refreshToken': token, 'user': _user_to_dict(info)})


@require_http_methods(['GET'])
@api_login_required
def profile(request):
    info = UserInfo.objects.filter(auth_user=request.user).first()
    if not info:
        return fail('用户不存在', status=401)
    return ok(_user_to_dict(info))


@require_http_methods(['GET'])
@api_login_required
def address_list(request):
    info = UserInfo.objects.filter(auth_user=request.user).first()
    if not info:
        return ok([])
    qs = info.addresses.all().order_by('-is_default', '-id')
    return ok([_addr_to_dict(a) for a in qs])


@require_http_methods(['POST'])
@api_login_required
def address_create(request):
    info = UserInfo.objects.filter(auth_user=request.user).first()
    if not info:
        return fail('用户不存在', status=401)
    data = get_json(request)
    addr = UserAddress.objects.create(
        user=info,
        receiver=data.get('name') or data.get('receiver') or '',
        phone=data.get('phone') or '',
        province=data.get('province') or '',
        city=data.get('city') or '',
        district=data.get('district') or '',
        detail=data.get('detail') or '',
        is_default=bool(data.get('isDefault')),
    )
    return ok(_addr_to_dict(addr))


@require_http_methods(['GET', 'DELETE', 'POST'])
@api_login_required
def address_delete(request, pk):
    info = UserInfo.objects.filter(auth_user=request.user).first()
    UserAddress.objects.filter(id=pk, user=info).delete()
    return ok(True)
