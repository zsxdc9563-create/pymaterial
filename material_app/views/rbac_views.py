# material_app/views/rbac_views.py
import logging

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User

from ..models import Role, Permission, UserRole, RolePermission
from ..serializers import (
    RoleSerializer, PermissionSerializer,
    UserRoleSerializer, RolePermissionSerializer,
)
from ..services.rbac_service import (
    get_all_roles, get_role_or_none, create_role, update_role, delete_role,
    get_all_permissions, get_permission_or_none, create_permission, delete_permission,
    get_all_user_roles, assign_role_to_user, remove_role_from_user,
    get_all_role_permissions, assign_permission_to_role, remove_permission_from_role,
    register_user, send_password_reset_email, reset_password,
)

from rest_framework.permissions import AllowAny
from ..services.rbac_service import register_user

logger = logging.getLogger(__name__)


# ── Role ──────────────────────────────────────────────

class RoleListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(RoleSerializer(get_all_roles(), many=True).data)

    def post(self, request):
        serializer = RoleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            role = create_role(
                name=serializer.validated_data['name'],
                description=serializer.validated_data.get('description'),
            )
            return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RoleDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, role_id):
        role = get_object_or_404(Role, id=role_id)
        return Response(RoleSerializer(role).data)

    def put(self, request, role_id):
        role = get_object_or_404(Role, id=role_id)
        serializer = RoleSerializer(role, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        updated_role = update_role(
            role=role,
            name=serializer.validated_data.get('name', role.name),
            description=serializer.validated_data.get('description'),
        )
        return Response(RoleSerializer(updated_role).data)

    def delete(self, request, role_id):
        role = get_object_or_404(Role, id=role_id)
        delete_role(role)
        return Response({'message': f'角色 {role.name} 已刪除'})


# ── Permission ────────────────────────────────────────

class PermissionListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PermissionSerializer(get_all_permissions(), many=True).data)

    def post(self, request):
        serializer = PermissionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            permission = create_permission(
                name=serializer.validated_data['name'],
                description=serializer.validated_data.get('description'),
            )
            return Response(PermissionSerializer(permission).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, permission_id):
        permission = get_object_or_404(Permission, id=permission_id)
        delete_permission(permission)
        return Response({'message': f'權限 {permission.name} 已刪除'})


# ── UserRole ──────────────────────────────────────────

class UserRoleListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserRoleSerializer(get_all_user_roles(), many=True).data)

    def post(self, request):
        user = get_object_or_404(User, id=request.data.get('user_id'))
        role = get_object_or_404(Role, id=request.data.get('role_id'))
        user_role, created = assign_role_to_user(user, role)
        if not created:
            return Response({'error': '此使用者已有此角色'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserRoleSerializer(user_role).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        user = get_object_or_404(User, id=request.data.get('user_id'))
        role = get_object_or_404(Role, id=request.data.get('role_id'))
        remove_role_from_user(user, role)
        return Response({'message': '角色已移除'})


# ── RolePermission ────────────────────────────────────

class RolePermissionListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(RolePermissionSerializer(get_all_role_permissions(), many=True).data)

    def post(self, request):
        role = get_object_or_404(Role, id=request.data.get('role_id'))
        permission = get_object_or_404(Permission, id=request.data.get('permission_id'))
        role_permission, created = assign_permission_to_role(role, permission)
        if not created:
            return Response({'error': '此角色已有此權限'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RolePermissionSerializer(role_permission).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        role = get_object_or_404(Role, id=request.data.get('role_id'))
        permission = get_object_or_404(Permission, id=request.data.get('permission_id'))
        remove_permission_from_role(role, permission)
        return Response({'message': '權限已移除'})


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]  # 註冊不需要登入

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email', '')

        if not username or not password:
            return Response(
                {'error': '帳號和密碼不能為空'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = register_user(username, password, email)
            return Response(
                {'message': f'帳號 {user.username} 註冊成功'},
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response(
                {'error': 'Email 不能為空'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            send_password_reset_email(email)
            return Response({'message': '重設密碼信件已寄出，請檢查您的信箱'})
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not uid or not token or not new_password:
            return Response(
                {'error': '資料不完整'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            reset_password(uid, token, new_password)
            return Response({'message': '密碼重設成功，請重新登入'})
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth.models import User
        from ..serializers import UserBriefSerializer
        users = User.objects.all().order_by('username')
        return Response(UserBriefSerializer(users, many=True).data)

#  回傳目前登入使用者的角色資訊       
class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from ..services.rbac_service import get_user_roles
        user = request.user
        user_roles = get_user_roles(user)
        role_names = [ur.role.name for ur in user_roles]
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'roles': role_names,
        })        