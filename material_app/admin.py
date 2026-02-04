# material_app/admin.py
#是用來註冊 Django 管理後台的，不是用來建立測試帳號的
# material_app/admin.py

from django.contrib import admin
from .models import (
    MaterialOverview,
    MaterialItems,
    TransactionLog,
    Employee

)

@admin.register(MaterialOverview)
class MaterialOverviewAdmin(admin.ModelAdmin):
    list_display = ['BoxID', 'Category', 'Description', 'Owner', 'Status', 'Locked', 'CreateDate']
    list_filter = ['Category', 'Status', 'Locked']
    search_fields = ['BoxID', 'Description', 'Owner']


@admin.register(MaterialItems)
class MaterialItemsAdmin(admin.ModelAdmin):
    list_display = ['SN', 'ItemName', 'Spec', 'BoxID', 'Quantity', 'Location', 'UpdateTime']
    list_filter = ['BoxID', 'Location']
    search_fields = ['SN', 'ItemName', 'Spec']


@admin.register(TransactionLog)
class MaterialTransactionAdmin(admin.ModelAdmin):
    list_display = ['LogID', 'SN', 'ActionType', 'FromBoxID', 'ToBoxID', 'TransQty', 'Operator', 'Timestamp']
    list_filter = ['ActionType', 'Timestamp']
    search_fields = ['SN__SN', 'SN__ItemName', 'Operator']
    date_hierarchy = 'Timestamp'


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['EmpID', 'Name', 'DeptID', 'IsActive', 'LastSync']
    list_filter = ['IsActive', 'DeptID']
    search_fields = ['EmpID', 'Name']