# material_app/views/material_views.py
import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..serializers import MaterialSerializer
from ..services.material_service import (
    get_all_items, get_all_boxes,
    create_item, update_item, delete_item, material_out,
)
from ..models import MaterialItems
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from ..services.material_service import material_out


logger = logging.getLogger(__name__)


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
@login_required  
def material_list(request):
    """物品列表"""
    ctx = _get_user_context(request)
    filter_box_id        = request.GET.get('box_id', '')
    ctx['items']         = get_all_items(filter_box_id)
    ctx['boxes']         = get_all_boxes()
    ctx['filter_box_id'] = filter_box_id
    return render(request, 'material/material_list.html', ctx)


def material_add(request):
    """新增物品"""
    ctx = _get_user_context(request)

    if request.method == 'POST':
        try:
            price = request.POST.get('Price')
            create_item(
                sn          = request.POST.get('SN'),
                box_id      = request.POST.get('BoxID'),
                item_name   = request.POST.get('ItemName'),
                spec        = request.POST.get('Spec') or None,
                location    = request.POST.get('Location') or None,
                quantity    = int(request.POST.get('Quantity', 0)),
                price       = int(price) if price and price.strip() else None,
                operator_id = ctx['current_user_id'],
            )
            messages.success(request, f'物品 {request.POST.get("SN")} 新增成功！')
            return redirect('material:material_list')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('material:material_list')
        except Exception as e:
            messages.error(request, f'失敗: {str(e)}')
            return redirect('material:material_list')

    ctx['boxes'] = get_all_boxes()
    return render(request, 'material/material_add.html', ctx)


def material_edit(request, sn):
    """編輯物品"""
    ctx = _get_user_context(request)

    if request.method == 'POST':
        try:
            update_item(
                sn         = sn,
                box_id_str = request.POST.get('BoxID', '').strip(),
                item_name  = request.POST.get('ItemName', '').strip(),
                spec       = request.POST.get('Spec', '').strip(),
                location   = request.POST.get('Location', '').strip(),
                quantity   = int(request.POST.get('Quantity', 0)),
            )
            messages.success(request, f'物品 {sn} 已成功更新')
            logger.info(f"✅ 物品編輯成功: SN={sn}")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'更新物品時發生錯誤: {str(e)}')
            logger.exception(f"❌ 物品編輯失敗: {e}")
        return redirect('material:material_list')

    try:
        item = MaterialItems.objects.get(SN=sn)
    except MaterialItems.DoesNotExist:
        messages.error(request, f'找不到序號為 {sn} 的物品')
        return redirect('material:material_list')
    except MaterialItems.MultipleObjectsReturned:
        item = MaterialItems.objects.filter(SN=sn).order_by('-UpdateTime', '-id').first()
        messages.warning(request, f'警告：序號 {sn} 有重複記錄，顯示最新一筆')

    ctx['item']  = item
    ctx['boxes'] = get_all_boxes()
    return render(request, 'material/material_edit.html', ctx)


def material_delete(request, sn):
    """刪除物品"""
    if request.method == 'POST':
        try:
            item_name, duplicate_count = delete_item(sn)
            if duplicate_count > 1:
                messages.success(request, f'已刪除物品：{sn} - {item_name}，剩餘 {duplicate_count - 1} 筆重複記錄')
            else:
                messages.success(request, f'已成功刪除物品：{sn} - {item_name}')
            logger.info(f"✅ 刪除物品成功: {sn}")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'刪除失敗: {str(e)}')
            logger.exception(f"❌ 刪除物品失敗: {e}")
    return redirect('material:material_list')




@require_POST
@login_required
def material_out_view(request):
    try:
        material_out(
            material_id = request.POST.get('material_id'),
            quantity    = request.POST.get('quantity'),
            from_box    = request.POST.get('from_box', ''),
            operator    = str(request.user.id) if request.user.is_authenticated else '系統',
            remark      = request.POST.get('remark', ''),
        )
        messages.success(request, '出庫成功！')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('material:material_list')
# ════════════════════════════════════════════════════════
# API 路由（回傳 JSON）
# ════════════════════════════════════════════════════════

@api_view(['GET', 'POST'])
def api_material_list(request):
    if request.method == 'GET':
        return Response(MaterialSerializer(get_all_items(), many=True).data)
    serializer = MaterialSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def api_material_detail(request, id):
    material = get_object_or_404(MaterialItems, pk=id)
    if request.method == 'GET':
        return Response(MaterialSerializer(material).data)
    if request.method == 'PUT':
        serializer = MaterialSerializer(material, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    material.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def api_material_out(request):
    material_id = request.data.get('material_id')
    quantity    = request.data.get('quantity')

    if not material_id or not quantity:
        return Response({'error': 'material_id 和 quantity 為必填'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        remaining = material_out(
            material_id = material_id,
            quantity    = quantity,
            from_box    = request.data.get('from_box', ''),
            operator    = request.data.get('operator', ''),
            remark      = request.data.get('remark', ''),
        )
        return Response({'message': '出庫成功', 'remaining_quantity': remaining})
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)