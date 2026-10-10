from django.conf import settings
from django.db import models

from common.models import BaseModel


class OperationLog(models.Model):
    """操作日志 / 审计（含 AI 工具调用）"""

    actor_id = models.IntegerField('操作者ID', null=True, blank=True)
    actor_role = models.CharField('操作者角色', max_length=20, blank=True, default='')
    action = models.CharField('动作', max_length=50)
    target_type = models.CharField('目标类型', max_length=50, blank=True, default='')
    target_id = models.IntegerField('目标ID', null=True, blank=True)
    detail = models.TextField('详情', blank=True, default='')
    result = models.CharField('结果', max_length=20, blank=True, default='')
    ip = models.CharField('IP', max_length=50, blank=True, default='')
    create_time = models.DateTimeField('时间', auto_now_add=True)

    class Meta:
        db_table = 'operation_log'
        verbose_name = '操作日志'
        verbose_name_plural = verbose_name
        indexes = [models.Index(fields=['actor_id', 'create_time'])]


class Notification(BaseModel):
    """站内信"""

    TYPE_URGE = 10
    TYPE_SYSTEM = 20

    TYPE_CHOICES = ((TYPE_URGE, '催单'), (TYPE_SYSTEM, '系统'))

    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications', verbose_name='接收人',
    )
    title = models.CharField('标题', max_length=100)
    content = models.CharField('内容', max_length=255, blank=True, default='')
    type = models.SmallIntegerField('类型', choices=TYPE_CHOICES, default=TYPE_SYSTEM)
    is_read = models.BooleanField('已读', default=False)

    class Meta:
        db_table = 'notification'
        verbose_name = '站内信'
        verbose_name_plural = verbose_name


class SystemConfig(BaseModel):
    """系统配置"""

    config_key = models.CharField('配置键', max_length=50, unique=True)
    config_value = models.CharField('配置值', max_length=255, blank=True, default='')
    remark = models.CharField('备注', max_length=255, blank=True, default='')

    class Meta:
        db_table = 'system_config'
        verbose_name = '系统配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.config_key
