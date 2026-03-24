# material_app/views/box_views.py
import logging

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..models import MaterialOverview, MaterialItems
from ..serializers import BoxSerializer
from ..services.box_service import (
    get_all_boxes, get_box_or_none, box_exists,
    create_box, update_box, toggle_box_lock, delete_box,
    checkin_items, get_bom_data, pickup_bom,
    export_boxes_to_excel, import_boxes_from_excel, build_download_template,
    get_dashboard_stats,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════
# 工具：取得目前使用者資訊
# ════════════════════════════════════════════════════════

def _get_user_context(request):
    is_auth = request.user.is_authenticated
    return {
        'current_user_id':   str(request.user.id) if is_auth else '',
        'current_user_name': (request.user.get_full_name() or request.user.username) if is_auth else '訪客',
        'is_admin':          request.user.groups.filter(name='Admin').exists() if is_auth else False,
        'is_manager':        request.user.groups.filter(name='Manager').exists() if is_auth else False,
        'is_employee':       request.user.groups.filter(name='emp').exists() if is_auth else False,
    }


# ════════════════════════════════════════════════════════
# 頁面路由（回傳 HTML）
# ════════════════════════════════════════════════════════

def index(request):
    """系統首頁"""
    ctx = _get_user_context(request)
    ctx['stats'] = get_dashboard_stats()
    ctx['feature_cards'] = {
        'box_list':             {'name': '容器管理', 'icon': 'bi-box-seam',         'url': 'material:box_list',             'description': '查看和管理容器',     'disabled': False},
        'material_list':        {'name': '物品管理', 'icon': 'bi-list-ul',          'url': 'material:material_list',        'description': '查看和管理物品',     'disabled': False},
        'transaction_transfer': {'name': '物品調撥', 'icon': 'bi-arrow-left-right', 'url': 'material:transaction_transfer', 'description': '在容器之間調撥物品', 'disabled': ctx['is_employee']},
        'box_add':              {'name': '新增容器', 'icon': 'bi-plus-circle',      'url': 'material:box_add',              'description': '建立新的容器',       'disabled': ctx['is_employee']},
        'transaction_history':  {'name': '交易記錄', 'icon': 'bi-clock-history',    'url': 'material:transaction_history',  'description': '查看歷史交易記錄',   'disabled': False},
    }
    logger.info(f"📊 首頁載入 - 使用者: {ctx['current_user_name']}")
    return render(request, 'material/index.html', ctx)


@login_required
def box_list(request):
    try:
        ctx = _get_user_context(request)
        ctx['boxes'] = MaterialOverview.objects.exclude(Category='專案').order_by('-CreateDate')
        return render(request, 'material/box_list.html', ctx)
    except Exception as e:
        logger.exception("box_list error")
        return JsonResponse({'error': str(e)}, status=500)


def box_add(request):
    """新增容器"""
    ctx = _get_user_context(request)

    if request.method == 'POST':
        try:
            box_id = request.POST.get('BoxID')
            if box_exists(box_id):
                messages.error(request, f'容器編號 {box_id} 已存在，請使用其他編號')
                return redirect('material:box_list')

            create_box(
                box_id      = box_id,
                category    = request.POST.get('Category', ''),
                description = request.POST.get('Description', ''),
                owner       = ctx['current_user_id'],
                status_val  = request.POST.get('Status', '使用中'),
                locked      = request.POST.get('Locked') == 'true',
            )
            messages.success(request, f'容器 {box_id} 新增成功！')
            return redirect('material:box_list')
        except Exception as e:
            logger.exception(f"新增容器失敗: {e}")
            messages.error(request, f'新增容器失敗: {str(e)}')
            return redirect('material:box_list')

    ctx['categories'] = MaterialOverview.CATEGORY_CHOICES
    return render(request, 'material/box_add.html', ctx)


def box_edit(request, box_id):
    """編輯容器"""
    box = get_object_or_404(MaterialOverview, BoxID=box_id)

    if request.method == 'POST':
        try:
            update_box(
                box         = box,
                category    = request.POST.get('Category'),
                description = request.POST.get('Description'),
                owner       = request.POST.get('Owner'),
                status_val  = request.POST.get('Status'),
                locked      = request.POST.get('Locked') == 'true',
            )
            messages.success(request, f'容器 {box_id} 更新成功！')
            return redirect('material:box_list')
        except Exception as e:
            messages.error(request, f'更新容器失敗: {str(e)}')
            return redirect('material:box_edit', box_id=box_id)

    ctx = _get_user_context(request)
    ctx['box']        = box
    ctx['categories'] = MaterialOverview.CATEGORY_CHOICES
    return render(request, 'material/box_edit.html', ctx)


def box_delete(request, box_id):
    """刪除容器（含容器內所有物品）"""
    if request.method == 'POST':
        try:
            box         = get_object_or_404(MaterialOverview, BoxID=box_id)
            items_count = delete_box(box)
            messages.success(request, f'容器 {box_id} 及其 {items_count} 筆物品已全數刪除')
        except Exception as e:
            messages.error(request, f'刪除容器失敗: {str(e)}')
    return redirect('material:box_list')


def box_toggle_lock(request):
    """鎖定 / 解鎖容器"""
    if request.method == 'POST':
        try:
            box_id = request.POST.get('BoxID')
            action = request.POST.get('action')
            box    = get_object_or_404(MaterialOverview, BoxID=box_id)
            toggle_box_lock(box, action)
            label = '鎖定' if action == 'lock' else '解鎖'
            messages.success(request, f'容器 {box_id} 已{label}')
            logger.info(f"✅ {request.user} {label}了容器 {box_id}")
        except Exception as e:
            messages.error(request, f'鎖定操作失敗: {str(e)}')
    return redirect('material:box_list')


def box_checkin(request):
    """容器入庫"""
    if request.method == 'POST':
        try:
            box_id         = request.POST.get('BoxID')
            selected_items = request.POST.getlist('selected_items')
            operator_id    = str(request.user.id) if request.user.is_authenticated else '系統'
            qty_map        = {sn: int(request.POST.get(f'qty_{sn}', 0)) for sn in selected_items}

            if not box_id:
                messages.error(request, '未指定目標容器')
                return redirect('material:box_list')

            success_count = checkin_items(box_id, selected_items, qty_map, operator_id)
            if success_count > 0:
                messages.success(request, f'成功處理 {success_count} 項物品到容器 {box_id}')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'入庫失敗: {str(e)}')
    return redirect('material:box_list')


