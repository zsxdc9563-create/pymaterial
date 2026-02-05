# material_app/models.py

# material_app/models.py

from django.db import models
from django.utils import timezone


class MaterialOverview(models.Model):
    """物料箱總覽"""
    BoxID = models.CharField(max_length=50, primary_key=True, verbose_name="箱子編號")
    Category = models.CharField(max_length=50, null=True, blank=True, verbose_name="類別")
    Description = models.CharField(max_length=255, null=True, blank=True, verbose_name="描述")
    Owner = models.CharField(max_length=50, null=True, blank=True, verbose_name="負責人")  # ✅ 儲存工號
    Status = models.CharField(max_length=20, null=True, blank=True, verbose_name="狀態")
    Locked = models.BooleanField(default=False, verbose_name="是否鎖定")
    CreateDate = models.DateTimeField(default=timezone.now, verbose_name="建立日期")

    class Meta:
        db_table = 'material_app_materialoverview'
        verbose_name = "物料箱總覽"
        verbose_name_plural = "物料箱總覽"

    def __str__(self):
        return f"{self.BoxID} - {self.Description or '無描述'}"


class MaterialItems(models.Model):
    """物料清單"""
    id = models.BigAutoField(primary_key=True)
    SN = models.CharField(max_length=100, verbose_name="料號")
    ItemName = models.CharField(max_length=255, verbose_name="品名")
    Spec = models.TextField(null=True, blank=True, verbose_name="規格")
    Location = models.CharField(max_length=100, null=True, blank=True, verbose_name="位置")
    Quantity = models.IntegerField(default=0, verbose_name="數量")
    UpdateTime = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    BoxID = models.ForeignKey(
        MaterialOverview,
        on_delete=models.RESTRICT,
        db_column='BoxID_id',
        verbose_name="所屬箱子"
    )

    class Meta:
        db_table = 'material_app_itemlist'
        managed = False
        verbose_name = "物料清單"
        verbose_name_plural = "物料清單"
        unique_together = [['SN', 'BoxID']]


class TransactionLog(models.Model):
    """交易記錄"""
    ACTION_CHOICES = [
        ('IN', '入庫'),
        ('OUT', '出庫'),
        ('MOVE', '移動'),
        ('ADJUST', '調整'),
    ]

    LogID = models.AutoField(primary_key=True, verbose_name="記錄編號")
    ActionType = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="動作類型")
    FromBoxID = models.CharField(max_length=50, null=True, blank=True, verbose_name="來源箱")
    ToBoxID = models.CharField(max_length=50, null=True, blank=True, verbose_name="目的箱")
    TransQty = models.IntegerField(verbose_name="異動數量")
    StockBefore = models.IntegerField(verbose_name="異動前庫存")
    StockAfter = models.IntegerField(verbose_name="異動後庫存")
    Operator = models.CharField(max_length=50, null=True, blank=True, verbose_name="操作人員")  # ✅ 儲存工號
    Remark = models.TextField(null=True, blank=True, verbose_name="備註")
    Timestamp = models.DateTimeField(auto_now_add=True, verbose_name="時間戳記")
    SN = models.ForeignKey(
        MaterialItems,
        on_delete=models.SET_NULL,  # ✅ 改為 SET_NULL
        null=True,  # ✅ 允許為空
        blank=True,
        db_column='SN_id',
        verbose_name="料號"
    )

    class Meta:
        db_table = 'material_app_transactionlog'
        verbose_name = "交易記錄"
        verbose_name_plural = "交易記錄"
        ordering = ['-Timestamp']
        indexes = [
            models.Index(fields=['SN']),
        ]

    def __str__(self):
        sn_display = self.SN.SN if self.SN else '已刪除物品'
        return f"{self.LogID} - {self.ActionType} - {sn_display}"


class Employee(models.Model):
    """員工基本資料（本地快取）"""
    EmpID = models.CharField(max_length=50, primary_key=True, verbose_name="工號")
    Name = models.CharField(max_length=50, verbose_name="姓名")
    DeptID = models.CharField(max_length=50, blank=True, null=True, verbose_name="部門")
    IsActive = models.BooleanField(default=True, verbose_name="是否在職")
    LastSync = models.DateTimeField(auto_now=True, verbose_name="最後同步時間")

    class Meta:
        db_table = 'employee' # ✅ 使用新的表名（避免與 material_app_employee 衝突）
        managed = True # ✅ 這個表由 Django 管理

    def __str__(self):
        return f"{self.EmpID} - {self.Name}"



