# material_app/serializers.py
from rest_framework import serializers
from .models import MaterialOverview, MaterialItems, TransactionLog


class BoxSerializer(serializers.ModelSerializer):
    """
    MaterialOverview（箱子）的序列化器
    對外 API 統一用 Box 稱呼
    """
    class Meta:
        model = MaterialOverview
        fields = [
            'BoxID',
            'Category',
            'Description',
            'Owner',
            'Status',
            'Locked',
            'LockedAt',
            'CreateDate',
        ]


class MaterialSerializer(serializers.ModelSerializer):
    """
    MaterialItems（物料）的序列化器
    對外 API 統一用 Material 稱呼
    bom_status / shortage 是 property，用 read_only 方式回傳給前端
    """
    bom_status = serializers.ReadOnlyField()
    shortage = serializers.ReadOnlyField()

    class Meta:
        model = MaterialItems
        fields = [
            'id',
            'SN',
            'ItemName',
            'Spec',
            'Location',
            'Quantity',
            'Price',
            'RequiredQty',
            'UpdateTime',
            'BoxID',        # ForeignKey，回傳 BoxID 字串
            'bom_status',   # property
            'shortage',     # property
        ]
        extra_kwargs = {
            'Category':    {'required': False},
            'Description': {'required': False},
            'Owner':       {'required': False},
            'Status':      {'required': False},
            'Locked':      {'required': False},
            'LockedAt':    {'required': False},
            'CreateDate':  {'required': False},
        }




class TransactionLogSerializer(serializers.ModelSerializer):
    """
    TransactionLog（交易記錄）的序列化器
    SN 是 ForeignKey，回傳關聯的 MaterialItems id
    """
    class Meta:
        model = TransactionLog
        fields = [
            'LogID',
            'ActionType',
            'FromBoxID',
            'ToBoxID',
            'TransQty',
            'StockBefore',
            'StockAfter',
            'Remark',
            'Timestamp',
            'Operator',
            'SN',           # ForeignKey → MaterialItems
        ]