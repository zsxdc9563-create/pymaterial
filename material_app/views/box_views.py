# material_app/views/box_views.py
import logging

from django.contrib import messages
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ..models import MaterialOverview, MaterialItems, TransactionLog
from ..serializers import BoxSerializer
from ..permissions import (
    can_manage, can_delete_box, can_edit_box,
    can_lock_box, can_manage_bom,
)
from ..services.box_service import (
    get_all_boxes, get_box_or_none, box_exists,
    create_box, update_box, toggle_box_lock, delete_box,
    checkin_items, get_bom_data, pickup_bom,
    export_boxes_to_excel, import_boxes_from_excel, build_download_template,
    get_dashboard_stats,
)

logger = logging.getLogger(__name__)


def _get_user_context(request):
    is_auth = request.user.is_authenticated
    return {
        'current_user_id':   str(request.user.id) if is_auth else '',
        'current_user_name': (request.user.get_full_name() or request.user.username) if is_auth else '訪客',
        'is_admin':          request.user.groups.filter(name='admin').exists() if is_auth else False,
        'is_manager':        request.user.groups.filter(name='manager').exists() if is_auth else False,
        'is_employee':       request.user.groups.filter(name='emp').exists() if is_auth else False,
    }


def index(request):
    ctx = _get_user_context(request)
    ctx['stats'] = get_dashboard_stats()
    ctx['feature_cards'] = {
        'box_list':             {'name': '容器管理', 'icon': 'bi-box-seam',         'url': 'material:box_list',             'description': '查看和管理容器',     'disabled': False},
        'material_list':        {'name': '物品管理', 'icon': 'bi-list-ul',          'url': 'material:material_list',        'description': '查看和管理物品',     'disabled': False},
        'transaction_transfer': {'name': '物品調撥', 'icon': 'bi-arrow-left-right', 'url': 'material:transaction_transfer', 'description': '在容器之間調撥物品', 'disabled': False},
        'box_add':              {'name': '新增容器', 'icon': 'bi-plus-circle',      'url': 'material:box_add',              'description': '建立新的容器',       'disabled': not can_manage(request.user)},
        'transaction_history':  {'name': '交易記錄', 'icon': 'bi-clock-history',    'url': 'material:transaction_history',  'description': '查看歷史交易記錄',   'disabled': False},
    }
    return render(request, 'material/index.html', ctx)


@login_required
def box_list(request):
    try:
        ctx = _get_user_context(request)
        ctx['boxes'] = get_all_boxes()
        return render(request, 'material/box_list.html', ctx)
    except Exception as e:
        logger.exception("box_list error")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def box_add(request):
    if not can_manage(request.user):
        messages.error(request, '權限不足，無法新增容器')
        return redirect('material:box_list')

    ctx = _get_user_context(request)
    if request.method == 'POST':
        try:
            box_id   = request.POST.get('box_id', '').strip()
            box_type = request.POST.get('box_type', '')

            if not box_id:
                messages.error(request, '容器編號不能為空')
                return redirect('material:box_list')

            if box_exists(box_id):
                messages.error(request, f'容器編號 {box_id} 已存在')
                return redirect('material:box_list')

            create_box(
                box_id      = box_id,
                box_type    = box_type,
                description = request.POST.get('description', ''),
                owner       = request.user,
                status_val  = request.POST.get('status', '使用中'),
                is_locked   = request.POST.get('is_locked') == 'true',
            )
            messages.success(request, f'容器 {box_id} 新增成功！')
            return redirect(f"{reverse('material:box_list')}?tab={box_type}")

        except Exception as e:
            logger.exception(f"新增容器失敗: {e}")
            messages.error(request, f'新增容器失敗: {str(e)}')
            return redirect('material:box_list')

    ctx['box_type_choices'] = MaterialOverview.BOX_TYPE_CHOICES
    return render(request, 'material/box_add.html', ctx)


