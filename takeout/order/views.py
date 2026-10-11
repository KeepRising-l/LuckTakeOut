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
from payment.models import PaymentRecord
from product.models import ProductInfo
from user.models import UserAddress, UserInfo

from .models import OrderInfo, OrderItem, OrderStatusLog
from .state import change_status


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
        'items': items,
    }


@require_http_methods(['POST'])
@api_login_required
def create_order(request):
    user_info = UserInfo.objects.filter(auth_user=request.user).first()
    if not user_info:
        return fail('用户不存在', status=401)

    data = get_json(request)
    merchant = MerchantInfo.objects.filter(id=data.get('merchantId'), status=20).first()
    if not merchant:
        return fail('商家不存在或未通过审核')

    items = data.get('items') or []
    if not items:
        return fail('购物车为空')

    address_id = data.get('addressId')
    address = None
    if address_id:
        address = UserAddress.objects.filter(id=address_id, user=user_info).first()
    if address is None:
        return fail('请选择收货地址')

    # 后端重新校验价格与库存（不信任前端传入的价格）
    total = Decimal('0')
    resolved = []
    for it in items:
        product = ProductInfo.objects.filter(
            id=it.get('productId'), merchant=merchant, status=10
        ).first()
        if not product:
            return fail('存在无效的商品')
        qty = int(it.get('quantity') or 0)
        if qty <= 0:
            return fail('商品数量非法')
        if product.stock < qty:
            return fail(f'「{product.name}」库存不足')
        amount = product.price * qty
        total += amount
        resolved.append((product, it, product.price, qty, amount))

    delivery_fee = settings.DELIVERY_FEE
    pay_amount = total + delivery_fee

    with transaction.atomic():
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
        for product, it, price, qty, amount in resolved:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                price=price,
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
    changed, message = change_status(
        o, OrderInfo.STATUS_CANCELED, operator_role='customer', operator_id=user_info.id,
    )
    if not changed:
        return fail(message)
    return ok(order_to_dict(o), info='订单已取消')
