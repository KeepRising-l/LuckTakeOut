"""订单域接口：下单、订单详情/列表、模拟支付。"""

import uuid
from decimal import Decimal

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

# 内部状态码 <-> 前端状态码（1 待付款 / 2 已付款 / 3 已接单 / 4 制作中 / 5 配送中 / 8 已完成 / 9 已取消 / 10 退款中）
STATUS_TO_API = {10: 1, 20: 2, 30: 3, 40: 5, 50: 8, 60: 9, 70: 10, 80: 10}
API_TO_STATUS = {
    1: [10], 2: [20], 3: [30], 4: [30],
    5: [40], 6: [40], 7: [40], 8: [50], 9: [60], 10: [70, 80],
}


def order_to_dict(o):
    items = [
        {
            'productId': it.product_id,
            'productName': it.product_name,
            'skuName': it.spec_text,
            'price': float(it.price),
            'quantity': it.quantity,
            'amount': float(it.amount),
        }
        for it in o.items.all()
    ]
    total = float(o.total_amount)
    actual = float(o.pay_amount)
    return {
        'id': o.id,
        'orderNo': o.order_no,
        'merchantId': o.merchant_id,
        'merchantName': o.merchant.name if o.merchant else '',
        'status': STATUS_TO_API.get(o.status, 1),
        'productAmount': total,
        'deliveryFee': round(actual - total, 2) if actual > total else 0.0,
        'discountAmount': 0.0,
        'actualAmount': actual,
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

    address = None
    if data.get('addressId'):
        address = UserAddress.objects.filter(id=data['addressId'], user=user_info).first()

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

    delivery_fee = Decimal(str(data.get('deliveryFee') or 0))
    pay_amount = total + delivery_fee

    with transaction.atomic():
        order = OrderInfo.objects.create(
            order_no=uuid.uuid4().hex[:20],
            user=user_info,
            merchant=merchant,
            address_snapshot=(address.detail if address else '') or '',
            total_amount=total,
            pay_amount=pay_amount,
            status=OrderInfo.STATUS_PENDING_PAY,
            remark=data.get('remark') or '',
        )
        for product, it, price, qty, amount in resolved:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                spec_text=it.get('skuName') or '',
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
    o = OrderInfo.objects.filter(id=pk).first()
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
            codes = API_TO_STATUS.get(int(status), [])
            if codes:
                qs = qs.filter(status__in=codes)
        except ValueError:
            pass
    return ok([order_to_dict(o) for o in qs[:50]])


@require_http_methods(['POST'])
@api_login_required
def order_pay(request, pk):
    o = OrderInfo.objects.filter(id=pk).first()
    if not o:
        return fail('订单不存在')
    if o.status != OrderInfo.STATUS_PENDING_PAY:
        return fail('当前订单状态不允许支付')
    with transaction.atomic():
        from_status = o.status
        o.status = OrderInfo.STATUS_PAID
        o.pay_time = timezone.now()
        o.save()
        OrderStatusLog.objects.create(
            order=o, from_status=from_status, to_status=o.status, operator_role='customer',
        )
        PaymentRecord.objects.filter(order=o).update(status=20, pay_time=timezone.now())
    return ok(order_to_dict(o))
