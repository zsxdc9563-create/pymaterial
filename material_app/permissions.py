# material_app/permissions.py


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or 
        user.groups.filter(name='admin').exists()
    )

def is_manager(user):
    return user.is_authenticated and user.groups.filter(name='manager').exists()


def is_employee(user):
    return user.is_authenticated and user.groups.filter(name='emp').exists()


def can_manage(user):
    """admin 或 manager 才能新增/編輯"""
    return is_admin(user) or is_manager(user)


def can_delete_box(user):
    """只有 admin 可以刪除箱子"""
    return is_admin(user)


def can_edit_box(user, box):
    """
    編輯箱子的權限：
    - admin：永遠可以
    - 個人箱子（personal）：只有 owner 可以編輯
    - 其他類型：manager 以上可以
    """
    if is_admin(user):
        return True
    if box.box_type == 'personal':
        return box.owner == user
    return is_manager(user)


def can_edit_material(user):
    """新增/刪除物料：admin 或 manager"""
    return is_admin(user) or is_manager(user)


def can_stock_in_out(user):
    """入庫/出庫/調撥：所有登入使用者"""
    return user.is_authenticated


def can_manage_bom(user):
    """BOM 管理：admin 或 manager"""
    return is_admin(user) or is_manager(user)


def can_lock_box(user):
    """鎖定/解鎖箱子：admin 或 manager"""
    return is_admin(user) or is_manager(user)