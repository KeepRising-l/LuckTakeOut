"""订单域接口：下单、订单详情/列表、模拟支付。"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from common.auth import api_login_required
from common.response import fail, ok
from common.utils import get_json
from merchant.models import MerchantInfo
from payment.models import PaymentRecord, RefundRecord
from product.models import ProductInfo
from user.models import UserAddress, UserInfo

from .models import OrderInfo, OrderItem, OrderStatusLog
from .services import restore_stock
from .state import change_status


def _to_int(value):
    """宽松转 int：非法输入返回 None，避免直接 500。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def order_to_dict(o):
    items = [
        {
            'productId': it.product_id,
            'productName': it.product_name,
            'price': float(it.price),
            'quantity': it.quantity,
            'amount': float(it.amount),
        }
        for it in o.items.all()
    ]
    # 最近一笔退款申请（可能没有）：前端据此展示申请原因与审核结果
    refund = o.refunds.order_by('-id').first()
    return {
        'id': o.id,
        'orderNo': o.order_no,
        'merchantId': o.merchant_id,
        'merchantName': o.merchant.name if o.merchant else '',
        'status': o.status,
        'productAmount': float(o.total_amount),
        'deliveryFee': float(o.delivery_fee),
        'discountAmount': 0.0,
        'actualAmount': float(o.pay_amount),
        'address': o.address_snapshot,
        'remark': o.remark,
        'createTime': o.create_time.strftime('%Y-%m-%d %H:%M:%S') if o.create_time else '',
        'refundStatus': refund.status if refund else None,
        'refundReason': refund.reason if refund else '',
        'refundRemark': refund.review_remark if refund else '',
        'items': items,
    }


@require_http_methods(['POST'])
@api_login_required
def create_order(request):
    user_info = UserInfo.objects.filter(auth_user=request.user).first()
    if not user_info:
        return fail('用户不存在', status=401)

    data = get_json(request)
    merchant_id = _to_int(data.get('merchantId'))
    merchant = MerchantInfo.objects.filter(id=merchant_id, status=20).first() if merchant_id else None
    if not merchant:
        return fail('商家不存在或未通过审核')

    items = data.get('items') or []
    if not items:
        return fail('购物车为空')

    address_id = _to_int(data.get('addressId'))
    address = UserAddress.objects.filter(id=address_id, user=user_info).first() if address_id else None
    if address is None:
        return fail('请选择收货地址')

    # 先解析行数据：保留行序 + 合并同一菜品的数量（防重复行绕过库存校验）
    lines = []
    qty_by_product = {}
    for it in items:
        product_id = _to_int(it.get('productId'))
        if not product_id:
            return fail('存在无效的商品')
        try:
            qty = int(it.get('quantity') or 0)
        except (TypeError, ValueError):
            return fail('商品数量非法')
        if qty <= 0:
            return fail('商品数量非法')
        lines.append((product_id, qty))
        qty_by_product[product_id] = qty_by_product.get(product_id, 0) + qty

    delivery_fee = settings.DELIVERY_FEE

    # 行锁内校验库存并扣减，防并发超卖；价格与库存一律以后端数据为准
    with transaction.atomic():
        locked = {}
        for product_id, qty in qty_by_product.items():
            product = ProductInfo.objects.select_for_update().filter(
                id=product_id, merchant=merchant, status=10
            ).first()
            if not product:
                return fail('存在无效的商品')
            if product.stock < qty:
                return fail(f'「{product.name}」库存不足')
            locked[product_id] = product

        total = Decimal('0')
        resolved = []
        for product_id, qty in lines:
            product = locked[product_id]
            amount = product.price * qty
            total += amount
            resolved.append((product, qty, amount))
        pay_amount = total + delivery_fee

        for product_id, qty in qty_by_product.items():
            product = locked[product_id]
            product.stock -= qty
            product.save(update_fields=['stock'])

        order = OrderInfo.objects.create(
            order_no=uuid.uuid4().hex[:20],
            user=user_info,
            merchant=merchant,
            address_snapshot=address.detail,
            total_amount=total,
            delivery_fee=delivery_fee,
            pay_amount=pay_amount,
            status=OrderInfo.STATUS_PENDING_PAY,
            remark=data.get('remark') or '',
        )
        for product, qty, amount in resolved:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                price=product.price,
                quantity=qty,
                amount=amount,
            )
        OrderStatusLog.objects.create(
            order=order, from_status=0, to_status=OrderInfo.STATUS_PENDING_PAY,
            operator_id=user_info.id, operator_role='customer',
        )
        PaymentRecord.objects.create(order=order, amount=pay_amount, method='mock', status=10)

    return ok({'id': order.id, 'orderNo': order.order_no, 'actualAmount': float(pay_amount)})


