"""商户域跨模块复用的业务判断。"""

from django.utils import timezone

from .models import MerchantInfo


def merchant_accepting_orders(merchant, now=None):
    """判断商户当前是否可接单，返回 (是否可下单, 不可下单时的提示)。

    规则：
    - 未通过审核 → 不可接单；
    - 商户手动打烊（is_open=False）→ 不可接单；
    - 未配置营业时间（或起止时间相同）→ 视为全天营业；
    - 营业时间为左闭右开区间；跨天营业（如 22:00–02:00）按跨零点处理。

    下单接口与 AI 草稿确认共用此函数，避免两条下单路径口径不一致。
    """
    if merchant.status != MerchantInfo.STATUS_APPROVED:
        return False, '商家未通过审核，暂不接单'
    if not merchant.is_open:
        return False, '商家休息中，暂不接单'

    open_time, close_time = merchant.open_time, merchant.close_time
    if not open_time or not close_time or open_time == close_time:
        return True, ''

    current_dt = now or timezone.now()
    current = (
        timezone.localtime(current_dt).time()
        if timezone.is_aware(current_dt) else current_dt.time()
    )
    if open_time < close_time:
        in_business_hours = open_time <= current < close_time
    else:  # 跨天营业
        in_business_hours = current >= open_time or current < close_time

    if in_business_hours:
        return True, ''
    return False, (
        f'商家营业时间为 {open_time.strftime("%H:%M")}-{close_time.strftime("%H:%M")}，'
        '当前不在营业时间'
    )
