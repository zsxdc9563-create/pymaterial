"""
Django settings for core project.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ==================================================
# 安全性設定
# ==================================================

# TODO: 正式上線前請更換為隨機產生的 secret key
# 產生方式：python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = 'django-insecure-8$a8gze^bc2!f^018cu1h7)#ag@^eo%12bb^yz@40cbkve19bf'

# 正式上線請改為 False
DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '192.168.1.160'
]


# ==================================================
# 應用程式
# ==================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'material_app',
    'rest_framework',
]


# ==================================================
# Middleware
# ==================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # 前公司第三方認證 middleware，已移除
    # 'material_app.middleware.ThirdPartyAuthMiddleware',
]


# ==================================================
# URL / WSGI
# ==================================================

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'


# ==================================================
# Templates
# ==================================================

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


# ==================================================
# 資料庫
# 前公司 MySQL 已移除，改用本地 SQLite 開發
# ==================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}



# ==================================================
# 認證
# ==================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 登入/登出導向頁面
LOGIN_URL = '/admin/login/'          # TODO: 之後自己設計登入頁面再改這裡
LOGIN_REDIRECT_URL = '/material/'
LOGOUT_REDIRECT_URL = '/admin/login/'

# 前公司外部認證 API（已移除）
# EXTERNAL_AUTH_LOGIN_URL = 'http://192.168.0.10:9987/api/auth/login'
# EXTERNAL_AUTH_API_BASE  = 'http://192.168.0.10:9987/api/users'
# EXTERNAL_AUTH_TIMEOUT   = 10


# ==================================================
# 快取（本地記憶體，開發用）
# ==================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}


# ==================================================
# 日誌
# ==================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'material_app': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


# ==================================================
# 國際化
# ==================================================

LANGUAGE_CODE = 'zh-hant'
TIME_ZONE = 'Asia/Taipei'
USE_I18N = True
USE_TZ = False


# ==================================================
# 靜態檔案
# ==================================================

STATIC_URL = 'static/'


# ==================================================
# Django REST Framework
# ==================================================

REST_FRAMEWORK = {
    # 目前全部公開，之後設計權限系統再調整
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
}