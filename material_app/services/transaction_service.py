# material_app/services/transaction_service.py
import logging
from collections import defaultdict

from django.shortcuts import get_object_or_404

from ..models import MaterialItems, MaterialOverview, TransactionLog

logger = logging.getLogger(__name__)


# ── 查詢 ──────────────────────────────────────────────

def get_all_transactions(action_type=None, from_box=None, operator=None):
    qs = TransactionLog.objects.all()
    if action_type:
        qs = qs.filter(ActionType=action_type)
    if from_box:
        qs = qs.filter(FromBoxID=from_box)
    if operator:
        qs = qs.filter(Operator=operator)
    return qs

def get_transaction_stats():
    transactions = TransactionLog.objects.all()
    return {
        'total':    transactions.count(),
        'checkin':  transactions.filter(ActionType='入庫').count(),
        'checkout': transactions.filter(ActionType='出庫').count(),
        'transfer': transactions.filter(ActionType='調撥').count(),
    }

def get_items_by_box():
    """依容器編號分組的物品（供調撥頁前端用）"""
    grouped = defaultdict(list)
    for item in MaterialItems.objects.select_related('BoxID').order_by('SN'):
        grouped[item.BoxID_id].append({
            'item_id':   item.SN,
            'item_name': item.ItemName,
            'quantity':  item.Quantity,
            'spec':      item.Spec or '',
        })
    return dict(grouped)

def get_recent_transfers(limit=10):
    """最近 N 筆調撥記錄"""
    transfers = (
        TransactionLog.objects.filter(ActionType='調撥')
        .select_related('SN')
        .order_by('-Timestamp')[:limit]
    )
    return [
        {
            'timestamp': t.Timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'item_name': t.SN.ItemName if t.SN else '未知',
            'quantity':  t.TransQty,
            'from_box':  t.FromBoxID or '—',
            'to_box':    t.ToBoxID or '—',
            'operator':  t.Operator or '未知',
        }
        for t in transfers
    ]

def get_unlocked_boxes():
    return MaterialOverview.objects.filter(Locked=False).order_by('BoxID')


# ── 調撥 ──────────────────────────────────────────────

def transfer_item(from_box_id, to_box_id, item_sn, quantity, operator_id, remark=''):
    from_box = get_object_or_404(MaterialOverview, BoxID=from_box_id)
    to_box   = get_object_or_404(MaterialOverview, BoxID=to_box_id)

    if from_box.Locked:
        raise ValueError(f'來源容器 {from_box_id} 已鎖定，無法調撥')
    if to_box.Locked:
        raise ValueError(f'目標容器 {to_box_id} 已鎖定，無法調撥')

    from_item    = MaterialItems.objects.get(SN=item_sn, BoxID=from_box)
    stock_before = from_item.Quantity
    from_item.Quantity -= quantity

    try:
        to_item = MaterialItems.objects.get(SN=item_sn, BoxID=to_box)
        to_item.Quantity += quantity
        to_item.save()
    except MaterialItems.DoesNotExist:
        to_item = MaterialItems.objects.create(
            SN=item_sn, BoxID=to_box, ItemName=from_item.ItemName,
            Spec=from_item.Spec, Location=from_item.Location, Quantity=quantity
        )

    if from_item.Quantity == 0:
        from_item.delete()
    else:
        from_item.save()

    TransactionLog.objects.create(
        SN=to_item, ActionType='調撥',
        FromBoxID=from_box_id, ToBoxID=to_box_id,
        TransQty=quantity, StockBefore=stock_before,
        StockAfter=from_item.Quantity,
        Operator=operator_id,
        Remark=remark or f'從 {from_box_id} 調撥',
    )