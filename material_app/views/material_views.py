# material_app/views/material_views.py
import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ..models import MaterialItems
from ..serializers import MaterialSerializer
from ..permissions import can_edit_material, can_stock_in_out
from ..services.material_service import (
    get_all_items, get_all_boxes,
    create_item, update_item, delete_item,
    stock_out, stock_in, adjust,
    check_shortage, check_box_shortage,
)

logger = logging.getLogger(__name__)


def _get_user_context(request):
    is_auth = request.user.is_authenticated
    return {
        'current_user_id':   str(request.user.id) if is_auth else '',
        'current_user_name': (request.user.get_full_name() or request.user.username) if is_auth else '訪客',
        'is_admin':          request.user.groups.filter(name='amin').exists() if is_auth else False,
        'is_manager':        request.user.groups.filter(name='manager').exists() if is_auth else False,
        'is_employee':       request.user.groups.filter(name='emp').exists() if is_auth else False,
    }


# ════════════════════════════════════════════════════════
# 頁面路由
# ════════════════════════════════════════════════════════

@login_required
def material_list(request):
    ctx                  = _get_user_context(request)
    filter_box_id        = request.GET.get('box_id', '')
    ctx['items']         = get_all_items(filter_box_id)
    ctx['boxes']         = get_all_boxes()
    ctx['filter_box_id'] = filter_box_id
    return render(request, 'material/material_list.html', ctx)


@login_required
def material_add(request):
    # 只有 Admin / Manager 可以新增物料
    if not can_edit_material(request.user):
        messages.error(request, '權限不足，無法新增物料')
        return redirect('material:material_list')

    ctx = _get_user_context(request)
    if request.method == 'POST':
        try:
            price = request.POST.get('price')
            create_item(
                sn        = request.POST.get('sn'),
                box_id    = request.POST.get('box_id'),
                item_name = request.POST.get('item_name'),
                spec      = request.POST.get('spec') or None,
                location  = request.POST.get('location') or None,
                quantity  = int(request.POST.get('quantity', 0)),
                price     = int(price) if price and price.strip() else None,
                operator  = request.user,
            )
            messages.success(request, f'物品 {request.POST.get("sn")} 新增成功！')
            return redirect('material:material_list')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('material:material_list')
        except Exception as e:
            logger.exception(f"新增物品失敗: {e}")
            messages.error(request, f'失敗: {str(e)}')
            return redirect('material:material_list')

    ctx['boxes'] = get_all_boxes()
    return render(request, 'material/material_add.html', ctx)


@login_required
def material_edit(request, item_id):
    # 只有 Admin / Manager 可以編輯物料
    if not can_edit_material(request.user):
        messages.error(request, '權限不足，無法編輯物料')
        return redirect('material:material_list')

    ctx  = _get_user_context(request)
    item = get_object_or_404(MaterialItems, pk=item_id)

    if request.method == 'POST':
        try:
            update_item(
                item_id   = item_id,
                item_name = request.POST.get('item_name', '').strip(),
                spec      = request.POST.get('spec', '').strip(),
                location  = request.POST.get('location', '').strip(),
                quantity  = int(request.POST.get('quantity', 0)),
                box_id    = request.POST.get('box_id', '').strip() or None,
            )
            messages.success(request, f'物品 {item.sn} 已成功更新')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'更新物品時發生錯誤: {str(e)}')
            logger.exception(f"物品編輯失敗: {e}")
        return redirect('material:material_list')

    ctx['item']  = item
    ctx['boxes'] = get_all_boxes()
    return render(request, 'material/material_edit.html', ctx)


@login_required
def material_delete(request, item_id):
    # 只有 Admin / Manager 可以刪除物料
    if not can_edit_material(request.user):
        messages.error(request, '權限不足，無法刪除物料')
        return redirect('material:material_list')

    if request.method == 'POST':
        try:
            item_name = delete_item(item_id)
            messages.success(request, f'已成功刪除物品：{item_name}')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'刪除失敗: {str(e)}')
            logger.exception(f"刪除物品失敗: {e}")
    return redirect('material:material_list')


@require_POST
@login_required
def material_out_view(request):
    # 所有登入使用者都可以出庫
    try:
        stock_out(
            item_id     = request.POST.get('item_id'),
            qty         = int(request.POST.get('quantity', 0)),
            operator    = request.user,
            from_box_id = request.POST.get('from_box', ''),
            remark      = request.POST.get('remark', ''),
        )
        messages.success(request, '出庫成功！')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('material:material_list')


