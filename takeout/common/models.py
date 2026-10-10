from django.db import models


class BaseModel(models.Model):
    """公共基础模型：统一带上创建/更新时间。"""

    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        abstract = True