def box_bom(request, box_id):
    """BOM 到料對照 - 僅限專案容器"""
    box = get_object_or_404(MaterialOverview, BoxID=box_id)

    if box.Category != '專案':
        messages.error(request, f'容器 {box_id} 不是專案類型，無法使用 BOM 功能')
        return redirect('material:box_list')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'set_required':
            # ✅ 直接用已 import 的 MaterialItems
            item     = get_object_or_404(MaterialItems, id=request.POST.get('item_id'), BoxID=box)
            required = request.POST.get('RequiredQty', '').strip()
            item.RequiredQty = int(required) if required else None
            item.save()
            messages.success(request, f'料號 {item.SN} 需求數量已更新')

        elif action == 'pickup_bom':
            try:
                operator_id = str(request.user.id) if request.user.is_authenticated else '系統'
                count = pickup_bom(box, operator_id)
                messages.success(request, f'領料完成！共扣減 {count} 筆物料庫存。')
            except ValueError as e:
                messages.error(request, str(e))
            return redirect('material:box_bom', box_id=box_id)

        elif action == 'add_item':
            sn           = request.POST.get('SN', '').strip()
            item_name    = request.POST.get('ItemName', '').strip()
            quantity     = int(request.POST.get('Quantity', 0))
            required_qty = int(request.POST.get('RequiredQty', 1))

            if sn and item_name:
                item, created = MaterialItems.objects.get_or_create(
                    SN=sn, BoxID=box,
                    defaults={
                        'ItemName':    item_name,
                        'Spec':        request.POST.get('Spec') or None,
                        'Location':    request.POST.get('Location') or None,
                        'Quantity':    quantity,
                        'RequiredQty': required_qty,
                    }
                )
                if not created:
                    item.RequiredQty = required_qty
                    item.save()
                    messages.warning(request, f'料號 {sn} 已存在，已更新需求數量')
                else:
                    messages.success(request, f'料號 {sn} 已新增至 BOM')
            else:
                messages.error(request, '料號和品名為必填欄位')

        elif action == 'delete_item':
            # ✅ 直接用已 import 的 MaterialItems
            item = get_object_or_404(MaterialItems, id=request.POST.get('item_id'), BoxID=box)
            sn   = item.SN
            item.delete()
            messages.success(request, f'料號 {sn} 已從 BOM 刪除')

        return redirect('material:box_bom', box_id=box_id)

    data = get_bom_data(box)
    return render(request, 'material/box_bom.html', {'box': box, **data})



