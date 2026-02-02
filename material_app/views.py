from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import MaterialOverview, ItemList, TransactionLog


# ==================== 容器 CRUD ====================

def box_list(request):
    """容器列表"""
    boxes = MaterialOverview.objects.all().order_by('-CreateDate')
    return render(request, 'material/box_list.html', {'boxes': boxes})


def box_add(request):
    """新增容器"""
    if request.method == 'POST':
        try:
            # 從表單獲取資料
            box_id = request.POST.get('BoxID')
            category = request.POST.get('Category', '')
            description = request.POST.get('Description', '')
            owner = request.POST.get('Owner', '')
            status = request.POST.get('Status', '使用中')
            locked = request.POST.get('Locked') == 'true'  # checkbox 值

            # 檢查容器編號是否已存在
            if MaterialOverview.objects.filter(BoxID=box_id).exists():
                messages.error(request, f'容器編號 {box_id} 已存在，請使用其他編號')
                return redirect('material:box_list')

            # 創建新容器
            box = MaterialOverview.objects.create(
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

    # GET 請求：顯示表單頁面（如果需要獨立頁面）
    return render(request, 'material/box_add.html')


def box_edit(request, box_id):
    """編輯容器"""
    box = get_object_or_404(MaterialOverview, BoxID=box_id)

    if request.method == 'POST':
        try:
            # 更新容器資料
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

    # GET 請求：顯示編輯表單
    return render(request, 'material/box_edit.html', {'box': box})


def box_delete(request, box_id):
    """刪除容器"""
    if request.method == 'POST':
        try:
            box = get_object_or_404(MaterialOverview, BoxID=box_id)

            # 檢查容器內是否還有物品
            items_count = ItemList.objects.filter(BoxID=box).count()
            if items_count > 0:
                messages.error(request, f'容器 {box_id} 內還有 {items_count} 個物品，無法刪除！請先清空容器。')
                return redirect('material:box_list')

            box.delete()
            messages.success(request, f'容器 {box_id} 已刪除')

        except Exception as e:
            messages.error(request, f'刪除容器失敗: {str(e)}')

    return redirect('material:box_list')


# ==================== 物品 CRUD ====================

def item_list(request):
    """物品列表"""
    items = ItemList.objects.all().select_related('BoxID').order_by('SN')
    boxes = MaterialOverview.objects.all().order_by('BoxID')
    return render(request, 'material/item_list.html', {
        'items': items,
        'boxes': boxes
    })


def item_add(request):
    """新增物品"""
    if request.method == 'POST':
        try:
            sn = request.POST.get('SN')
            box_id = request.POST.get('BoxID')
            item_name = request.POST.get('ItemName')
            spec = request.POST.get('Spec', '')
            location = request.POST.get('Location', '')
            quantity = int(request.POST.get('Quantity', 0))

            # 檢查物品序號是否已存在
            if ItemList.objects.filter(SN=sn).exists():
                messages.error(request, f'物品序號 {sn} 已存在')
                return redirect('material:item_list')

            # 獲取容器
            box = get_object_or_404(MaterialOverview, BoxID=box_id)

            # 創建物品
            item = ItemList.objects.create(
                SN=sn,
                BoxID=box,
                ItemName=item_name,
                Spec=spec if spec else None,
                Location=location if location else None,
                Quantity=quantity
            )

            # 記錄入庫
            TransactionLog.objects.create(
                SN=item,
                ActionType='入庫',
                ToBoxID=box_id,
                TransQty=quantity,
                StockBefore=0,
                StockAfter=quantity,
                Operator=request.POST.get('Operator', '系統'),
                Remark=f'新增物品入庫'
            )

            messages.success(request, f'物品 {sn} 新增成功！')
            return redirect('material:item_list')

        except Exception as e:
            messages.error(request, f'新增物品失敗: {str(e)}')
            return redirect('material:item_list')

    # GET 請求
    boxes = MaterialOverview.objects.all().order_by('BoxID')
    return render(request, 'material/item_add.html', {'boxes': boxes})


def item_edit(request, item_id):
    """編輯物品"""
    item = get_object_or_404(ItemList, SN=item_id)

    if request.method == 'POST':
        try:
            box_id = request.POST.get('BoxID')
            old_quantity = item.Quantity
            new_quantity = int(request.POST.get('Quantity', 0))

            item.BoxID = get_object_or_404(MaterialOverview, BoxID=box_id)
            item.ItemName = request.POST.get('ItemName')
            item.Spec = request.POST.get('Spec') or None
            item.Location = request.POST.get('Location') or None
            item.Quantity = new_quantity
            item.save()

            # 如果數量有變化，記錄異動
            if old_quantity != new_quantity:
                action_type = '入庫' if new_quantity > old_quantity else '出庫'
                trans_qty = abs(new_quantity - old_quantity)

                TransactionLog.objects.create(
                    SN=item,
                    ActionType=action_type,
                    ToBoxID=box_id if action_type == '入庫' else None,
                    FromBoxID=box_id if action_type == '出庫' else None,
                    TransQty=trans_qty,
                    StockBefore=old_quantity,
                    StockAfter=new_quantity,
                    Operator=request.POST.get('Operator', '系統'),
                    Remark='編輯物品資料'
                )

            messages.success(request, f'物品 {item_id} 更新成功！')
            return redirect('material:item_list')

        except Exception as e:
            messages.error(request, f'更新物品失敗: {str(e)}')
            return redirect('material:item_edit', item_id=item_id)

    boxes = MaterialOverview.objects.all().order_by('BoxID')
    return render(request, 'material/item_edit.html', {
        'item': item,
        'boxes': boxes
    })


def item_delete(request, item_id):
    """刪除物品"""
    if request.method == 'POST':
        try:
            item = get_object_or_404(ItemList, SN=item_id)

            # 記錄刪除前的狀態
            TransactionLog.objects.create(
                SN=item,
                ActionType='出庫',
                FromBoxID=item.BoxID.BoxID,
                TransQty=item.Quantity,
                StockBefore=item.Quantity,
                StockAfter=0,
                Operator=request.POST.get('Operator', '系統'),
                Remark='刪除物品'
            )

            item.delete()
            messages.success(request, f'物品 {item_id} 已刪除')
        except Exception as e:
            messages.error(request, f'刪除物品失敗: {str(e)}')

    return redirect('material:item_list')


# ==================== 調撥功能 ====================

# 替換你 views.py 中的 transaction_transfer 函數

def transaction_transfer(request):
    """物品調撥"""
    if request.method == 'POST':
        try:
            from_box_id = request.POST.get('from_box')
            to_box_id = request.POST.get('to_box')
            item_sn = request.POST.get('item')
            quantity = int(request.POST.get('quantity', 0))
            operator = request.POST.get('operator', '系統')
            remark = request.POST.get('remark', '')

            # 獲取來源和目標容器
            from_box = get_object_or_404(MaterialOverview, BoxID=from_box_id)
            to_box = get_object_or_404(MaterialOverview, BoxID=to_box_id)

            # 檢查容器是否鎖定
            if from_box.Locked:
                messages.error(request, f'來源容器 {from_box_id} 已鎖定，無法調撥')
                return redirect('material:transaction_transfer')

            if to_box.Locked:
                messages.error(request, f'目標容器 {to_box_id} 已鎖定，無法調撥')
                return redirect('material:transaction_transfer')

            # 檢查來源容器中的物品
            try:
                from_item = ItemList.objects.get(SN=item_sn, BoxID=from_box)
            except ItemList.DoesNotExist:
                messages.error(request, f'來源容器中找不到物品 {item_sn}')
                return redirect('material:transaction_transfer')

            if from_item.Quantity < quantity:
                messages.error(request, f'來源容器庫存不足！現有: {from_item.Quantity}，需要: {quantity}')
                return redirect('material:transaction_transfer')

            # 記錄調撥前的庫存
            stock_before = from_item.Quantity
            item_name = from_item.ItemName  # 先保存物品名稱

            # 執行調撥 - 從來源扣除
            from_item.Quantity -= quantity

            # 檢查目標容器是否已有相同物品
            try:
                to_item = ItemList.objects.get(SN=item_sn, BoxID=to_box)
                to_item.Quantity += quantity
                to_item.save()
            except ItemList.DoesNotExist:
                to_item = ItemList.objects.create(
                    SN=item_sn,
                    BoxID=to_box,
                    ItemName=from_item.ItemName,
                    Spec=from_item.Spec,
                    Location=from_item.Location,
                    Quantity=quantity
                )

            # 保存或刪除來源物品
            if from_item.Quantity == 0:
                from_item.delete()
            else:
                from_item.save()

            # 記錄調撥交易
            TransactionLog.objects.create(
                SN=to_item,
                ActionType='調撥',
                FromBoxID=from_box_id,
                ToBoxID=to_box_id,
                TransQty=quantity,
                StockBefore=stock_before,
                StockAfter=from_item.Quantity if from_item.Quantity > 0 else 0,
                Operator=operator,
                Remark=remark or f'從 {from_box_id} 調撥到 {to_box_id}'
            )

            # 加入成功訊息（只有這一行）
            messages.success(request, f'調撥成功！已將 {quantity} 件 {item_name} 從 {from_box_id} 調撥到 {to_box_id}')

            return redirect('material:transaction_transfer')

        except Exception as e:
            messages.error(request, f'調撥失敗: {str(e)}')
            import traceback
            print(traceback.format_exc())
            return redirect('material:transaction_transfer')

    # GET 請求
    boxes = MaterialOverview.objects.filter(Locked=False).order_by('BoxID')
    return render(request, 'material/transaction_transfer.html', {'boxes': boxes})

def transaction_history(request):
    """交易記錄"""
    transactions = TransactionLog.objects.all().select_related(
        'SN', 'SN__BoxID'
    ).order_by('-Timestamp')

    return render(request, 'material/transaction_history.html', {
        'transactions': transactions
    })


# ==================== API ====================

def get_box_items(request, box_id):
    """API: 獲取指定容器內的所有物品"""
    try:
        box = get_object_or_404(MaterialOverview, BoxID=box_id)
        items = ItemList.objects.filter(BoxID=box)

        items_data = [{
            'item_id': item.SN,
            'item_name': item.ItemName,
            'spec': item.Spec or '',
            'quantity': item.Quantity,
            'location': item.Location or ''
        } for item in items]

        return JsonResponse({'items': items_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)



def get_recent_transfers(request):
    """API: 獲取最近的調撥記錄"""
    try:
        transfers = TransactionLog.objects.filter(
            ActionType='調撥'
        ).select_related('SN').order_by('-Timestamp')[:10]

        transfers_data = [{
            'timestamp': transfer.Timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'item_name': transfer.SN.ItemName,
            'quantity': transfer.TransQty,
            'from_box': transfer.FromBoxID,
            'to_box': transfer.ToBoxID,
            'operator': transfer.Operator or '未知'
        } for transfer in transfers]

        return JsonResponse({'transfers': transfers_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)