# material_app/services/borrow_service.py
import logging

from django.db import transaction
from django.utils import timezone

from ..models import BorrowRequest, MaterialItems, TransactionLog

logger = logging.getLogger(__name__)


# ── 申請 ──────────────────────────────────────────────

@transaction.atomic
def create_borrow_request(item_id: int, qty: int, requester, expected_return_date=None, remark=None) -> BorrowRequest:
    """
    建立借用申請。

    此階段只建立申請單，不異動庫存。
    庫存在審核通過（approve_borrow）後才扣。

    Args:
        item_id:              MaterialItems pk
        qty:                  借用數量
        requester:            User 物件（申請人）
        expected_return_date: 預計歸還日（date 物件，可選）
        remark:               備註

    Raises:
        ValueError: qty <= 0、庫存不足、物料已鎖定箱子
    """
    if qty <= 0:
        raise ValueError("借用數量必須大於 0")

    item = MaterialItems.objects.select_for_update().get(pk=item_id)

    if item.box.is_locked:
        raise ValueError(f"箱子 {item.box.box_id} 已鎖定，無法申請借用")

    if item.quantity < qty:
        raise ValueError(f"庫存不足：現有 {item.quantity}，申請借用 {qty}")

    request = BorrowRequest.objects.create(
        item=item,
        requester=requester,
        qty=qty,
        status='PENDING',
        expected_return_date=expected_return_date,
        remark=remark,
    )

    logger.info(f'借用申請建立：request_id={request.pk}, item={item.sn}, qty={qty}, requester={requester.username}')
    return request


# ── 審核 ──────────────────────────────────────────────

@transaction.atomic
def approve_borrow(request_id: int, approver) -> BorrowRequest:
    """
    審核通過借用申請，並扣庫存。

    Args:
        request_id: BorrowRequest pk
        approver:   User 物件（審核人）

    Raises:
        ValueError: 申請單不是 PENDING、庫存不足
    """
    # 鎖定申請單，防止同時兩個人審核同一筆
    borrow = BorrowRequest.objects.select_for_update().get(pk=request_id)

    if borrow.status != 'PENDING':
        raise ValueError(f"此申請單狀態為 {borrow.get_status_display()}，無法審核")

    # 再次確認庫存（申請到審核之間可能被其他人出庫）
    item = MaterialItems.objects.select_for_update().get(pk=borrow.item.pk)

    if item.quantity < borrow.qty:
        raise ValueError(f"庫存不足：現有 {item.quantity}，借用需求 {borrow.qty}")

    # 扣庫存
    stock_before   = item.quantity
    item.quantity -= borrow.qty
    item.save()

    # 寫交易記錄
    TransactionLog.objects.create(
        action_type='BORROW',
        item=item,
        from_box_id=item.box.box_id,    # 快照
        trans_qty=borrow.qty,
        stock_before=stock_before,
        stock_after=item.quantity,
        operator=approver,
        remark=f'借用申請 #{borrow.pk} 審核通過',
    )

    # 更新申請單狀態
    borrow.status   = 'APPROVED'
    borrow.approver = approver
    borrow.save()

    logger.info(f'借用審核通過：request_id={borrow.pk}, approver={approver.username}')
    return borrow


# ── 拒絕 ──────────────────────────────────────────────

@transaction.atomic
def reject_borrow(request_id: int, approver, remark=None) -> BorrowRequest:
    """
    拒絕借用申請（不異動庫存）。

    Raises:
        ValueError: 申請單不是 PENDING
    """
    borrow = BorrowRequest.objects.select_for_update().get(pk=request_id)

    if borrow.status != 'PENDING':
        raise ValueError(f"此申請單狀態為 {borrow.get_status_display()}，無法拒絕")

    borrow.status   = 'REJECTED'
    borrow.approver = approver
    if remark:
        borrow.remark = remark
    borrow.save()

    logger.info(f'借用申請拒絕：request_id={borrow.pk}, approver={approver.username}')
    return borrow


# ── 歸還 ──────────────────────────────────────────────

@transaction.atomic
def return_borrow(request_id: int, operator, actual_return_date=None, remark=None) -> BorrowRequest:
    """
    歸還借用物料，並加回庫存。

    Args:
        request_id:         BorrowRequest pk
        operator:           User 物件（執行歸還的人）
        actual_return_date: 實際歸還日，預設今天
        remark:             備註

    Raises:
        ValueError: 申請單不是 APPROVED
    """
    borrow = BorrowRequest.objects.select_for_update().get(pk=request_id)

    if borrow.status != 'APPROVED':
        raise ValueError(f"此申請單狀態為 {borrow.get_status_display()}，無法執行歸還")

    item = MaterialItems.objects.select_for_update().get(pk=borrow.item.pk)

    # 加回庫存
    stock_before   = item.quantity
    item.quantity += borrow.qty
    item.save()

    # 寫交易記錄
    TransactionLog.objects.create(
        action_type='RETURN',
        item=item,
        to_box_id=item.box.box_id,      # 快照：歸還到哪個箱子
        trans_qty=borrow.qty,
        stock_before=stock_before,
        stock_after=item.quantity,
        operator=operator,
        remark=remark or f'借用申請 #{borrow.pk} 歸還',
    )

    # 更新申請單狀態
    borrow.status              = 'RETURNED'
    borrow.actual_return_date  = actual_return_date or timezone.now().date()
    borrow.save()

    logger.info(f'借用歸還完成：request_id={borrow.pk}, operator={operator.username}')
    return borrow


# ── 查詢 ──────────────────────────────────────────────

def get_pending_requests() -> list:
    """
    取得所有待審核的借用申請（供 manager/admin 用）。
    """
    return BorrowRequest.objects.filter(
        status='PENDING'
    ).select_related('item', 'requester').order_by('created_at')


def get_user_requests(user) -> list:
    """
    取得某個使用者的所有借用申請。
    """
    return BorrowRequest.objects.filter(
        requester=user
    ).select_related('item', 'approver').order_by('-created_at')


def get_overdue_requests() -> list:
    """
    取得逾期未還的借用申請（狀態 APPROVED 且超過預計歸還日）。
    """
    today = timezone.now().date()
    return BorrowRequest.objects.filter(
        status='APPROVED',
        expected_return_date__lt=today,     # 預計歸還日 < 今天
    ).select_related('item', 'requester').order_by('expected_return_date')