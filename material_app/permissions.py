# material/permissions.py

from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


class MaterialBoxPermission(permissions.BasePermission):
    """
    物料容器權限控制

    角色權限對應：
    - Admin (超級管理者): 完整 CRUD 權限
    - Manager (管理者): CRU 權限，不可刪除 transaction log
    - emp (使用者): 只讀權限
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Admin (超級管理者): 擁有所有權限 (CRUD)
        if user.groups.filter(name='Admin').exists():
            return True

        # Manager (管理者): 可 CRU，不可刪除 transaction log
        if user.groups.filter(name='Manager').exists():
            if request.method == 'DELETE':
                # 檢查是否刪除 transaction log
                if 'transaction' in request.path.lower() or 'history' in request.path.lower():
                    logger.warning(f"Manager {user.username} 嘗試刪除 transaction log")
                    return False
            return True

        # emp (使用者): 只能讀取
        if user.groups.filter(name='emp').exists():
            return request.method in permissions.SAFE_METHODS

        return False


class TransactionPermission(permissions.BasePermission):
    """
    交易記錄權限控制

    角色權限對應：
    - Admin (超級管理者): 查看/管理所有記錄
    - Manager (管理者): 查看所有記錄
    - emp (使用者): 只能查看自己的記錄
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Admin / Manager: 可查看全部
        if user.groups.filter(name__in=['Admin', 'Manager']).exists():
            return True

        # emp: 只能查看自己的
        if user.groups.filter(name='emp').exists():
            # ✅ 修正：檢查 view 是否有 action 屬性
            if hasattr(view, 'action') and view.action in ['list', 'my_transactions']:
                return True
            # 如果不是 ViewSet，允許 GET 請求
            if request.method in permissions.SAFE_METHODS:
                return True

        return False

    def has_object_permission(self, request, view, obj):
        """物件級權限 - emp 只能存取自己的記錄"""
        user = request.user

        # Admin / Manager: 可存取全部
        if user.groups.filter(name__in=['Admin', 'Manager']).exists():
            return True

        # emp: 只能存取自己的記錄
        # ✅ 修正：確保 obj 有 Operator 屬性
        if hasattr(obj, 'Operator'):
            return obj.Operator == user.username

        return False