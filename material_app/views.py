from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from django.http import JsonResponse, HttpResponse
from urllib.parse import unquote  # ✅ 加在最上面
import json
import secrets
import requests
import logging

from .models import MaterialItems, MaterialOverview, TransactionLog

logger = logging.getLogger(__name__)

# 外部 API 設定
EXTERNAL_API_URL = 'http://192.168.0.10:9987/api/auth/login'
API_TIMEOUT = 10  # 秒


# ==================== 容器 CRUD ====================

def box_list(request):
    """容器列表頁面"""
    try:
        containers = MaterialOverview.objects.all()
        items = MaterialItems.objects.all()

        # ✅ 獲取當前使用者資訊
        current_user_id = request.COOKIES.get('user_emp_id', '')
        current_user_name = unquote(request.COOKIES.get('user_name', ''))

        # ✅ 獲取使用者列表並建立對應表
        token = request.COOKIES.get('auth_token')
        users_list = []
        users_map = {}  # 工號 -> 姓名的對應表

        if token:
            try:
                user_api_url = 'http://192.168.0.10:9987/api/users'
                headers = {'Authorization': f'Bearer {token}'}
                response = requests.get(user_api_url, headers=headers, timeout=API_TIMEOUT)

                print(f"🔍 API 回應狀態: {response.status_code}")

                if response.status_code == 200:
                    user_data = response.json()
                    print(f"🔍 API 回應資料類型: {type(user_data)}")

                    if isinstance(user_data, list):
                        print(f"🔍 使用者總數: {len(user_data)}")

                        for user in user_data:
                            # 過濾離職員工
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

                            # ✅ 建立工號 -> 姓名的對應
                            users_map[emp_id] = emp_name

                        print(f"✅ 成功載入 {len(users_list)} 位使用者")
                        print(f"✅ users_map 內容: {users_map}")

            except Exception as e:
                logger.error(f"獲取使用者列表失敗: {str(e)}")
                print(f"❌ 獲取使用者列表錯誤: {str(e)}")

        # ✅ 為每個容器添加 owner_display 屬性
        for box in containers:
            print(f"🔍 容器 {box.BoxID} 的 Owner: {box.Owner}")

            if box.Owner:
                # 檢查 Owner 是否在 users_map 中
                if box.Owner in users_map:
                    box.owner_display = f"{users_map[box.Owner]} ({box.Owner})"
                    print(f"✅ 找到對應: {box.owner_display}")
                else:
                    # 找不到對應，只顯示工號
                    box.owner_display = box.Owner
                    print(f"⚠️ 找不到工號 {box.Owner} 的對應姓名")
            else:
                box.owner_display = "未指定"
                print(f"ℹ️ 容器 {box.BoxID} 沒有負責人")

        return render(request, 'material/box_list.html', {
            'boxes': containers,
            'items': items,
            'users_list': users_list,
            'users_map': users_map,
            'current_user_id': current_user_id,
            'current_user_name': current_user_name,
        })
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        logger.exception("box_list error")
        return JsonResponse({'error': str(e)}, status=500)



def box_add(request):
    """新增容器"""
    if request.method == 'POST':
        try:
            box_id = request.POST.get('BoxID')
            category = request.POST.get('Category', '')
            description = request.POST.get('Description', '')
            owner = request.POST.get('Owner', '')  # ✅ 工號
            status = request.POST.get('Status', '使用中')
            locked = request.POST.get('Locked') == 'true'

            if MaterialOverview.objects.filter(BoxID=box_id).exists():
                messages.error(request, f'容器編號 {box_id} 已存在，請使用其他編號')
                return redirect('material:box_list')

            MaterialOverview.objects.create(
                BoxID=box_id,
                Category=category if category else None,
                Description=description if description else None,
                Owner=owner if owner else None,
                Status=status if status else None,
                Locked=locked
            )

            messages.success(request, f'容器 {box_id} 新增成功！')
            return redirect('material:box_list')

        except Exception as e:
            messages.error(request, f'新增容器失敗: {str(e)}')
            return redirect('material:box_list')

    # ✅ GET 請求：準備使用者列表和當前使用者資訊
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
                        # 過濾離職員工
                        is_active = user.get('IsActive')
                        status = user.get('Status') or user.get('status') or ''

                        if is_active == False or '離職' in str(status):
                            continue

                        emp_id = str(user.get('ID') or user.get('id') or user.get('EmpID', ''))
                        emp_name = user.get('Name') or user.get('name') or '未知'

                        # ✅ 只添加非當前使用者（當前使用者已在最上方顯示）
                        if emp_id != current_user_id:
                            users_list.append({
                                'id': emp_id,
                                'name': emp_name,
                                'display': f"{emp_name} ({emp_id})"
                            })
        except Exception as e:
            logger.error(f"獲取使用者列表失敗: {str(e)}")

    # ✅ 按姓名排序（可選）
    users_list.sort(key=lambda x: x['name'])

    return render(request, 'material/box_add.html', {
        'users_list': users_list,
        'current_user_id': current_user_id,
        'current_user_name': current_user_name,
    })


