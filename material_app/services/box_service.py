# material_app/services/box_service.py
import logging
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from ..models import MaterialItems, MaterialOverview, TransactionLog

logger = logging.getLogger(__name__)


# ── 查詢 ──────────────────────────────────────────────

def get_all_boxes():
    """容器列表不顯示專案類型（專案在專案管理頁面）"""
    return MaterialOverview.objects.exclude(Category='專案').order_by('-CreateDate')


def get_box_or_none(box_id):
    try:
        return MaterialOverview.objects.get(BoxID=box_id)
    except MaterialOverview.DoesNotExist:
        return None

def box_exists(box_id):
    return MaterialOverview.objects.filter(BoxID=box_id).exists()


# ── 建立 ──────────────────────────────────────────────

def create_box(box_id, category, description, owner, status_val, locked=False):
    return MaterialOverview.objects.create(
        BoxID=box_id,
        Category=category if category else None,
        Description=description if description else None,
        Owner=owner,
        Status=status_val if status_val else None,
        Locked=locked,
    )


# ── 更新 ──────────────────────────────────────────────

def update_box(box, category, description, owner, status_val, locked):
    box.Category    = category or None
    box.Description = description or None
    box.Owner       = owner or None
    box.Status      = status_val or None
    box.Locked      = locked
    box.save()
    return box

def toggle_box_lock(box, action):
    if action == 'lock':
        box.Locked   = True
        box.LockedAt = timezone.now()
    elif action == 'unlock':
        box.Locked   = False
        box.LockedAt = timezone.now()
    box.save()
    return box


# ── 刪除 ──────────────────────────────────────────────

def delete_box(box):
    items_count = MaterialItems.objects.filter(BoxID=box).count()
    MaterialItems.objects.filter(BoxID=box).delete()
    box.delete()
    return items_count


# ── 入庫 ──────────────────────────────────────────────

def checkin_items(box_id, selected_items, qty_map, operator_id):
    """
    將物品入庫到指定容器。
    qty_map: {sn: qty}
    回傳成功筆數。
    """
    from django.shortcuts import get_object_or_404
    target_box = get_object_or_404(MaterialOverview, BoxID=box_id)

    if target_box.Locked:
        raise ValueError(f'容器 {box_id} 已鎖定，無法入庫')

    success_count = 0
    for sn in selected_items:
        qty = qty_map.get(sn, 0)
        if qty <= 0:
            continue

        source_item      = MaterialItems.objects.get(SN=sn)
        original_box_id  = source_item.BoxID.BoxID
        stock_before     = source_item.Quantity

        if source_item.BoxID == target_box:
            source_item.Quantity += qty
            source_item.save()
            action       = '入庫'
            remark       = '從容器列表直接入庫'
            current_item = source_item
        else:
            try:
                target_item = MaterialItems.objects.get(SN=sn, BoxID=target_box)
                target_item.Quantity += qty
                target_item.save()
            except MaterialItems.DoesNotExist:
                target_item = MaterialItems.objects.create(
                    SN=sn, BoxID=target_box, ItemName=source_item.ItemName,
                    Spec=source_item.Spec, Location=source_item.Location, Quantity=qty
                )
            source_item.Quantity -= qty
            if source_item.Quantity <= 0:
                source_item.delete()
            else:
                source_item.save()
            action       = '調撥'
            remark       = f'入庫調撥（來源：{original_box_id}）'
            current_item = target_item

        TransactionLog.objects.create(
            SN=current_item, ActionType=action,
            FromBoxID=original_box_id if action == '調撥' else None,
            ToBoxID=box_id, TransQty=qty,
            StockBefore=stock_before, StockAfter=current_item.Quantity,
            Operator=operator_id, Remark=remark,
        )
        success_count += 1

    return success_count


# ── BOM ───────────────────────────────────────────────

def get_bom_data(box):
    all_items       = MaterialItems.objects.filter(BoxID=box).order_by('SN')
    bom_items       = [item for item in all_items if item.is_bom_item]
    total           = len(bom_items)
    fulfilled_count = sum(1 for item in bom_items if item.bom_status == 'fulfilled')
    is_all_ready    = total > 0 and total == fulfilled_count
    existing_items  = list(MaterialItems.objects.values('SN', 'ItemName', 'Spec').distinct().order_by('SN'))
    return {
        'all_items': all_items,
        'bom_items': bom_items,
        'total': total,
        'fulfilled_count': fulfilled_count,
        'is_all_ready': is_all_ready,
        'existing_items': existing_items,
    }


def get_bom_summary(box):
    """
    回傳 BOM 進度摘要，供 project_list 顯示進度條用。
    {total, fulfilled, pct}
    """
    from ..models import MaterialItems
    all_items       = MaterialItems.objects.filter(BoxID=box)
    bom_items       = [item for item in all_items if item.is_bom_item]
    total           = len(bom_items)
    fulfilled       = sum(1 for item in bom_items if item.bom_status == 'fulfilled')
    pct             = int(fulfilled / total * 100) if total > 0 else 0
    return {'total': total, 'fulfilled': fulfilled, 'pct': pct}
# 加在 box_service.py 的 # ── BOM ─ 區塊裡，get_bom_data 後面

