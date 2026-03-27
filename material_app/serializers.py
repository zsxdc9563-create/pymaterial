from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Category,
    MaterialOverview,
    MaterialItems,
    TransactionLog,
    BoxPermission,
    BorrowRequest,
    BOMNode,
    BOMRelease,
    BOMReleaseLog,
)


# ────────────────────────────────────────────
# User（內嵌用，唯讀）
# ────────────────────────────────────────────

class UserBriefSerializer(serializers.ModelSerializer):
    """
    User 簡要資訊，用於巢狀內嵌（唯讀）。
    只回傳 id / username / email，不暴露敏感欄位。
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = fields


# ────────────────────────────────────────────
# Category
# ────────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']


# ────────────────────────────────────────────
# Box（MaterialOverview）
# ────────────────────────────────────────────

class BoxSerializer(serializers.ModelSerializer):
    """
    箱子序列化器。
    - owner：巢狀回傳完整 User 物件（id + username + email），唯讀
    - 寫入時用 owner_id 指定使用者
    """
    owner = UserBriefSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='owner',
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = MaterialOverview
        fields = [
            'box_id',
            'box_type',
            'description',
            'owner',        # 讀：完整 user 物件
            'owner_id',     # 寫：只需傳 user pk
            'status',
            'is_locked',
            'locked_at',
            'created_at',
        ]
        read_only_fields = ['created_at']


# ────────────────────────────────────────────
# Material（MaterialItems）
# ────────────────────────────────────────────

class MaterialSerializer(serializers.ModelSerializer):
    """
    物料序列化器。
    - box：巢狀回傳完整 BoxSerializer，唯讀
    - 寫入時用 box_id 指定箱子
    - bom_status / shortage 是 model property，唯讀回傳
    """
    box = BoxSerializer(read_only=True)
    box_id = serializers.PrimaryKeyRelatedField(
        queryset=MaterialOverview.objects.all(),
        source='box',
        write_only=True,
    )
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True,
    )

    # model property → 唯讀
    bom_status = serializers.ReadOnlyField()
    shortage = serializers.ReadOnlyField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = MaterialItems
        fields = [
            'id',
            'sn',
            'item_name',
            'spec',
            'location',
            'quantity',
            'price',
            'total_price',      # SerializerMethodField
            'required_qty',
            'updated_at',
            'box',              # 讀：巢狀 BoxSerializer
            'box_id',           # 寫：只需傳 box_id
            'category',         # 讀：巢狀 CategorySerializer
            'category_id',      # 寫：只需傳 category pk
            'bom_status',       # property
            'shortage',         # property
        ]
        read_only_fields = ['updated_at']

    def get_total_price(self, obj):
        return obj.get_total_price()


# ────────────────────────────────────────────
# TransactionLog
# ────────────────────────────────────────────

class TransactionLogSerializer(serializers.ModelSerializer):
    """
    交易記錄序列化器。
    - operator：回傳 username 字串（可讀性高），唯讀
    - item：回傳 sn 字串，唯讀
    兩者寫入時分別用 operator_id / item_id。
    """
    # 讀：字串（可讀性高）
    operator = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
    )
    item = serializers.SlugRelatedField(
        slug_field='sn',
        read_only=True,
    )

    # 寫：pk
    operator_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='operator',
        write_only=True,
        required=False,
        allow_null=True,
    )
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=MaterialItems.objects.all(),
        source='item',
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = TransactionLog
        fields = [
            'id',
            'action_type',
            'from_box_id',
            'to_box_id',
            'trans_qty',
            'stock_before',
            'stock_after',
            'remark',
            'timestamp',
            'operator',         # 讀：username
            'operator_id',      # 寫：user pk
            'item',             # 讀：sn 字串
            'item_id',          # 寫：item pk
        ]
        read_only_fields = ['timestamp', 'stock_before', 'stock_after']


# ────────────────────────────────────────────
# BoxPermission
# ────────────────────────────────────────────

class BoxPermissionSerializer(serializers.ModelSerializer):
    """
    箱子權限序列化器。
    讀取時顯示 username 與 box_id，寫入時用 pk。
    """
    user = serializers.SlugRelatedField(slug_field='username', read_only=True)
    box = serializers.SlugRelatedField(slug_field='box_id', read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
        write_only=True,
    )
    box_id = serializers.PrimaryKeyRelatedField(
        queryset=MaterialOverview.objects.all(),
        source='box',
        write_only=True,
    )

    class Meta:
        model = BoxPermission
        fields = [
            'id',
            'user',         # 讀：username
            'user_id',      # 寫：pk
            'box',          # 讀：box_id
            'box_id',       # 寫：pk
            'can_read',
            'can_write',
        ]


# ────────────────────────────────────────────
# BorrowRequest
# ────────────────────────────────────────────

class BorrowRequestSerializer(serializers.ModelSerializer):
    """
    借用申請序列化器。
    - requester / approver：回傳 username
    - item：回傳 sn
    """
    requester = serializers.SlugRelatedField(slug_field='username', read_only=True)
    approver = serializers.SlugRelatedField(slug_field='username', read_only=True, allow_null=True)
    item = serializers.SlugRelatedField(slug_field='sn', read_only=True)

    item_id = serializers.PrimaryKeyRelatedField(
        queryset=MaterialItems.objects.all(),
        source='item',
        write_only=True,
    )

    class Meta:
        model = BorrowRequest
        fields = [
            'id',
            'item',                 # 讀：sn
            'item_id',              # 寫：pk
            'requester',            # 讀：username（由 view 帶入，不需前端傳）
            'approver',             # 讀：username
            'qty',
            'status',
            'expected_return_date',
            'actual_return_date',
            'remark',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['requester', 'approver', 'status', 'created_at', 'updated_at']


# ────────────────────────────────────────────
# BOM
# ────────────────────────────────────────────

class BOMNodeSerializer(serializers.ModelSerializer):
    """
    BOM 節點序列化器（扁平，不遞迴展開）。
    樹狀展開由 BOMTreeSerializer 處理。
    """
    item_sn = serializers.CharField(source='item.sn', read_only=True, allow_null=True)

    class Meta:
        model = BOMNode
        fields = [
            'id',
            'name',
            'parent',
            'item',
            'item_sn',      # 讀：sn 字串
            'qty_required',
            'level',
        ]


class BOMNodeTreeSerializer(serializers.ModelSerializer):
    """
    BOM 樹狀序列化器（遞迴展開子節點）。
    用於前端渲染 BOM 樹。
    """
    children = serializers.SerializerMethodField()
    item_sn = serializers.CharField(source='item.sn', read_only=True, allow_null=True)

    class Meta:
        model = BOMNode
        fields = ['id', 'name', 'item', 'item_sn', 'qty_required', 'level', 'children']

    def get_children(self, obj):
        children = obj.children.all()
        return BOMNodeTreeSerializer(children, many=True).data


class BOMReleaseLogSerializer(serializers.ModelSerializer):
    item_sn = serializers.CharField(source='item.sn', read_only=True, allow_null=True)

    class Meta:
        model = BOMReleaseLog
        fields = [
            'id',
            'item',
            'item_sn',
            'required_qty',
            'actual_qty',
            'is_shortage',
        ]


class BOMReleaseSerializer(serializers.ModelSerializer):
    """
    BOM 批次出庫序列化器。
    - logs：巢狀回傳出庫明細
    - created_by：回傳 username
    """
    created_by = serializers.SlugRelatedField(slug_field='username', read_only=True)
    logs = BOMReleaseLogSerializer(many=True, read_only=True)

    class Meta:
        model = BOMRelease
        fields = [
            'id',
            'bom_root',
            'produce_qty',
            'status',
            'created_by',
            'created_at',
            'remark',
            'logs',
        ]
        read_only_fields = ['status', 'created_by', 'created_at', 'logs']