def box_edit(request, box_id):
    """編輯容器"""
    box = get_object_or_404(MaterialOverview, BoxID=box_id)

    if request.method == 'POST':
        try:
            box.Category = request.POST.get('Category') or None
            box.Description = request.POST.get('Description') or None
            box.Owner = request.POST.get('Owner') or None  # ✅ 儲存工號
            box.Status = request.POST.get('Status') or None
            box.Locked = request.POST.get('Locked') == 'true'
            box.save()

            messages.success(request, f'容器 {box_id} 更新成功！')
            return redirect('material:box_list')

        except Exception as e:
            messages.error(request, f'更新容器失敗: {str(e)}')
            return redirect('material:box_edit', box_id=box_id)

    # ✅ GET 請求：準備使用者列表
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


def box_delete(request, box_id):
    """刪除容器"""
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

            # ✅ 改為儲存工號
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
                if qty <= 0: continue

                source_item = MaterialItems.objects.get(SN=sn)
                original_box_id = source_item.BoxID.BoxID
                stock_before = source_item.Quantity

                # 累加或調撥邏輯
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
                    Operator=operator_id,  # ✅ 儲存工號
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
    items = MaterialItems.objects.all().select_related('BoxID').order_by('SN')
    boxes = MaterialOverview.objects.all().order_by('BoxID')

    # ✅ 獲取當前使用者資訊
    current_user_id = request.COOKIES.get('user_emp_id', '')
    current_user_name = unquote(request.COOKIES.get('user_name', '未知使用者'))

    print(f"🔍 item_list - 當前使用者 - 工號: {current_user_id}, 姓名: {current_user_name}")

    return render(request, 'material/item_list.html', {
        'items': items,
        'boxes': boxes,
        'current_user_id': current_user_id,  # ✅ 新增這行
        'current_user_name': current_user_name,  # ✅ 新增這行
    })

def item_add(request):
    """新增物品"""
    # ✅ 獲取當前使用者資訊
    current_user_id = request.COOKIES.get('user_emp_id', '')
    current_user_name = unquote(request.COOKIES.get('user_name', '未知使用者'))

    if request.method == 'POST':
        try:
            sn = request.POST.get('SN')
            box_id = request.POST.get('BoxID')
            quantity = int(request.POST.get('Quantity', 0))

            # ✅ 操作人員直接使用當前登入使用者的工號
            operator_id = current_user_id

            box = get_object_or_404(MaterialOverview, BoxID=box_id)
            item = MaterialItems.objects.create(
                SN=sn, BoxID=box, ItemName=request.POST.get('ItemName'),
                Spec=request.POST.get('Spec') or None,
                Location=request.POST.get('Location') or None,
                Quantity=quantity
            )

            TransactionLog.objects.create(
                SN=item, ActionType='入庫', ToBoxID=box_id,
                TransQty=quantity, StockBefore=0, StockAfter=quantity,
                Operator=operator_id,  # ✅ 儲存當前登入使用者工號
                Remark='手動新增物品入庫'
            )

            messages.success(request, f'物品 {sn} 新增成功！')
            return redirect('material:item_list')
        except Exception as e:
            messages.error(request, f'失敗: {str(e)}')
            return redirect('material:item_list')

    boxes = MaterialOverview.objects.all().order_by('BoxID')

    # ✅ 傳遞當前使用者資訊到模板
    return render(request, 'material/item_add.html', {
        'boxes': boxes,
        'current_user_id': current_user_id,
        'current_user_name': current_user_name,
    })


