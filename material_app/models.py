from django.db import models
from django.utils import timezone


class MaterialOverview(models.Model):
    """
    物料箱總覽（箱子層級）。

    一個箱子（`BoxID`）底下會有多筆 `MaterialItems`（透過 `MaterialItems.BoxID` 外鍵）。
    此表用來記錄箱子的基本屬性：類別、描述、負責人、狀態，以及鎖定狀態/時間。
    """
    BoxID = models.CharField(max_length=50, primary_key=True, verbose_name="箱子編號")
    # 箱子分類：用 choices 讓後台/表單有一致選項，並避免任意字串造成統計困難。
    CATEGORY_CHOICES = [
        ('專案', '專案'),
        ('個人', '個人'),
        ('倉庫', '倉庫'),
        ('備品', '備品'),
        ('測試', '測試'),
        ('其他', '其他'),
    ]
    Category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, null=True, blank=True, verbose_name="類別")
    Description = models.CharField(max_length=255, null=True, blank=True, verbose_name="描述")
    Owner = models.CharField(max_length=50, null=True, blank=True, verbose_name="負責人")  # 測試可用
    Status = models.CharField(max_length=20, null=True, blank=True, verbose_name="狀態")
    Locked = models.BooleanField(default=False, verbose_name="是否鎖定")
    LockedAt = models.DateTimeField(null=True, blank=True, verbose_name="鎖住時間")
    CreateDate = models.DateTimeField(default=timezone.now, verbose_name="建立日期")

    class Meta:
        db_table = 'material_overview'
        verbose_name = "物料箱總覽"
        verbose_name_plural = "物料箱總覽"

    def __str__(self):
        return f"{self.BoxID} - {self.Description or '無描述'}"


class MaterialItems(models.Model):
    """
    物料清單（箱內物料明細）。

    - 同一個箱子內，同一料號（`SN`）只允許一筆（見 `unique_together`）。
    - `RequiredQty` 不為 None 代表此筆是 BOM 需求項；可用 `shortage` / `bom_status` 取得缺料與狀態。
    """
    id = models.BigAutoField(primary_key=True)
    SN = models.CharField(max_length=100, verbose_name="料號")
    ItemName = models.CharField(max_length=255, verbose_name="品名")
    Spec = models.TextField(null=True, blank=True, verbose_name="規格")
    Location = models.CharField(max_length=100, null=True, blank=True, verbose_name="位置")
    Quantity = models.IntegerField(default=0, verbose_name="數量")
    UpdateTime = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    # 使用 RESTRICT：避免箱子被刪除後留下孤兒物料；如需刪箱，應先移轉/清空箱內物料。
    BoxID = models.ForeignKey(MaterialOverview, to_field='BoxID', on_delete=models.RESTRICT, related_name='items', verbose_name="所屬箱子")
    
    # BOM & 價格：若有匯入 BOM，`RequiredQty` 用於計算缺料；`Price` 可計算總價（Quantity * Price）。
    Price = models.IntegerField(null=True, blank=True, verbose_name="單價")
    RequiredQty = models.IntegerField(null=True, blank=True, verbose_name="需求數量")

    @property
    def is_bom_item(self):
        """是否為 BOM 需求項（只要 `RequiredQty` 有值就視為 BOM）。"""
        return self.RequiredQty is not None

    @property
    def shortage(self):
        """
        缺料數量。

        - 非 BOM（`RequiredQty` 為 None）回傳 None
        - BOM：回傳 max(0, RequiredQty - Quantity)
        """
        if self.RequiredQty is None:
            return None
        return max(0, self.RequiredQty - self.Quantity)

    @property
    def bom_status(self):
        """
        BOM 狀態（便於前端/報表用固定值做顏色或篩選）。

        - 非 BOM：None
        - `missing`：Quantity == 0
        - `partial`：0 < Quantity < RequiredQty
        - `fulfilled`：Quantity >= RequiredQty
        """
        if self.RequiredQty is None:
            return None
        if self.Quantity == 0:
            return 'missing'
        elif self.Quantity < self.RequiredQty:
            return 'partial'
        else:
            return 'fulfilled'

    def get_total_price(self):
        """總價（Price * Quantity）；若未填單價則回傳 None。"""
        return self.Price * self.Quantity if self.Price is not None else None

    class Meta:
        db_table = 'material_items'
        verbose_name = "物料清單"
        verbose_name_plural = "物料清單"
        # 同箱同料號唯一：避免同一箱內重複出現相同 SN 而導致庫存計算混亂。
        unique_together = [['SN', 'BoxID']]

    def __str__(self):
        return f"{self.SN} - {self.ItemName}"


class TransactionLog(models.Model):
    """
    交易記錄（庫存異動流水）。

    以「記錄」為主體，不強制依賴箱子外鍵（`FromBoxID`/`ToBoxID` 用 CharField），
    讓歷史紀錄能在箱子資料變動時仍完整保留（也方便記錄箱號的快照）。
    """
    ACTION_CHOICES = [
        ('IN', '入庫'),
        ('OUT', '出庫'),
        ('MOVE', '移動'),
        ('ADJUST', '調整'),
    ]
    LogID = models.AutoField(primary_key=True, verbose_name="記錄編號")
    # ActionType 對應 ACTION_CHOICES：維持動作類型一致性（入庫/出庫/移動/調整）。
    ActionType = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="動作類型")
    FromBoxID = models.CharField(max_length=50, null=True, blank=True, verbose_name="來源箱")
    ToBoxID = models.CharField(max_length=50, null=True, blank=True, verbose_name="目的箱")
    TransQty = models.IntegerField(verbose_name="異動數量")
    StockBefore = models.IntegerField(verbose_name="異動前庫存")
    StockAfter = models.IntegerField(verbose_name="異動後庫存")
    Remark = models.TextField(null=True, blank=True, verbose_name="備註")
    Timestamp = models.DateTimeField(auto_now_add=True, verbose_name="時間戳記")
    # 操作者（通常存使用者 id 字串）；與後台 list_display / 篩選交易用。
    Operator = models.CharField(max_length=50, null=True, blank=True, verbose_name="操作人員")
    # 使用 SET_NULL：即使物料被刪除，也保留交易記錄；透過 __str__ 做「已刪除物品」顯示。
    SN = models.ForeignKey(MaterialItems, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="料號")

    class Meta:
        db_table = 'transaction_log'
        verbose_name = "交易記錄"
        verbose_name_plural = "交易記錄"
        ordering = ['-Timestamp']

    def __str__(self):
        sn_display = self.SN.SN if self.SN else '已刪除物品'
        return f"{self.LogID} - {self.ActionType} - {sn_display}"


# ✅ 簡單個人權限模型
class BoxPermission(models.Model):
    """
    Side Project 簡易權限設計（箱子層級）。

    目前模型僅紀錄「對某個箱子是否可讀/可寫」兩個布林值；
    若之後要做到「使用者/群組」層級的權限，通常會再加上 User 外鍵或改用 Django 權限/guardian。
    """
    # 此處用 CASCADE：箱子刪除時一併清理權限設定，避免殘留無主權限資料。
    box = models.ForeignKey(MaterialOverview, on_delete=models.CASCADE)
    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=True)

    class Meta:
        db_table = 'box_permission'
        verbose_name = "容器簡易權限"
        verbose_name_plural = "容器簡易權限"

    def __str__(self):
        return f"{self.box.BoxID} - Read:{self.can_read} Write:{self.can_write}"