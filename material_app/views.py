# material_app/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from django.http import JsonResponse, HttpResponse
from urllib.parse import unquote, quote
import json
import secrets
import requests
import logging
from .decorators import admin_required, manager_or_admin_required
from django.core.cache import cache
from .models import MaterialItems, MaterialOverview, TransactionLog


from rest_framework.decorators import api_view
from rest_framework.response import Response

from rest_framework import viewsets
from rest_framework.response import Response
from .permissions import MaterialBoxPermission, TransactionPermission



logger = logging.getLogger(__name__)

# 外部 API 設定
EXTERNAL_API_URL = 'http://192.168.0.10:9987/api/auth/login'
API_TIMEOUT = 10  # 秒





# ✅ 移除重複的 normalize_role 函數（已在 middleware 中定義）

def index(request):
    """系統首頁 - 根據角色顯示不同權限"""

    # ✅ 從 middleware 取得使用者資訊
    user_info = getattr(request, 'user_info', {})

    current_user_id = user_info.get('id') or request.COOKIES.get('user_emp_id', '')
    current_user_name = user_info.get('username') or unquote(request.COOKIES.get('user_name', '未知使用者'))

    # ✅ 從 middleware 取得的角色
    api_role = user_info.get('role_display', 'MMS_user')

    # ✅ 角色中文顯示對應
    role_display_map = {
        'MMS_admin': '物料系統_超級管理者',
        'MMS_manager': '物料系統_管理者',
        'MMS_user': '物料系統_使用者',
    }

    # ✅ 判斷使用者角色（使用 Django Groups）
    is_admin = request.user.groups.filter(name='Admin').exists()
    is_manager = request.user.groups.filter(name='Manager').exists()
    is_employee = request.user.groups.filter(name='emp').exists()

    # ✅ 設定角色顯示名稱和樣式
    if is_admin:
        role_display = role_display_map.get(api_role, '物料系統_超級管理者')
        role_class = 'danger'
    elif is_manager:
        role_display = role_display_map.get(api_role, '物料系統_管理者')
        role_class = 'warning'
    else:
        role_display = role_display_map.get(api_role, '物料系統_使用者')
        role_class = 'info'

    # 取得統計數據
    try:
        total_boxes = MaterialOverview.objects.count()
        total_items = MaterialItems.objects.count()
        locked_boxes = MaterialOverview.objects.filter(Locked=True).count()
        recent_transactions = TransactionLog.objects.count()

        if is_employee:
            recent_transactions = TransactionLog.objects.filter(Operator=current_user_id).count()

    except Exception as e:
        logger.error(f"獲取統計數據失敗: {str(e)}")
        total_boxes = total_items = locked_boxes = recent_transactions = 0

    # 定義功能卡片的權限狀態
    permissions = {
        'box_list': {
            'name': '容器管理',
            'icon': 'bi-box-seam',
            'url': 'material:box_list',
            'description': '查看和管理所有容器',
            'permission': '完整權限' if (is_admin or is_manager) else '唯讀',
            'permission_class': 'success' if (is_admin or is_manager) else 'secondary',
            'disabled': False,
        },
        'item_list': {
            'name': '物品管理',
            'icon': 'bi-list-ul',
            'url': 'material:item_list',
            'description': '查看和管理所有物品',
            'permission': '完整權限' if (is_admin or is_manager) else '唯讀',
            'permission_class': 'success' if (is_admin or is_manager) else 'secondary',
            'disabled': False,
        },
        'transaction_transfer': {
            'name': '物品調撥',
            'icon': 'bi-arrow-left-right',
            'url': 'material:transaction_transfer',
            'description': '在容器之間調撥物品',
            'permission': '可使用',
            'permission_class': 'success',
            'disabled': False,
        },
        'box_add': {
            'name': '新增容器',
            'icon': 'bi-plus-circle',
            'url': 'material:box_add',
            'description': '建立新的容器',
            'permission': '完整權限' if (is_admin or is_manager) else '權限不足',
            'permission_class': 'success' if (is_admin or is_manager) else 'danger',
            'disabled': is_employee,
        },
        'transaction_history': {
            'name': '交易記錄',
            'icon': 'bi-clock-history',
            'url': 'material:transaction_history',
            'description': '查看歷史交易記錄',
            'permission': '完整權限' if (is_admin or is_manager) else '僅限本人',
            'permission_class': 'success' if (is_admin or is_manager) else 'warning',
            'disabled': False,
        },
    }

    context = {
        'current_user_id': current_user_id,
        'current_user_name': current_user_name,
        'role_display': role_display,
        'role_class': role_class,
        'is_admin': is_admin,
        'is_manager': is_manager,
        'is_employee': is_employee,
        'permissions': permissions,
        'stats': {
            'total_boxes': total_boxes,
            'total_items': total_items,
            'locked_boxes': locked_boxes,
            'recent_transactions': recent_transactions,
        }
    }

    logger.info(
        f"📊 首頁載入 - 使用者: {current_user_name} ({current_user_id}), API角色: {api_role}, 顯示: {role_display}")

    return render(request, 'material/index.html', context)

# ==================== 容器 CRUD ====================

