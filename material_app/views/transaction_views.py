# material_app/views/transaction_views.py
import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..serializers import TransactionLogSerializer
from ..services.transaction_service import (
    get_all_transactions, get_transaction_stats,
    get_items_by_box, get_recent_transfers,
    get_unlocked_boxes, transfer_item,
)

from django.contrib.auth.decorators import login_required
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
def transaction_transfer(request):
    ctx = _get_user_context(request)

    if request.method == 'POST':
        try:
            transfer_item(
                from_box_id = request.POST.get('from_box'),
                to_box_id   = request.POST.get('to_box'),
                item_sn     = request.POST.get('item'),
                quantity    = int(request.POST.get('quantity', 0)),
                operator_id = ctx['current_user_id'],
                remark      = request.POST.get('remark', ''),
            )
            messages.success(request, '調撥成功！')
            return redirect('material:transaction_transfer')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'失敗: {str(e)}')

    ctx.update({
        'boxes':                    get_unlocked_boxes(),
        'pre_sn':                   request.GET.get('sn', ''),
        'pre_source_box':           request.GET.get('source_box', ''),
        'pre_location':             request.GET.get('location', ''),
        'items_by_box':             get_items_by_box(),
        'recent_transfers_payload': get_recent_transfers(),
    })
    return render(request, 'material/transaction_transfer.html', ctx)


def transaction_history(request):
    transactions = get_all_transactions()
    return render(request, 'material/transaction_history.html', {
        'transactions': transactions,
        'stats':        get_transaction_stats(),
    })


# ════════════════════════════════════════════════════════
# API 路由（回傳 JSON）
# ════════════════════════════════════════════════════════

@api_view(['GET'])
def api_transaction_list(request):
    qs = get_all_transactions(
        action_type = request.query_params.get('action_type'),
        from_box    = request.query_params.get('from_box'),
        operator    = request.query_params.get('operator'),
    )
    return Response(TransactionLogSerializer(qs, many=True).data)