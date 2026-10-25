"""商户端订单处理与统计接口。"""

from datetime import date, timedelta

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from common.auth import merchant_approved_required
from common.response import fail_m, ok_m
from common.utils import get_json
from payment.models import PaymentRecord, RefundRecord

from .models import OrderInfo, OrderItem
from .services import restore_stock
from .state import MERCHANT_TARGET_STATUSES, change_status


def order_to_dict(o):
    u = o.user
    items = [
        {
            'productName': it.product_name,
            'price': float(it.price),
            'quantity': it.quantity,
            'amount': float(it.amount),
        }
        for it in o.items.all()
    ]
    refund = o.refunds.order_by('-id').first()
    return {
        'id': o.id,
        'orderNumber': o.order_no,
        'customerName': u.nickname if u else '',
        'customerPhone': u.phone if u else '',
        'deliveryAddress': o.address_snapshot,
        'items': items,
        'productAmount': float(o.total_amount),
        'deliveryFee': float(o.delivery_fee),
        'totalAmount': float(o.pay_amount),
        'paymentMethod': '模拟支付',
        'remark': o.remark,
        'status': o.status,
        'refundStatus': refund.status if refund else None,
        'refundReason': refund.reason if refund else '',
        'refundRemark': refund.review_remark if refund else '',
        'createTime': o.create_time.strftime('%Y-%m-%d %H:%M:%S') if o.create_time else '',
    }


@require_http_methods(['GET'])
@merchant_approved_required
def order_list(request):
    merchant = request.merchant
    qs = OrderInfo.objects.filter(merchant=merchant).order_by('-id')

    status = request.GET.get('status')
    if status:
        try:
            qs = qs.filter(status=int(status))
        except ValueError:
            pass

    try:
        page = int(request.GET.get('page') or 1)
        size = int(request.GET.get('size') or 10)
    except ValueError:
        page, size = 1, 10
    start = (page - 1) * size
    total = qs.count()
    items = qs[start:start + size]

    today = date.today()
    stats = {
        'pending': OrderInfo.objects.filter(merchant=merchant, status__in=[10, 20]).count(),
        'preparing': OrderInfo.objects.filter(merchant=merchant, status=30).count(),
        'today': OrderInfo.objects.filter(merchant=merchant, create_time__date=today).count(),
    }
    return ok_m({
        'items': [order_to_dict(o) for o in items],
        'total': total,
        'totalPages': (total + size - 1) // size,
        'page': page,
        'size': size,
        'stats': stats,
    })


@require_http_methods(['GET'])
@merchant_approved_required
def order_detail(request, pk):
    o = OrderInfo.objects.filter(id=pk, merchant=request.merchant).first()
    if not o:
        return fail_m('订单不存在')
    return ok_m(order_to_dict(o))


@require_http_methods(['PUT', 'POST'])
@merchant_approved_required
def order_update_status(request, pk):
    o = OrderInfo.objects.filter(id=pk, merchant=request.merchant).first()
    if not o:
        return fail_m('订单不存在')
    data = get_json(request)
    try:
        target = int(data.get('status'))
    except (TypeError, ValueError):
        return fail_m('未知的订单状态')
    if target not in MERCHANT_TARGET_STATUSES:
        return fail_m('未知的订单状态')
    if o.status == OrderInfo.STATUS_REFUNDING:
        # 退款审核中只能走退款审核接口，防止通用状态接口把订单改回「已接单」绕过审核
        return fail_m('退款审核中的订单请在退款审核中处理')
    changed, message = change_status(
        o, target, operator_role='merchant', operator_id=request.merchant.id,
    )
    if not changed:
        return fail_m(message)
    return ok_m(order_to_dict(o), message='订单状态已更新')


@require_http_methods(['PUT', 'POST'])
@merchant_approved_required
def order_cancel(request, pk):
    o = OrderInfo.objects.filter(id=pk, merchant=request.merchant).first()
    if not o:
        return fail_m('订单不存在')
    with transaction.atomic():
        changed, message = change_status(
            o, OrderInfo.STATUS_CANCELED, operator_role='merchant', operator_id=request.merchant.id,
        )
        if not changed:
            return fail_m(message)
        restore_stock(o)
    return ok_m(order_to_dict(o), message='订单已取消')


