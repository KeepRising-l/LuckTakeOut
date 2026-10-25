"""骑手端（配送）接口，契约见前端 rider/api.js。

任务直接映射到订单：待接单(未分配) / 已接单(已分配) / 配送中 / 已完成。
"""

from datetime import date

from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from common.auth import make_rider_token, rider_login_required
from common.response import fail, ok
from common.utils import get_json
from order.models import OrderInfo
from order.state import change_status

from .models import Rider

# 前端任务状态口径：6 = 已送达（接单即进入配送中，本期不设中间态）
TASK_STATUS_COMPLETED = 6


def rider_to_dict(r):
    today = date.today()
    done = OrderInfo.objects.filter(
        rider=r, status=OrderInfo.STATUS_FINISHED, finish_time__date=today
    ).count()
    return {
        'id': r.id,
        'name': r.name,
        'phone': r.phone,
        'todayDeliveryCount': done,
        'workStatus': 1 if r.status == 0 else 2,
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
    return {
        'id': o.id,
        'orderId': o.id,
        'orderNo': o.order_no,
        'merchantName': o.merchant.name if o.merchant else '',
        'deliveryAddress': o.address_snapshot,
        'contactName': u.nickname if u else '',
        'contactPhone': u.phone if u else '',
        'deliveryFee': float(o.delivery_fee),
        'totalAmount': float(o.pay_amount),
        'status': _task_status(o),
        'createTime': o.create_time.strftime('%Y-%m-%d %H:%M:%S') if o.create_time else '',
        'items': items,
    }


@require_http_methods(['POST'])
def login(request):
    """骑手登录：账号密码，账号须绑定骑手档案。"""
    data = get_json(request)
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    user = authenticate(username=username, password=password)
    if user is None:
        return fail('用户名或密码错误')
    rider = Rider.objects.filter(auth_user=user).first()
    if rider is None:
        return fail('该账号不是骑手账号')
    return ok({
        'token': make_rider_token(user),
        'riderId': rider.id,
        'name': rider.name,
        'phone': rider.phone,
    })


@require_http_methods(['GET'])
@rider_login_required
def rider_info(request, rider_id):
    if rider_id != request.rider.id:
        return fail('无权查看其他骑手信息', status=403)
    return ok(rider_to_dict(request.rider))


@require_http_methods(['POST'])
@rider_login_required
def rider_status(request, rider_id):
    if rider_id != request.rider.id:
        return fail('无权修改其他骑手状态', status=403)
    data = get_json(request)
    raw = data.get('workStatus') or request.GET.get('workStatus')
    try:
        work_status = int(raw or 1)
    except (TypeError, ValueError):
        return fail('工作状态格式不正确')
    # 1=接单中(上线) 2=休息中(下线)，与 rider_to_dict 的展示口径互逆
    request.rider.status = 0 if work_status == 1 else 1
    request.rider.save()
    return ok({'workStatus': work_status})


@require_http_methods(['GET'])
@rider_login_required
def rider_tasks(request, rider_id):
    if rider_id != request.rider.id:
        return fail('无权查看其他骑手任务', status=403)
    r_id = request.rider.id
    qs = OrderInfo.objects.filter(
        Q(status=OrderInfo.STATUS_PENDING_ACCEPT)
        | Q(rider_id=r_id, status__in=[
            OrderInfo.STATUS_PENDING_ACCEPT,
            OrderInfo.STATUS_DELIVERING,
            OrderInfo.STATUS_FINISHED,
        ])
    ).order_by('-id')
    return ok({'list': [task_to_dict(o) for o in qs[:100]], 'total': qs.count()})


@require_http_methods(['GET'])
@rider_login_required
def pending_tasks(request):
    qs = OrderInfo.objects.filter(
        status=OrderInfo.STATUS_PENDING_ACCEPT, rider__isnull=True
    ).order_by('-id')
    return ok({'list': [task_to_dict(o) for o in qs[:100]], 'total': qs.count()})


@require_http_methods(['GET'])
@rider_login_required
def task_detail(request, task_id):
    o = OrderInfo.objects.filter(id=task_id).first()
    if not o:
        return fail('任务不存在')
    # 可见范围与任务列表一致：待抢单的任务，或已分配给自己的任务
    is_grabbable = o.status == OrderInfo.STATUS_PENDING_ACCEPT and o.rider_id is None
    if o.rider_id != request.rider.id and not is_grabbable:
        return fail('无权查看其他骑手的任务', status=403)
    return ok(task_to_dict(o))


@require_http_methods(['POST'])
@rider_login_required
def accept_task(request, task_id):
    """接单：记录骑手并直接进入配送中（本期不设中间态）。

    锁单读取后再校验，防止两名骑手并发抢单互相覆盖。
    """
    with transaction.atomic():
        o = OrderInfo.objects.select_for_update().filter(id=task_id).first()
        if not o:
            return fail('任务不存在')
        if o.status != OrderInfo.STATUS_PENDING_ACCEPT:
            return fail('订单状态不允许接单')
        rider = request.rider
        if o.rider_id and o.rider_id != rider.id:
            return fail('订单已被其他骑手接单')
        changed, message = change_status(
            o, OrderInfo.STATUS_DELIVERING, operator_role='rider', operator_id=rider.id,
            rider=rider,
        )
        if not changed:
            return fail(message)
    return ok(task_to_dict(o), info='接单成功')


@require_http_methods(['POST'])
@rider_login_required
def update_task_status(request, task_id):
    """确认送达：配送中 -> 已完成。"""
    o = OrderInfo.objects.filter(id=task_id).first()
    if not o:
        return fail('任务不存在')
    if o.rider_id != request.rider.id:
        return fail('无权操作其他骑手的订单', status=403)
    data = get_json(request)
    try:
        status = int(data.get('status'))
    except (TypeError, ValueError):
        return fail('未知的配送状态')
    if status != TASK_STATUS_COMPLETED:
        return fail('未知的配送状态')
    now = timezone.now()
    changed, message = change_status(
        o, OrderInfo.STATUS_FINISHED, operator_role='rider', operator_id=request.rider.id,
        deliver_time=now, finish_time=now,
    )
    if not changed:
        return fail(message)
    return ok(task_to_dict(o), info='状态已更新')


@require_http_methods(['GET'])
@rider_login_required
def statistics(request):
    rider_id = request.rider.id
    today = date.today()
    done = OrderInfo.objects.filter(
        rider_id=rider_id, status=OrderInfo.STATUS_FINISHED, finish_time__date=today
    ).count()
    return ok({
        'todayDeliveryCount': done,
        'totalDeliveryCount': OrderInfo.objects.filter(
            rider_id=rider_id, status=OrderInfo.STATUS_FINISHED
        ).count(),
    })