def item_edit(request, item_id):
    """編輯物品"""
    item = get_object_or_404(MaterialItems, SN=item_id)

    # ✅ 獲取當前使用者資訊
    current_user_id = request.COOKIES.get('user_emp_id', '')
    current_user_name = unquote(request.COOKIES.get('user_name', '未知使用者'))

    if request.method == 'POST':
        try:
            old_qty = item.Quantity
            new_qty = int(request.POST.get('Quantity', 0))

            # ✅ 操作人員直接使用當前登入使用者的工號
            operator_id = current_user_id

            item.BoxID = get_object_or_404(MaterialOverview, BoxID=request.POST.get('BoxID'))
            item.ItemName = request.POST.get('ItemName')
            item.Spec = request.POST.get('Spec') or None
            item.Location = request.POST.get('Location') or None
            item.Quantity = new_qty
            item.save()

            if old_qty != new_qty:
                TransactionLog.objects.create(
                    SN=item, ActionType='入庫' if new_qty > old_qty else '出庫',
                    TransQty=abs(new_qty - old_qty), StockBefore=old_qty, StockAfter=new_qty,
                    Operator=operator_id,  # ✅ 儲存當前登入使用者工號
                    Remark='編輯資料變更數量'
                )
            messages.success(request, f'物品 {item_id} 已更新')
            return redirect('material:item_list')
        except Exception as e:
            messages.error(request, f'失敗: {str(e)}')

    # ✅ 傳遞當前使用者資訊到模板
    return render(request, 'material/item_edit.html', {
        'item': item,
        'boxes': MaterialOverview.objects.all(),
        'current_user_id': current_user_id,
        'current_user_name': current_user_name,
    })

def item_delete(request, item_id):
    """刪除物品"""
    if request.method == 'POST':
        try:
            item = get_object_or_404(MaterialItems, SN=item_id)

            # ✅ 改為儲存工號
            operator_id = request.COOKIES.get('user_emp_id', '系統')

            # 先保存必要資訊
            item_sn = item.SN
            box_id = item.BoxID.BoxID
            quantity = item.Quantity

            # 先建立刪除紀錄
            TransactionLog.objects.create(
                SN=item,
                ActionType='出庫',
                FromBoxID=box_id,
                TransQty=quantity,
                StockBefore=quantity,
                StockAfter=0,
                Operator=operator_id,  # ✅ 儲存工號
                Remark='刪除物品'
            )

            # 刪除物品
            item.delete()

            messages.success(request, f'物品 {item_sn} 已刪除')

        except Exception as e:
            messages.error(request, f'刪除失敗: {str(e)}')

    return redirect('material:item_list')

# ==================== 調撥功能 ====================

