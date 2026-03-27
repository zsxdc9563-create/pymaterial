# material_app/services/material_service.py
import logging

from django.db import transaction
from django.shortcuts import get_object_or_404

from ..models import MaterialItems, MaterialOverview, TransactionLog

logger = logging.getLogger(__name__)


# ── 查詢 ──────────────────────────────────────────────

def get_all_items(filter_box_id=None):
    # select_related('box')：一次 JOIN 查出箱子資料，避免 N+1 query
    # 舊版是 select_related('BoxID')，對應新 models 的 box 欄位
    items = MaterialItems.objects.all().select_related('box')
    if filter_box_id:
        # 舊版：filter(BoxID__BoxID=filter_box_id)
        # 新版：FK 欄位叫 box，箱子 pk 叫 box_id
        items = items.filter(box__box_id=filter_box_id)
    return items.order_by('-updated_at', '-id')


def get_all_boxes():
    return MaterialOverview.objects.all().order_by('box_id')


# ── 建立 ──────────────────────────────────────────────

@transaction.atomic
def create_item(sn, box_id, item_name, spec, location, quantity, price, operator):
    """
    新增物料並寫入入庫 log。

    Args:
        operator: User 物件（舊版是傳 operator_id 字串，新版改成 FK）

    Raises:
        ValueError: 箱子已鎖定
    """
    # select_for_update()：鎖住箱子這一列，防止同時多人對同箱操作
    box = MaterialOverview.objects.select_for_update().get(box_id=box_id)

    # 舊版：box.Locked → 新版：box.is_locked
    if box.is_locked:
        raise ValueError(f'容器 {box_id} 已鎖定，無法新增物品')

    item = MaterialItems.objects.create(
        sn=sn,
        box=box,
        item_name=item_name,
        spec=spec or None,
        location=location or None,
        quantity=quantity,
        price=price,
    )

    # 入庫 log
    # 舊版：ActionType='入庫'（中文），新版統一用英文 choices
    TransactionLog.objects.create(
        item=item,
        action_type='IN',
        to_box_id=box_id,       # 快照：存箱子 id 字串
        trans_qty=quantity,
        stock_before=0,
        stock_after=quantity,
        operator=operator,      # 舊版是字串，新版是 User FK
        remark='手動新增物品入庫',
    )

    return item


# ── 更新 ──────────────────────────────────────────────

@transaction.atomic
def update_item(item_id, item_name, spec, location, quantity, box_id=None):
    """
    更新物料基本資料。

    Args:
        item_id: MaterialItems pk（舊版用 sn 查，改成 pk 更精確）
        box_id:  若要換箱子則傳入，否則維持原箱子

    Raises:
        ValueError: 箱子已鎖定、目標箱已有相同 sn
    """
    # select_for_update()：鎖住這筆物料，防止並發編輯
    item = MaterialItems.objects.select_for_update().get(pk=item_id)

    if box_id and box_id != item.box.box_id:
        # 換箱子：先確認目標箱沒有同 sn
        target_box = MaterialOverview.objects.select_for_update().get(box_id=box_id)

        if target_box.is_locked:
            raise ValueError(f'容器 {box_id} 已被鎖定，無法移入')

        already_exists = MaterialItems.objects.filter(
            sn=item.sn,
            box=target_box,
        ).exclude(pk=item.pk).exists()

        if already_exists:
            raise ValueError(f'容器 {box_id} 中已存在料號 {item.sn}，無法移動')

        item.box = target_box

    item.item_name = item_name
    item.spec      = spec
    item.location  = location
    item.quantity  = quantity
    item.save()
    return item


# ── 刪除 ──────────────────────────────────────────────

@transaction.atomic
def delete_item(item_id):
    """
    刪除物料。

    舊版用 sn 查詢 + 原生 SQL 檢查 transaction_count，
    新版改用 pk 查詢 + ORM，更安全也更易讀。

    Raises:
        ValueError: 有關聯的交易記錄（保護歷史資料）
    """
    item = get_object_or_404(MaterialItems, pk=item_id)

    # 舊版：用原生 SQL cursor 查 → 新版改用 ORM
    transaction_count = TransactionLog.objects.filter(item=item).count()
    if transaction_count > 0:
        raise ValueError(f'無法刪除：此物品有 {transaction_count} 筆交易記錄關聯')

    item_name = item.item_name
    item.delete()
    return item_name


