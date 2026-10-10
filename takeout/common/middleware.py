"""开发用中间件：CORS + API 路径豁免 CSRF。"""

from django.http import HttpResponse
from django.middleware.csrf import CsrfViewMiddleware


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'OPTIONS':
            response = HttpResponse()
        else:
            response = self.get_response(request)

        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
        return response


class ApiCsrfExemptMiddleware(CsrfViewMiddleware):
    """/api/ 下的接口使用 Bearer Token 认证，不使用 Cookie，因此豁免 CSRF 校验。"""

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if request.path.startswith('/api/'):
            return None
        return super().process_view(request, callback, callback_args, callback_kwargs)
