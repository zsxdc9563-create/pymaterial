# material_app/services/transaction_service.py

from material_app.models import ItemList, MaterialOverview, TransactionLog


class TransactionService:
    """交易服務類別 - 用於處理物料調撥相關操作"""

    # --------------------------------------------------------
    # 調撥
    # --------------------------------------------------------
    @staticmethod
    def transfer(sn, quantity, from_box, to_box, operator="Admin", remark=""):
        """
        執行物料調撥（從 from_box 移動到 to_box）

        Args:
            sn: 物品序號 (ItemList.SN)
            quantity: 調撥數量
            from_box: 來源容器 BoxID
            to_box: 目標容器 BoxID
            operator: 操作人員
            remark: 備註

        Returns:
            建立的 TransactionLog 物件

        Raises:
            ValueError: 參數錯誤或庫存不足
            ItemList.DoesNotExist: 物品不存在
        """
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("調撥數量必須大於 0")

        # 確認來源容器裡的物品存在
        try:
            source_item = ItemList.objects.get(SN=sn, BoxID__BoxID=from_box)
        except ItemList.DoesNotExist:
            raise ValueError(f"來源容器 {from_box} 裡找不到物品 {sn}")

        # 庫存不足檢查
        if source_item.Quantity < quantity:
            raise ValueError(
                f"來源容器 {from_box} 的物品 {sn} 庫存不足 "
                f"（現有 {source_item.Quantity}，調撥 {quantity}）"
            )

        # 確認目標容器存在
        if not MaterialOverview.objects.filter(BoxID=to_box).exists():
            raise ValueError(f"目標容器 {to_box} 不存在")

        # 確認目標容器沒有被鎖定
        target_box_obj = MaterialOverview.objects.get(BoxID=to_box)
        if target_box_obj.Locked:
            raise ValueError(f"目標容器 {to_box} 已被鎖定，無法調撥")

        # 確認來源容器沒有被鎖定
        source_box_obj = MaterialOverview.objects.get(BoxID=from_box)
        if source_box_obj.Locked:
            raise ValueError(f"來源容器 {from_box} 已被鎖定，無法調撥")

        # ---- 開始執行調撥 ----
        stock_before = source_item.Quantity

        # 來源：減少庫存
        source_item.Quantity -= quantity
        source_item.save()

        # 目標：如果同一 SN 已存在於目標容器就累加，否則新建
        target_item, created = ItemList.objects.get_or_create(
            SN=sn,
            BoxID=target_box_obj,
            defaults={
                'ItemName': source_item.ItemName,
                'Spec': source_item.Spec,
                'Location': source_item.Location,
                'Quantity': quantity,
            }
        )
        if not created:
            target_item.Quantity += quantity
            target_item.save()

        # ---- 寫入交易記錄 ----
        log = TransactionLog.objects.create(
            SN=source_item,
            ActionType='調撥',
            FromBoxID=from_box,
            ToBoxID=to_box,
            TransQty=quantity,
            StockBefore=stock_before,
            StockAfter=source_item.Quantity,
            Operator=operator,
            Remark=remark,
        )
        return log

    # --------------------------------------------------------
    # 入庫
    # --------------------------------------------------------
    @staticmethod
    def checkin(sn, quantity, to_box, operator="Admin", remark=""):
        """
        執行入庫（增加指定容器裡的物品庫存）

        Args:
            sn: 物品序號
            quantity: 入庫數量
            to_box: 目標容器 BoxID
            operator: 操作人員
            remark: 備註

        Returns:
            建立的 TransactionLog 物件
        """
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("入庫數量必須大於 0")

        # 確認目標容器存在且沒被鎖定
        try:
            box_obj = MaterialOverview.objects.get(BoxID=to_box)
        except MaterialOverview.DoesNotExist:
            raise ValueError(f"容器 {to_box} 不存在")
        if box_obj.Locked:
            raise ValueError(f"容器 {to_box} 已被鎖定，無法入庫")

        # 找或建立物品記錄
        item, created = ItemList.objects.get_or_create(
            SN=sn,
            BoxID=box_obj,
            defaults={
                'ItemName': sn,   # 新物品暫以 SN 當名稱，後續可補充
                'Quantity': 0,
            }
        )

        stock_before = item.Quantity
        item.Quantity += quantity
        item.save()

        # 寫入交易記錄
        log = TransactionLog.objects.create(
            SN=item,
            ActionType='入庫',
            FromBoxID=None,
            ToBoxID=to_box,
            TransQty=quantity,
            StockBefore=stock_before,
            StockAfter=item.Quantity,
            Operator=operator,
            Remark=remark,
        )
        return log

    # --------------------------------------------------------
    # 出庫
    # --------------------------------------------------------
    @staticmethod
    def checkout(sn, quantity, from_box, operator="Admin", remark=""):
        """
        執行出庫（減少指定容器裡的物品庫存）

        Args:
            sn: 物品序號
            quantity: 出庫數量
            from_box: 來源容器 BoxID
            operator: 操作人員
            remark: 備註

        Returns:
            建立的 TransactionLog 物件
        """
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("出庫數量必須大於 0")

        try:
            item = ItemList.objects.get(SN=sn, BoxID__BoxID=from_box)
        except ItemList.DoesNotExist:
            raise ValueError(f"容器 {from_box} 裡找不到物品 {sn}")

        if item.Quantity < quantity:
            raise ValueError(
                f"容器 {from_box} 的物品 {sn} 庫存不足 "
                f"（現有 {item.Quantity}，出庫 {quantity}）"
            )

        # 確認來源容器沒鎖定
        source_box = MaterialOverview.objects.get(BoxID=from_box)
        if source_box.Locked:
            raise ValueError(f"容器 {from_box} 已被鎖定，無法出庫")

        stock_before = item.Quantity
        item.Quantity -= quantity
        item.save()

        log = TransactionLog.objects.create(
            SN=item,
            ActionType='出庫',
            FromBoxID=from_box,
            ToBoxID=None,
            TransQty=quantity,
            StockBefore=stock_before,
            StockAfter=item.Quantity,
            Operator=operator,
            Remark=remark,
        )
        return log

    # --------------------------------------------------------
    # 查詢
    # --------------------------------------------------------
    @staticmethod
    def get_all_transactions():
        """
        取得所有交易記錄（時間降序）

        Returns:
            QuerySet[TransactionLog]
        """
        return TransactionLog.objects.select_related('SN').order_by('-Timestamp')

    @staticmethod
    def get_transaction_stats():
        """
        取得交易統計資訊，供歷史記錄頁面的統計卡片使用

        Returns:
            dict: { 'total': int, 'checkin': int, 'checkout': int, 'transfer': int }
        """
        qs = TransactionLog.objects
        return {
            'total':    qs.count(),
            'checkin':  qs.filter(ActionType='入庫').count(),
            'checkout': qs.filter(ActionType='出庫').count(),
            'transfer': qs.filter(ActionType='調撥').count(),
        }