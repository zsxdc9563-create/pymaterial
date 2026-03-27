from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    """
    物料分類主檔。
    將分類從 CharField choices 獨立成表，方便日後新增/修改分類，不需改 code。
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="分類名稱")
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name="說明")

    class Meta:
        db_table = 'category'
        verbose_name = "分類"
        verbose_name_plural = "分類"

    def __str__(self):
        return self.name


class MaterialOverview(models.Model):
    """
    物料箱總覽（箱子層級）。

    一個箱子（BoxID）底下會有多筆 MaterialItems（透過 MaterialItems.box 外鍵）。
    此表用來記錄箱子的基本屬性：類別、描述、負責人、狀態，以及鎖定狀態/時間。
    """
    BOX_TYPE_CHOICES = [
        ('project', '專案'),
        ('personal', '個人'),
        ('warehouse', '倉庫'),
        ('spare', '備品'),
        ('test', '測試'),
        ('other', '其他'),
    ]

    box_id = models.CharField(max_length=50, primary_key=True, verbose_name="箱子編號")
    box_type = models.CharField(
        max_length=20,
        choices=BOX_TYPE_CHOICES,
        null=True, blank=True,
        verbose_name="箱子類型"
    )
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name="描述")

    # 改成 FK：與 User 建立真實關聯，方便後續做權限過濾
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='owned_boxes',
        verbose_name="負責人"
    )

    status = models.CharField(max_length=20, null=True, blank=True, verbose_name="狀態")
    is_locked = models.BooleanField(default=False, verbose_name="是否鎖定")
    locked_at = models.DateTimeField(null=True, blank=True, verbose_name="鎖住時間")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="建立日期")

    class Meta:
        db_table = 'material_overview'
        verbose_name = "物料箱總覽"
        verbose_name_plural = "物料箱總覽"

    def __str__(self):
        return f"{self.box_id} - {self.description or '無描述'}"


class MaterialItems(models.Model):
    """
    物料清單（箱內物料明細）。

    - 同一個箱子內，同一料號（sn）只允許一筆（見 unique_together）。
    - required_qty 不為 None 代表此筆是 BOM 需求項；可用 shortage / bom_status 取得缺料狀態。
    """
    sn = models.CharField(max_length=100, verbose_name="料號")
    item_name = models.CharField(max_length=255, verbose_name="品名")
    spec = models.TextField(null=True, blank=True, verbose_name="規格")
    location = models.CharField(max_length=100, null=True, blank=True, verbose_name="位置")
    quantity = models.IntegerField(default=0, verbose_name="數量")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    # 使用 RESTRICT：避免箱子被刪除後留下孤兒物料；如需刪箱，應先移轉/清空箱內物料。
    box = models.ForeignKey(
        MaterialOverview,
        to_field='box_id',
        on_delete=models.RESTRICT,
        related_name='items',
        verbose_name="所屬箱子"
    )

    # 分類改用 FK
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="分類"
    )

    price = models.IntegerField(null=True, blank=True, verbose_name="單價")

    # BOM 需求數量：有值代表此筆是 BOM 需求項
    required_qty = models.IntegerField(null=True, blank=True, verbose_name="需求數量")

    @property
    def is_bom_item(self):
        """是否為 BOM 需求項（只要 required_qty 有值就視為 BOM）。"""
        return self.required_qty is not None

    @property
    def shortage(self):
        """
        缺料數量。
        - 非 BOM（required_qty 為 None）回傳 None
        - BOM：回傳 max(0, required_qty - quantity)
        """
        if self.required_qty is None:
            return None
        return max(0, self.required_qty - self.quantity)

    @property
    def bom_status(self):
        """
        BOM 狀態（便於前端/報表用固定值做顏色或篩選）。
        - 非 BOM：None
        - missing：quantity == 0
        - partial：0 < quantity < required_qty
        - fulfilled：quantity >= required_qty
        """
        if self.required_qty is None:
            return None
        if self.quantity == 0:
            return 'missing'
        elif self.quantity < self.required_qty:
            return 'partial'
        else:
            return 'fulfilled'

    def get_total_price(self):
        """總價（price * quantity）；若未填單價則回傳 None。"""
        return self.price * self.quantity if self.price is not None else None

    class Meta:
        db_table = 'material_items'
        verbose_name = "物料清單"
        verbose_name_plural = "物料清單"
        # 同箱同料號唯一：避免同一箱內重複出現相同 sn 而導致庫存計算混亂。
        unique_together = [['sn', 'box']]

    def __str__(self):
        return f"{self.sn} - {self.item_name}"


class TransactionLog(models.Model):
    """
    交易記錄（庫存異動流水）。

    FromBoxID / ToBoxID 保留 CharField 快照設計，
    讓歷史紀錄能在箱子資料變動時仍完整保留。
    Operator 改為 FK，與 User 建立真實關聯。
    """
    ACTION_CHOICES = [
        ('IN', '入庫'),
        ('OUT', '出庫'),
        ('MOVE', '移動'),
        ('ADJUST', '調整'),
        ('BORROW', '借用'),
        ('RETURN', '歸還'),
    ]

    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="動作類型")
    from_box_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="來源箱（快照）")
    to_box_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="目的箱（快照）")
    trans_qty = models.IntegerField(verbose_name="異動數量")
    stock_before = models.IntegerField(verbose_name="異動前庫存")
    stock_after = models.IntegerField(verbose_name="異動後庫存")
    remark = models.TextField(null=True, blank=True, verbose_name="備註")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="時間戳記")

    # 改成 FK：與 User 建立真實關聯，保留 SET_NULL 讓歷史紀錄不因帳號刪除而消失
    operator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='transactions',
        verbose_name="操作人員"
    )

    # 使用 SET_NULL：即使物料被刪除，也保留交易記錄
    item = models.ForeignKey(
        MaterialItems,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="物料"
    )

    class Meta:
        db_table = 'transaction_log'
        verbose_name = "交易記錄"
        verbose_name_plural = "交易記錄"
        ordering = ['-timestamp']

    def __str__(self):
        sn_display = self.item.sn if self.item else '已刪除物品'
        return f"{self.pk} - {self.action_type} - {sn_display}"


class BoxPermission(models.Model):
    """
    箱子層級權限（使用者 × 箱子）。

    每筆記錄代表「某個使用者對某個箱子的讀/寫權限」。
    unique_together 確保同一使用者對同一箱子只有一筆權限設定。
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='box_permissions',
        verbose_name="使用者"
    )
    box = models.ForeignKey(
        MaterialOverview,
        on_delete=models.CASCADE,
        related_name='permissions',
        verbose_name="箱子"
    )
    can_read = models.BooleanField(default=True, verbose_name="可讀")
    can_write = models.BooleanField(default=False, verbose_name="可寫")

    class Meta:
        db_table = 'box_permission'
        verbose_name = "箱子權限"
        verbose_name_plural = "箱子權限"
        unique_together = [['user', 'box']]

    def __str__(self):
        return f"{self.user.username} | {self.box.box_id} | R:{self.can_read} W:{self.can_write}"


