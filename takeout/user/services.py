"""用户域跨视图复用的业务校验。"""

import re

MOBILE_RE = re.compile(r'^1[3-9]\d{9}$')


def _clean_text(value, label, max_length, required=False):
    """去首尾空白并校验长度，返回 (清洗后的值, 错误信息)。"""
    if value is None:
        value = ''
    if not isinstance(value, str):
        return None, f'{label}格式不正确'
    value = value.strip()
    if required and not value:
        return None, f'请填写{label}'
    if len(value) > max_length:
        return None, f'{label}不能超过 {max_length} 个字符'
    return value, ''


def validate_address_payload(data):
    """校验并清洗收货地址入参，返回 (清洗后的字段, 错误信息)。

    后端不信任前端校验：姓名、手机号、详细地址均为必填，
    手机号须为 11 位大陆手机号，省市区选填但限制长度。
    """
    receiver, error = _clean_text(
        data.get('name') or data.get('receiver'), '收货人', 50, required=True,
    )
    if error:
        return None, error

    phone, error = _clean_text(data.get('phone'), '联系电话', 20)
    if error:
        return None, error
    if not phone or not MOBILE_RE.match(phone):
        return None, '请填写正确的 11 位手机号'

    detail, error = _clean_text(data.get('detail'), '详细地址', 200, required=True)
    if error:
        return None, error

    cleaned = {'receiver': receiver, 'phone': phone, 'detail': detail}
    for key, label in (('province', '省份'), ('city', '城市'), ('district', '区县')):
        value, error = _clean_text(data.get(key), label, 50)
        if error:
            return None, error
        cleaned[key] = value
    return cleaned, ''
