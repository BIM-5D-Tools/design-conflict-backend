from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser,
    Project,
    Zone,
    Floor,
    App,
    UserAppPermission,
    DesignConflict,
)


# Register your models here.
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    ordering = ("email",)

    list_display = ("email", "full_name", "role", "is_staff", "is_superuser")

    search_fields = ("email", "full_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Thông tin cá nhân",
            {"fields": ("full_name", "avatar", "gender", "birthday", "language")},
        ),
        (
            "Quyền hạn",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Ngày tháng", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "id", "created_at")
    filter_horizontal = ("users",)


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "project", "id", "created_at")


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "zone", "id", "created_at")


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_at")
    search_fields = ("name", "code")


@admin.register(UserAppPermission)
class UserAppPermissionAdmin(admin.ModelAdmin):
    list_display = ("user", "app", "permissions", "created_at")
    list_filter = ("app", "user")


@admin.register(DesignConflict)
class DesignConflictAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "project", "status", "created_at")