def pickup_bom(box, operator_id):
    """
    領料：把容器內所有 BOM 物料按 RequiredQty 扣減庫存。
    - 只有 is_all_ready 才能執行
    - 每筆寫一筆 TransactionLog（ActionType='OUT'）
    回傳：領料筆數
    """
    all_items   = MaterialItems.objects.filter(BoxID=box).order_by('SN')
    bom_items   = [item for item in all_items if item.is_bom_item]
    is_all_ready = all(item.bom_status == 'fulfilled' for item in bom_items) and len(bom_items) > 0

    if not is_all_ready:
        raise ValueError('物料尚未全數到齊，無法執行領料')

    count = 0
    for item in bom_items:
        stock_before   = item.Quantity
        item.Quantity -= item.RequiredQty
        item.save()

        TransactionLog.objects.create(
            ActionType  = 'OUT',
            SN          = item,
            FromBoxID   = box.BoxID,
            ToBoxID     = '',
            TransQty    = item.RequiredQty,
            StockBefore = stock_before,
            StockAfter  = item.Quantity,
            Operator    = operator_id,
            Remark      = f'BOM 領料 - {box.BoxID}',
        )
        count += 1

    return count

# ── Excel ─────────────────────────────────────────────

def export_boxes_to_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "容器列表"

    header_fill = PatternFill(start_color="667eea", end_color="667eea", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    headers = ['容器編號', '類別', '描述', '負責人', '狀態', '是否鎖定', '建立日期']
    ws.append(headers)
    for cell in ws[1]:
        cell.fill      = header_fill
        cell.font      = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border    = border

    containers = MaterialOverview.objects.all().order_by('BoxID')
    for box in containers:
        locked_status = '是' if box.Locked else '否'
        create_date   = box.CreateDate.strftime('%Y-%m-%d %H:%M:%S') if box.CreateDate else ''
        ws.append([box.BoxID, box.Category or '', box.Description or '',
                   box.Owner or '', box.Status or '', locked_status, create_date])
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(horizontal='left', vertical='center')
            cell.border    = border

    for i, width in enumerate([15, 12, 30, 12, 12, 12, 20], 1):
        ws.column_dimensions[chr(64 + i)].width = width

    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    return excel_file, containers.count()


def import_boxes_from_excel(excel_file, current_user_id):
    wb = load_workbook(excel_file)
    ws = wb.active

    success_count = skip_count = error_count = 0
    errors = []

    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        try:
            if not any(row):
                continue

            box_id = str(row[0]).strip() if row[0] else None
            if not box_id:
                errors.append(f'第 {row_num} 行：容器編號不能為空')
                error_count += 1
                continue

            if MaterialOverview.objects.filter(BoxID=box_id).exists():
                skip_count += 1
                continue

            category    = str(row[1]).strip() if row[1] else None
            description = str(row[2]).strip() if row[2] else None
            owner       = str(row[3]).strip() if row[3] else current_user_id
            status_val  = str(row[4]).strip() if len(row) > 4 and row[4] else '使用中'
            locked_val  = str(row[5]).strip() if len(row) > 5 and row[5] else '否'
            is_locked   = locked_val in ['是', 'True', 'true', '1', 'YES', 'yes']

            MaterialOverview.objects.create(
                BoxID=box_id, Category=category, Description=description,
                Owner=owner, Status=status_val, Locked=is_locked
            )
            success_count += 1

        except Exception as e:
            errors.append(f'第 {row_num} 行：{str(e)}')
            error_count += 1

    return success_count, skip_count, error_count, errors


def build_download_template():
    wb = Workbook()
    ws = wb.active
    ws.title = "容器匯入範本"

    header_fill = PatternFill(start_color="667eea", end_color="667eea", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    headers = ['容器編號*', '類別', '描述', '負責人', '狀態', '是否鎖定']
    ws.append(headers)
    for cell in ws[1]:
        cell.fill      = header_fill
        cell.font      = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border    = border

    for row_data in [
        ['BOX-001', '專案', '測試專案容器', '1001', '使用中', '否'],
        ['BOX-002', '個人', '個人物品',     '1002', '空閒',   '否'],
        ['BOX-003', '倉庫', '倉庫備品',     '1003', '使用中', '是'],
    ]:
        ws.append(row_data)
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(horizontal='left', vertical='center')
            cell.border    = border

    ws.append([])
    for note in [
        ['說明：'], ['1. 帶 * 的欄位為必填'], ['2. 容器編號不可重複'],
        ['3. 負責人若為空，將自動設定為匯入者'],
        ['4. 狀態可填：使用中、空閒、結案'],
        ['5. 是否鎖定可填：是、否'],
    ]:
        ws.append(note)

    for i, width in enumerate([15, 12, 30, 15, 12, 12], 1):
        ws.column_dimensions[chr(64 + i)].width = width

    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    return excel_file


# ── 統計 ──────────────────────────────────────────────

def get_dashboard_stats():
    try:
        return {
            'total_boxes':          MaterialOverview.objects.count(),
            'total_items':          MaterialItems.objects.count(),
            'locked_boxes':         MaterialOverview.objects.filter(Locked=True).count(),
            'recent_transactions':  TransactionLog.objects.count(),
        }
    except Exception as e:
        logger.error(f"獲取統計數據失敗: {str(e)}")
        return {'total_boxes': 0, 'total_items': 0, 'locked_boxes': 0, 'recent_transactions': 0}