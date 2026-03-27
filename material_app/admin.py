# material_app/admin.py

from django.contrib import admin
from .models import (
    MaterialOverview,
    MaterialItems,
    TransactionLog,
    BoxPermission,
    BorrowRequest,
    BOMNode,
    BOMRelease,
)


@admin.register(MaterialOverview)
class MaterialOverviewAdmin(admin.ModelAdmin):
    """容器管理後台"""
    # 舊版：BoxID, Category, Owner, Locked, CreateDate
    # 新版：box_id, box_type, owner（FK）, is_locked, created_at
    list_display  = ['box_id', 'box_type', 'description', 'owner', 'status', 'is_locked', 'created_at']
    list_filter   = ['box_type', 'status', 'is_locked']
    search_fields = ['box_id', 'description', 'owner__username']
    readonly_fields = ['created_at']


@admin.register(MaterialItems)
class MaterialItemsAdmin(admin.ModelAdmin):
    """物品管理後台"""
    # 舊版：SN, ItemName, BoxID, Quantity, UpdateTime
    # 新版：sn, item_name, box（FK）, quantity, updated_at
    list_display  = ['sn', 'item_name', 'spec', 'box', 'quantity', 'location', 'updated_at']
    list_filter   = ['box']
    search_fields = ['sn', 'item_name', 'spec']
    readonly_fields = ['updated_at']


@admin.register(TransactionLog)
class MaterialTransactionAdmin(admin.ModelAdmin):
    """交易記錄後台"""
    # 舊版：LogID, SN(FK), ActionType, FromBoxID, Operator, Timestamp
    # 新版：pk, item(FK), action_type, from_box_id, operator(FK), timestamp
    list_display  = ['pk', 'get_item_sn', 'action_type', 'from_box_id', 'to_box_id', 'trans_qty', 'get_operator', 'timestamp']
    list_filter   = ['action_type', 'timestamp']
    search_fields = ['item__sn', 'item__item_name', 'operator__username']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']

    @admin.display(description='料號')
    def get_item_sn(self, obj):
        # 舊版：obj.SN.SN → 新版：obj.item.sn
        return obj.item.sn if obj.item else '（已刪除物品）'

    @admin.display(description='操作人員')
    def get_operator(self, obj):
        # 舊版：Operator 字串 → 新版：operator FK 取 username
        return obj.operator.username if obj.operator else '—'


@admin.register(BoxPermission)
class BoxPermissionAdmin(admin.ModelAdmin):
    """箱子權限管理後台"""
    # 新版加上 user 欄位
    list_display  = ['user', 'box', 'can_read', 'can_write']
    list_filter   = ['can_read', 'can_write']
    search_fields = ['user__username', 'box__box_id']


@admin.register(BorrowRequest)
class BorrowRequestAdmin(admin.ModelAdmin):
    """借用申請管理後台"""
    list_display  = ['pk', 'item', 'requester', 'qty', 'status', 'expected_return_date', 'created_at']
    list_filter   = ['status']
    search_fields = ['item__sn', 'requester__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BOMNode)
class BOMNodeAdmin(admin.ModelAdmin):
    """BOM 節點管理後台"""
    list_display  = ['pk', 'name', 'parent', 'item', 'qty_required', 'level']
    search_fields = ['name', 'item__sn']


@admin.register(BOMRelease)
class BOMReleaseAdmin(admin.ModelAdmin):
    """BOM 批次出庫管理後台"""
    list_display  = ['pk', 'bom_root', 'produce_qty', 'status', 'created_by', 'created_at']
    list_filter   = ['status']
    readonly_fields = ['created_at']