# material_app/services/material_service.py
import logging

from django.db import connection
from django.shortcuts import get_object_or_404

from ..models import MaterialItems, MaterialOverview, TransactionLog

logger = logging.getLogger(__name__)


# ── 查詢 ──────────────────────────────────────────────

def get_all_items(filter_box_id=None):
    items = MaterialItems.objects.all().select_related('BoxID')
    if filter_box_id:
        items = items.filter(BoxID__BoxID=filter_box_id)
    return items.order_by('-UpdateTime', '-id')

def get_all_boxes():
    return MaterialOverview.objects.all().order_by('BoxID')


# ── 建立 ──────────────────────────────────────────────

def create_item(sn, box_id, item_name, spec, location, quantity, price, operator_id):
    box = get_object_or_404(MaterialOverview, BoxID=box_id)

    if box.Locked:
        raise ValueError(f'容器 {box_id} 已鎖定，無法新增物品')

    item = MaterialItems.objects.create(
        SN=sn,
        BoxID=box,
        ItemName=item_name,
        Spec=spec or None,
        Location=location or None,
        Quantity=quantity,
        Price=price,
    )

    TransactionLog.objects.create(
        SN=item,
        ActionType='入庫',
        ToBoxID=box_id,
        TransQty=quantity,
        StockBefore=0,
        StockAfter=quantity,
        Operator=operator_id,
        Remark='手動新增物品入庫',
    )

    return item


# ── 更新 ──────────────────────────────────────────────

def update_item(sn, box_id_str, item_name, spec, location, quantity):
    try:
        item = MaterialItems.objects.get(SN=sn)
    except MaterialItems.MultipleObjectsReturned:
        item = MaterialItems.objects.filter(SN=sn).order_by('-UpdateTime', '-id').first()

    box = get_object_or_404(MaterialOverview, BoxID=box_id_str)

    if box.Locked:
        raise ValueError(f'容器 {box_id_str} 已被鎖定，無法編輯物品')

    if item.BoxID_id != box_id_str:
        existing = MaterialItems.objects.filter(
            SN=sn, BoxID_id=box_id_str
        ).exclude(id=item.id).exists()
        if existing:
            raise ValueError(f'容器 {box_id_str} 中已存在序號 {sn} 的物品，無法移動')

    item.ItemName = item_name
    item.Spec     = spec
    item.Location = location
    item.Quantity = quantity
    item.BoxID    = box
    item.save()
    return item


# ── 刪除 ──────────────────────────────────────────────

def delete_item(sn):
    items_qs = MaterialItems.objects.filter(SN=sn)

    if not items_qs.exists():
        raise ValueError(f'找不到序號為 {sn} 的物品')

    item = items_qs.order_by('id').first()

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM transaction_log WHERE SN_id = %s",
            [item.id]
        )
        transaction_count = cursor.fetchone()[0]

    if transaction_count > 0:
        raise ValueError(f'無法刪除：此物品有 {transaction_count} 筆交易記錄關聯')

    item_name      = item.ItemName
    duplicate_count = items_qs.count()
    item.delete()
    return item_name, duplicate_count


# ── 出庫 ──────────────────────────────────────────────

def material_out(material_id, quantity, from_box='', operator='', remark=''):
    material = get_object_or_404(MaterialItems, pk=material_id)
    quantity = int(quantity)

    if material.Quantity < quantity:
        raise ValueError(f'庫存不足，目前庫存：{material.Quantity}')

    stock_before       = material.Quantity
    material.Quantity -= quantity
    material.save()

    TransactionLog.objects.create(
        ActionType  = 'OUT',
        SN          = material,
        FromBoxID   = from_box,
        ToBoxID     = '',
        TransQty    = quantity,
        StockBefore = stock_before,
        StockAfter  = material.Quantity,
        Operator    = operator,
        Remark      = remark,
    )

    return material.Quantity