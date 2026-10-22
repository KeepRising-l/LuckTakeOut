"""个性化推荐：基于顾客历史订单构建口味画像，并给出可解释的推荐。

口径约定：
- 只统计有效订单（已支付/待接单/配送中/已完成），取消与退款不计入
- 推荐优先级：常点菜品（复购）→ 常点商户的其他菜 → 全站热销（冷启动）
- 推荐结果只包含「在售且有库存」的菜品，避免推荐了却下不了单
- 每条推荐都带 reason，前端直接展示，避免"黑箱推荐"
"""

from collections import Counter
from decimal import Decimal

from django.db.models import Count

from order.models import OrderInfo, OrderItem
from product.models import ProductInfo

VALID_STATUSES = (
    OrderInfo.STATUS_PAID,
    OrderInfo.STATUS_PENDING_ACCEPT,
    OrderInfo.STATUS_DELIVERING,
    OrderInfo.STATUS_FINISHED,
)

SLOTS = ((5, 10, '早餐'), (10, 15, '午餐'), (15, 21, '晚餐'))


def _valid_orders(customer, limit=30):
    return (OrderInfo.objects.select_related('merchant')
            .filter(user=customer, status__in=VALID_STATUSES).order_by('-id')[:limit])


def _slot_of(hour):
    for start, end, name in SLOTS:
        if start <= hour < end:
            return name
    return '夜宵'


def build_profile(customer, limit=30):
    """聚合历史订单 → 口味画像。无历史时返回空画像（前端据此走冷启动文案）。"""
    orders = list(_valid_orders(customer, limit))
    if not orders:
        return {
            'orderCount': 0, 'avgAmount': 0, 'totalSpend': 0,
            'topMerchants': [], 'topDishes': [], 'favoriteSlot': '',
        }

    items = OrderItem.objects.filter(order__in=orders).select_related('product', 'order__merchant')

    dish_counter = Counter()
    dish_meta = {}
    merchant_counter = Counter()
    merchant_name = {}
    # 商户维度按「订单数」统计，避免多菜品订单被重复计数
    for o in orders:
        merchant_counter[o.merchant_id] += 1
        merchant_name[o.merchant_id] = o.merchant.name
    for it in items:
        # 菜品维度按「出现次数」统计（同一订单同一菜品只占一条明细）
        dish_counter[it.product_id] += 1
        dish_meta[it.product_id] = {
            'productId': it.product_id,
            'name': it.product_name,
            'merchantId': it.order.merchant_id,
            'merchantName': it.order.merchant.name,
        }

    spend = sum((o.pay_amount or Decimal('0')) for o in orders)
    slot_counter = Counter(_slot_of(o.create_time.hour) for o in orders if o.create_time)

    top_dishes = [
        {**dish_meta[pid], 'times': times}
        for pid, times in dish_counter.most_common(5)
    ]
    top_merchants = [
        {'merchantId': mid, 'name': merchant_name[mid], 'orders': cnt}
        for mid, cnt in merchant_counter.most_common(3)
    ]

    return {
        'orderCount': len(orders),
        'avgAmount': round(float(spend) / len(orders), 2),
        'totalSpend': round(float(spend), 2),
        'topMerchants': top_merchants,
        'topDishes': top_dishes,
        'favoriteSlot': slot_counter.most_common(1)[0][0] if slot_counter else '',
    }


def _pack(p, reason):
    return {
        'productId': p.id,
        'name': p.name,
        'image': p.image or '',
        'price': float(p.price),
        'merchantId': p.merchant_id,
        'merchantName': p.merchant.name,
        'reason': reason,
    }


def recommend_dishes(customer, limit=6):
    """返回最多 limit 条推荐，按「复购 → 常点商户 → 全站热销」依次补足。"""
    profile = build_profile(customer)
    picks = []
    seen = set()

    # 1) 常点菜品：优先复购
    for d in profile['topDishes']:
        if len(picks) >= limit:
            break
        p = (ProductInfo.objects.select_related('merchant')
             .filter(id=d['productId'], status=10, stock__gt=0).first())
        if p and p.id not in seen:
            seen.add(p.id)
            picks.append(_pack(p, f"你点过 {d['times']} 次"))

    # 2) 常点商户的其他菜：同店探索
    for m in profile['topMerchants']:
        if len(picks) >= limit:
            break
        qs = (ProductInfo.objects.select_related('merchant')
              .filter(merchant_id=m['merchantId'], status=10, stock__gt=0)
              .exclude(id__in=seen)
              .annotate(sold=Count('order_items'))
              .order_by('-sold', '-id')[:3])
        for p in qs:
            if len(picks) >= limit:
                break
            seen.add(p.id)
            picks.append(_pack(p, f"来自你常点的「{m['name']}」"))

    # 3) 补足：全站热销（冷启动用户也走这条）
    if len(picks) < limit:
        qs = (ProductInfo.objects.select_related('merchant')
              .filter(status=10, stock__gt=0)
              .exclude(id__in=seen)
              .annotate(sold=Count('order_items'))
              .order_by('-sold', '-id')[:limit - len(picks)])
        for p in qs:
            seen.add(p.id)
            picks.append(_pack(p, '大家都在点' if profile['orderCount'] else '本店人气'))

    return picks


def build_reorder(customer):
    """取最近一笔有效订单，返回 (订单, 可复购明细, 不可用清单)。

    明细为 [(product, quantity)]，已过滤下架与库存不足的菜品。
    """
    order = (OrderInfo.objects.select_related('merchant')
             .filter(user=customer, status__in=VALID_STATUSES).order_by('-id').first())
    if not order:
        return None, [], []

    items, missing = [], []
    for it in order.items.select_related('product'):
        p = it.product
        if p.status != 10:
            missing.append(f'{it.product_name}（已下架）')
            continue
        if p.stock < it.quantity:
            missing.append(f'{it.product_name}（库存不足）')
            continue
        items.append((p, it.quantity))
    return order, items, missing
