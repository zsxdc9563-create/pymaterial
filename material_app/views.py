from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
import json
import secrets
import requests
import logging

from .models import MaterialItems, MaterialOverview, TransactionLog  # ✅ 正確

logger = logging.getLogger(__name__)

# 外部 API 設定
EXTERNAL_API_URL = 'http://192.168.0.10:9987/api/auth/login'
API_TIMEOUT = 10  # 秒

# ==================== 容器 CRUD ====================

# views.py

def box_list(request):
    """容器列表頁面"""
    try:
        containers = MaterialOverview.objects.all()
        items = MaterialItems.objects.all()  # ✅ 加這行

        return render(request, 'material/box_list.html', {
            'boxes': containers,
            'items': items  # ✅ 加這行
        })
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def box_add(request):
    """新增容器"""
    if request.method == 'POST':
        try:
            box_id = request.POST.get('BoxID')
            category = request.POST.get('Category', '')
            description = request.POST.get('Description', '')
            owner = request.POST.get('Owner', '')
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

    return render(request, 'material/box_add.html')


def box_edit(request, box_id):
    """編輯容器"""
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

    return render(request, 'material/box_edit.html', {'box': box})


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
            # 獲取當前登入員工姓名
            operator_name = request.employee.Name if request.employee else '系統'

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
                    Operator=operator_name, Remark=remark
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
    return render(request, 'material/item_list.html', {'items': items, 'boxes': boxes})


def item_add(request):
    """新增物品"""
    if request.method == 'POST':
        try:
            sn = request.POST.get('SN')
            box_id = request.POST.get('BoxID')
            quantity = int(request.POST.get('Quantity', 0))
            operator_name = request.employee.Name if request.employee else '系統'

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
                Operator=operator_name, Remark='手動新增物品入庫'
            )

            messages.success(request, f'物品 {sn} 新增成功！')
            return HttpResponseRedirect('/material/items/')
        except Exception as e:
            messages.error(request, f'失敗: {str(e)}')
            return redirect('material:item_list')

    boxes = MaterialOverview.objects.all().order_by('BoxID')
    return render(request, 'material/item_add.html', {'boxes': boxes})


def item_edit(request, item_id):
    """編輯物品"""
    item = get_object_or_404(MaterialItems, SN=item_id)
    if request.method == 'POST':
        try:
            old_qty = item.Quantity
            new_qty = int(request.POST.get('Quantity', 0))
            operator_name = request.employee.Name if request.employee else '系統'

            item.BoxID = get_object_or_404(MaterialOverview, BoxID=request.POST.get('BoxID'))
            item.ItemName = request.POST.get('ItemName')
            item.Quantity = new_qty
            item.save()

            if old_qty != new_qty:
                TransactionLog.objects.create(
                    SN=item, ActionType='入庫' if new_qty > old_qty else '出庫',
                    TransQty=abs(new_qty - old_qty), StockBefore=old_qty, StockAfter=new_qty,
                    Operator=operator_name, Remark='編輯資料變更數量'
                )
            messages.success(request, f'物品 {item_id} 已更新')
            return redirect('material:item_list')
        except Exception as e:
            messages.error(request, f'失敗: {str(e)}')
    return render(request, 'material/item_edit.html', {'item': item, 'boxes': MaterialOverview.objects.all()})


def item_delete(request, item_id):
    """刪除物品"""
    if request.method == 'POST':
        try:
            item = get_object_or_404(MaterialItems, SN=item_id)
            TransactionLog.objects.create(
                SN=item, ActionType='出庫', FromBoxID=item.BoxID.BoxID,
                TransQty=item.Quantity, StockBefore=item.Quantity, StockAfter=0,
                Operator=request.employee.Name if request.employee else '系統', Remark='刪除物品'
            )
            item.delete()
            messages.success(request, f'物品 {item_id} 已刪除')
        except Exception as e:
            messages.error(request, f'失敗: {str(e)}')
    return redirect('material:item_list')


# ==================== 調撥功能 ====================

def transaction_transfer(request):
    """物品調撥"""
    if request.method == 'POST':
        try:
            from_box_id = request.POST.get('from_box')
            to_box_id = request.POST.get('to_box')
            item_sn = request.POST.get('item')
            quantity = int(request.POST.get('quantity', 0))
            # 優先使用登入者姓名
            operator_name = request.employee.Name if request.employee else request.POST.get('operator', '系統')

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
                Operator=operator_name, Remark=request.POST.get('remark', f'從 {from_box_id} 調撥')
            )
            messages.success(request, '調撥成功！')
            return redirect('material:transaction_transfer')
        except Exception as e:
            messages.error(request, f'失敗: {str(e)}')

    boxes = MaterialOverview.objects.filter(Locked=False).order_by('BoxID')
    return render(request, 'material/transaction_transfer.html', {'boxes': boxes})


def transaction_history(request):
    """歷史紀錄"""
    transactions = TransactionLog.objects.all().select_related('SN').order_by('-Timestamp')
    stats = {
        'total': transactions.count(),
        'checkin': transactions.filter(ActionType='入庫').count(),
        'checkout': transactions.filter(ActionType='出庫').count(),
        'transfer': transactions.filter(ActionType='調撥').count(),
    }
    return render(request, 'material/transaction_history.html', {'transactions': transactions, 'stats': stats})


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

        # 呼叫外部 API
        try:
            payload = {'emp_id': emp_id, 'password': pw}

            response = requests.post(EXTERNAL_API_URL, data=payload, timeout=API_TIMEOUT)

            if response.status_code == 200:
                api_data = response.json()
                token_from_api = api_data.get('token')

                if not token_from_api:
                    return render(request, 'material/login.html', {'error_msg': '認證服務回應格式錯誤'})

                # ✅ 獲取使用者資訊
                user_name = api_data.get('name', emp_id)  # 如果 API 有回傳 name


                # ✅ 直接設定 cookie 並跳轉，不查資料庫
                expiry = timezone.now() + timedelta(hours=24)

                response_obj = redirect('material:box_list')

                # ✅ 設定 auth_token
                response_obj.set_cookie(
                    'auth_token',
                    token_from_api,
                    expires=expiry,
                    httponly=True,
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
    transfers = TransactionLog.objects.filter(ActionType='調撥').order_by('-Timestamp')[:10]
    data = [{'item_name': t.SN.ItemName, 'from': t.FromBoxID, 'to': t.ToBoxID} for t in transfers]
    return JsonResponse({'transfers': data})
