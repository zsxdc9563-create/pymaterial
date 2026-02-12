# material_app/management/commands/manage_employee.py
#
# 用法：
#   python manage.py manage_employee list                          ← 列出所有員工
#   python manage.py manage_employee add --id E001 --name 小明 --pw 123456  ← 新增員工
#   python manage.py manage_employee change_pw --id E001 --pw 新密碼        ← 改密碼
#   python manage.py manage_employee deactivate --id E001                   ← 停用帳號
#   python manage.py manage_employee activate --id E001                     ← 啟用帳號

from django.core.management.base import BaseCommand
from material_app.models import Employee


class Command(BaseCommand):
    help = '員工帳號管理：list / add / change_pw / activate / deactivate'

    def add_arguments(self, parser):
        parser.add_argument('action', type=str,
                            choices=['list', 'add', 'change_pw', 'activate', 'deactivate'],
                            help='操作類型')
        parser.add_argument('--id',   type=str, help='輸入工號')
        parser.add_argument('--name', type=str, help='員工姓名')
        parser.add_argument('--pw',   type=str, help='密碼')

    def handle(self, *args, **options):
        action = options['action']

        # ── list ──
        if action == 'list':
            employees = Employee.objects.all()
            if not employees.exists():
                self.stdout.write('目前沒有任何員工帳號。')
                return
            self.stdout.write(self.style.SUCCESS('── 員工列表 ──'))
            for emp in employees:
                status = '啟用' if emp.IsActive else '停用'
                self.stdout.write(f'  {emp.EmpID}  {emp.Name}  [{status}]')
            return

        # ── add ──
        if action == 'add':
            emp_id = options.get('id')
            name   = options.get('name')
            pw     = options.get('pw')

            if not emp_id or not name or not pw:
                self.stderr.write('新增員工需要 --id、--name、--pw 三個參數')
                return

            if Employee.objects.filter(EmpID=emp_id).exists():
                self.stderr.write(f'打工號 {emp_id} 已存在')
                return

            emp = Employee(EmpID=emp_id, Name=name)
            emp.set_password(pw)
            emp.save()
            self.stdout.write(self.style.SUCCESS(f'員工 {emp_id} ({name}) 新增完成'))
            return

        # ── change_pw ──
        if action == 'change_pw':
            emp_id = options.get('id')
            pw     = options.get('pw')

            if not emp_id or not pw:
                self.stderr.write('改密碼需要 --id 和 --pw')
                return

            try:
                emp = Employee.objects.get(EmpID=emp_id)
                emp.set_password(pw)
                emp.save()
                self.stdout.write(self.style.SUCCESS(f'{emp_id} 密碼已更新'))
            except Employee.DoesNotExist:
                self.stderr.write(f'找不到打工號 {emp_id}')
            return

        # ── activate / deactivate ──
        if action in ('activate', 'deactivate'):
            emp_id = options.get('id')
            if not emp_id:
                self.stderr.write('需要 --id 參數')
                return

            try:
                emp = Employee.objects.get(EmpID=emp_id)
                emp.IsActive = (action == 'activate')
                emp.save()
                label = '啟用' if emp.IsActive else '停用'
                self.stdout.write(self.style.SUCCESS(f'{emp_id} 已{label}'))
            except Employee.DoesNotExist:
                self.stderr.write(f'找不到打工號 {emp_id}')
            return