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
    Role,
    Permission,
    UserRole,
    RolePermission,
)


# ────────────────────────────────────────────
# User（內嵌用，唯讀）
# ────────────────────────────────────────────

class UserBriefSerializer(serializers.ModelSerializer):
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
            'box_id', 'box_type', 'description',
            'owner', 'owner_id',
            'status', 'is_locked', 'locked_at', 'created_at',
        ]
        read_only_fields = ['created_at']


# ────────────────────────────────────────────
# Material（MaterialItems）
# ────────────────────────────────────────────

class MaterialSerializer(serializers.ModelSerializer):
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
    bom_status = serializers.SerializerMethodField()
    shortage = serializers.ReadOnlyField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = MaterialItems
        fields = [
            'id', 'sn', 'item_name', 'spec', 'location',
            'quantity', 'price', 'total_price', 'required_qty', 'updated_at',
            'box', 'box_id', 'category', 'category_id',
            'bom_status', 'shortage',
        ]
        read_only_fields = ['updated_at']

    def get_total_price(self, obj):
        return obj.get_total_price()

    def get_bom_status(self, obj):
        if obj.required_qty is None:
            return None
        # 從 view 傳入的 context 取得已完成出庫的 item id 集合
        # 這樣可以避免每筆都打一次 DB（N+1 問題）
        done_ids = self.context.get('done_item_ids', set())
        if obj.pk in done_ids:
            return 'fulfilled'
        if obj.quantity == 0:
            return 'missing'
        elif obj.quantity < obj.required_qty:
            return 'partial'
        else:
            return 'fulfilled'


# ────────────────────────────────────────────
# TransactionLog
# ────────────────────────────────────────────

class TransactionLogSerializer(serializers.ModelSerializer):
    operator = serializers.SlugRelatedField(slug_field='username', read_only=True)
    item = serializers.SlugRelatedField(slug_field='sn', read_only=True)
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
            'id', 'action_type', 'from_box_id', 'to_box_id',
            'trans_qty', 'stock_before', 'stock_after', 'remark', 'timestamp',
            'operator', 'operator_id', 'item', 'item_id',
        ]
        read_only_fields = ['timestamp', 'stock_before', 'stock_after']


# ────────────────────────────────────────────
# BoxPermission
# ────────────────────────────────────────────

class BoxPermissionSerializer(serializers.ModelSerializer):
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
        fields = ['id', 'user', 'user_id', 'box', 'box_id', 'can_read', 'can_write']


# ────────────────────────────────────────────
# BorrowRequest
# ────────────────────────────────────────────

class BorrowRequestSerializer(serializers.ModelSerializer):
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
            'id', 'item', 'item_id', 'requester', 'approver',
            'qty', 'status', 'expected_return_date', 'actual_return_date',
            'remark', 'created_at', 'updated_at',
        ]
        read_only_fields = ['requester', 'approver', 'status', 'created_at', 'updated_at']


# ────────────────────────────────────────────
# BOM
# ────────────────────────────────────────────

class BOMNodeSerializer(serializers.ModelSerializer):
    item_sn = serializers.CharField(source='item.sn', read_only=True, allow_null=True)

    class Meta:
        model = BOMNode
        fields = ['id', 'name', 'parent', 'item', 'item_sn', 'qty_required', 'level']


class BOMNodeTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    item_sn = serializers.CharField(source='item.sn', read_only=True, allow_null=True)

    class Meta:
        model = BOMNode
        fields = ['id', 'name', 'item', 'item_sn', 'qty_required', 'level', 'children']

    def get_children(self, obj):
        return BOMNodeTreeSerializer(obj.children.all(), many=True).data


class BOMReleaseLogSerializer(serializers.ModelSerializer):
    item_sn = serializers.CharField(source='item.sn', read_only=True, allow_null=True)

    class Meta:
        model = BOMReleaseLog
        fields = ['id', 'item', 'item_sn', 'required_qty', 'actual_qty', 'is_shortage']


class BOMReleaseSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='username', read_only=True)
    logs = BOMReleaseLogSerializer(many=True, read_only=True)

    class Meta:
        model = BOMRelease
        fields = ['id', 'bom_root', 'produce_qty', 'status', 'created_by', 'created_at', 'remark', 'logs']
        read_only_fields = ['status', 'created_by', 'created_at', 'logs']


# ────────────────────────────────────────────
# RBAC
# ────────────────────────────────────────────

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'description']


class UserRoleSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username', read_only=True)
    role = RoleSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
        write_only=True,
    )
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source='role',
        write_only=True,
    )

    class Meta:
        model = UserRole
        fields = ['id', 'user', 'user_id', 'role', 'role_id']


class RolePermissionSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    permission = PermissionSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source='role',
        write_only=True,
    )
    permission_id = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        source='permission',
        write_only=True,
    )

    class Meta:
        model = RolePermission
        fields = ['id', 'role', 'role_id', 'permission', 'permission_id']