@require_http_methods(['GET'])
@api_login_required
def order_detail(request, pk):
    user_info = UserInfo.objects.filter(auth_user=request.user).first()
    if not user_info:
        return fail('用户不存在', status=401)
    o = OrderInfo.objects.filter(id=pk, user=user_info).first()
    if not o:
        return fail('订单不存在')
    return ok(order_to_dict(o))


@require_http_methods(['GET'])
@api_login_required
def order_list(request):
    user_info = UserInfo.objects.filter(auth_user=request.user).first()
    qs = OrderInfo.objects.filter(user=user_info).order_by('-id') if user_info else OrderInfo.objects.none()
    status = request.GET.get('status')
    if status:
        try:
            qs = qs.filter(status=int(status))
        except ValueError:
            pass
    return ok([order_to_dict(o) for o in qs[:50]])


@require_http_methods(['POST'])
@api_login_required
def order_pay(request, pk):
    user_info = UserInfo.objects.filter(auth_user=request.user).first()
    if not user_info:
        return fail('用户不存在', status=401)
    o = OrderInfo.objects.filter(id=pk, user=user_info).first()
    if not o:
        return fail('订单不存在')
    if o.status != OrderInfo.STATUS_PENDING_PAY:
        return fail('当前订单状态不允许支付')
    now = timezone.now()
    with transaction.atomic():
        changed, message = change_status(
            o, OrderInfo.STATUS_PAID, operator_role='customer',
            operator_id=user_info.id, pay_time=now,
        )
        if not changed:
            return fail(message)
        PaymentRecord.objects.filter(order=o).update(status=20, pay_time=now)
    return ok(order_to_dict(o))


@require_http_methods(['POST'])
@api_login_required
def order_cancel(request, pk):
    """顾客取消本人订单：仅待支付/已支付未接单可取消。"""
    user_info = UserInfo.objects.filter(auth_user=request.user).first()
    if not user_info:
        return fail('用户不存在', status=401)
    o = OrderInfo.objects.filter(id=pk, user=user_info).first()
    if not o:
        return fail('订单不存在')
    if o.status not in (OrderInfo.STATUS_PENDING_PAY, OrderInfo.STATUS_PAID):
        return fail('当前订单状态不允许取消')
    with transaction.atomic():
        changed, message = change_status(
            o, OrderInfo.STATUS_CANCELED, operator_role='customer', operator_id=user_info.id,
        )
        if not changed:
            return fail(message)
        restore_stock(o)
    return ok(order_to_dict(o), info='订单已取消')


@require_http_methods(['POST'])
@api_login_required
def order_refund_apply(request, pk):
    """顾客申请退款：已支付/待接单的订单进入「退款中」，留存退款记录待商户审核。

    金额为实付全额（模拟退款），拒绝时按记录里的原状态退回。
    """
    user_info = UserInfo.objects.filter(auth_user=request.user).first()
    if not user_info:
        return fail('用户不存在', status=401)

    data = get_json(request)
    with transaction.atomic():
        # 行锁防止并发重复申请绕过「待审核唯一」检查
        o = OrderInfo.objects.select_for_update().filter(id=pk, user=user_info).first()
        if not o:
            return fail('订单不存在')
        if o.refunds.filter(status=RefundRecord.STATUS_PENDING).exists():
            return fail('已有退款申请待审核，请耐心等待')
        if o.status not in (OrderInfo.STATUS_PAID, OrderInfo.STATUS_PENDING_ACCEPT):
            return fail('当前订单状态不支持申请退款')

        from_status = o.status
        changed, message = change_status(
            o, OrderInfo.STATUS_REFUNDING, operator_role='customer', operator_id=user_info.id,
        )
        if not changed:
            return fail(message)
        refund = RefundRecord.objects.create(
            order=o,
            amount=o.pay_amount,
            reason=(data.get('reason') or '').strip()[:255],
            status=RefundRecord.STATUS_PENDING,
            from_status=from_status,
        )
    return ok({
        'id': o.id,
        'status': o.status,
        'refundId': refund.id,
        'refundAmount': float(refund.amount),
    }, info='退款申请已提交，等待商家审核')
