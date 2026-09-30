# core/views.py

from django.http import HttpResponse
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.authentication import TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import UserAppPermission, App, CustomUser, Project, DesignConflict
from .serializer import (
    AppSerializer,
    UserSerializer,
    ProjectSerializer,
    DesignConflictSerializer,
)
from .services import generate_conflict_excel, generate_conflict_pdf


class HasAppPermission(BasePermission):
    """
    Kiểm tra quyền truy cập app dựa trên UserAppPermission.
    ViewSet chỉ cần khai báo thuộc tính: required_app_code = '<app_code>'
    """
    # Ánh xạ HTTP method sang quyền tương ứng
    METHOD_ACTIONS_MAP = {
        'GET': 'READ',
        'OPTIONS': 'READ',
        'HEAD': 'READ',
        'POST': 'CREATE',
        'PUT': 'UPDATE',
        'PATCH': 'UPDATE',
        'DELETE': 'DELETE',
    }

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Superuser hoặc các vai trò quản trị tối cao luôn được qua
        if user.is_superuser or getattr(user, 'role', None) in ["SUPERUSER", "ADMIN"]:
            return True

        # Lấy app_code được chỉ định ở ViewSet
        app_code = getattr(view, 'required_app_code', None)
        if not app_code:
            return True

        # Tìm quyền của user đối với app đó trong database
        user_perm = UserAppPermission.objects.filter(
            user=user, 
            app__code=app_code
        ).first()

        if not user_perm or not user_perm.permissions:
            return False

        # Chuẩn hóa về chữ in hoa để so sánh chính xác
        user_actions = [p.upper() for p in user_perm.permissions]

        # Nếu user có toàn quyền với app đó
        if "ALL" in user_actions:
            return True

        # Xác định quyền cần thiết dựa theo phương thức HTTP
        required_action = self.METHOD_ACTIONS_MAP.get(request.method)
        if required_action and required_action in user_actions:
            return True

        return False


class IsAdminOrSuperuser(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_superuser or getattr(request.user, 'role', None) in ["SUPERUSER", "ADMIN"]


class AppViewSet(ModelViewSet):
    queryset = App.objects.all().order_by("-created_at")
    serializer_class = AppSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, HasAppPermission]
    required_app_code = "app"


class LoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(email=email, password=password)

        if not user:
            return Response(
                {"message": "Tên tài khoản hoặc mật khẩu không chính xác!"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=user)

        apps_data = []

        if user.is_superuser or user.role in ["SUPERUSER", "ADMIN"]:
            all_apps = App.objects.all()
            apps_data = [{"code": app.code, "permissions": ["ALL"]} for app in all_apps]
        else:
            user_perms = UserAppPermission.objects.filter(user=user).select_related("app")
            for perm in user_perms:
                apps_data.append(
                    {"code": perm.app.code, "permissions": perm.permissions}
                )

        return Response(
            {
                "token": token.key,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name or user.email,
                    "role": user.role,
                    "apps": apps_data,
                },
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        apps_data = []

        if user.is_superuser or user.role in ["SUPERUSER", "ADMIN"]:
            all_apps = App.objects.all()
            apps_data = [{"code": app.code, "permissions": ["ALL"]} for app in all_apps]
        else:
            user_perms = UserAppPermission.objects.filter(user=user).select_related("app")
            for perm in user_perms:
                apps_data.append(
                    {"code": perm.app.code, "permissions": perm.permissions}
                )

        avatar_url = (
            request.build_absolute_uri(user.avatar.url) if user.avatar else None
        )

        return Response(
            {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "avatar": avatar_url,
                "gender": user.gender,
                "birthday": user.birthday,
                "language": user.language,
                "is_superuser": user.is_superuser,
                "apps": apps_data,
            }
        )


class UserViewSet(ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, HasAppPermission]
    required_app_code = "user_management"  # Kiểm tra quyền trên app quản lý người dùng
    
    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]
    queryset = CustomUser.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer

    @action(detail=True, methods=["post"], url_path="update-app-permissions")
    def update_app_permissions(self, request, pk=None):
        user = self.get_object()

        app_ids = request.data.get("apps", [])
        permissions_data = request.data.get("permissions", [])

        user.apps.set(app_ids)

        UserAppPermission.objects.filter(user=user).exclude(app_id__in=app_ids).delete()

        for item in permissions_data:
            app_id = item.get("app_id")
            actions = item.get("actions", [])
            if app_id in app_ids:
                UserAppPermission.objects.update_or_create(
                    user=user, app_id=app_id, defaults={"permissions": actions}
                )

        return Response(
            {"message": "Cập nhật phân quyền thành công!"}, status=status.HTTP_200_OK
        )


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = "page_size"
    max_page_size = 100


class ProjectViewSet(ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, HasAppPermission]
    required_app_code = "project"  # Mã code của App Project trong database (vd: 'project' hoặc 'project_management')

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = Project.objects.all().order_by("-created_at")
    serializer_class = ProjectSerializer

    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = ["name", "code"]
    ordering_fields = ["created_at", "name", "code"]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_update(serializer)
        return Response(serializer.data)


class DesignConflictViewSet(ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, HasAppPermission]
    required_app_code = "design_conflict"  # Thay đúng bằng app code trong bảng App của bạn

    queryset = DesignConflict.objects.all().order_by("-created_at")
    serializer_class = DesignConflictSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    filterset_fields = {
        'project': ['exact'],
        'status': ['exact'],
        'zone': ['exact'],
        'created_at': ['gte', 'lte'],
    }

    @action(detail=False, methods=["get"], url_path="export-report")
    def export_report(self, request):
        if getattr(request.user, "role", None) == "CUSTOMER":
            raise PermissionDenied(
                "Tài khoản Khách hàng không có quyền xuất file báo cáo!"
            )

        queryset = self.filter_queryset(self.get_queryset())

        project_id = request.query_params.get("project")
        project_obj = (
            Project.objects.filter(id=project_id).first() if project_id else None
        )
        export_type = request.query_params.get("type", "excel").lower()

        base_filename = (
            f"Bao_Cao_Xung_Dot_{project_obj.code if project_obj else 'Tong_Hop'}"
        )

        if export_type == "pdf":
            pdf_file = generate_conflict_pdf(queryset, project_obj=project_obj)
            response = HttpResponse(pdf_file.getvalue(), content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="{base_filename}.pdf"'
            )
            return response
        else:
            excel_file = generate_conflict_excel(queryset, project_obj=project_obj)
            response = HttpResponse(
                excel_file.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = (
                f'attachment; filename="{base_filename}.xlsx"'
            )
            return response