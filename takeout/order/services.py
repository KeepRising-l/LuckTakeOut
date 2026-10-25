"""订单域跨视图复用的业务动作。"""

from django.db.models import F

from product.models import ProductInfo


def restore_stock(order):
    """取消订单时按明细回补库存（须在事务内调用）。"""
    for it in order.items.all():
        ProductInfo.objects.filter(id=it.product_id).update(stock=F('stock') + it.quantity)