def box_list(request):
    """容器列表頁面"""
    try:
        containers = MaterialOverview.objects.all()
        items = MaterialItems.objects.all()

        current_user_id = request.COOKIES.get('user_emp_id', '')
        current_user_name = unquote(request.COOKIES.get('user_name', ''))

        token = request.COOKIES.get('auth_token')
        users_list = []
        users_map = {}

        if token:
            try:
                user_api_url = 'http://192.168.0.10:9987/api/users'
                headers = {'Authorization': f'Bearer {token}'}
                response = requests.get(user_api_url, headers=headers, timeout=API_TIMEOUT)

                if response.status_code == 200:
                    user_data = response.json()

                    if isinstance(user_data, list):
                        for user in user_data:
                            is_active = user.get('IsActive')
                            status = user.get('Status') or user.get('status') or ''

                            if is_active == False or '離職' in str(status):
                                continue

                            emp_id = str(user.get('ID') or user.get('id') or user.get('EmpID', ''))
                            emp_name = user.get('Name') or user.get('name') or '未知'

                            users_list.append({
                                'id': emp_id,
                                'name': emp_name,
                                'display': f"{emp_name} ({emp_id})"
                            })

                            users_map[emp_id] = emp_name

            except Exception as e:
                logger.error(f"獲取使用者列表失敗: {str(e)}")

        for box in containers:
            if box.Owner:
                if box.Owner in users_map:
                    box.owner_display = f"{users_map[box.Owner]} ({box.Owner})"
                else:
                    box.owner_display = box.Owner
            else:
                box.owner_display = "未指定"

        return render(request, 'material/box_list.html', {
            'boxes': containers,
            'items': items,
            'users_list': users_list,
            'users_map': users_map,
            'current_user_id': current_user_id,
            'current_user_name': current_user_name,
        })
    except Exception as e:
        logger.exception("box_list error")
        return JsonResponse({'error': str(e)}, status=500)


@manager_or_admin_required
def box_add(request):
    """新增容器"""
    # ✅ 權限檢查：只有 Admin 和 Manager 可以新增
    if not request.user.groups.filter(name__in=['Admin', 'Manager']).exists():
        messages.error(request, '您沒有權限新增容器')
        return redirect('material:box_list')

    current_user_id = request.COOKIES.get('user_emp_id', '')
    current_user_name = unquote(request.COOKIES.get('user_name', '未知使用者'))

    if request.method == 'POST':
        try:
            box_id = request.POST.get('BoxID')
            category = request.POST.get('Category', '')
            description = request.POST.get('Description', '')
            status = request.POST.get('Status', '使用中')
            locked = request.POST.get('Locked') == 'true'

            # ✅ 負責人直接使用當前登入使用者的 ID
            owner = current_user_id

            if MaterialOverview.objects.filter(BoxID=box_id).exists():
                messages.error(request, f'容器編號 {box_id} 已存在，請使用其他編號')
                return redirect('material:box_list')

            MaterialOverview.objects.create(
                BoxID=box_id,
                Category=category if category else None,
                Description=description if description else None,
                Owner=owner,  # ✅ 使用當前登入使用者
                Status=status if status else None,
                Locked=locked
            )

            messages.success(request, f'容器 {box_id} 新增成功！負責人：{current_user_name}')
            return redirect('material:box_list')

        except Exception as e:
            messages.error(request, f'新增容器失敗: {str(e)}')
            return redirect('material:box_list')

    return render(request, 'material/box_add.html', {
        'current_user_id': current_user_id,
        'current_user_name': current_user_name,
    })


def box_edit(request, box_id):
    """編輯容器"""
    # ✅ 權限檢查：只有 Admin 和 Manager 可以編輯
    if not request.user.groups.filter(name__in=['Admin', 'Manager']).exists():
        messages.error(request, '您沒有權限編輯容器')
        return redirect('material:box_list')

    box = get_object_or_404(MaterialOverview, BoxID=box_id)

    if request.method == 'POST':
        try:
            box.Category = request.POST.get('Category') or None
            box.Description = request.POST.get('Description') or None
            box.Owner = request.POST.get('Owner') or None
            box.Status = request.POST.get('Status') or None
            box.Locked = request.POST.get('Locked') == 'true'
            box.save()

            messages.success(request, f'容器 {box_id} 更新成功！')
            return redirect('material:box_list')

        except Exception as e:
            messages.error(request, f'更新容器失敗: {str(e)}')
            return redirect('material:box_edit', box_id=box_id)

    current_user_id = request.COOKIES.get('user_emp_id', '')
    current_user_name = unquote(request.COOKIES.get('user_name', '未知使用者'))

    token = request.COOKIES.get('auth_token')
    users_list = []

    if token:
        try:
            user_api_url = 'http://192.168.0.10:9987/api/users'
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(user_api_url, headers=headers, timeout=API_TIMEOUT)

            if response.status_code == 200:
                user_data = response.json()
                if isinstance(user_data, list):
                    for user in user_data:
                        is_active = user.get('IsActive')
                        status = user.get('Status') or user.get('status') or ''

                        if is_active == False or '離職' in str(status):
                            continue

                        emp_id = str(user.get('ID') or user.get('id') or user.get('EmpID', ''))
                        emp_name = user.get('Name') or user.get('name') or '未知'

                        users_list.append({
                            'id': emp_id,
                            'name': emp_name,
                            'display': f"{emp_name} ({emp_id})"
                        })
        except Exception as e:
            logger.error(f"獲取使用者列表失敗: {str(e)}")

    users_list.sort(key=lambda x: x['name'])

    return render(request, 'material/box_edit.html', {
        'box': box,
        'users_list': users_list,
        'current_user_id': current_user_id,
        'current_user_name': current_user_name,
    })

