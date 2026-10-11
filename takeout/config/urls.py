"""URL 配置。

- /admin/          平台运营后台
- /api/v1/         顾客端 H5 调用的接口
- /api/            商户端后台调用的接口
- /h5/             复用的顾客端页面
- /merchant-admin/ 复用的商户端页面
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve
from django.shortcuts import redirect
from django.http import FileResponse, Http404
import os

from common.dispatch import by_method
from ai_service import views as ai_api
from delivery import api_views as delivery_api
from merchant import api_views as merchant_api
from merchant import views as merchant_views
from order import api_views as order_api
from order import views as order_views
from platform_ops import api_views as platform_api
from product import api_views as product_api
from product import views as product_views
from review import views as review_views
from user import views as user_views

WEB_APPS = settings.BASE_DIR.parent / 'web' / 'apps'


def spa_serve(dist_root, legacy_root=None):
    """托管 Vite 构建产物：命中文件返回文件，未命中回退 index.html（SPA 路由）；
    dist 尚未构建时回退 legacy_root 旧页面目录。"""

    def wrapper(request, path='index.html'):
        base = os.path.normpath(str(dist_root))
        full = os.path.normpath(os.path.join(base, path))
        if full.startswith(base) and os.path.isfile(full):
            return FileResponse(open(full, 'rb'))
        index = os.path.join(base, 'index.html')
        if os.path.isfile(index):
            return FileResponse(open(index, 'rb'))
        if legacy_root is not None:
            return serve(request, path, document_root=legacy_root)
        raise Http404('前端尚未构建：请在 web/ 目录执行 npm run build')

    return wrapper

# 顾客端（H5）
api_patterns = [
    path('auth/code', user_views.auth_code),
    path('auth/login', user_views.auth_login),
    path('auth/callback', user_views.auth_callback),
    path('users/profile', user_views.profile),
    path('addresses', by_method(GET=user_views.address_list, POST=user_views.address_create)),
    path('addresses/<int:pk>', user_views.address_delete),
    path('merchants/nearby', merchant_views.nearby),
    path('merchants/<int:pk>', merchant_views.detail),
    path('merchants/<int:pk>/categories', merchant_views.categories),
    path('merchants/<int:pk>/products', product_views.merchant_products),
    path('products/search', product_views.product_search),
    path('products/<int:pk>', product_views.product_detail),
    path('orders', by_method(POST=order_views.create_order, GET=platform_api.orders)),
    path('orders/user', order_views.order_list),
    path('orders/<int:pk>', order_views.order_detail),
    path('orders/<int:pk>/cancel', order_views.order_cancel),
    path('orders/<int:pk>/review', review_views.create_review),
    path('merchants/<int:pk>/reviews', review_views.merchant_reviews),
    path('orders/<int:pk>/pay', order_views.order_pay),

    # 骑手端（配送）
    path('delivery/login', delivery_api.login),
    path('delivery/riders/<int:rider_id>', delivery_api.rider_info),
    path('delivery/riders/<int:rider_id>/status', delivery_api.rider_status),
    path('delivery/riders/<int:rider_id>/tasks', delivery_api.rider_tasks),
    path('delivery/tasks/pending', delivery_api.pending_tasks),
    path('delivery/tasks/<int:task_id>', delivery_api.task_detail),
    path('delivery/tasks/<int:task_id>/accept', delivery_api.accept_task),
    path('delivery/tasks/<int:task_id>/reject', delivery_api.reject_task),
    path('delivery/tasks/<int:task_id>/status', delivery_api.update_task_status),
    path('delivery/statistics', delivery_api.statistics),

    # 运营端（平台）
    path('platform/login', platform_api.login),
    path('platform/merchants', platform_api.merchants),
    path('platform/merchants/<int:pk>/audit', platform_api.merchant_audit),
    path('platform/statistics', platform_api.statistics),
    path('users', platform_api.users),

    # AI 点餐助手（顾客端功能）
    path('ai/session', ai_api.create_session),
    path('ai/chat', ai_api.chat),
    path('ai/drafts/<int:pk>', ai_api.draft_detail),
    path('ai/drafts/<int:pk>/confirm', ai_api.draft_confirm),
]

# 商户端（merchant-admin）
merchant_api_patterns = [
    path('merchant/register', merchant_api.register),
    path('merchant/login', merchant_api.login),
    path('merchant/current', merchant_api.current),
    path('merchant/info', merchant_api.update_info),
    path('merchant/status', merchant_api.update_status),
    path('merchant/avatar', merchant_api.upload_avatar),

    path('product/categories', product_api.category_list),
    path('product/category', product_api.category_create),
    path('product/category/<int:pk>', by_method(
        PUT=product_api.category_update, POST=product_api.category_update,
        DELETE=product_api.category_delete,
    )),
    path('product/merchant', product_api.product_list),
    path('product', product_api.product_create),
    path('product/<int:pk>', by_method(
        GET=product_api.product_detail,
        PUT=product_api.product_update, POST=product_api.product_update,
        DELETE=product_api.product_delete,
    )),
    path('product/<int:pk>/status', product_api.product_update_status),
    path('product/<int:pk>/stock', product_api.product_update_stock),

    path('order/merchant', order_api.order_list),
    path('order/<int:pk>', order_api.order_detail),
    path('order/<int:pk>/status', order_api.order_update_status),
    path('order/<int:pk>/cancel', order_api.order_cancel),

    path('stats/overview', order_api.stats_overview),
    path('stats/recent-orders', order_api.stats_recent_orders),
    path('stats/order-status', order_api.stats_order_status),
    path('stats/sales', order_api.stats_sales),
    path('stats/orders', order_api.stats_orders),
    path('stats/top-products', order_api.stats_top_products),
    path('stats/revenue-trend', order_api.stats_revenue_trend),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(api_patterns)),
    path('api/', include(merchant_api_patterns)),
    # 新前端 SPA（Vite 构建产物；未构建时自动回退旧 frontend 页面）
    path('merchant/', spa_serve(WEB_APPS / 'merchant' / 'dist',
                                settings.BASE_DIR / 'frontend' / 'merchant-admin')),
    path('merchant/<path:path>', spa_serve(WEB_APPS / 'merchant' / 'dist',
                                           settings.BASE_DIR / 'frontend' / 'merchant-admin')),
    path('rider/', spa_serve(WEB_APPS / 'rider' / 'dist',
                             settings.BASE_DIR / 'frontend' / 'rider')),
    path('rider/<path:path>', spa_serve(WEB_APPS / 'rider' / 'dist',
                                        settings.BASE_DIR / 'frontend' / 'rider')),
    # 旧前端页面（清理前保留可用）
    path('h5/<path:path>', serve, {'document_root': settings.BASE_DIR / 'frontend' / 'h5-food-delivery'}),
    path('merchant-admin/<path:path>', serve, {'document_root': settings.BASE_DIR / 'frontend' / 'merchant-admin'}),
    path('rider-index/', lambda request: redirect('/rider/index.html')),
    path('admin-ui/<path:path>', serve, {'document_root': settings.BASE_DIR / 'frontend' / 'admin'}),
    path('ai/', lambda request: redirect('/ai/index.html')),
    path('ai/<path:path>', serve, {'document_root': settings.BASE_DIR / 'frontend' / 'ai'}),
    path('frontend/<path:path>', serve, {'document_root': settings.BASE_DIR / 'frontend'}),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 顾客端 SPA：根路径兜底（必须放最后，吞掉所有未匹配路径并回退 index.html）
urlpatterns += [
    path('', spa_serve(WEB_APPS / 'customer' / 'dist', settings.BASE_DIR / 'frontend')),
    path('<path:path>', spa_serve(WEB_APPS / 'customer' / 'dist', settings.BASE_DIR / 'frontend')),
]
