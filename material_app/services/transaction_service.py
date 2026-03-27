# material_app/services/transaction_service.py
import logging
from collections import defaultdict

from django.db import transaction
from django.shortcuts import get_object_or_404

from ..models import MaterialItems, MaterialOverview, TransactionLog

logger = logging.getLogger(__name__)


# ── 查詢 ──────────────────────────────────────────────

def get_all_transactions(action_type=None, from_box=None, operator=None):
    """
    取得交易記錄，支援篩選。

    舊版：filter(ActionType=...) 中文、filter(Operator=字串)
    新版：filter(action_type=...) 英文 choices、filter(operator__username=字串)
    """
    qs = TransactionLog.objects.select_related('item', 'operator').all()
    if action_type:
        # 舊版：ActionType='入庫'（中文）→ 新版：action_type='IN'（英文 choices）
        qs = qs.filter(action_type=action_type)
    if from_box:
        # from_box_id 是快照字串，直接 filter
        qs = qs.filter(from_box_id=from_box)
    if operator:
        # 舊版：Operator=字串 → 新版：operator 是 FK，用 username 查
        qs = qs.filter(operator__username=operator)
    return qs


def get_transaction_stats():
    """
    交易統計。

    舊版：ActionType 中文（'入庫'、'出庫'、'調撥'）
    新版：action_type 英文 choices（'IN'、'OUT'、'MOVE'）
    """
    qs = TransactionLog.objects.all()
    return {
        'total':    qs.count(),
        'stock_in':  qs.filter(action_type='IN').count(),
        'stock_out': qs.filter(action_type='OUT').count(),
        'move':      qs.filter(action_type='MOVE').count(),
        'borrow':    qs.filter(action_type='BORROW').count(),
        'returned':  qs.filter(action_type='RETURN').count(),
        'adjust':    qs.filter(action_type='ADJUST').count(),
    }


def get_items_by_box():
    """
    依箱子分組的物料（供調撥頁前端用）。

    舊版：item.BoxID_id、item.SN、item.ItemName、item.Quantity
    新版：item.box_id、item.sn、item.item_name、item.quantity
    """
    grouped = defaultdict(list)
    for item in MaterialItems.objects.select_related('box').order_by('sn'):
        grouped[item.box_id].append({
            'item_id':   item.pk,
            'sn':        item.sn,
            'item_name': item.item_name,
            'quantity':  item.quantity,
            'spec':      item.spec or '',
        })
    return dict(grouped)


def get_recent_transfers(limit=10):
    """
    最近 N 筆調撥記錄。

    舊版：ActionType='調撥'（中文）、t.SN.ItemName、t.Operator（字串）
    新版：action_type='MOVE'、t.item.item_name、t.operator.username（FK）
    """
    transfers = (
        TransactionLog.objects.filter(action_type='MOVE')
        .select_related('item', 'operator')
        .order_by('-timestamp')[:limit]
    )
    return [
        {
            'timestamp': t.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'item_name': t.item.item_name if t.item else '未知',
            'quantity':  t.trans_qty,
            'from_box':  t.from_box_id or '—',
            'to_box':    t.to_box_id or '—',
            # operator 是 FK，取 username；若已刪除則顯示「未知」
            'operator':  t.operator.username if t.operator else '未知',
        }
        for t in transfers
    ]


def get_unlocked_boxes():
    return MaterialOverview.objects.filter(is_locked=False).order_by('box_id')


# ── 調撥 ──────────────────────────────────────────────

@transaction.atomic
def transfer_item(from_box_id, to_box_id, item_sn, quantity, operator, remark=''):
    """
    物品調撥（從一個箱子移到另一個箱子）。

    舊版問題：
      1. 沒有 select_for_update（並發調撥會出錯）
      2. 沒有 @transaction.atomic（移動和寫 log 不是原子操作）
      3. operator 傳字串

    新版修正：
      1. 加上 select_for_update
      2. 加上 @transaction.atomic
      3. operator 傳 User 物件
    """
    if quantity <= 0:
        raise ValueError("調撥數量必須大於 0")

    from_box = get_object_or_404(MaterialOverview, box_id=from_box_id)
    to_box   = get_object_or_404(MaterialOverview, box_id=to_box_id)

    if from_box.is_locked:
        raise ValueError(f'來源容器 {from_box_id} 已鎖定，無法調撥')
    if to_box.is_locked:
        raise ValueError(f'目標容器 {to_box_id} 已鎖定，無法調撥')

    # 鎖定來源物料，防止並發
    from_item = MaterialItems.objects.select_for_update().get(
        sn=item_sn, box=from_box
    )

    if from_item.quantity < quantity:
        raise ValueError(f'庫存不足：現有 {from_item.quantity}，要調撥 {quantity}')

    stock_before       = from_item.quantity
    from_item.quantity -= quantity

    # 目的箱：同 sn 合併，否則新建
    to_item, created = MaterialItems.objects.select_for_update().get_or_create(
        sn=item_sn,
        box=to_box,
        defaults={
            'item_name': from_item.item_name,
            'spec':      from_item.spec,
            'location':  from_item.location,
            'price':     from_item.price,
            'category':  from_item.category,
            'quantity':  0,
        }
    )
    to_item.quantity += quantity
    to_item.save()

    # 來源數量歸零則刪除（保持箱內不留零庫存紀錄）
    if from_item.quantity == 0:
        from_item.delete()
    else:
        from_item.save()

    TransactionLog.objects.create(
        action_type='MOVE',
        item=to_item,
        from_box_id=from_box_id,    # 快照
        to_box_id=to_box_id,        # 快照
        trans_qty=quantity,
        stock_before=stock_before,
        stock_after=from_item.quantity if from_item.pk else 0,
        operator=operator,          # 舊版字串 → 新版 User FK
        remark=remark or f'從 {from_box_id} 調撥至 {to_box_id}',
    )