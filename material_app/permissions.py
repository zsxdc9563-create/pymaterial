# material_app/permissions.py
from .models import UserRole


def has_role(user, role_name):
    return UserRole.objects.filter(
        user=user,
        role__name=role_name
    ).exists()


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or
        has_role(user, 'admin') or
        has_role(user, 'superadmin')
    )


def is_manager(user):
    return user.is_authenticated and has_role(user, 'manager')


def is_employee(user):
    return user.is_authenticated and has_role(user, 'employee')


def can_manage(user):
    """admin 或 manager 才能新增/編輯"""
    return is_admin(user) or is_manager(user)


def can_delete_box(user):
    """只有 admin 可以刪除箱子"""
    return is_admin(user)


def can_edit_box(user, box):
    if is_admin(user):
        return True
    if box.box_type == 'personal':
        return box.owner == user
    return is_manager(user)


def can_edit_material(user):
    return is_admin(user) or is_manager(user)


def can_stock_in_out(user):
    return user.is_authenticated


def can_manage_bom(user):
    return is_admin(user) or is_manager(user)


def can_lock_box(user):
    return is_admin(user) or is_manager(user)