"""
Django settings for the "基于 Python 的外卖平台" project.

数据库默认使用 SQLite，可通过环境变量 DB_ENGINE=mysql 一键切换到 MySQL。
"""

import os
from decimal import Decimal
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# 运行模式：默认开发/演示（DEBUG=True）；生产部署时设置环境变量 DJANGO_DEBUG=0
DEBUG = os.environ.get('DJANGO_DEBUG', '1').lower() not in ('0', 'false', 'no')

# 密钥：优先从环境变量 DJANGO_SECRET_KEY 注入。
# 生产模式（DJANGO_DEBUG=0）下未注入则拒绝启动；开发/演示模式使用内置值以保持零配置运行。
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured('生产环境必须通过 DJANGO_SECRET_KEY 环境变量注入密钥')
    SECRET_KEY = 'django-insecure-9$e+9ra9^0)*6()v$2!t%(ldgi6js4e7xl4snxx266wjsd+ef%'  # 仅限本地开发与演示

# 允许的主机：生产部署时通过环境变量 DJANGO_ALLOWED_HOSTS 注入（逗号分隔）
ALLOWED_HOSTS = [h for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',') if h]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 业务模块
    'common',
    'user',
    'merchant',
    'product',
    'cart',
    'order',
    'payment',
    'delivery',
    'review',
    'ai_service',
    'platform_ops',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'common.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'common.middleware.ApiCsrfExemptMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# 默认 SQLite；设置环境变量 DB_ENGINE=mysql 即切换到 MySQL。
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite').lower()

if DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'takeout'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {'charset': 'utf8mb4'},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = False


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media (上传文件)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---- AI 大语言模型（OpenAI 兼容接口，默认经 rayagent 中转的 DeepSeek）----
# 通过环境变量注入，未配置 Key 时自动使用内置 Mock，便于本地联调。
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://rayagent.cloud:2026/v1")
LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-v4.1-flash")

# 平台统一配送费（本期为固定值，下单时快照入订单）
DELIVERY_FEE = Decimal(os.environ.get('DELIVERY_FEE', '2.00'))