def transaction_transfer(request):
    """物品調撥"""
    # ✅ 獲取當前使用者資訊
    current_user_id = request.COOKIES.get('user_emp_id', '')
    current_user_name = unquote(request.COOKIES.get('user_name', '未知使用者'))

    # 🔍 DEBUG - 印出接收到的值
    print("=" * 60)
    print("🔍 transaction_transfer - 接收到的 Cookie 值:")
    print(f"   Raw Cookie user_emp_id = '{request.COOKIES.get('user_emp_id', 'NOT_FOUND')}'")
    print(f"   Raw Cookie user_name = '{request.COOKIES.get('user_name', 'NOT_FOUND')}'")
    print(f"   current_user_id = '{current_user_id}'")
    print(f"   current_user_name = '{current_user_name}'")
    print(f"   顯示格式將是: {current_user_name} ({current_user_id})")
    print("=" * 60)

    # ✅ 接收從物品列表傳來的參數
    pre_sn = request.GET.get('sn', '')  # 物品序號
    pre_source_box = request.GET.get('source_box', '')  # 來源容器
    pre_location = request.GET.get('location', '')  # 位置

    if request.method == 'POST':
        try:
            from_box_id = request.POST.get('from_box')
            to_box_id = request.POST.get('to_box')
            item_sn = request.POST.get('item')
            quantity = int(request.POST.get('quantity', 0))

            # ✅ 操作人員直接使用當前登入使用者的工號
            operator_id = current_user_id

            from_box = get_object_or_404(MaterialOverview, BoxID=from_box_id)
            to_box = get_object_or_404(MaterialOverview, BoxID=to_box_id)

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
                Operator=operator_id,  # ✅ 儲存當前登入使用者工號
                Remark=request.POST.get('remark', f'從 {from_box_id} 調撥')
            )
            messages.success(request, '調撥成功！')
            return redirect('material:transaction_transfer')
        except Exception as e:
            messages.error(request, f'失敗: {str(e)}')

    boxes = MaterialOverview.objects.filter(Locked=False).order_by('BoxID')

    # ✅ 傳遞當前使用者資訊和預填充參數到模板
    return render(request, 'material/transaction_transfer.html', {
        'boxes': boxes,
        'current_user_id': current_user_id,
        'current_user_name': current_user_name,
        'pre_sn': pre_sn,  # ✅ 預填充物品序號
        'pre_source_box': pre_source_box,  # ✅ 預填充來源容器
        'pre_location': pre_location,  # ✅ 預填充位置
    })

def transaction_history(request):
    """歷史紀錄"""
    transactions = TransactionLog.objects.all().select_related('SN').order_by('-Timestamp')

    # ✅ 獲取使用者列表建立工號到姓名的對應
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

    # ✅ 為每筆交易記錄添加 operator_display 屬性
    for trans in transactions:
        if trans.Operator:
            operator_id = trans.Operator
            if operator_id in users_map:
                trans.operator_display = f"{users_map[operator_id]} ({operator_id})"
            else:
                trans.operator_display = operator_id  # 找不到對應姓名，只顯示工號
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

        # 呼叫外部 API 登入
        try:
            payload = {'emp_id': emp_id, 'password': pw}
            response = requests.post(EXTERNAL_API_URL, data=payload, timeout=API_TIMEOUT)

            if response.status_code == 200:
                api_data = response.json()
                token_from_api = api_data.get('token')

                if not token_from_api:
                    return render(request, 'material/login.html', {'error_msg': '認證服務回應格式錯誤'})

                # ✅ 預設值：使用輸入的帳號（作為備用）
                user_emp_id = emp_id
                user_name = emp_id

                # ✅ 使用 token 呼叫 /api/me 取得當前使用者詳細資料
                try:
                    me_api_url = 'http://192.168.0.10:9987/api/me'
                    headers = {'Authorization': f'Bearer {token_from_api}'}
                    me_response = requests.get(me_api_url, headers=headers, timeout=API_TIMEOUT)

                    print(f"🔍 /api/me 回應狀態: {me_response.status_code}")

                    if me_response.status_code == 200:
                        me_data = me_response.json()
                        print(f"🔍 /api/me 完整回應內容:")
                        print(json.dumps(me_data, ensure_ascii=False, indent=2))

                        # ✅ 嘗試多種可能的欄位名稱來取得工號
                        extracted_emp_id = (
                            me_data.get('ID') or
                            me_data.get('id') or
                            me_data.get('EmpID') or
                            me_data.get('emp_id') or
                            me_data.get('EmployeeID') or
                            me_data.get('employee_id')
                        )

                        # ✅ 取得姓名
                        extracted_name = (
                            me_data.get('Name') or
                            me_data.get('name') or
                            me_data.get('DisplayName') or
                            me_data.get('display_name')
                        )

                        # ✅ 只有成功取得資料才覆蓋預設值
                        if extracted_emp_id:
                            user_emp_id = str(extracted_emp_id)
                            print(f"✅ 從 API 取得工號: {user_emp_id}")
                        else:
                            print(f"⚠️ 警告：無法從 /api/me 取得工號")
                            print(f"⚠️ 可用的欄位: {list(me_data.keys())}")
                            print(f"⚠️ 將使用輸入的帳號作為工號: {user_emp_id}")

                        if extracted_name:
                            user_name = extracted_name
                            print(f"✅ 從 API 取得姓名: {user_name}")
                        else:
                            print(f"⚠️ 警告：無法從 /api/me 取得姓名，將使用輸入的帳號: {user_name}")

                    else:
                        print(f"⚠️ /api/me 回應異常，狀態碼: {me_response.status_code}")
                        print(f"⚠️ 回應內容: {me_response.text}")
                        print(f"⚠️ 將使用輸入的帳號 - 工號: {user_emp_id}, 姓名: {user_name}")

                except Exception as e:
                    print(f"❌ 呼叫 /api/me 錯誤: {str(e)}")
                    logger.exception("Failed to fetch user data from /api/me")
                    print(f"⚠️ 將使用輸入的帳號 - 工號: {user_emp_id}, 姓名: {user_name}")

                print(f"=" * 60)
                print(f"✅ 最終設定 Cookie:")
                print(f"   user_emp_id = '{user_emp_id}'")
                print(f"   user_name = '{user_name}'")
                print(f"   顯示結果將是: {user_name} ({user_emp_id})")
                print(f"=" * 60)

                expiry = timezone.now() + timedelta(hours=24)
                response_obj = redirect('material:box_list')

                # 設定 auth_token
                response_obj.set_cookie(
                    'auth_token',
                    token_from_api,
                    expires=expiry,
                    httponly=True,
                    samesite='Lax',
                )

                # ✅ 設定使用者工號
                response_obj.set_cookie(
                    'user_emp_id',
                    user_emp_id,
                    expires=expiry,
                    samesite='Lax',
                )

                # ✅ 設定使用者姓名（URL 編碼以支援中文）
                from urllib.parse import quote
                response_obj.set_cookie(
                    'user_name',
                    quote(user_name),
                    expires=expiry,
                    samesite='Lax',
                )

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
    response = redirect('material:login')
    response.delete_cookie('auth_token')
    response.delete_cookie('user_emp_id')
    response.delete_cookie('user_name')
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
        "IDNumber": "********",
        "Birthday": emp.Birthday.strftime('%Y-%m-%d') if hasattr(emp, 'Birthday') and emp.Birthday else "N/A",
        "Gender": getattr(emp, 'Gender', 'N/A')
    }, json_dumps_params={'ensure_ascii': False})


