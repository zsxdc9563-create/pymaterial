# material_app/views/borrow_views.py
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from ..models import BorrowRequest, MaterialItems
from ..serializers import BorrowRequestSerializer
from ..permissions import is_admin, has_role

logger = logging.getLogger(__name__)


class BorrowRequestListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # admin 看全部，一般使用者只看自己的
        if is_admin(request.user):
            requests = BorrowRequest.objects.all().order_by('-created_at')
        else:
            requests = BorrowRequest.objects.filter(
                requester=request.user
            ).order_by('-created_at')
        return Response(BorrowRequestSerializer(requests, many=True).data)

    def post(self, request):
        item = get_object_or_404(MaterialItems, id=request.data.get('item_id'))
        qty = request.data.get('qty')
        expected_return_date = request.data.get('expected_return_date')
        remark = request.data.get('remark', '')

        if not qty or int(qty) <= 0:
            return Response({'error': '借用數量必須大於 0'}, status=status.HTTP_400_BAD_REQUEST)

        borrow = BorrowRequest.objects.create(
            item=item,
            requester=request.user,
            qty=int(qty),
            expected_return_date=expected_return_date or None,
            remark=remark,
        )
        return Response(BorrowRequestSerializer(borrow).data, status=status.HTTP_201_CREATED)


class BorrowRequestApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_admin(request.user):
            return Response({'error': '只有 admin 可以審核'}, status=status.HTTP_403_FORBIDDEN)

        borrow = get_object_or_404(BorrowRequest, pk=pk)
        action = request.data.get('action')

        if borrow.status != 'PENDING':
            return Response({'error': '此申請已審核過'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'approve':
            borrow.status = 'APPROVED'
            borrow.approver = request.user
            borrow.save()
            return Response({'message': '已核准'})
        elif action == 'reject':
            borrow.status = 'REJECTED'
            borrow.approver = request.user
            borrow.save()
            return Response({'message': '已拒絕'})
        else:
            return Response({'error': 'action 必須是 approve 或 reject'}, status=status.HTTP_400_BAD_REQUEST)


class BorrowRequestReturnAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        borrow = get_object_or_404(BorrowRequest, pk=pk)

        if borrow.requester != request.user and not is_admin(request.user):
            return Response({'error': '權限不足'}, status=status.HTTP_403_FORBIDDEN)

        if borrow.status != 'APPROVED':
            return Response({'error': '只有已核准的申請才能歸還'}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        borrow.status = 'RETURNED'
        borrow.actual_return_date = timezone.now().date()
        borrow.save()
        return Response({'message': '已歸還'})