@admin_required
def box_delete(request, box_id):
    """刪除容器"""
    # ✅ 權限檢查：只有 Admin 可以刪除
    if not request.user.groups.filter(name='Admin').exists():
        messages.error(request, '您沒有權限刪除容器')
        return redirect('material:box_list')

    if request.method == 'POST':
        try:
            box = get_object_or_404(MaterialOverview, BoxID=box_id)
            items_count = MaterialItems.objects.filter(BoxID=box).count()

            if items_count > 0:
                messages.error(request, f'容器 {box_id} 內還有 {items_count} 個物品，無法刪除！')
                return redirect('material:box_list')

            box.delete()
            messages.success(request, f'容器 {box_id} 已刪除')

        except Exception as e:
            messages.error(request, f'刪除容器失敗: {str(e)}')

    return redirect('material:box_list')


def box_toggle_lock(request):
    """鎖定 / 解鎖容器"""
    # ✅ 權限檢查：只有 Admin 和 Manager 可以鎖定/解鎖
    if not request.user.groups.filter(name__in=['Admin', 'Manager']).exists():
        messages.error(request, '您沒有權限執行此操作')
        return redirect('material:box_list')

    if request.method == 'POST':
        try:
            box_id = request.POST.get('BoxID')
            action = request.POST.get('action')
            box = get_object_or_404(MaterialOverview, BoxID=box_id)

            if action == 'lock':
                box.Locked = True
                box.save()
                messages.success(request, f'容器 {box_id} 已鎖定')
            elif action == 'unlock':
                box.Locked = False
                box.save()
                messages.success(request, f'容器 {box_id} 已解鎖')

        except Exception as e:
            messages.error(request, f'鎖定操作失敗: {str(e)}')

    return redirect('material:box_list')


def box_checkin(request):
    """入庫：將選定的物品數量累加到指定容器"""
    if request.method == 'POST':
        try:
            box_id = request.POST.get('BoxID')
            selected_items = request.POST.getlist('selected_items')

            operator_id = request.COOKIES.get('user_emp_id', '系統')

            if not box_id:
                messages.error(request, '未指定目標容器')
                return redirect('material:box_list')

            target_box = get_object_or_404(MaterialOverview, BoxID=box_id)

            if target_box.Locked:
                messages.error(request, f'容器 {box_id} 已鎖定，無法入庫')
                return redirect('material:box_list')

            success_count = 0
            for sn in selected_items:
                qty = int(request.POST.get(f'qty_{sn}', 0))
                if qty <= 0:
                    continue

                source_item = MaterialItems.objects.get(SN=sn)
                original_box_id = source_item.BoxID.BoxID
                stock_before = source_item.Quantity

                if source_item.BoxID == target_box:
                    source_item.Quantity += qty
                    source_item.save()
                    action = '入庫'
                    remark = '從容器列表直接入庫'
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
                    action = '調撥'
                    remark = f'入庫調撥（來源：{original_box_id}）'
                    current_item = target_item

                TransactionLog.objects.create(
                    SN=current_item, ActionType=action,
                    FromBoxID=original_box_id if action == '調撥' else None,
                    ToBoxID=box_id, TransQty=qty,
                    StockBefore=stock_before, StockAfter=current_item.Quantity,
                    Operator=operator_id,
                    Remark=remark
                )
                success_count += 1

            if success_count > 0:
                messages.success(request, f'成功處理 {success_count} 項物品到容器 {box_id}')
        except Exception as e:
            messages.error(request, f'入庫失敗: {str(e)}')

    return redirect('material:box_list')


# ==================== 物品 CRUD ====================

def item_list(request):
    """物品列表"""
    filter_box_id = request.GET.get('box_id', '')

    # ✅ 改用 '-UpdateTime' 排序，最新的在最上面
    items = MaterialItems.objects.all().select_related('BoxID')

    if filter_box_id:
        items = items.filter(BoxID__BoxID=filter_box_id)

    # ✅ 按更新時間降序排列（最新的在最上面）
    items = items.order_by('-UpdateTime', '-id')

    boxes = MaterialOverview.objects.all().order_by('BoxID')

    current_user_id = request.COOKIES.get('user_emp_id', '')
    current_user_name = unquote(request.COOKIES.get('user_name', '未知使用者'))

    return render(request, 'material/item_list.html', {
        'items': items,
        'boxes': boxes,
        'current_user_id': current_user_id,
        'current_user_name': current_user_name,
        'filter_box_id': filter_box_id,
    })