@require_POST
@login_required
def material_in_view(request):
    # 所有登入使用者都可以入庫
    try:
        stock_in(
            item_id   = request.POST.get('item_id'),
            qty       = int(request.POST.get('quantity', 0)),
            operator  = request.user,
            to_box_id = request.POST.get('to_box', ''),
            remark    = request.POST.get('remark', ''),
        )
        messages.success(request, '入庫成功！')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect(request.META.get('HTTP_REFERER', 'material:material_list'))


@require_POST
@login_required
def material_adjust_view(request):
    # 只有 Admin / Manager 可以盤點調整
    if not can_edit_material(request.user):
        messages.error(request, '權限不足，無法執行盤點調整')
        return redirect('material:material_list')

    try:
        adjust(
            item_id  = request.POST.get('item_id'),
            new_qty  = int(request.POST.get('new_qty', 0)),
            operator = request.user,
            remark   = request.POST.get('remark', ''),
        )
        messages.success(request, '盤點調整成功！')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('material:material_list')


# ════════════════════════════════════════════════════════
# API 路由
# ════════════════════════════════════════════════════════

class MaterialListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filter_box_id = request.query_params.get('box_id', '')
        return Response(MaterialSerializer(get_all_items(filter_box_id), many=True).data)

    def post(self, request):
        if not can_edit_material(request.user):
            return Response({'error': '權限不足'}, status=status.HTTP_403_FORBIDDEN)
        serializer = MaterialSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            item = create_item(
                sn        = serializer.validated_data['sn'],
                box_id    = serializer.validated_data['box'].box_id,
                item_name = serializer.validated_data['item_name'],
                spec      = serializer.validated_data.get('spec'),
                location  = serializer.validated_data.get('location'),
                quantity  = serializer.validated_data.get('quantity', 0),
                price     = serializer.validated_data.get('price'),
                operator  = request.user,
            )
            return Response(MaterialSerializer(item).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MaterialDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_item(self, item_id):
        return get_object_or_404(MaterialItems, pk=item_id)

    def get(self, request, item_id):
        return Response(MaterialSerializer(self._get_item(item_id)).data)

    def put(self, request, item_id):
        if not can_edit_material(request.user):
            return Response({'error': '權限不足'}, status=status.HTTP_403_FORBIDDEN)
        item       = self._get_item(item_id)
        serializer = MaterialSerializer(item, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            updated = update_item(
                item_id   = item_id,
                item_name = serializer.validated_data.get('item_name', item.item_name),
                spec      = serializer.validated_data.get('spec', item.spec),
                location  = serializer.validated_data.get('location', item.location),
                quantity  = serializer.validated_data.get('quantity', item.quantity),
                box_id    = serializer.validated_data['box'].box_id if 'box' in serializer.validated_data else None,
            )
            return Response(MaterialSerializer(updated).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, item_id):
        if not can_edit_material(request.user):
            return Response({'error': '權限不足'}, status=status.HTTP_403_FORBIDDEN)
        try:
            item_name = delete_item(item_id)
            return Response({'message': f'{item_name} 已刪除'})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MaterialStockOutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, item_id):
        qty = request.data.get('quantity')
        if not qty:
            return Response({'error': 'quantity 為必填'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            remaining = stock_out(
                item_id     = item_id,
                qty         = int(qty),
                operator    = request.user,
                from_box_id = request.data.get('from_box_id', ''),
                remark      = request.data.get('remark', ''),
            )
            return Response({'message': '出庫成功', 'remaining_quantity': remaining})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MaterialStockInAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, item_id):
        qty = request.data.get('quantity')
        if not qty:
            return Response({'error': 'quantity 為必填'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            remaining = stock_in(
                item_id   = item_id,
                qty       = int(qty),
                operator  = request.user,
                to_box_id = request.data.get('to_box_id', ''),
                remark    = request.data.get('remark', ''),
            )
            return Response({'message': '入庫成功', 'remaining_quantity': remaining})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MaterialAdjustAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, item_id):
        if not can_edit_material(request.user):
            return Response({'error': '權限不足'}, status=status.HTTP_403_FORBIDDEN)
        new_qty = request.data.get('new_qty')
        if new_qty is None:
            return Response({'error': 'new_qty 為必填'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = adjust(
                item_id  = item_id,
                new_qty  = int(new_qty),
                operator = request.user,
                remark   = request.data.get('remark', ''),
            )
            return Response({'message': '調整成功', 'new_quantity': result})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MaterialShortageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, item_id):
        try:
            result = check_shortage(item_id)
            return Response(result)
        except MaterialItems.DoesNotExist:
            return Response({'error': '找不到此物料'}, status=status.HTTP_404_NOT_FOUND)