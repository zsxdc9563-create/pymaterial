# material_app/admin.py

from django.contrib import admin
from .models import (
    MaterialOverview,
    MaterialItems,
    TransactionLog,
    BoxPermission,
)


@admin.register(MaterialOverview)
class MaterialOverviewAdmin(admin.ModelAdmin):
    """容器管理後台"""
    list_display = ['BoxID', 'Category', 'Description', 'Owner', 'Status', 'Locked', 'CreateDate']
    list_filter = ['Category', 'Status', 'Locked']
    search_fields = ['BoxID', 'Description', 'Owner']
    readonly_fields = ['CreateDate']


@admin.register(MaterialItems)
class MaterialItemsAdmin(admin.ModelAdmin):
    """物品管理後台"""
    list_display = ['SN', 'ItemName', 'Spec', 'BoxID', 'Quantity', 'Location', 'UpdateTime']
    list_filter = ['BoxID']
    search_fields = ['SN', 'ItemName', 'Spec']
    readonly_fields = ['UpdateTime']


@admin.register(TransactionLog)
class MaterialTransactionAdmin(admin.ModelAdmin):
    """交易記錄後台"""
    # ✅ SN 是 ForeignKey，用 get_sn 自訂方法顯示，避免 admin 驗證問題
    list_display = ['LogID', 'get_sn', 'ActionType', 'FromBoxID', 'ToBoxID', 'TransQty', 'Operator', 'Timestamp']
    list_filter = ['ActionType', 'Timestamp']
    search_fields = ['SN__SN', 'SN__ItemName', 'Operator']
    date_hierarchy = 'Timestamp'
    readonly_fields = ['Timestamp']

    @admin.display(description='料號')
    def get_sn(self, obj):
        """顯示關聯物品的料號，物品已刪除時顯示提示"""
        return obj.SN.SN if obj.SN else '（已刪除物品）'


@admin.register(BoxPermission)
class BoxPermissionAdmin(admin.ModelAdmin):
    """容器權限管理後台"""
    list_display = ['box', 'can_read', 'can_write']
    list_filter = ['can_read', 'can_write']