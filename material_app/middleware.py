# material_app/middleware.py

from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from .models import AuthToken


class AuthMiddleware:
    """只檢查 cookie 中的 token，不查資料庫"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 不需要驗證的路徑
        excluded_paths = ['/material/login/',
                          '/material/logout/',
                          '/admin/'
                          ]

        # 跳過不需要驗證的路徑
        if request.path in excluded_paths:
            return self.get_response(request)

        # 驗證 token
        token = request.COOKIES.get('auth_token')

        if not token:
            print(f"❌ No token found, redirecting to login")
            return redirect('material:login')

            # ✅ 只要有 token 就放行，不驗證資料庫
        print(f"✅ Token found in cookie: {token[:20]}...")

        # 不再設定 request.employee（因為不查資料庫）
        # 如果 base.html 需要使用者資訊，後續再處理

        return self.get_response(request)