def item_add(request):
    """新增物品"""
    current_user_id = request.COOKIES.get('user_emp_id', '')
    current_user_name = unquote(request.COOKIES.get('user_name', '未知使用者'))

    if request.method == 'POST':
        try:
            sn = request.POST.get('SN')
            box_id = request.POST.get('BoxID')
            quantity = int(request.POST.get('Quantity', 0))

            operator_id = current_user_id

            box = get_object_or_404(MaterialOverview, BoxID=box_id)

            if box.Locked:
                messages.error(request, f'容器 {box_id} 已鎖定，無法新增物品')
                return redirect('material:item_list')

            item = MaterialItems.objects.create(
                SN=sn, BoxID=box, ItemName=request.POST.get('ItemName'),
                Spec=request.POST.get('Spec') or None,
                Location=request.POST.get('Location') or None,
                Quantity=quantity
            )

            TransactionLog.objects.create(
                SN=item, ActionType='入庫', ToBoxID=box_id,
                TransQty=quantity, StockBefore=0, StockAfter=quantity,
                Operator=operator_id,
                Remark='手動新增物品入庫'
            )

            messages.success(request, f'物品 {sn} 新增成功！')
            return redirect('material:item_list')
        except Exception as e:
            messages.error(request, f'失敗: {str(e)}')
            return redirect('material:item_list')

    boxes = MaterialOverview.objects.all().order_by('BoxID')

    return render(request, 'material/item_add.html', {
        'boxes': boxes,
        'current_user_id': current_user_id,
        'current_user_name': current_user_name,
    })


def item_edit(request, sn):
    """編輯物品"""

    # ✅ 用一個標記避免重複警告
    has_duplicate_warning = False

    try:
        item = MaterialItems.objects.get(SN=sn)
    except MaterialItems.DoesNotExist:
        messages.error(request, f'找不到序號為 {sn} 的物品')
        return redirect('material:box_list')
    except MaterialItems.MultipleObjectsReturned:
        # 如果有多筆記錄，取最新的一筆
        items = MaterialItems.objects.filter(SN=sn).order_by('-UpdateTime', '-id')
        item = items.first()

        # ✅ 只添加一次警告訊息
        if not has_duplicate_warning:
            messages.warning(
                request,
                f'警告：序號 {sn} 有 {items.count()} 筆重複記錄！'
                f'請使用管理命令清理：python manage.py merge_duplicate_items --sn "{sn}"'
            )
            has_duplicate_warning = True

        print(f"⚠️ 發現重複 SN: {sn}, 共 {items.count()} 筆")

    if request.method == 'POST':
        try:
            # 取得表單資料
            box_id_str = request.POST.get('BoxID', '').strip()
            item_name = request.POST.get('ItemName', '').strip()
            spec = request.POST.get('Spec', '').strip()
            location = request.POST.get('Location', '').strip()

            try:
                quantity = int(request.POST.get('Quantity', 0))
            except (ValueError, TypeError):
                quantity = 0

            # 驗證
            if not item_name:
                messages.error(request, '物品名稱為必填欄位')
                return redirect('material:box_list')

            if not box_id_str:
                messages.error(request, '所在容器為必填欄位')
                return redirect('material:box_list')

            # 取得容器
            try:
                box = MaterialOverview.objects.get(BoxID=box_id_str)
            except MaterialOverview.DoesNotExist:
                messages.error(request, f'容器 {box_id_str} 不存在')
                return redirect('material:box_list')

            if box.Locked:
                messages.error(request, f'容器 {box_id_str} 已被鎖定，無法編輯物品')
                return redirect('material:box_list')

            # ✅ 檢查是否會造成唯一約束衝突
            # 如果改變了 BoxID，需要檢查新的 (SN, BoxID) 組合是否已存在
            if item.BoxID_id != box_id_str:
                existing = MaterialItems.objects.filter(
                    SN=sn,
                    BoxID_id=box_id_str
                ).exclude(id=item.id).exists()

                if existing:
                    messages.error(
                        request,
                        f'容器 {box_id_str} 中已存在序號 {sn} 的物品，無法移動'
                    )
                    return redirect('material:box_list')

            # 更新
            item.ItemName = item_name
            item.Spec = spec
            item.Location = location
            item.Quantity = quantity
            item.BoxID = box

            item.save()

            messages.success(request, f'物品 {sn} 已成功更新')
            print(f"✅ 物品編輯成功: SN={sn}")

        except Exception as e:
            messages.error(request, f'更新物品時發生錯誤: {str(e)}')
            print(f"❌ 物品編輯失敗: {e}")
            import traceback
            traceback.print_exc()

        return redirect('material:box_list')

    boxes = MaterialOverview.objects.all().order_by('BoxID')
    return render(request, 'material/item_edit.html', {
        'item': item,
        'boxes': boxes
    })


