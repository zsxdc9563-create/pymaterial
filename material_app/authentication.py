# material_app/middleware.py

import requests
from django.shortcuts import redirect
from django.core.cache import cache
from django.contrib.auth.models import User, Group
from django.conf import settings
from .models import AuthToken
from urllib.parse import unquote
import logging

logger = logging.getLogger(__name__)


class ThirdPartyAuthMiddleware:
    """整合第三方 API 認證的中介層（適配現有 cookie 登入）"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 不需要驗證的路徑
        excluded_paths = [
            '/material/login/',
            '/material/logout/',
            '/admin/',
            '/static/',
            '/media/',
        ]

        # 跳過不需要驗證的路徑
        if any(request.path.startswith(path) for path in excluded_paths):
            return self.get_response(request)

        # 取得 token 和使用者資訊（從 cookie）
        token = request.COOKIES.get('auth_token')
        user_emp_id = request.COOKIES.get('user_emp_id')
        user_name = unquote(request.COOKIES.get('user_name', ''))

        if not token or not user_emp_id:
            logger.warning(f"❌ No token or user_emp_id found, redirecting to login")
            return redirect('material:login')

        # ✅ 驗證 token 並取得使用者角色
        user_info = self._verify_token_and_get_role(token, user_emp_id, user_name)

        if not user_info:
            logger.warning(f"❌ Invalid token, redirecting to login")
            response = redirect('material:login')
            response.delete_cookie('auth_token')
            response.delete_cookie('user_emp_id')
            response.delete_cookie('user_name')
            return response

        # 取得或建立 Django User，並設定到 request
        user = self._get_or_create_user(user_info)
        request.user = user
        request.user_info = user_info

        logger.info(f"✅ User authenticated: {user.username} (Role: {user_info.get('role')})")

        return self.get_response(request)

    def _verify_token_and_get_role(self, token, user_emp_id, user_name):
        """驗證 token 並從第三方 API 取得使用者角色"""

        # 先檢查快取
        cache_key = f'user_role_{user_emp_id}'
        cached_info = cache.get(cache_key)

        if cached_info:
            logger.debug(f"📦 Using cached user info for {user_emp_id}")
            return cached_info

        try:
            # ✅ 呼叫 /api/me 取得當前使用者完整資訊（包括角色）
            me_api_url = 'http://192.168.0.10:9987/api/me'
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(me_api_url, headers=headers, timeout=5)

            if response.status_code == 200:
                user_data = response.json()

                # 提取角色資訊
                role = (
                        user_data.get('Role') or
                        user_data.get('role') or
                        user_data.get('JobTitle') or
                        user_data.get('job_title') or
                        'employee'  # 預設角色
                )

                user_info = {
                    'id': user_emp_id,
                    'username': user_name or user_emp_id,
                    'email': user_data.get('Email') or user_data.get('email', ''),
                    'role': role,
                    'first_name': user_name.split()[0] if user_name else '',
                    'last_name': user_name.split()[1] if len(user_name.split()) > 1 else '',
                }

                # 快取 10 分鐘
                cache.set(cache_key, user_info, 600)

                logger.debug(f"✅ Fetched role from API: {role} for user {user_emp_id}")
                return user_info

            elif response.status_code == 401:
                # Token 失效
                logger.warning(f"Token expired for user {user_emp_id}")
                return None
            else:
                logger.error(f"API returned status {response.status_code}")
                # API 異常時使用備援
                return self._fallback_verification(user_emp_id, user_name)

        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            return self._fallback_verification(user_emp_id, user_name)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    def _fallback_verification(self, user_emp_id, user_name):
        """當第三方 API 無法連線時的備援方案"""
        logger.warning(f"⚠️ Using fallback verification for {user_emp_id}")

        return {
            'id': user_emp_id,
            'username': user_name or user_emp_id,
            'email': '',
            'role': 'employee',  # 預設角色
            'first_name': user_name.split()[0] if user_name else '',
            'last_name': '',
            'from_fallback': True
        }

    def _get_or_create_user(self, user_info):
        """取得或建立 Django User，並同步角色"""

        username = user_info.get('username', f"user_{user_info.get('id')}")

        # 取得或建立 User
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': user_info.get('email', ''),
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
            }
        )

        if created:
            logger.info(f"✨ Created new user: {username}")

        # 同步角色到 Django Groups
        self._sync_user_role(user, user_info.get('role'))

        return user

    def _sync_user_role(self, user, role):
        """同步使用者角色到 Django Groups"""

        # ✅ 角色映射（根據你的第三方 API 可能回傳的角色名稱）
        role_mapping = {
            # 可能的角色名稱變體
            'Admin': 'Admin',
            'admin': 'Admin',
            'Administrator': 'Admin',
            '管理員': 'Admin',

            'Manager': 'Manager',
            'manager': 'Manager',
            '主管': 'Manager',
            '經理': 'Manager',

            'Employee': 'emp',
            'employee': 'emp',
            'Staff': 'emp',
            'staff': 'emp',
            '員工': 'emp',
        }

        # 清除現有群組
        user.groups.clear()

        # 分配新群組
        group_name = role_mapping.get(role, 'emp')  # 預設為 emp
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)

        logger.debug(f"👥 Assigned user {user.username} to group {group_name} (原始角色: {role})")