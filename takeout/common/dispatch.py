"""按 HTTP 方法分发的视图包装器（用于同一 URL 支持 GET/PUT/DELETE）。"""

from django.http import JsonResponse


def by_method(**handlers):
    def view(request, *args, **kwargs):
        handler = handlers.get(request.method)
        if handler is None:
            return JsonResponse(
                {'success': False, 'data': None, 'message': '方法不允许'},
                status=405,
                json_dumps_params={'ensure_ascii': False},
            )
        return handler(request, *args, **kwargs)

    return view