@login_required
def box_edit(request, box_id):
    box = get_object_or_404(MaterialOverview, box_id=box_id)

    if not can_edit_box(request.user, box):
        messages.error(request, '權限不足，無法編輯此容器')
        return redirect('material:box_list')

    if request.method == 'POST':
        try:
            update_box(
                box         = box,
                box_type    = request.POST.get('box_type'),
                description = request.POST.get('description'),
                owner       = request.user,
                status_val  = request.POST.get('status'),
                is_locked   = request.POST.get('is_locked') == 'true',
            )
            messages.success(request, f'容器 {box_id} 更新成功！')
            return redirect('material:box_list')
        except Exception as e:
            messages.error(request, f'更新容器失敗: {str(e)}')
            return redirect('material:box_edit', box_id=box_id)

    ctx = _get_user_context(request)
    ctx['box']              = box
    ctx['box_type_choices'] = MaterialOverview.BOX_TYPE_CHOICES
    return render(request, 'material/box_edit.html', ctx)


@login_required
def box_delete(request, box_id):
    if request.method == 'POST':
        if not can_delete_box(request.user):
            messages.error(request, '權限不足，只有 Admin 可以刪除容器')
            return redirect('material:box_list')
        try:
            box         = get_object_or_404(MaterialOverview, box_id=box_id)
            items_count = delete_box(box)
            messages.success(request, f'容器 {box_id} 及其 {items_count} 筆物品已全數刪除')
        except Exception as e:
            messages.error(request, f'刪除容器失敗: {str(e)}')
    return redirect('material:box_list')


@login_required
def box_detail(request, box_id):
    box   = get_object_or_404(MaterialOverview, box_id=box_id)
    items = MaterialItems.objects.filter(box=box).order_by('sn')
    logs  = TransactionLog.objects.filter(
        models.Q(from_box_id=box_id) | models.Q(to_box_id=box_id)
    ).order_by('-timestamp')[:20]

    ctx = _get_user_context(request)
    ctx.update({
        'box':        box,
        'items':      items,
        'logs':       logs,
        'all_boxes':  get_all_boxes(),
        'can_edit':   can_edit_box(request.user, box),
        'can_delete': can_delete_box(request.user),
    })
    return render(request, 'material/box_detail.html', ctx)


@login_required
def box_toggle_lock(request):
    if request.method == 'POST':
        if not can_lock_box(request.user):
            messages.error(request, '權限不足，無法執行鎖定操作')
            return redirect('material:box_list')
        try:
            box_id = request.POST.get('box_id')
            action = request.POST.get('action')
            box    = get_object_or_404(MaterialOverview, box_id=box_id)
            toggle_box_lock(box, action)
            label = '鎖定' if action == 'lock' else '解鎖'
            messages.success(request, f'容器 {box_id} 已{label}')
        except Exception as e:
            messages.error(request, f'鎖定操作失敗: {str(e)}')
    return redirect('material:box_list')


@login_required
def box_checkin(request):
    if request.method == 'POST':
        try:
            box_id         = request.POST.get('box_id')
            selected_items = request.POST.getlist('selected_items')
            qty_map        = {sn: int(request.POST.get(f'qty_{sn}', 0)) for sn in selected_items}
            if not box_id:
                messages.error(request, '未指定目標容器')
                return redirect('material:box_list')
            success_count = checkin_items(box_id, selected_items, qty_map, request.user)
            if success_count > 0:
                messages.success(request, f'成功處理 {success_count} 項物品到容器 {box_id}')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'入庫失敗: {str(e)}')
    return redirect('material:box_list')


