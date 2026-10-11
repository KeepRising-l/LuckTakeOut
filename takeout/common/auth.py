"""简易 Token 认证（基于 Django 签名，无需额外依赖）。"""

from functools import wraps

from django.contrib.auth.models import User
from django.core import signing
from django.http import JsonResponse

TOKEN_SALT = 'takeout-api-token'
TOKEN_MAX_AGE = 7 * 24 * 3600  # 7 天


def make_token(auth_user):
    return signing.dumps({'uid': auth_user.id}, salt=TOKEN_SALT)


def get_user_from_request(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[len('Bearer '):].strip()
    try:
        payload = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
    except Exception:
        return None
    return User.objects.filter(id=payload.get('uid')).first()


def api_login_required(view):
    """要求登录的接口装饰器；未登录返回 HTTP 401。"""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        auth_user = get_user_from_request(request)
        if auth_user is None:
            return JsonResponse(
                {'code': 'A0401', 'info': '未登录或登录已过期', 'data': None},
                status=401,
                json_dumps_params={'ensure_ascii': False},
            )
        request.user = auth_user
        return view(request, *args, **kwargs)

    return wrapper


# ---- 商户端 Token（独立盐值）----

MERCHANT_SALT = 'takeout-merchant-token'


def make_merchant_token(auth_user):
    return signing.dumps({'uid': auth_user.id}, salt=MERCHANT_SALT)


def _get_merchant_user(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[len('Bearer '):].strip()
    try:
        payload = signing.loads(token, salt=MERCHANT_SALT, max_age=TOKEN_MAX_AGE)
    except Exception:
        return None
    return User.objects.filter(id=payload.get('uid')).first()


def merchant_login_required(view):
    """要求商户登录；把 merchant 注入到 request，未登录返回 401。"""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        from merchant.models import MerchantInfo

        auth_user = _get_merchant_user(request)
        merchant = None
        if auth_user is not None:
            merchant = MerchantInfo.objects.filter(auth_user=auth_user).first()
        if merchant is None:
            return JsonResponse(
                {'code': 'A0401', 'info': '未登录或登录已过期', 'data': None},
                status=401,
                json_dumps_params={'ensure_ascii': False},
            )
        request.user = auth_user
        request.merchant = merchant
        return view(request, *args, **kwargs)

    return wrapper


def merchant_approved_required(view):
    """要求商户登录且已通过入驻审核（R3）。

    未登录返回 401；未通过审核返回 403——未过审商户登录后只能查看入驻审核状态。

    约定：新增的商户端**经营类**接口（菜品、订单、营业统计、店铺信息维护）必须挂本装饰器，
    只有登录与查看本人资料这两个接口使用 merchant_login_required。
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        from merchant.models import MerchantInfo

        auth_user = _get_merchant_user(request)
        merchant = None
        if auth_user is not None:
            merchant = MerchantInfo.objects.filter(auth_user=auth_user).first()
        if merchant is None:
            return JsonResponse(
                {'code': 'A0401', 'info': '未登录或登录已过期', 'data': None},
                status=401,
                json_dumps_params={'ensure_ascii': False},
            )
        request.user = auth_user
        request.merchant = merchant
        if merchant.status != MerchantInfo.STATUS_APPROVED:
            return JsonResponse(
                {
                    'code': 'A0403',
                    'info': '商户尚未通过入驻审核，暂时无法使用经营功能',
                    'data': {'status': merchant.status},
                },
                status=403,
                json_dumps_params={'ensure_ascii': False},
            )
        return view(request, *args, **kwargs)

    return wrapper


# ---- 骑手端 Token（独立盐值）----

RIDER_SALT = 'takeout-rider-token'


def make_rider_token(auth_user):
    return signing.dumps({'uid': auth_user.id}, salt=RIDER_SALT)


def _get_rider_user(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth[len('Bearer '):].strip()
    try:
        payload = signing.loads(token, salt=RIDER_SALT, max_age=TOKEN_MAX_AGE)
    except Exception:
        return None
    return User.objects.filter(id=payload.get('uid')).first()


def rider_login_required(view):
    """要求骑手登录；把 rider 注入到 request，未登录返回 401（骑手侧 fail 格式）。"""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        from delivery.models import Rider

        auth_user = _get_rider_user(request)
        rider = None
        if auth_user is not None:
            rider = Rider.objects.filter(auth_user=auth_user).first()
        if rider is None:
            return JsonResponse(
                {'code': 'A0401', 'info': '未登录或登录已过期', 'data': None},
                status=401,
                json_dumps_params={'ensure_ascii': False},
            )
        request.user = auth_user
        request.rider = rider
        return view(request, *args, **kwargs)

    return wrapper


# ---- 平台运营端 Token（独立盐值，要求 is_staff）----

PLATFORM_SALT = 'takeout-platform-token'


def make_platform_token(auth_user):
    return signing.dumps({'uid': auth_user.id}, salt=PLATFORM_SALT)


def platform_login_required(view):
    """要求平台运营登录（is_staff）；未登录/非运营返回 401。"""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        auth_user = None
        if auth.startswith('Bearer '):
            token = auth[len('Bearer '):].strip()
            try:
                payload = signing.loads(token, salt=PLATFORM_SALT, max_age=TOKEN_MAX_AGE)
                auth_user = User.objects.filter(id=payload.get('uid')).first()
            except Exception:
                auth_user = None
        if auth_user is None or not auth_user.is_staff:
            return JsonResponse(
                {'code': 'A0401', 'info': '未登录或无运营权限', 'data': None},
                status=401,
                json_dumps_params={'ensure_ascii': False},
            )
        request.user = auth_user
        return view(request, *args, **kwargs)

    return wrapper
