from django.db import models

class MaterialOverview(models.Model):
    """容器/專案總覽"""
    BoxID = models.CharField(max_length=50, primary_key=True, help_text="編號唯一，不可重複")
    Category = models.CharField(max_length=50, blank=True, null=True, help_text="類別（如：一般物料、維修件）")
    Description = models.CharField(max_length=255, blank=True, null=True, help_text="備註該編號的用途")
    Owner = models.CharField(max_length=50, blank=True, null=True, help_text="負責人姓名")
    Status = models.CharField(max_length=20, blank=True, null=True, help_text="狀態（使用中、空閒、結案）")
    Locked = models.BooleanField(default=False, help_text="是否鎖定")
    CreateDate = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.BoxID} - {self.Category or ''}"


class ItemList(models.Model):
    """物品明細清單"""
    # 移除 primary_key=True，Django 會自動創建 id 欄位
    SN = models.CharField(max_length=100, help_text="產品唯一識別序號或條碼")
    ItemName = models.CharField(max_length=255, help_text="商品名稱")
    Spec = models.TextField(blank=True, null=True, help_text="規格型號")
    Location = models.CharField(max_length=100, blank=True, null=True, help_text="實體存放位置")
    BoxID = models.ForeignKey(MaterialOverview, on_delete=models.CASCADE, help_text="關聯到容器")
    Quantity = models.IntegerField(default=0, help_text="目前庫存數量")
    UpdateTime = models.DateTimeField(auto_now=True)

    class Meta:
        # 設置組合唯一：同一個 SN 在同一個容器中只能出現一次
        # 但允許同一個 SN 在不同容器中出現
        unique_together = [['SN', 'BoxID']]

    def __str__(self):
        return f"{self.SN} - {self.ItemName}"


class TransactionLog(models.Model):
    """異動/調撥紀錄"""
    LogID = models.AutoField(primary_key=True)
    SN = models.ForeignKey(ItemList, on_delete=models.CASCADE, help_text="哪件東西動了")
    ActionType = models.CharField(max_length=20, help_text="入庫、出庫、調撥")
    FromBoxID = models.CharField(max_length=50, blank=True, null=True, help_text="來源位置")
    ToBoxID = models.CharField(max_length=50, blank=True, null=True, help_text="目的位置")
    TransQty = models.IntegerField(help_text="變動數量")
    StockBefore = models.IntegerField(help_text="動作前的原始庫存")
    StockAfter = models.IntegerField(help_text="動作後的剩餘庫存")
    Operator = models.CharField(max_length=50, blank=True, null=True, help_text="誰執行的")
    Remark = models.TextField(blank=True, null=True, help_text="異動原因")
    Timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ActionType} {self.TransQty} of {self.SN_id}"




# ==================== 新增：認證相關 model ====================

class Employee(models.Model):
    """員工帳號（打工號登入）"""
    EmpID = models.CharField(max_length=50, primary_key=True, help_text="打工號，唯一")
    Name = models.CharField(max_length=50, help_text="員工姓名")
    Password = models.CharField(max_length=255, help_text="密碼（存儲為 hash）")
    IsActive = models.BooleanField(default=True, help_text="帳號是否啟用")
    CreateDate = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.EmpID} - {self.Name}"

    # ── 密碼工具方法 ──
    def set_password(self, raw_password):
        """將明文密碼 hash 後儲存"""
        import hashlib, os
        salt = os.urandom(32)                          # 隨機 salt
        key = hashlib.pbkdf2_hmac('sha256',
                                  raw_password.encode('utf-8'),
                                  salt, 100000)        # 迭代 10 萬次
        # 儲存格式：salt(hex) + "$" + key(hex)
        self.Password = salt.hex() + '$' + key.hex()

    def check_password(self, raw_password):
        """驗證明文密碼是否正確"""
        import hashlib
        if '$' not in self.Password:
            return False
        salt_hex, key_hex = self.Password.split('$', 1)
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac('sha256',
                                      raw_password.encode('utf-8'),
                                      salt, 100000)
        return new_key == stored_key


class AuthToken(models.Model):
    """登入後生成的 Token"""
    Token = models.CharField(max_length=128, primary_key=True, help_text="隨機生成的 token 字串")
    Employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='tokens')
    CreatedAt = models.DateTimeField(auto_now_add=True)
    ExpiresAt = models.DateTimeField(help_text="過期時間（login 時設為當前 + 24h）")

    def __str__(self):
        return f"{self.Token[:16]}... → {self.Employee.EmpID}"

    def is_expired(self):
        """檢查 token 是否已過期"""
        from django.utils import timezone
        return timezone.now() > self.ExpiresAt