# ==================== API ====================

def get_box_items(request, box_id):
    items = MaterialItems.objects.filter(BoxID_id=box_id)
    data = [{'item_id': i.SN, 'item_name': i.ItemName, 'quantity': i.Quantity} for i in items]
    return JsonResponse({'items': data})


def get_recent_transfers(request):
    """獲取最近的調撥記錄"""
    try:
        transfers = TransactionLog.objects.filter(ActionType='調撥').order_by('-Timestamp')[:10]

        # ✅ 獲取使用者列表建立工號到姓名的對應
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

        # ✅ 組裝返回資料
        data = []
        for t in transfers:
            # 取得操作人員姓名
            operator_id = t.Operator or '未知'

            # ✅ 修正：確保顯示格式為「姓名 (工號)」
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
                'operator': operator_display  # ✅ 返回「姓名 (工號)」格式
            })

        return JsonResponse({'transfers': data})

    except Exception as e:
        logger.exception("獲取調撥記錄失敗")
        return JsonResponse({'error': str(e), 'transfers': []}, status=500)

# ==================== API - 獲取使用者列表 ====================

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
                    # ✅ 過濾離職員工
                    is_active = user.get('IsActive')
                    status = user.get('Status') or user.get('status') or ''

                    # 跳過已離職員工
                    if is_active == False:
                        continue
                    if '離職' in str(status) or 'resigned' in str(status).lower():
                        continue

                    # ✅ 返回工號和姓名（前端會用工號作為 value）
                    users.append({
                        'id': user.get('ID') or user.get('id') or user.get('EmpID'),  # 工號
                        'name': user.get('Name') or user.get('name') or user.get('employee_name', '未知')  # 姓名
                    })

            return JsonResponse({'users': users})
        else:
            return JsonResponse({'error': '無法獲取使用者列表'}, status=500)

    except Exception as e:
        logger.exception("Failed to fetch users list")
        return JsonResponse({'error': str(e)}, status=500)