@login_required
def box_bom(request, box_id):
    box = get_object_or_404(MaterialOverview, box_id=box_id)

    if box.box_type != 'project':
        messages.error(request, f'容器 {box_id} 不是專案類型，無法使用 BOM 功能')
        return redirect('material:box_list')

    if request.method == 'POST':
        if not can_manage_bom(request.user):
            messages.error(request, '權限不足，無法管理 BOM')
            return redirect('material:box_bom', box_id=box_id)

        action = request.POST.get('action')
        if action == 'set_required':
            item     = get_object_or_404(MaterialItems, id=request.POST.get('item_id'), box=box)
            required = request.POST.get('required_qty', '').strip()
            item.required_qty = int(required) if required else None
            item.save()
            messages.success(request, f'料號 {item.sn} 需求數量已更新')
        elif action == 'pickup_bom':
            try:
                count = pickup_bom(box, request.user)
                messages.success(request, f'領料完成！共扣減 {count} 筆物料庫存。')
            except ValueError as e:
                messages.error(request, str(e))
            return redirect('material:box_bom', box_id=box_id)
        elif action == 'add_item':
            sn           = request.POST.get('sn', '').strip()
            item_name    = request.POST.get('item_name', '').strip()
            quantity     = int(request.POST.get('quantity', 0))
            required_qty = int(request.POST.get('required_qty', 1))
            if sn and item_name:
                item, created = MaterialItems.objects.get_or_create(
                    sn=sn, box=box,
                    defaults={
                        'item_name':    item_name,
                        'spec':         request.POST.get('spec') or None,
                        'location':     request.POST.get('location') or None,
                        'quantity':     quantity,
                        'required_qty': required_qty,
                    }
                )
                if not created:
                    item.required_qty = required_qty
                    item.save()
                    messages.warning(request, f'料號 {sn} 已存在，已更新需求數量')
                else:
                    messages.success(request, f'料號 {sn} 已新增至 BOM')
            else:
                messages.error(request, '料號和品名為必填欄位')
        elif action == 'delete_item':
            item = get_object_or_404(MaterialItems, id=request.POST.get('item_id'), box=box)
            sn   = item.sn
            item.delete()
            messages.success(request, f'料號 {sn} 已從 BOM 刪除')
        return redirect('material:box_bom', box_id=box_id)

    data = get_bom_data(box)
    ctx  = {'box': box, 'can_manage_bom': can_manage_bom(request.user), **data}
    return render(request, 'material/box_bom.html', ctx)


@login_required
def project_list(request):
    from ..services.box_service import get_bom_summary
    boxes = MaterialOverview.objects.filter(box_type='project').order_by('-created_at')
    for box in boxes:
        box.bom_summary = get_bom_summary(box)
    ctx          = _get_user_context(request)
    ctx['boxes'] = boxes
    return render(request, 'material/project_list.html', ctx)


def box_export_excel(request):
    try:
        excel_file, count = export_boxes_to_excel()
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="容器列表.xlsx"'
        response.write(excel_file.getvalue())
        return response
    except Exception as e:
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
            success, skip, error, errors = import_boxes_from_excel(f, request.user)
            if success: messages.success(request, f'成功匯入 {success} 筆容器資料')
            if skip:    messages.warning(request, f'跳過 {skip} 筆已存在的容器')
            if error:
                msg = f'匯入失敗 {error} 筆'
                if errors: msg += '：' + '；'.join(errors[:5])
                messages.error(request, msg)
        except Exception as e:
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
        messages.error(request, f'下載範本失敗: {str(e)}')
        return redirect('material:box_list')


# ════════════════════════════════════════════════════════
# API 路由
# ════════════════════════════════════════════════════════

class BoxListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(BoxSerializer(get_all_boxes(), many=True).data)

    def post(self, request):
        if not can_manage(request.user):
            return Response({'error': '權限不足'}, status=status.HTTP_403_FORBIDDEN)
        serializer = BoxSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            box = create_box(
                box_id      = serializer.validated_data['box_id'],
                box_type    = serializer.validated_data.get('box_type'),
                description = serializer.validated_data.get('description'),
                owner       = request.user,
                status_val  = serializer.validated_data.get('status'),
                is_locked   = serializer.validated_data.get('is_locked', False),
            )
            return Response(BoxSerializer(box).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BoxDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_box(self, box_id):
        return get_object_or_404(MaterialOverview, box_id=box_id)

    def get(self, request, box_id):
        return Response(BoxSerializer(self._get_box(box_id)).data)

    def put(self, request, box_id):
        box = self._get_box(box_id)
        if not can_edit_box(request.user, box):
            return Response({'error': '權限不足'}, status=status.HTTP_403_FORBIDDEN)
        serializer = BoxSerializer(box, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            updated_box = update_box(
                box         = box,
                box_type    = serializer.validated_data.get('box_type'),
                description = serializer.validated_data.get('description'),
                owner       = request.user,
                status_val  = serializer.validated_data.get('status'),
                is_locked   = serializer.validated_data.get('is_locked'),
            )
            return Response(BoxSerializer(updated_box).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, box_id):
        if not can_delete_box(request.user):
            return Response({'error': '權限不足'}, status=status.HTTP_403_FORBIDDEN)
        box = self._get_box(box_id)
        try:
            items_count = delete_box(box)
            return Response({'message': f'容器 {box_id} 及 {items_count} 筆物品已刪除'})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BoxToggleLockAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, box_id):
        if not can_lock_box(request.user):
            return Response({'error': '權限不足'}, status=status.HTTP_403_FORBIDDEN)
        action = request.data.get('action')
        if action not in ('lock', 'unlock'):
            return Response({'error': 'action 必須是 lock 或 unlock'}, status=status.HTTP_400_BAD_REQUEST)
        box = get_object_or_404(MaterialOverview, box_id=box_id)
        try:
            toggle_box_lock(box, action)
            label = '鎖定' if action == 'lock' else '解鎖'
            return Response({'message': f'容器 {box_id} 已{label}'})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BoxShortageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, box_id):
        from ..services.material_service import check_box_shortage
        result = check_box_shortage(box_id)
        return Response(result)


class BoxBOMAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, box_id):
        """取得箱子的 BOM 資料"""
        box = get_object_or_404(MaterialOverview, box_id=box_id)
        if box.box_type != 'project':
            return Response({'error': '此箱子不是專案類型'}, status=status.HTTP_400_BAD_REQUEST)
        data = get_bom_data(box)
        from ..serializers import MaterialSerializer
        return Response({
            'box_id': box_id,
            'all_items': MaterialSerializer(data['all_items'], many=True).data,
            'bom_items': MaterialSerializer(data['bom_items'], many=True).data,
            'total': data['total'],
            'fulfilled_count': data['fulfilled_count'],
            'is_all_ready': data['is_all_ready'],
        })

    def post(self, request, box_id):
        """執行 BOM 領料"""
        if not can_manage_bom(request.user):
            return Response({'error': '權限不足'}, status=status.HTTP_403_FORBIDDEN)
        box = get_object_or_404(MaterialOverview, box_id=box_id)
        try:
            count = pickup_bom(box, request.user)
            return Response({'message': f'領料完成！共扣減 {count} 筆物料庫存。'})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BoxBOMItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, box_id, item_id):
        """更新 BOM 需求數量"""
        if not can_manage_bom(request.user):
            return Response({'error': '權限不足'}, status=status.HTTP_403_FORBIDDEN)
        box = get_object_or_404(MaterialOverview, box_id=box_id)
        item = get_object_or_404(MaterialItems, id=item_id, box=box)
        required_qty = request.data.get('required_qty')
        item.required_qty = int(required_qty) if required_qty else None
        item.save()
        return Response({'message': f'料號 {item.sn} 需求數量已更新'})


class ProjectListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """取得所有專案箱子列表"""
        from ..services.box_service import get_bom_summary
        boxes = MaterialOverview.objects.filter(box_type='project').order_by('-created_at')
        result = []
        for box in boxes:
            summary = get_bom_summary(box)
            result.append({
                'box_id': box.box_id,
                'description': box.description,
                'owner': box.owner.username if box.owner else None,
                'is_locked': box.is_locked,
                'bom_total': summary['total'],
                'bom_fulfilled': summary['fulfilled'],
                'bom_pct': summary['pct'],
            })
        return Response(result)        