# ── 出庫 ──────────────────────────────────────────────

@transaction.atomic
def stock_out(item_id, qty, operator, from_box_id=None, remark=None):
    """
    出庫。

    舊版：material_out(material_id, quantity, from_box='', operator='', remark='')
    新版：
      - 加上 select_for_update()（防並發）
      - operator 改成 User FK
      - 函式名改成 stock_out（與 action_type 一致）

    Raises:
        ValueError: qty <= 0 或庫存不足
    """
    if qty <= 0:
        raise ValueError("出庫數量必須大於 0")

    # select_for_update()：鎖住這列，讓其他人等這筆交易完成再讀
    item = MaterialItems.objects.select_for_update().get(pk=item_id)

    if item.quantity < qty:
        raise ValueError(f'庫存不足：現有 {item.quantity}，要出庫 {qty}')

    stock_before   = item.quantity
    item.quantity -= qty
    item.save()

    TransactionLog.objects.create(
        action_type='OUT',
        item=item,
        from_box_id=from_box_id or item.box.box_id,  # 快照
        trans_qty=qty,
        stock_before=stock_before,
        stock_after=item.quantity,
        operator=operator,
        remark=remark,
    )

    return item.quantity


# ── 入庫 ──────────────────────────────────────────────

@transaction.atomic
def stock_in(item_id, qty, operator, to_box_id=None, remark=None):
    """
    入庫（對已存在的物料追加數量）。

    與 create_item 的差別：
      - create_item：物料不存在，從零建立
      - stock_in：物料已存在，追加數量

    Raises:
        ValueError: qty <= 0
    """
    if qty <= 0:
        raise ValueError("入庫數量必須大於 0")

    item = MaterialItems.objects.select_for_update().get(pk=item_id)
    stock_before   = item.quantity
    item.quantity += qty
    item.save()

    TransactionLog.objects.create(
        action_type='IN',
        item=item,
        to_box_id=to_box_id or item.box.box_id,
        trans_qty=qty,
        stock_before=stock_before,
        stock_after=item.quantity,
        operator=operator,
        remark=remark,
    )

    return item.quantity


# ── 盤點調整 ──────────────────────────────────────────

@transaction.atomic
def adjust(item_id, new_qty, operator, remark=None):
    """
    盤點調整（直接設定數量）。

    Raises:
        ValueError: new_qty < 0
    """
    if new_qty < 0:
        raise ValueError("調整後數量不可為負數")

    item = MaterialItems.objects.select_for_update().get(pk=item_id)
    stock_before  = item.quantity
    delta         = new_qty - stock_before
    item.quantity = new_qty
    item.save()

    TransactionLog.objects.create(
        action_type='ADJUST',
        item=item,
        from_box_id=item.box.box_id,
        trans_qty=delta,            # 正數=增加，負數=減少
        stock_before=stock_before,
        stock_after=new_qty,
        operator=operator,
        remark=remark or f'盤點調整：{stock_before} → {new_qty}',
    )

    return new_qty


# ── 缺料查詢 ──────────────────────────────────────────

def check_shortage(item_id):
    """
    查詢單一物料缺料狀況（純查詢，不異動庫存）。
    """
    item = get_object_or_404(MaterialItems, pk=item_id)
    return {
        'item_id':      item.pk,
        'sn':           item.sn,
        'quantity':     item.quantity,
        'required_qty': item.required_qty,
        'shortage':     item.shortage,      # model property
        'bom_status':   item.bom_status,    # model property
    }


def check_box_shortage(box_id):
    """
    查詢整個箱子內所有 BOM 物料的缺料狀況（純查詢）。
    只回傳有 required_qty 且有缺料的清單。
    """
    items = MaterialItems.objects.filter(
        box__box_id=box_id,
        required_qty__isnull=False,     # 只查 BOM 項目
    )
    return [
        {
            'item_id':      item.pk,
            'sn':           item.sn,
            'item_name':    item.item_name,
            'quantity':     item.quantity,
            'required_qty': item.required_qty,
            'shortage':     item.shortage,
            'bom_status':   item.bom_status,
        }
        for item in items
        if item.shortage and item.shortage > 0
    ]