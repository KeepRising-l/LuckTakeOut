"""统一响应格式：ResultAPI {code, info, data}，成功 code = '00000'。"""

from django.http import JsonResponse


def ok(data=None, info='success'):
    return JsonResponse(
        {'code': '00000', 'info': info, 'data': data},
        json_dumps_params={'ensure_ascii': False},
    )


def fail(info='请求失败', code='A0400', status=200):
    return JsonResponse(
        {'code': code, 'info': info, 'data': None},
        status=status,
        json_dumps_params={'ensure_ascii': False},
    )


def ok_m(data=None, message='success'):
    """兼容别名：商户端历史视图统一走 ResultAPI。"""
    return ok(data, info=message)


def fail_m(message='操作失败', status=200):
    """兼容别名：商户端历史视图统一走 ResultAPI。"""
    return fail(message, status=status)
