from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import MaterialOverview, ItemList, TransactionLog


# ==================== 容器 CRUD ====================

def box_list(request):
    """容器列表"""
    boxes = MaterialOverview.objects.all().order_by('-CreateDate')
    items = ItemList.objects.all().select_related('BoxID').order_by('SN')  # ← 新增：傳物品列表給入庫 Modal
    return render(request, 'material/box_list.html', {
        'boxes': boxes,
        'items': items,
    })


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

            items_count = ItemList.objects.filter(BoxID=box).count()
            if items_count > 0:
                messages.error(request, f'容器 {box_id} 內還有 {items_count} 個物品，無法刪除！請先清空容器。')
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
            action = request.POST.get('action')  # 'lock' or 'unlock'

            box = get_object_or_404(MaterialOverview, BoxID=box_id)

            # ── 將來加權限判斷的位置 ──
            # if not has_lock_permission(request.user):
            #     messages.error(request, '您沒有鎖定/解鎖的權限')
            #     return redirect('material:box_list')

            if action == 'lock':
                if box.Locked:
                    messages.warning(request, f'容器 {box_id} 已經是鎖定狀態')
                else:
                    box.Locked = True
                    box.save()
                    messages.success(request, f'容器 {box_id} 已鎖定')

            elif action == 'unlock':
                if not box.Locked:
                    messages.warning(request, f'容器 {box_id} 已經是未鎖定狀態')
                else:
                    box.Locked = False
                    box.save()
                    messages.success(request, f'容器 {box_id} 已解鎖')

            else:
                messages.error(request, '無效的操作')

        except Exception as e:
            messages.error(request, f'鎖定操作失敗: {str(e)}')

    return redirect('material:box_list')



def box_checkin(request):
    """入庫：將選定的物品數量累加到指定容器"""
    if request.method == 'POST':
        try:
            box_id = request.POST.get('BoxID')
            selected_items = request.POST.getlist('selected_items')  # 勾選的物品序號（可多筆）

            if not box_id:
                messages.error(request, '未指定目標容器')
                return redirect('material:box_list')

            # 確認目標容器存在
            target_box = get_object_or_404(MaterialOverview, BoxID=box_id)

            # 檢查容器是否鎖定
            if target_box.Locked:
                messages.error(request, f'容器 {box_id} 已鎖定，無法入庫')
                return redirect('material:box_list')

            if not selected_items:
                messages.warning(request, '沒有選擇任何物品')
                return redirect('material:box_list')

            success_count = 0

            for sn in selected_items:
                qty = int(request.POST.get(f'qty_{sn}', 0))
                if qty <= 0:
                    continue

                # 找到來源物品（原本在哪個容器）
                try:
                    source_item = ItemList.objects.get(SN=sn)
                except ItemList.DoesNotExist:
                    messages.warning(request, f'物品序號 {sn} 不存在，已跳過')
                    continue

                original_box_id = source_item.BoxID.BoxID
                stock_before = source_item.Quantity

                # ── 情況一：物品本身就在目標容器，直接累加 ──
                if source_item.BoxID == target_box:
                    source_item.Quantity += qty
                    source_item.save()

                    TransactionLog.objects.create(
                        SN=source_item,
                        ActionType='入庫',
                        ToBoxID=box_id,
                        TransQty=qty,
                        StockBefore=stock_before,
                        StockAfter=source_item.Quantity,
                        Operator='系統',
                        Remark=f'從容器列表入庫'
                    )
                    success_count += 1
                    continue

                # ── 情況二：物品在其他容器，視為調撥 ──
                # 檢查目標容器裡是否已有同一序號的物品
                try:
                    target_item = ItemList.objects.get(SN=sn, BoxID=target_box)
                    target_item.Quantity += qty
                    target_item.save()
                except ItemList.DoesNotExist:
                    # 目標容器沒有，複製一筆過來
                    target_item = ItemList.objects.create(
                        SN=sn,
                        BoxID=target_box,
                        ItemName=source_item.ItemName,
                        Spec=source_item.Spec,
                        Location=source_item.Location,
                        Quantity=qty
                    )

                # 來源容器扣減
                source_item.Quantity -= qty
                if source_item.Quantity <= 0:
                    source_item.delete()
                else:
                    source_item.save()

                # 記錄調撥
                TransactionLog.objects.create(
                    SN=target_item,
                    ActionType='調撥',
                    FromBoxID=original_box_id,
                    ToBoxID=box_id,
                    TransQty=qty,
                    StockBefore=stock_before,
                    StockAfter=target_item.Quantity,
                    Operator='系統',
                    Remark=f'從容器列表入庫（來源：{original_box_id}）'
                )
                success_count += 1

            if success_count > 0:
                messages.success(request, f'成功入庫 {success_count} 個物品到容器 {box_id}')
            else:
                messages.warning(request, '沒有有效的物品入庫')

        except Exception as e:
            messages.error(request, f'入庫失敗: {str(e)}')

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

            if ItemList.objects.filter(SN=sn).exists():
                messages.error(request, f'物品序號 {sn} 已存在')
                return redirect('material:item_list')

            box = get_object_or_404(MaterialOverview, BoxID=box_id)

            item = ItemList.objects.create(
                SN=sn,
                BoxID=box,
                ItemName=item_name,
                Spec=spec if spec else None,
                Location=location if location else None,
                Quantity=quantity
            )

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
            # 用 HttpResponseRedirect 直接指定 URL，避免帶參數導致訊息重複
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect('/material/items/')

        except Exception as e:
            messages.error(request, f'新增物品失敗: {str(e)}')
            return redirect('material:item_list')

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

