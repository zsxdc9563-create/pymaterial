# material_app/decorators.py (新增檔案)

from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    """只允許 Admin 訪問"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.groups.filter(name='Admin').exists():
            messages.error(request, '此功能需要管理員權限')
            return redirect('material:index')
        return view_func(request, *args, **kwargs)
    return wrapper

def manager_or_admin_required(view_func):
    """只允許 Manager 或 Admin 訪問"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.groups.filter(name__in=['Admin', 'Manager']).exists():
            messages.error(request, '此功能需要主管或管理員權限')
            return redirect('material:index')
        return view_func(request, *args, **kwargs)
    return wrapper