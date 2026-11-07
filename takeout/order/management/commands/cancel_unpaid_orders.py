"""取消超时未支付订单并回补库存。

由计划任务周期执行（建议每分钟一次）：
    * * * * * cd /path/to/takeout && python manage.py cancel_unpaid_orders

常用参数：
    --minutes 30    临时指定超时分钟数（默认取 settings.UNPAID_ORDER_TIMEOUT_MINUTES）
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from order.services import cancel_expired_unpaid_orders


class Command(BaseCommand):
    help = '取消超过时限仍未支付的订单，并回补对应库存（可重复执行）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=None,
            help='超时分钟数；缺省读取 UNPAID_ORDER_TIMEOUT_MINUTES（默认 15）',
        )

    def handle(self, *args, **options):
        minutes = options.get('minutes')
        if minutes is None:
            minutes = getattr(settings, 'UNPAID_ORDER_TIMEOUT_MINUTES', 15)
        if minutes <= 0:
            raise CommandError('--minutes 必须为正整数')

        canceled = cancel_expired_unpaid_orders(minutes)
        self.stdout.write(self.style.SUCCESS(
            f'已取消 {canceled} 笔超过 {minutes} 分钟未支付的订单'
        ))