def transaction_transfer(request):
    """物品調撥"""
    if request.method == 'POST':
        # ... POST 的部分完全不動 ...
        try:
            from_box_id = request.POST.get('from_box')
            to_box_id = request.POST.get('to_box')
            item_sn = request.POST.get('item')
            quantity = int(request.POST.get('quantity', 0))
            operator = request.POST.get('operator', '系統')
            remark = request.POST.get('remark', '')

            from_box = get_object_or_404(MaterialOverview, BoxID=from_box_id)
            to_box = get_object_or_404(MaterialOverview, BoxID=to_box_id)

            if from_box.Locked:
                messages.error(request, f'來源容器 {from_box_id} 已鎖定，無法調撥')
                return redirect('material:transaction_transfer')

            if to_box.Locked:
                messages.error(request, f'目標容器 {to_box_id} 已鎖定，無法調撥')
                return redirect('material:transaction_transfer')

            try:
                from_item = ItemList.objects.get(SN=item_sn, BoxID=from_box)
            except ItemList.DoesNotExist:
                messages.error(request, f'來源容器中找不到物品 {item_sn}')
                return redirect('material:transaction_transfer')

            if from_item.Quantity < quantity:
                messages.error(request, f'來源容器庫存不足！現有: {from_item.Quantity}，需要: {quantity}')
                return redirect('material:transaction_transfer')

            stock_before = from_item.Quantity
            item_name = from_item.ItemName

            from_item.Quantity -= quantity

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

            if from_item.Quantity == 0:
                from_item.delete()
            else:
                from_item.save()

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

            messages.success(request, f'調撥成功！已將 {quantity} 件 {item_name} 從 {from_box_id} 調撥到 {to_box_id}')
            return redirect('material:transaction_transfer')

        except Exception as e:
            messages.error(request, f'調撥失敗: {str(e)}')
            import traceback
            print(traceback.format_exc())
            return redirect('material:transaction_transfer')

    # ===== GET：讀取參數來預填充，沒有參數的話就是空的 =====
    pre_sn = request.GET.get('sn', '')
    pre_source_box = request.GET.get('source_box', '')
    pre_item = ItemList.objects.filter(SN=pre_sn).first() if pre_sn else None

    boxes = MaterialOverview.objects.filter(Locked=False).order_by('BoxID')
    return render(request, 'material/transaction_transfer.html', {
        'boxes': boxes,
        'pre_sn': pre_sn,                 # 預填充物品序號
        'pre_source_box': pre_source_box, # 預填充來源容器
        'pre_item': pre_item,             # 預填充物品物件（帶有數量等資訊）
    })

def transaction_history(request):
    """交易記錄"""
    transactions = TransactionLog.objects.all().select_related(
        'SN', 'SN__BoxID'
    ).order_by('-Timestamp')

    # 統計卡片 — 直接用 ORM filter，不需要額外引進 service
    stats = {
        'total':    transactions.count(),
        'checkin':  transactions.filter(ActionType='入庫').count(),
        'checkout': transactions.filter(ActionType='出庫').count(),
        'transfer': transactions.filter(ActionType='調撥').count(),
    }

    return render(request, 'material/transaction_history.html', {
        'transactions': transactions,
        'stats': stats,
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