class BorrowRequest(models.Model):
    """
    借用申請單。

    流程：申請 → 審核（APPROVED/REJECTED） → 歸還（RETURNED）。
    approved_by 為 null 代表尚未審核。
    """
    STATUS_CHOICES = [
        ('PENDING', '待審核'),
        ('APPROVED', '已核准'),
        ('REJECTED', '已拒絕'),
        ('RETURNED', '已歸還'),
    ]

    item = models.ForeignKey(
        MaterialItems,
        on_delete=models.RESTRICT,
        related_name='borrow_requests',
        verbose_name="物料"
    )
    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='borrow_requests',
        verbose_name="申請人"
    )
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_requests',
        verbose_name="審核人"
    )
    qty = models.IntegerField(verbose_name="借用數量")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="狀態")
    expected_return_date = models.DateField(null=True, blank=True, verbose_name="預計歸還日")
    actual_return_date = models.DateField(null=True, blank=True, verbose_name="實際歸還日")
    remark = models.TextField(null=True, blank=True, verbose_name="備註")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="申請時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        db_table = 'borrow_request'
        verbose_name = "借用申請"
        verbose_name_plural = "借用申請"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.pk} - {self.requester.username} 借 {self.item.sn} x{self.qty} [{self.status}]"


class BOMNode(models.Model):
    """
    BOM 樹狀結構（自關聯多層）。

    - parent 為 null 代表根節點（產品層）
    - item 對應實際庫存物料（葉節點才有，中間節點可為 null）
    - qty_required 為相對父節點的需求數量

    範例：
        產品A（root）
        ├── 子組件B（parent=產品A, qty_required=2）
        │   ├── 零件C（parent=子組件B, qty_required=3, item=零件C）
        │   └── 零件D（parent=子組件B, qty_required=1, item=零件D）
        └── 零件E（parent=產品A, qty_required=5, item=零件E）
    """
    name = models.CharField(max_length=100, verbose_name="節點名稱")
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='children',
        verbose_name="父節點"
    )
    item = models.ForeignKey(
        MaterialItems,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bom_nodes',
        verbose_name="對應物料"
    )
    qty_required = models.IntegerField(default=1, verbose_name="需求數量（相對父節點）")
    level = models.IntegerField(default=0, verbose_name="層級（0=根）")

    class Meta:
        db_table = 'bom_node'
        verbose_name = "BOM 節點"
        verbose_name_plural = "BOM 節點"

    def __str__(self):
        return f"{'  ' * self.level}{self.name} x{self.qty_required}"