@require_http_methods(['PUT', 'POST'])
@merchant_approved_required
def order_refund_review(request, pk):
    """商户审核退款申请：同意 → 模拟退款到账（订单「已退款」）；拒绝 → 退回申请前状态。

    退款同意不回补库存（与取消订单的口径区分：退款是交易完成后的资金退回）。
    """
    with transaction.atomic():
        o = OrderInfo.objects.select_for_update().filter(
            id=pk, merchant=request.merchant
        ).first()
        if not o:
            return fail_m('订单不存在')
        if o.status != OrderInfo.STATUS_REFUNDING:
            return fail_m('订单不在退款审核中')
        refund = o.refunds.filter(status=RefundRecord.STATUS_PENDING).order_by('-id').first()
        if not refund:
            return fail_m('没有待审核的退款申请')

        data = get_json(request)
        approve = bool(data.get('approve'))
        now = timezone.now()

        if approve:
            changed, message = change_status(
                o, OrderInfo.STATUS_REFUNDED,
                operator_role='merchant', operator_id=request.merchant.id,
            )
            if not changed:
                return fail_m(message)
            refund.status = RefundRecord.STATUS_APPROVED
            PaymentRecord.objects.filter(order=o, status=20).update(status=40)
            message = '已同意退款（模拟到账）'
        else:
            changed, message = change_status(
                o, refund.from_status,
                operator_role='merchant', operator_id=request.merchant.id,
            )
            if not changed:
                return fail_m(message)
            refund.status = RefundRecord.STATUS_REJECTED
            message = '已拒绝退款申请'

        refund.review_remark = (data.get('remark') or '').strip()[:255]
        refund.review_time = now
        refund.save()
    return ok_m(order_to_dict(o), message=message)


# ---- 统计 ----

@require_http_methods(['GET'])
@merchant_approved_required
def stats_overview(request):
    merchant = request.merchant
    today = date.today()
    today_qs = OrderInfo.objects.filter(merchant=merchant, create_time__date=today)
    paid_qs = OrderInfo.objects.filter(merchant=merchant, status__in=[20, 30, 40, 50])
    return ok_m({
        'todayOrders': today_qs.count(),
        'todayRevenue': float(today_qs.aggregate(s=Sum('pay_amount'))['s'] or 0),
        'totalOrders': OrderInfo.objects.filter(merchant=merchant).count(),
        'totalRevenue': float(paid_qs.aggregate(s=Sum('pay_amount'))['s'] or 0),
        'pendingCount': OrderInfo.objects.filter(merchant=merchant, status__in=[10, 20]).count(),
    })


@require_http_methods(['GET'])
@merchant_approved_required
def stats_recent_orders(request):
    qs = OrderInfo.objects.filter(merchant=request.merchant).order_by('-id')[:5]
    return ok_m([order_to_dict(o) for o in qs])


@require_http_methods(['GET'])
@merchant_approved_required
def stats_order_status(request):
    rows = (
        OrderInfo.objects.filter(merchant=request.merchant)
        .values('status').annotate(count=Count('id'))
    )
    return ok_m([{'status': r['status'], 'count': r['count']} for r in rows])


@require_http_methods(['GET'])
@merchant_approved_required
def stats_sales(request):
    """近 7 天每日单量。"""
    merchant = request.merchant
    days = _last_days(7)
    rows = (
        OrderInfo.objects.filter(merchant=merchant, create_time__date__gte=days[0])
        .values('create_time__date').annotate(count=Count('id'))
    )
    by_day = {r['create_time__date']: r['count'] for r in rows}
    return ok_m([{'date': d.strftime('%m-%d'), 'count': by_day.get(d, 0)} for d in days])


@require_http_methods(['GET'])
@merchant_approved_required
def stats_revenue_trend(request):
    """近 7 天每日营业额（已支付口径）。"""
    merchant = request.merchant
    days = _last_days(7)
    rows = (
        OrderInfo.objects.filter(
            merchant=merchant, status__in=[20, 30, 40, 50], create_time__date__gte=days[0]
        )
        .values('create_time__date').annotate(s=Sum('pay_amount'))
    )
    by_day = {r['create_time__date']: float(r['s'] or 0) for r in rows}
    return ok_m([{'date': d.strftime('%m-%d'), 'revenue': round(by_day.get(d, 0), 2)} for d in days])


@require_http_methods(['GET'])
@merchant_approved_required
def stats_top_products(request):
    """近 30 天销量 Top10。"""
    start = date.today() - timedelta(days=30)
    rows = (
        OrderItem.objects.filter(
            order__merchant=request.merchant,
            order__status__in=[20, 30, 40, 50],
            order__create_time__date__gte=start,
        )
        .values('product_name').annotate(count=Sum('quantity'))
        .order_by('-count')[:10]
    )
    return ok_m([{'name': r['product_name'], 'count': r['count']} for r in rows])


@require_http_methods(['GET'])
@merchant_approved_required
def stats_orders(request):
    """近期订单（供报表页复用）。"""
    qs = OrderInfo.objects.filter(merchant=request.merchant).order_by('-id')[:20]
    return ok_m([order_to_dict(o) for o in qs])


def _last_days(n):
    today = date.today()
    return [today - timedelta(days=i) for i in range(n - 1, -1, -1)]
