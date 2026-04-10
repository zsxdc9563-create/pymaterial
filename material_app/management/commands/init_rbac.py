# material_app/management/commands/init_rbac.py
from django.core.management.base import BaseCommand
from material_app.models import Role, Permission, RolePermission


class Command(BaseCommand):
    help = '初始化 RBAC 角色和權限資料'

    def handle(self, *args, **kwargs):

        # ── 建立 Permission ────────────────────────────────────
        permissions_data = [
            ('create', '新增資料'),
            ('read', '查看資料'),
            ('update', '修改資料'),
            ('delete', '刪除資料'),
            ('approve_borrow', '審核借用申請'),
        ]

        permissions = {}
        for name, description in permissions_data:
            perm, created = Permission.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            permissions[name] = perm
            status = '建立' if created else '已存在'
            self.stdout.write(f'Permission [{status}]: {name}')

        # ── 建立 Role ──────────────────────────────────────────
        roles_data = [
            ('superadmin', '超級管理員'),
            ('admin', '管理員'),
            ('manager', '倉管員'),
            ('employee', '一般員工'),
        ]

        roles = {}
        for name, description in roles_data:
            role, created = Role.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            roles[name] = role
            status = '建立' if created else '已存在'
            self.stdout.write(f'Role [{status}]: {name}')

        # ── 指派 RolePermission ────────────────────────────────
        role_permissions = {
            'superadmin': ['create', 'read', 'update', 'delete', 'approve_borrow'],
            'admin':      ['create', 'read', 'update', 'approve_borrow'],
            'manager':    ['create', 'read'],
            'employee':   ['read'],
        }

        for role_name, perm_names in role_permissions.items():
            for perm_name in perm_names:
                rp, created = RolePermission.objects.get_or_create(
                    role=roles[role_name],
                    permission=permissions[perm_name]
                )
                status = '建立' if created else '已存在'
                self.stdout.write(f'RolePermission [{status}]: {role_name} → {perm_name}')

        self.stdout.write(self.style.SUCCESS('\nRBAC 初始化完成！'))