"""
Django settings for core project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv



# 載入 .env 檔案
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# ==================================================
# 安全性設定
# ==================================================

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only-key')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
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
    'corsheaders',
]


# ==================================================
# Middleware
# ==================================================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
# ==================================================


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'material',
        'USER': 'root',
        'PASSWORD': 'root1234',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
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

LOGIN_URL = '/material/login/'
LOGIN_REDIRECT_URL = '/material/'
LOGOUT_REDIRECT_URL = '/material/login/'


# ==================================================
# 快取
# ==================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}








# ==================================================
# Email 設定（Gmail）
# ==================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'zsxdc9563@gmail.com'
EMAIL_HOST_PASSWORD = 'xjegkmdnvmggzdas'
DEFAULT_FROM_EMAIL = 'zsxdc9563@gmail.com'

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
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}
#SessionAuthentication（原本的）
#登入之後 Django 會在瀏覽器存一個 Cookie，之後每次請求都帶著這個 Cookie 來驗證身份。
#使用者登入 → Django 存 Cookie → 之後請求帶 Cookie → Django 認得你
#適合：傳統網頁（Django Template）

#JWTAuthentication（新加的）
#登入之後後端回傳一個 Token 字串，之後每次請求都在 Header 帶著這個 Token。
#使用者登入 → 後端回傳 Token → 之後請求帶 Token → 後端認得你
#適合：前後端分離（React + Django API）



#   在 Django 後端告訴瀏覽器：
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]