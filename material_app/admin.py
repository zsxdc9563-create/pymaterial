# material_app/admin.py

from django.contrib import admin
from .models import (
    MaterialOverview,
    MaterialItems,
    TransactionLog,
)

@admin.register(MaterialOverview)
class MaterialOverviewAdmin(admin.ModelAdmin):
    list_display = ['BoxID', 'Category', 'Description', 'Owner', 'Status', 'Locked', 'CreateDate']
    list_filter = ['Category', 'Status', 'Locked']
    search_fields = ['BoxID', 'Description', 'Owner']
    readonly_fields = ['CreateDate']  # ✅ 創建時間設為只讀


@admin.register(MaterialItems)
class MaterialItemsAdmin(admin.ModelAdmin):
    list_display = ['SN', 'ItemName', 'Spec', 'BoxID', 'Quantity', 'Location', 'UpdateTime']
    list_filter = ['BoxID', 'Location']
    search_fields = ['SN', 'ItemName', 'Spec']
    readonly_fields = ['UpdateTime']  # ✅ 更新時間設為只讀


@admin.register(TransactionLog)
class MaterialTransactionAdmin(admin.ModelAdmin):
    list_display = ['LogID', 'SN', 'ActionType', 'FromBoxID', 'ToBoxID', 'TransQty', 'Operator', 'Timestamp']
    list_filter = ['ActionType', 'Timestamp']
    search_fields = ['SN__SN', 'SN__ItemName', 'Operator']
    date_hierarchy = 'Timestamp'
    readonly_fields = ['Timestamp']  # ✅ 時間戳設為只讀

# ❌ 移除 Employee 的 admin 註冊（因為使用外部 API 認證）
# 如果 models.py 中還有 Employee 模型但不使用，可以註解掉或刪除