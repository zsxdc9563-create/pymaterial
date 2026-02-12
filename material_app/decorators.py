# material_app/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)


def admin_required(view_func):
    """只有 Admin 可以執行"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.groups.filter(name='Admin').exists():
            messages.error(request, '此功能僅限超級管理者使用')
            logger.warning(f"權限不足: {request.user.username} 嘗試執行 Admin 功能")
            return redirect('material:index')
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_or_admin_required(view_func):
    """Admin 或 Manager 可以執行"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['Admin', 'Manager']).exists():
            messages.error(request, '此功能僅限管理者使用')
            logger.warning(f"權限不足: {request.user.username} 嘗試執行 Manager 功能")
            return redirect('material:index')
        return view_func(request, *args, **kwargs)
    return wrapper


def employee_can_view(view_func):
    """所有人都可以查看 (包括 Employee)"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 所有登入用戶都可以查看
        return view_func(request, *args, **kwargs)
    return wrapper