def item_delete(request, sn):
    """刪除物品"""
    if request.method == 'POST':
        try:
            # ✅ 使用 filter + first() 處理可能的多筆記錄
            items = MaterialItems.objects.filter(SN=sn)

            if not items.exists():
                messages.error(request, f'找不到序號為 {sn} 的物品')
                return redirect('material:item_list')

            # 如果有多筆，先警告
            if items.count() > 1:
                messages.warning(
                    request,
                    f'警告：序號 {sn} 有 {items.count()} 筆記錄！'
                    f'建議先使用合併命令清理：python manage.py merge_duplicate_items --sn "{sn}"'
                )
                # 可以選擇只刪除第一筆，或者拒絕刪除
                # 選項1：拒絕刪除
                messages.error(request, '請先清理重複記錄再執行刪除操作')
                return redirect('material:item_list')

            # 只有一筆時才刪除
            item = items.first()

            # 檢查是否有交易記錄引用
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM material_app_transactionlog
                    WHERE SN_id = %s
                """, [item.id])
                transaction_count = cursor.fetchone()[0]

            if transaction_count > 0:
                messages.error(
                    request,
                    f'無法刪除：此物品有 {transaction_count} 筆交易記錄關聯'
                )
                return redirect('material:item_list')

            # 執行刪除
            item_name = item.ItemName
            item.delete()

            messages.success(request, f'已成功刪除物品：{sn} - {item_name}')
            print(f"✅ 刪除物品成功: {sn}")

        except Exception as e:
            messages.error(request, f'刪除失敗: {str(e)}')
            print(f"❌ 刪除物品失敗: {e}")
            import traceback
            traceback.print_exc()

        return redirect('material:item_list')

    # GET 請求：顯示確認頁面（如果有的話）
    try:
        items = MaterialItems.objects.filter(SN=sn)
        if items.count() > 1:
            messages.warning(request, f'此序號有 {items.count()} 筆重複記錄')
        item = items.first()
    except Exception as e:
        messages.error(request, f'找不到物品: {str(e)}')
        return redirect('material:item_list')

    return render(request, 'material/item_delete_confirm.html', {'item': item})


# ==================== 調撥功能 ====================

def transaction_transfer(request):
    """物品調撥"""
    current_user_id = request.COOKIES.get('user_emp_id', '')
    current_user_name = unquote(request.COOKIES.get('user_name', '未知使用者'))

    pre_sn = request.GET.get('sn', '')
    pre_source_box = request.GET.get('source_box', '')
    pre_location = request.GET.get('location', '')

    if request.method == 'POST':
        try:
            from_box_id = request.POST.get('from_box')
            to_box_id = request.POST.get('to_box')
            item_sn = request.POST.get('item')
            quantity = int(request.POST.get('quantity', 0))
            operator_id = current_user_id

            from_box = get_object_or_404(MaterialOverview, BoxID=from_box_id)
            to_box = get_object_or_404(MaterialOverview, BoxID=to_box_id)

            if from_box.Locked:
                messages.error(request, f'來源容器 {from_box_id} 已鎖定，無法調撥')
                return redirect('material:transaction_transfer')

            if to_box.Locked:
                messages.error(request, f'目標容器 {to_box_id} 已鎖定，無法調撥')
                return redirect('material:transaction_transfer')

            from_item = MaterialItems.objects.get(SN=item_sn, BoxID=from_box)
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
                SN=to_item, ActionType='調撥', FromBoxID=from_box_id, ToBoxID=to_box_id,
                TransQty=quantity, StockBefore=stock_before, StockAfter=from_item.Quantity,
                Operator=operator_id,
                Remark=request.POST.get('remark', f'從 {from_box_id} 調撥')
            )
            messages.success(request, '調撥成功！')
            return redirect('material:transaction_transfer')
        except Exception as e:
            messages.error(request, f'失敗: {str(e)}')

    boxes = MaterialOverview.objects.filter(Locked=False).order_by('BoxID')

    return render(request, 'material/transaction_transfer.html', {
        'boxes': boxes,
        'current_user_id': current_user_id,
        'current_user_name': current_user_name,
        'pre_sn': pre_sn,
        'pre_source_box': pre_source_box,
        'pre_location': pre_location,
    })






def transaction_history(request):
    """歷史紀錄"""
    transactions = TransactionLog.objects.all().select_related('SN').order_by('-Timestamp')

    # ✅ 權限檢查：Employee 只能看自己的
    if request.user.groups.filter(name='emp').exists():
        current_user_id = request.COOKIES.get('user_emp_id', '')
        transactions = transactions.filter(Operator=current_user_id)

    token = request.COOKIES.get('auth_token')
    users_map = {}

    if token:
        try:
            user_api_url = 'http://192.168.0.10:9987/api/users'
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(user_api_url, headers=headers, timeout=API_TIMEOUT)

            if response.status_code == 200:
                user_data = response.json()
                if isinstance(user_data, list):
                    for user in user_data:
                        emp_id = str(user.get('ID') or user.get('id') or user.get('EmpID', ''))
                        emp_name = user.get('Name') or user.get('name') or '未知'
                        users_map[emp_id] = emp_name
        except Exception as e:
            logger.error(f"獲取使用者列表失敗: {str(e)}")

    for trans in transactions:
        if trans.Operator:
            operator_id = trans.Operator
            if operator_id in users_map:
                trans.operator_display = f"{users_map[operator_id]} ({operator_id})"
            else:
                trans.operator_display = operator_id
        else:
            trans.operator_display = "系統"

    stats = {
        'total': transactions.count(),
        'checkin': transactions.filter(ActionType='入庫').count(),
        'checkout': transactions.filter(ActionType='出庫').count(),
        'transfer': transactions.filter(ActionType='調撥').count(),
    }

    return render(request, 'material/transaction_history.html', {
        'transactions': transactions,
        'stats': stats
    })









# ==================== 認證：API Login / Logout ====================

# material_app/views.py

@csrf_exempt
def api_login(request):
    """純外部 API 認證"""
    if request.method == 'GET':
        return render(request, 'material/login.html')

    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            emp_id = data.get('emp_id')
            pw = data.get('password')

            if not emp_id or not pw:
                return render(request, 'material/login.html', {'error_msg': '請輸入工號和密碼'})

        except Exception as e:
            logger.error(f"Parse error: {str(e)}")
            return render(request, 'material/login.html', {'error_msg': '資料格式錯誤'})

        try:
            payload = {'emp_id': emp_id, 'password': pw}
            response = requests.post(EXTERNAL_API_URL, data=payload, timeout=API_TIMEOUT)

            if response.status_code == 200:
                api_data = response.json()
                token_from_api = api_data.get('token')

                if not token_from_api:
                    return render(request, 'material/login.html', {'error_msg': '認證服務回應格式錯誤'})

                # ✅ 檢查 MMS 權限（只讀 roles，不讀 permissions）
                try:
                    me_response = requests.get(
                        'http://192.168.0.10:9987/api/me',
                        headers={'Authorization': f'Bearer {token_from_api}'},
                        timeout=5
                    )

                    if me_response.status_code == 200:
                        me_data = me_response.json()
                        user_name = me_data.get('name') or me_data.get('Name') or emp_id

                        # ✅ 只讀取 roles 字段
                        all_roles = me_data.get('roles', [])

                        # ✅ 過濾 MMS 角色
                        mms_roles = [role for role in all_roles if isinstance(role, str) and role.startswith('MMS_')]

                        logger.info(f"📋 所有角色: {all_roles}")
                        logger.info(f"🎯 MMS 角色: {mms_roles}")

                        # 檢查是否有 MMS 角色
                        if not mms_roles:
                            logger.warning(f"❌ 用戶 {emp_id} 沒有 MMS 系統權限")
                            return render(request, 'material/login.html', {
                                'error_msg': '您沒有物料管理系統的存取權限，請聯絡系統管理員設定 MMS 角色'
                            })

                        logger.info(f"✅ 用戶 {emp_id} MMS 權限驗證通過: {mms_roles}")

                except Exception as e:
                    logger.error(f"❌ 權限驗證失敗: {e}")
                    user_name = emp_id

                # 清除快取
                cache_key = f'user_info_{emp_id}'
                cache.delete(cache_key)
                logger.info(f"🗑️ 清除快取: {cache_key}")

                # 設定 cookie
                expiry = timezone.now() + timedelta(hours=24)
                response_obj = redirect('material:index')

                response_obj.set_cookie('auth_token', token_from_api, expires=expiry, httponly=True, samesite='Lax')
                response_obj.set_cookie('user_emp_id', emp_id, expires=expiry, samesite='Lax')
                response_obj.set_cookie('user_name', quote(user_name), expires=expiry, samesite='Lax')

                logger.info(f"✅ 登入成功: {emp_id} ({user_name})")
                return response_obj

            elif response.status_code == 401:
                return render(request, 'material/login.html', {'error_msg': '帳號或密碼錯誤'})
            else:
                return render(request, 'material/login.html', {'error_msg': f'認證服務異常'})

        except Exception as e:
            logger.exception(f"Login error: {str(e)}")
            return render(request, 'material/login.html', {'error_msg': '系統發生錯誤'})

    return JsonResponse({"error": "不支援的請求方法"}, status=405)



@require_http_methods(["GET", "POST"])
def api_logout(request):
    """登出"""

    # ✅ 清除快取
    user_id = request.COOKIES.get('user_emp_id')
    if user_id:
        cache_key = f'user_info_{user_id}'
        cache.delete(cache_key)
        logger.info(f"🗑️ Cleared cache for user {user_id}")

    response = redirect('material:login')
    response.delete_cookie('auth_token')
    response.delete_cookie('user_emp_id')
    response.delete_cookie('user_name')
    response.delete_cookie('user_role')

    return response


@csrf_exempt
def api_refresh(request):
    """POST /api/auth/refresh - 刷新 token"""
    token_val = request.headers.get('Authorization', '').replace('Bearer ', '')

    old_token = AuthToken.objects.filter(Token=token_val).first()
    if old_token:
        new_val = secrets.token_urlsafe(64)
        old_token.Token = new_val
        old_token.ExpiresAt = timezone.now() + timedelta(hours=24)
        old_token.save()
        return JsonResponse({"token": new_val})

    return JsonResponse({"error": "無效的 Token"}, status=401,
                        json_dumps_params={'ensure_ascii': False})


# material/views.py 或 material/api_views.py

def get_me(request):
    """GET /api/me - 取得當前登入使用者資訊"""
    emp = getattr(request, 'employee', None)
    if not emp:
        return JsonResponse({"error": "未登入"}, status=401,
                            json_dumps_params={'ensure_ascii': False})

    return JsonResponse({
        "ID": emp.EmpID,
        "Name": emp.Name,
        "DepartmentID": getattr(emp, 'DeptID', 'N/A'),
        "JobGrade": getattr(emp, 'JobGrade', 'N/A'),
        "IDNumber": "********",  # 隱私保護
        "Birthday": emp.Birthday if isinstance(emp.Birthday, str) else "N/A",
        "Gender": getattr(emp, 'Gender', 'N/A'),
        # 新增角色資訊
        "Role": getattr(request, 'user_role', 'user'),
        "RoleDisplay": getattr(request, 'user_role_display', '物料系統_使用者')
    }, json_dumps_params={'ensure_ascii': False})


# ==================== API ====================

def get_box_items(request, box_id):
    items = MaterialItems.objects.filter(BoxID_id=box_id)
    data = [{'item_id': i.SN, 'item_name': i.ItemName, 'quantity': i.Quantity} for i in items]
    return JsonResponse({'items': data})


@require_http_methods(["GET"])
def get_box_details(request, box_id):
    """
    取得容器詳細資料（包含容器資訊和內含物品列表）
    GET /material/api/box/<box_id>/details/
    """
    try:
        # 取得容器資訊
        box = get_object_or_404(MaterialOverview, BoxID=box_id)

        # 取得容器內的所有物品
        items = MaterialItems.objects.filter(BoxID=box).order_by('SN')

        # 組裝容器資料
        box_data = {
            'BoxID': box.BoxID,
            'Category': box.Category,
            'Description': box.Description,
            'Owner': box.Owner,
            'Status': box.Status,
            'Locked': box.Locked,
            'CreateDate': box.CreateDate.strftime('%Y-%m-%d %H:%M:%S') if box.CreateDate else None,
        }

        # 組裝物品資料
        items_data = []
        for item in items:
            items_data.append({
                'SN': item.SN,
                'ItemName': item.ItemName,
                'Spec': item.Spec,
                'Quantity': item.Quantity,
                'Location': item.Location,
                'UpdateTime': item.UpdateTime.strftime('%Y-%m-%d %H:%M:%S') if item.UpdateTime else None,
            })

        return JsonResponse({
            'success': True,
            'box': box_data,
            'items': items_data
        })

    except Exception as e:
        logger.exception("取得容器詳細資料失敗")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)





def get_recent_transfers(request):
    """獲取最近的調撥記錄"""
    try:
        transfers = TransactionLog.objects.filter(ActionType='調撥').order_by('-Timestamp')[:10]

        token = request.COOKIES.get('auth_token')
        users_map = {}

        if token:
            try:
                user_api_url = 'http://192.168.0.10:9987/api/users'
                headers = {'Authorization': f'Bearer {token}'}
                response = requests.get(user_api_url, headers=headers, timeout=API_TIMEOUT)

                if response.status_code == 200:
                    user_data = response.json()
                    if isinstance(user_data, list):
                        for user in user_data:
                            emp_id = str(user.get('ID') or user.get('id') or user.get('EmpID', ''))
                            emp_name = user.get('Name') or user.get('name') or '未知'
                            users_map[emp_id] = emp_name
            except Exception as e:
                logger.error(f"獲取使用者列表失敗: {str(e)}")

        data = []
        for t in transfers:
            operator_id = t.Operator or '未知'

            if operator_id != '未知':
                operator_name = users_map.get(operator_id, operator_id)
                operator_display = f"{operator_name} ({operator_id})"
            else:
                operator_display = '未知'

            data.append({
                'timestamp': t.Timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'item_name': t.SN.ItemName if t.SN else '未知',
                'quantity': t.TransQty,
                'from_box': t.FromBoxID or '—',
                'to_box': t.ToBoxID or '—',
                'operator': operator_display
            })

        return JsonResponse({'transfers': data})

    except Exception as e:
        logger.exception("獲取調撥記錄失敗")
        return JsonResponse({'error': str(e), 'transfers': []}, status=500)


def get_users_list(request):
    """獲取所有使用者列表 (供前端下拉選單使用,過濾已離職員工)"""
    try:
        token = request.COOKIES.get('auth_token')
        if not token:
            return JsonResponse({'error': '未登入'}, status=401)

        user_api_url = 'http://192.168.0.10:9987/api/users'
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(user_api_url, headers=headers, timeout=API_TIMEOUT)

        if response.status_code == 200:
            user_data = response.json()
            users = []

            if isinstance(user_data, list):
                for user in user_data:
                    is_active = user.get('IsActive')
                    status = user.get('Status') or user.get('status') or ''

                    if is_active == False:
                        continue
                    if '離職' in str(status) or 'resigned' in str(status).lower():
                        continue

                    users.append({
                        'id': user.get('ID') or user.get('id') or user.get('EmpID'),
                        'name': user.get('Name') or user.get('name') or user.get('employee_name', '未知')
                    })

            return JsonResponse({'users': users})
        else:
            return JsonResponse({'error': '無法獲取使用者列表'}, status=500)

    except Exception as e:
        logger.exception("Failed to fetch users list")
        return JsonResponse({'error': str(e)}, status=500)


# ==================== 交易記錄 API ====================

@api_view(['GET'])
def get_my_transactions(request):
    """
    GET /api/transactions/my
    Employee 專用：只能看自己的交易記錄
    """
    try:
        # 從 cookie 取得當前使用者工號
        current_user_id = request.COOKIES.get('user_emp_id', '')

        if not current_user_id:
            return JsonResponse({
                'error': '未登入或無法識別使用者'
            }, status=401)

        # 只查詢當前使用者的記錄
        transactions = TransactionLog.objects.filter(
            Operator=current_user_id
        ).select_related('SN').order_by('-Timestamp')

        # 取得使用者列表建立工號到姓名的對應
        token = request.COOKIES.get('auth_token')
        users_map = {}

        if token:
            try:
                user_api_url = 'http://192.168.0.10:9987/api/users'
                headers = {'Authorization': f'Bearer {token}'}
                response = requests.get(user_api_url, headers=headers, timeout=API_TIMEOUT)

                if response.status_code == 200:
                    user_data = response.json()
                    if isinstance(user_data, list):
                        for user in user_data:
                            emp_id = str(user.get('ID') or user.get('id') or user.get('EmpID', ''))
                            emp_name = user.get('Name') or user.get('name') or '未知'
                            users_map[emp_id] = emp_name
            except Exception as e:
                logger.error(f"獲取使用者列表失敗: {str(e)}")

        # 組裝資料
        data = []
        for trans in transactions:
            operator_id = trans.Operator or '未知'

            if operator_id != '未知' and operator_id in users_map:
                operator_display = f"{users_map[operator_id]} ({operator_id})"
            else:
                operator_display = operator_id

            data.append({
                'id': trans.ID,
                'timestamp': trans.Timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'item_sn': trans.SN.SN if trans.SN else '未知',
                'item_name': trans.SN.ItemName if trans.SN else '未知',
                'action_type': trans.ActionType,
                'from_box': trans.FromBoxID or '—',
                'to_box': trans.ToBoxID or '—',
                'quantity': trans.TransQty,
                'stock_before': trans.StockBefore,
                'stock_after': trans.StockAfter,
                'operator': operator_display,
                'remark': trans.Remark or '',
            })

        return JsonResponse({
            'success': True,
            'count': len(data),
            'scope': 'personal',  # 標記這是個人記錄
            'transactions': data
        })

    except Exception as e:
        logger.exception("獲取個人交易記錄失敗")
        return JsonResponse({
            'error': str(e),
            'transactions': []
        }, status=500)


@api_view(['GET'])
def get_all_transactions(request):
    """
    GET /api/transactions/all
    Manager/Admin 專用：可以看所有人的交易記錄
    """
    try:
        # ✅ 權限檢查：只有 Admin 和 Manager 可以訪問
        if not request.user.groups.filter(name__in=['Admin', 'Manager']).exists():
            return JsonResponse({
                'error': '權限不足：此功能僅限 Manager 或 Admin'
            }, status=403)

        # 查詢所有記錄
        transactions = TransactionLog.objects.all().select_related('SN').order_by('-Timestamp')

        # 可選：支援分頁
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 100)

        try:
            page = int(page)
            page_size = int(page_size)
            start = (page - 1) * page_size
            end = start + page_size
            transactions = transactions[start:end]
        except ValueError:
            pass

        # 取得使用者列表建立工號到姓名的對應
        token = request.COOKIES.get('auth_token')
        users_map = {}

        if token:
            try:
                user_api_url = 'http://192.168.0.10:9987/api/users'
                headers = {'Authorization': f'Bearer {token}'}
                response = requests.get(user_api_url, headers=headers, timeout=API_TIMEOUT)

                if response.status_code == 200:
                    user_data = response.json()
                    if isinstance(user_data, list):
                        for user in user_data:
                            emp_id = str(user.get('ID') or user.get('id') or user.get('EmpID', ''))
                            emp_name = user.get('Name') or user.get('name') or '未知'
                            users_map[emp_id] = emp_name
            except Exception as e:
                logger.error(f"獲取使用者列表失敗: {str(e)}")

        # 組裝資料
        data = []
        for trans in transactions:
            operator_id = trans.Operator or '未知'

            if operator_id != '未知' and operator_id in users_map:
                operator_display = f"{users_map[operator_id]} ({operator_id})"
            else:
                operator_display = operator_id

            data.append({
                'id': trans.ID,
                'timestamp': trans.Timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'item_sn': trans.SN.SN if trans.SN else '未知',
                'item_name': trans.SN.ItemName if trans.SN else '未知',
                'action_type': trans.ActionType,
                'from_box': trans.FromBoxID or '—',
                'to_box': trans.ToBoxID or '—',
                'quantity': trans.TransQty,
                'stock_before': trans.StockBefore,
                'stock_after': trans.StockAfter,
                'operator': operator_display,
                'remark': trans.Remark or '',
            })

        return JsonResponse({
            'success': True,
            'count': len(data),
            'scope': 'all',  # 標記這是全部記錄
            'transactions': data
        })

    except Exception as e:
        logger.exception("獲取全部交易記錄失敗")
        return JsonResponse({
            'error': str(e),
            'transactions': []
        }, status=500)