class BOMRelease(models.Model):
    """
    BOM 批次出庫單。

    流程：建立（CHECKING）→ 缺料檢查 → 確認（CONFIRMED）→ 扣庫存（DONE）
    若缺料或取消則為 FAILED。
    """
    STATUS_CHOICES = [
        ('CHECKING', '檢查中'),
        ('CONFIRMED', '已確認'),
        ('DONE', '已完成'),
        ('FAILED', '失敗/取消'),
    ]

    bom_root = models.ForeignKey(
        BOMNode,
        on_delete=models.RESTRICT,
        related_name='releases',
        verbose_name="BOM 根節點（產品）"
    )
    produce_qty = models.IntegerField(default=1, verbose_name="生產數量")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CHECKING', verbose_name="狀態")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='bom_releases',
        verbose_name="建立人"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    remark = models.TextField(null=True, blank=True, verbose_name="備註")

    class Meta:
        db_table = 'bom_release'
        verbose_name = "BOM 批次出庫"
        verbose_name_plural = "BOM 批次出庫"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.pk} - {self.bom_root.name} x{self.produce_qty} [{self.status}]"


class BOMReleaseLog(models.Model):
    """
    BOM 批次出庫明細。

    記錄每次出庫的需求量與實際扣庫量，供後續追蹤與對帳。
    """
    release = models.ForeignKey(
        BOMRelease,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="出庫單"
    )
    item = models.ForeignKey(
        MaterialItems,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="物料"
    )
    required_qty = models.IntegerField(verbose_name="需求總量")
    actual_qty = models.IntegerField(default=0, verbose_name="實際扣庫量")
    is_shortage = models.BooleanField(default=False, verbose_name="是否缺料")

    class Meta:
        db_table = 'bom_release_log'
        verbose_name = "BOM 出庫明細"
        verbose_name_plural = "BOM 出庫明細"

    def __str__(self):
        item_sn = self.item.sn if self.item else '已刪除'
        return f"出庫單{self.release.pk} | {item_sn} 需求:{self.required_qty} 實際:{self.actual_qty}"