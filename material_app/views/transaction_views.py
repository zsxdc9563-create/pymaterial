# material_app/views/transaction_views.py
import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ..serializers import TransactionLogSerializer
from ..services.transaction_service import (
    get_all_transactions, get_transaction_stats,
    get_items_by_box, get_recent_transfers,
    get_unlocked_boxes, transfer_item,
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
        'is_admin':          request.user.groups.filter(name='admin').exists() if is_auth else False,
        'is_manager':        request.user.groups.filter(name='manager').exists() if is_auth else False,
        'is_employee':       request.user.groups.filter(name='emp').exists() if is_auth else False,
    }


# ════════════════════════════════════════════════════════
# 頁面路由（回傳 HTML）
# 待 React 前端完成後可整段移除
# ════════════════════════════════════════════════════════

@login_required
def transaction_transfer(request):
    """
    物品調撥頁面。

    舊版：operator_id 傳字串
    新版：operator 傳 User 物件（對應新 models FK）
    """
    ctx = _get_user_context(request)

    if request.method == 'POST':
        try:
            transfer_item(
                from_box_id = request.POST.get('from_box'),
                to_box_id   = request.POST.get('to_box'),
                item_sn     = request.POST.get('item'),
                quantity    = int(request.POST.get('quantity', 0)),
                # 舊版：operator_id=ctx['current_user_id']（字串）
                # 新版：operator=request.user（User 物件）
                operator    = request.user,
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


@login_required
def transaction_history(request):
    """
    交易記錄頁面。

    舊版：無 @login_required
    新版：加上登入保護
    """
    return render(request, 'material/transaction_history.html', {
        'transactions': get_all_transactions(),
        'stats':        get_transaction_stats(),
    })


# ════════════════════════════════════════════════════════
# API 路由（回傳 JSON，給 React 前端用）
# ════════════════════════════════════════════════════════

class TransactionListAPIView(APIView):
    """
    GET /api/transactions/  → 取得交易記錄清單

    支援篩選參數：
      ?action_type=OUT
      ?from_box=BOX001
      ?operator=username

    舊版：@api_view(['GET']) api_transaction_list，無驗證
    新版：APIView class + IsAuthenticated
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = get_all_transactions(
            action_type = request.query_params.get('action_type'),
            from_box    = request.query_params.get('from_box'),
            # 舊版：operator 傳字串查詢
            # 新版：傳 username，service 再轉成 User FK 查詢
            operator    = request.query_params.get('operator'),
        )
        return Response(TransactionLogSerializer(qs, many=True).data)


class TransactionStatsAPIView(APIView):
    """
    GET /api/transactions/stats/  → 取得交易統計資料

    供 dashboard 或報表用。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_transaction_stats())


class TransferAPIView(APIView):
    """
    POST /api/transactions/transfer/  → 物品調撥

    body:
    {
        "from_box_id": "BOX001",
        "to_box_id":   "BOX002",
        "item_sn":     "R0001",
        "quantity":    5,
        "remark":      "備註"
    }

    舊版：無對應 API（只有頁面路由）
    新版：新增 API，operator 從 JWT token 取得
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        required_fields = ['from_box_id', 'to_box_id', 'item_sn', 'quantity']
        missing = [f for f in required_fields if not request.data.get(f)]
        if missing:
            return Response(
                {'error': f'缺少必填欄位：{", ".join(missing)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            transfer_item(
                from_box_id = request.data['from_box_id'],
                to_box_id   = request.data['to_box_id'],
                item_sn     = request.data['item_sn'],
                quantity    = int(request.data['quantity']),
                operator    = request.user,
                remark      = request.data.get('remark', ''),
            )
            return Response({'message': '調撥成功'})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)