# material_app/services/rbac_service.py
import logging
from ..models import Role, Permission, UserRole, RolePermission
from django.contrib.auth.models import User


from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
logger = logging.getLogger(__name__)


# ── Role ──────────────────────────────────────────────

def get_all_roles():
    return Role.objects.all().order_by('id')


def get_role_or_none(role_id):
    try:
        return Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        return None


def create_role(name, description=None):
    return Role.objects.create(name=name, description=description)


def update_role(role, name, description=None):
    role.name = name
    role.description = description
    role.save()
    return role


def delete_role(role):
    role.delete()


# ── Permission ────────────────────────────────────────

def get_all_permissions():
    return Permission.objects.all().order_by('id')


def get_permission_or_none(permission_id):
    try:
        return Permission.objects.get(id=permission_id)
    except Permission.DoesNotExist:
        return None


def create_permission(name, description=None):
    return Permission.objects.create(name=name, description=description)


def delete_permission(permission):
    permission.delete()


# ── UserRole ──────────────────────────────────────────

def get_all_user_roles():
    return UserRole.objects.select_related('user', 'role').all()


def assign_role_to_user(user, role):
    user_role, created = UserRole.objects.get_or_create(user=user, role=role)
    return user_role, created


def remove_role_from_user(user, role):
    UserRole.objects.filter(user=user, role=role).delete()


def get_user_roles(user):
    return UserRole.objects.filter(user=user).select_related('role')


# ── RolePermission ────────────────────────────────────

def get_all_role_permissions():
    return RolePermission.objects.select_related('role', 'permission').all()


def assign_permission_to_role(role, permission):
    role_permission, created = RolePermission.objects.get_or_create(
        role=role, permission=permission
    )
    return role_permission, created


def remove_permission_from_role(role, permission):
    RolePermission.objects.filter(role=role, permission=permission).delete()


def get_role_permissions(role):
    return RolePermission.objects.filter(role=role).select_related('permission')






def register_user(username, password, email=None):
    if User.objects.filter(username=username).exists():
        raise ValueError('帳號已存在')
    
    if not email:
        raise ValueError('Email 為必填')
    
    if User.objects.filter(email=email).exists():
        raise ValueError('此 Email 已被註冊')
    
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
    )
    
    try:
        employee_role = Role.objects.get(name='employee')
        UserRole.objects.create(user=user, role=employee_role)
    except Role.DoesNotExist:
        pass
    
    return user

def send_password_reset_email(email, frontend_url='http://localhost:3000'):
    """寄送重設密碼信件"""
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        raise ValueError('此 Email 尚未註冊')

    # 產生 token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # 重設密碼連結
    reset_url = f'{frontend_url}/reset-password/{uid}/{token}'

    # 寄信
    send_mail(
        subject='重設密碼',
        message=f'請點擊以下連結重設密碼：\n\n{reset_url}\n\n此連結有效期限為 24 小時。',
        from_email=None,  # 使用 settings.py 的 DEFAULT_FROM_EMAIL
        recipient_list=[email],
    )
    return True


def reset_password(uid, token, new_password):
    """驗證 token 並重設密碼"""
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError):
        raise ValueError('無效的連結')

    if not default_token_generator.check_token(user, token):
        raise ValueError('連結已過期或無效')

    user.set_password(new_password)
    user.save()
    return True