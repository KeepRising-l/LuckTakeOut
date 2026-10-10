"""通用工具函数。"""

import json


def get_json(request):
    """从请求体中解析 JSON，失败时返回空字典。"""
    try:
        body = request.body.decode('utf-8') if request.body else ''
        return json.loads(body) if body else {}
    except Exception:
        return {}
