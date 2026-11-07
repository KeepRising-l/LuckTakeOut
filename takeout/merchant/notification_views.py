"""商户端站内信接口：新订单通知的查询与已读标记。"""

from django.utils import timezone
from django.views.decorators.http import require_http_methods

from common.auth import merchant_approved_required
from common.response import fail_m, ok_m
from common.utils import get_json
from platform_ops.models import Notification


def _to_dict(n):
    return {
        'id': n.id,
        'title': n.title,
        'content': n.content,
        'type': n.type,
        'isRead': n.is_read,
        'createTime': n.create_time.strftime('%Y-%m-%d %H:%M:%S') if n.create_time else '',
    }


@require_http_methods(['GET'])
@merchant_approved_required
def notification_list(request):
    """当前商户收到的站内信（默认最近 20 条）与未读数。"""
    qs = Notification.objects.filter(to_user=request.user).order_by('-id')
    try:
        limit = int(request.GET.get('limit') or 20)
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 50))
    return ok_m({
        'items': [_to_dict(n) for n in qs[:limit]],
        'unread': qs.filter(is_read=False).count(),
    })


@require_http_methods(['POST', 'PUT'])
@merchant_approved_required
def notification_read(request):
    """标记已读：传 all=True 或 id / ids；只能影响当前商户自己的通知。"""
    data = get_json(request)
    qs = Notification.objects.filter(to_user=request.user, is_read=False)

    if data.get('all'):
        qs.update(is_read=True, update_time=timezone.now())
    else:
        ids = data.get('ids')
        if ids is None and data.get('id') is not None:
            ids = [data.get('id')]
        if not isinstance(ids, list):
            return fail_m('请提供要标记的通知')
        clean_ids = []
        for value in ids:
            try:
                clean_ids.append(int(value))
            except (TypeError, ValueError):
                continue
        if not clean_ids:
            return fail_m('请提供要标记的通知')
        qs.filter(id__in=clean_ids).update(is_read=True, update_time=timezone.now())

    unread = Notification.objects.filter(to_user=request.user, is_read=False).count()
    return ok_m({'unread': unread}, message='已标记为已读')
