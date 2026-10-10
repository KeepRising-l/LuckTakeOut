"""骑手端（配送）接口，契约见前端 rider/api.js。

任务直接映射到订单：待接单(未分配) / 已接单(已分配) / 配送中 / 已完成。
"""

from datetime import date

from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from common.response import fail, ok
from common.utils import get_json
from order.models import OrderInfo, OrderStatusLog

from .models import Rider


def rider_to_dict(r):
    today = date.today()
    done = OrderInfo.objects.filter(
        rider=r, status=OrderInfo.STATUS_FINISHED, finish_time__date=today
    ).count()
    return {
        'id': r.id,
        'name': r.name,
        'phone': r.phone,
        'rating': 4.9,
        'todayDeliveryCount': done,
        'todayEarnings': done * 5,
        'workStatus': 1 if r.status == 0 else 2,
        'location': {'latitude': 39.9042, 'longitude': 116.4074, 'address': '示例市'},
    }


def _task_status(o):
    if o.status == OrderInfo.STATUS_PENDING_ACCEPT:
        return 'accepted' if o.rider_id else 'pending'
    if o.status == OrderInfo.STATUS_DELIVERING:
        return 'delivering'
    if o.status == OrderInfo.STATUS_FINISHED:
        return 'completed'
    return 'pending'


def task_to_dict(o):
    u = o.user
    items = [
        {'name': it.product_name, 'quantity': it.quantity, 'price': float(it.price)}
        for it in o.items.all()
    ]
    fee = float(o.pay_amount) - float(o.total_amount)
    return {
        'id': o.id,
        'orderId': o.id,
        'orderNo': o.order_no,
        'merchantName': o.merchant.name if o.merchant else '',
        'deliveryAddress': o.address_snapshot,
        'contactName': u.nickname if u else '',
        'contactPhone': u.phone if u else '',
        'distance': '2.0km',
        'estimatedTime': '25分钟',
        'deliveryFee': round(fee, 2) if fee > 0 else 5.0,
        'totalAmount': float(o.pay_amount),
        'status': _task_status(o),
        'createTime': o.create_time.strftime('%Y-%m-%d %H:%M:%S') if o.create_time else '',
        'items': items,
    }


@require_http_methods(['GET'])
def rider_info(request, rider_id):
    r = Rider.objects.filter(id=rider_id).first()
    if not r:
        return fail('骑手不存在')
    return ok(rider_to_dict(r))


@require_http_methods(['POST'])
def rider_status(request, rider_id):
    r = Rider.objects.filter(id=rider_id).first()
    if not r:
        return fail('骑手不存在')
    work_status = int(request.GET.get('workStatus') or 1)
    r.status = 0 if work_status in (1, 2) else 1
    r.save()
    return ok({'workStatus': work_status})


@require_http_methods(['GET'])
def rider_tasks(request, rider_id):
    qs = OrderInfo.objects.filter(
        Q(status=OrderInfo.STATUS_PENDING_ACCEPT)
        | Q(rider_id=rider_id, status__in=[
            OrderInfo.STATUS_PENDING_ACCEPT,
            OrderInfo.STATUS_DELIVERING,
            OrderInfo.STATUS_FINISHED,
        ])
    ).order_by('-id')
    return ok({'list': [task_to_dict(o) for o in qs[:100]], 'total': qs.count()})


@require_http_methods(['GET'])
def pending_tasks(request):
    qs = OrderInfo.objects.filter(
        status=OrderInfo.STATUS_PENDING_ACCEPT, rider__isnull=True
    ).order_by('-id')
    return ok({'list': [task_to_dict(o) for o in qs[:100]], 'total': qs.count()})


@require_http_methods(['GET'])
def task_detail(request, task_id):
    o = OrderInfo.objects.filter(id=task_id).first()
    if not o:
        return fail('任务不存在')
    return ok(task_to_dict(o))


@require_http_methods(['POST'])
def accept_task(request, task_id):
    o = OrderInfo.objects.filter(id=task_id).first()
    if not o:
        return fail('任务不存在')
    if o.status != OrderInfo.STATUS_PENDING_ACCEPT:
        return fail('订单状态不允许接单')
    rider = Rider.objects.filter(id=request.GET.get('riderId')).first()
    if rider is None:
        return fail('骑手不存在')
    if o.rider_id and o.rider_id != rider.id:
        return fail('订单已被其他骑手接单')
    o.rider = rider
    o.save()
    return ok(task_to_dict(o), info='接单成功')


@require_http_methods(['POST'])
def reject_task(request, task_id):
    return ok(True, info='已拒单')


@require_http_methods(['POST'])
def update_task_status(request, task_id):
    o = OrderInfo.objects.filter(id=task_id).first()
    if not o:
        return fail('任务不存在')
    data = get_json(request)
    status = data.get('status')
    from_status = o.status
    if status == 4:            # 取餐中：保持待配送
        pass
    elif status == 5:          # 配送中
        o.status = OrderInfo.STATUS_DELIVERING
    elif status == 6:          # 已送达 -> 已完成
        o.status = OrderInfo.STATUS_FINISHED
        o.deliver_time = timezone.now()
        o.finish_time = timezone.now()
    else:
        return fail('未知的配送状态')
    o.save()
    if from_status != o.status:
        OrderStatusLog.objects.create(
            order=o, from_status=from_status, to_status=o.status, operator_role='rider',
        )
    return ok(task_to_dict(o), info='状态已更新')


@require_http_methods(['GET'])
def statistics(request):
    rider_id = request.GET.get('riderId')
    today = date.today()
    done = OrderInfo.objects.filter(
        rider_id=rider_id, status=OrderInfo.STATUS_FINISHED, finish_time__date=today
    ).count()
    return ok({
        'todayDeliveryCount': done,
        'todayEarnings': done * 5,
        'totalDeliveryCount': OrderInfo.objects.filter(
            rider_id=rider_id, status=OrderInfo.STATUS_FINISHED
        ).count(),
    })