@login_required
def project_list(request):
    """專案管理頁面 - 只顯示專案類型容器"""
    from ..services.box_service import get_bom_summary
    boxes = MaterialOverview.objects.filter(Category='專案').order_by('-CreateDate')

    for box in boxes:
        box.bom_summary = get_bom_summary(box)

    ctx = _get_user_context(request)
    ctx['boxes'] = boxes
    return render(request, 'material/project_list.html', ctx)


# ── Excel ─────────────────────────────────────────────

def box_export_excel(request):
    try:
        excel_file, count = export_boxes_to_excel()
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="容器列表.xlsx"'
        response.write(excel_file.getvalue())
        logger.info(f"✅ 容器列表匯出成功，共 {count} 筆")
        return response
    except Exception as e:
        logger.exception("匯出 Excel 失敗")
        messages.error(request, f'匯出失敗: {str(e)}')
        return redirect('material:box_list')


def box_import_excel(request):
    if request.method == 'POST':
        try:
            if 'excel_file' not in request.FILES:
                messages.error(request, '請選擇要匯入的 Excel 檔案')
                return redirect('material:box_list')

            f = request.FILES['excel_file']
            if not f.name.endswith(('.xlsx', '.xls')):
                messages.error(request, '檔案格式錯誤，請上傳 .xlsx 或 .xls 檔案')
                return redirect('material:box_list')

            current_user_id = str(request.user.id) if request.user.is_authenticated else ''
            success, skip, error, errors = import_boxes_from_excel(f, current_user_id)

            if success: messages.success(request, f'成功匯入 {success} 筆容器資料')
            if skip:    messages.warning(request, f'跳過 {skip} 筆已存在的容器')
            if error:
                msg = f'匯入失敗 {error} 筆'
                if errors: msg += '：' + '；'.join(errors[:5])
                messages.error(request, msg)

            logger.info(f"📊 Excel 匯入完成 - 成功:{success} 跳過:{skip} 失敗:{error}")
        except Exception as e:
            logger.exception("匯入 Excel 失敗")
            messages.error(request, f'匯入失敗: {str(e)}')
    return redirect('material:box_list')


def box_download_template(request):
    try:
        excel_file = build_download_template()
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="容器匯入範本.xlsx"'
        response.write(excel_file.getvalue())
        return response
    except Exception as e:
        logger.exception("下載範本失敗")
        messages.error(request, f'下載範本失敗: {str(e)}')
        return redirect('material:box_list')


# ════════════════════════════════════════════════════════
# API 路由（回傳 JSON）
# ════════════════════════════════════════════════════════

@api_view(['GET', 'POST'])
def api_box_list(request):
    """GET /api/boxes/ | POST /api/boxes/"""
    if request.method == 'GET':
        return Response(BoxSerializer(get_all_boxes(), many=True).data)

    serializer = BoxSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def api_box_detail(request, id):
    """GET/PUT/DELETE /api/boxes/{id}/"""
    box = get_object_or_404(MaterialOverview, BoxID=id)

    if request.method == 'GET':
        return Response(BoxSerializer(box).data)

    if request.method == 'PUT':
        serializer = BoxSerializer(box, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    box.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)