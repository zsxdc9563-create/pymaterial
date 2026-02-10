# material_app/middleware.py

import requests
import logging
from django.shortcuts import redirect
from django.contrib import messages
from django.core.cache import cache
from django.contrib.auth.models import User, Group
from urllib.parse import unquote

logger = logging.getLogger(__name__)


class Employee:
    """模擬 Employee 物件，存儲從外部 API 取得的資料"""

    def __init__(self, data):
        self.EmpID = data.get('emp_id') or data.get('ID') or data.get('id') or data.get('EmpID')
        self.Name = data.get('name') or data.get('Name')
        self.DeptID = data.get('department') or data.get('DepartmentID') or data.get('department_mode')
        self.JobGrade = data.get('JobGrade') or data.get('job_grade')
        self.Birthday = data.get('Birthday') or data.get('birthday')
        self.Gender = data.get('gender') or data.get('Gender')
        self.Email = data.get('email') or data.get('Email', '')


class ThirdPartyAuthMiddleware:
    """整合第三方 API 認證的中介層"""

    def __init__(self, get_response):
        self.get_response = get_response
        # 不需要驗證的路徑
        self.exempt_paths = [
            '/material/login/',
            '/material/logout/',
            '/admin/',
            '/static/',
            '/media/',
        ]

    def __call__(self, request):
        # 跳過不需要驗證的路徑
        if any(request.path.startswith(path) for path in self.exempt_paths):
            return self.get_response(request)

        # 檢查 token
        token = request.COOKIES.get('auth_token')
        user_emp_id = request.COOKIES.get('user_emp_id')
        user_name = unquote(request.COOKIES.get('user_name', ''))

        if not token or not user_emp_id:
            logger.warning(f"❌ 沒有 token 或 user_emp_id")
            messages.error(request, '請先登入')
            return redirect('material:login')

        try:
            # 檢查快取
            cache_key = f'user_info_{user_emp_id}'
            cached_info = cache.get(cache_key)

            if cached_info:
                logger.debug(f"📦 使用快取: {user_emp_id} - {cached_info['raw_role']}")
                request.employee = Employee(cached_info['employee_data'])
                request.user_role = cached_info['role']
                request.user_role_display = cached_info['role_display']
                request.user_roles = cached_info['roles']

                request.user_info = {
                    'id': user_emp_id,
                    'username': user_name or user_emp_id,
                    'role': cached_info['normalized_role'],
                    'role_display': cached_info['raw_role'],
                }
            else:
                # 呼叫 /api/me 取得資料
                logger.info(f"📤 呼叫 /api/me 驗證用戶 {user_emp_id}...")
                me_response = requests.get(
                    'http://192.168.0.10:9987/api/me',
                    headers={'Authorization': f'Bearer {token}'},
                    timeout=5
                )

                if me_response.status_code != 200:
                    logger.error(f"❌ Token 驗證失敗: {me_response.status_code}")
                    messages.error(request, '登入已過期，請重新登入')
                    response = redirect('material:login')
                    response.delete_cookie('auth_token')
                    response.delete_cookie('user_emp_id')
                    response.delete_cookie('user_name')
                    return response

                user_data = me_response.json()
                logger.info(f"📥 API 返回資料: emp_id={user_data.get('emp_id')}, name={user_data.get('name')}")

                # 建立 Employee 物件
                request.employee = Employee(user_data)

                # ✅ 只讀取 roles 字段，忽略 permissions
                all_roles = user_data.get('roles', [])
                logger.info(f"📋 所有角色 (roles): {all_roles}")

                # ✅ 過濾出 MMS 開頭的角色
                mms_roles = [role for role in all_roles if isinstance(role, str) and role.startswith('MMS_')]
                logger.info(f"🎯 MMS 角色: {mms_roles}")

                # 檢查是否有 MMS 角色
                if not mms_roles:
                    logger.warning(f"❌ 用戶 {user_emp_id} 沒有 MMS 系統角色")
                    messages.error(request, '您沒有物料管理系統的存取權限，請聯絡系統管理員')
                    response = redirect('material:login')
                    response.delete_cookie('auth_token')
                    response.delete_cookie('user_emp_id')
                    response.delete_cookie('user_name')
                    return response

                # ✅ 選擇最高權限的 MMS 角色
                raw_role = self._get_highest_mms_role(mms_roles)
                logger.info(f"🔐 最高 MMS 角色: {raw_role}")

                # 標準化角色
                normalized_role = self._normalize_role(raw_role)
                logger.info(f"🔄 標準化: {raw_role} → {normalized_role}")

                # 判斷權限等級和顯示名稱
                if normalized_role == 'Admin':
                    request.user_role = 'admin'
                    request.user_role_display = '物料系統_超級管理者'
                elif normalized_role == 'Manager':
                    request.user_role = 'manager'
                    request.user_role_display = '物料系統_管理者'
                else:
                    request.user_role = 'user'
                    request.user_role_display = '物料系統_使用者'

                request.user_roles = mms_roles

                request.user_info = {
                    'id': user_emp_id,
                    'username': user_name or user_emp_id,
                    'role': normalized_role,
                    'role_display': raw_role,
                }

                # 快取 10 分鐘
                cache.set(cache_key, {
                    'employee_data': user_data,
                    'role': request.user_role,
                    'role_display': request.user_role_display,
                    'roles': mms_roles,
                    'normalized_role': normalized_role,
                    'raw_role': raw_role,
                }, 600)
                logger.info(f"💾 快取 MMS 角色: {raw_role} ({request.user_role_display})")

            # 同步到 Django User
            user_info = {
                'id': user_emp_id,
                'username': user_name or user_emp_id,
                'role': request.user_role,
                'email': getattr(request.employee, 'Email', ''),
            }
            django_user = self._get_or_create_user(user_info)
            request.user = django_user

            logger.info(f"✅ 驗證成功: {request.user.username} - {request.user_role_display}")

        except requests.RequestException as e:
            logger.error(f"❌ API 請求失敗: {e}")
            messages.error(request, '驗證服務異常，請稍後再試')
            return redirect('material:login')
        except Exception as e:
            logger.error(f"❌ 系統錯誤: {e}")
            import traceback
            traceback.print_exc()
            messages.error(request, '系統錯誤，請稍後再試')
            return redirect('material:login')

        response = self.get_response(request)
        return response

    def _get_highest_mms_role(self, mms_roles):
        """
        從 MMS 角色列表中選擇最高權限的角色

        優先級: MMS_admin > MMS_manager > MMS_user
        """
        # 角色優先級（數字越小優先級越高）
        priority = {
            'MMS_admin': 1,
            'MMS_manager': 2,
            'MMS_user': 3,
        }

        # 找出優先級最高的角色
        highest_role = min(mms_roles, key=lambda role: priority.get(role, 999))

        logger.debug(f"🎖️ 角色選擇: {mms_roles} → {highest_role}")
        return highest_role

    def _normalize_role(self, raw_role):
        """標準化角色名稱（只處理 MMS 三層角色）"""
        role_mapping = {
            'MMS_admin': 'Admin',  # 超級管理者
            'MMS_manager': 'Manager',  # 管理者
            'MMS_user': 'Employee',  # 使用者
        }
        normalized = role_mapping.get(raw_role, 'Employee')
        return normalized

    def _get_or_create_user(self, user_info):
        """取得或建立 Django User，並同步角色"""
        username = user_info.get('username', f"user_{user_info.get('id')}")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': user_info.get('email', ''),
                'first_name': username.split()[0] if username else '',
                'last_name': username.split()[1] if len(username.split()) > 1 else '',
            }
        )

        if created:
            logger.info(f"✨ 建立新用戶: {username}")

        # 同步角色到 Django Groups
        self._sync_user_role(user, user_info.get('role'))
        return user

    def _sync_user_role(self, user, role):
        """同步使用者角色到 Django Groups"""
        group_mapping = {
            'admin': 'Admin',  # MMS_admin → Admin
            'manager': 'Manager',  # MMS_manager → Manager
            'user': 'emp',  # MMS_user → emp
        }

        user.groups.clear()
        group_name = group_mapping.get(role, 'emp')
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
        logger.debug(f"👥 分配群組: {user.username} → {group_name}")