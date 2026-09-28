import json
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from .models import (
    App,
    UserAppPermission,
    CustomUser,
    Floor,
    Zone,
    Project,
    DesignConflict,
    ConflictImage,
)

User = get_user_model()


class AppSerializer(serializers.ModelSerializer):
    class Meta:
        model = App
        fields = ["id", "code", "name", "description", "created_at", "updated_at"]


class UserAppPermissionSerializer(serializers.ModelSerializer):
    app_code = serializers.CharField(source="app.code", read_only=True)
    app_name = serializers.CharField(source="app.name", read_only=True)

    class Meta:
        model = UserAppPermission
        fields = ["id", "user", "app", "app_code", "app_name", "permissions"]


class UserSerializer(serializers.ModelSerializer):
    apps_detail = AppSerializer(source="apps", many=True, read_only=True)
    app_permissions = UserAppPermissionSerializer(many=True, read_only=True)

    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "full_name",
            "role",
            "apps",
            "apps_detail",
            "avatar",
            "gender",
            "birthday",
            "language",
            "apps",
            "apps_detail",
            "app_permissions",
            "is_superuser",
            "is_active",
            "password",
            "created_at" if hasattr(CustomUser, "created_at") else "date_joined",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = CustomUser(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class FloorSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)

    class Meta:
        model = Floor
        fields = ["id", "name", "code"]


class ZoneSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    floors = FloorSerializer(many=True, required=False)

    class Meta:
        model = Zone
        fields = ["id", "name", "code", "floors"]


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "avatar", "email", "full_name"]


class ProjectSerializer(serializers.ModelSerializer):
    zones = ZoneSerializer(many=True, required=False)
    image = serializers.ImageField(required=False, allow_null=True)
    users_detail = UserSimpleSerializer(source="users", many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "code",
            "image",
            "address",
            "created_at",
            "updated_at",
            "zones",
            "users",
            "users_detail",
        ]
        extra_kwargs = {"code": {"validators": []}, "users": {"required": False}}

    def _ensure_superusers(self, user_ids):
        superuser_ids = list(
            User.objects.filter(is_superuser=True).values_list("id", flat=True)
        )

        if isinstance(user_ids, list):
            existing_set = set(user_ids)
            for su_id in superuser_ids:
                existing_set.add(su_id)
            return list(existing_set)
        return superuser_ids

    def validate_code(self, value):
        instance = getattr(self, "instance", None)
        if (
            Project.objects.filter(code=value)
            .exclude(id=getattr(instance, "id", None))
            .exists()
        ):
            raise serializers.ValidationError("Mã dự án này đã tồn tại!")
        return value

    def run_validation(self, data=serializers.empty):
        if data is not serializers.empty:
            # Lấy request từ context
            request = self.context.get("request")

            data_dict = {}

            if hasattr(data, "items"):
                for key, val in data.items():
                    data_dict[key] = val

            if request and request.FILES and "image" in request.FILES:
                data_dict["image"] = request.FILES["image"]
            elif "image" in data_dict and not isinstance(
                data_dict["image"], serializers.PKOnlyObject
            ):
                if not data_dict["image"] or isinstance(data_dict["image"], str):
                    data_dict.pop("image", None)

            zones_val = data_dict.get("zones")
            if isinstance(zones_val, str):
                try:
                    data_dict["zones"] = json.loads(zones_val)
                except Exception:
                    data_dict["zones"] = []

            users_val = data_dict.get("users")
            if isinstance(users_val, str):
                try:
                    data_dict["users"] = json.loads(users_val)
                except Exception:
                    data_dict["users"] = []

            data = data_dict

        return super().run_validation(data)

    def create(self, validated_data):
        zones_data = validated_data.pop("zones", [])
        users_data = validated_data.pop("users", [])

        users_data = self._ensure_superusers(users_data)

        project = Project.objects.create(**validated_data)

        project.users.set(users_data)

        for z in zones_data:
            floors_data = z.pop("floors", [])
            z.pop("id", None)
            zone = Zone.objects.create(
                project=project, name=z.get("name", ""), code=z.get("code", "")
            )
            for f in floors_data:
                f.pop("id", None)
                Floor.objects.create(
                    zone=zone, name=f.get("name", ""), code=f.get("code", "")
                )

        return project

    def update(self, instance, validated_data):
        zones_data = validated_data.pop("zones", None)
        users_data = validated_data.pop("users", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if users_data is not None:
            users_data = self._ensure_superusers(users_data)
            instance.users.set(users_data)

        if zones_data is not None:
            instance.zones.all().delete()

            for z in zones_data:
                floors_data = z.pop("floors", [])
                z.pop("id", None)
                zone = Zone.objects.create(
                    project=instance, name=z.get("name", ""), code=z.get("code", "")
                )
                for f in floors_data:
                    f.pop("id", None)
                    Floor.objects.create(
                        zone=zone, name=f.get("name", ""), code=f.get("code", "")
                    )

        return instance


class ConflictImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConflictImage
        fields = ["id", "image", "uploaded_at"]


class DesignConflictSerializer(serializers.ModelSerializer):
    images = ConflictImageSerializer(many=True, read_only=True)

    class Meta:
        model = DesignConflict
        fields = [
            "id",
            "project",
            "zone",
            "floor",
            "code",
            "name",
            "category",
            "axis",
            "description",
            "solution",
            "comment",
            "status",
            "images",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        conflict = DesignConflict.objects.create(**validated_data)

        if request and request.FILES:
            images_data = request.FILES.getlist("images")
            for img in images_data:
                ConflictImage.objects.create(conflict=conflict, image=img)

        return conflict

    def update(self, instance, validated_data):
        request = self.context.get("request")

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if request and request.FILES:
            images_data = request.FILES.getlist("images")
            for img in images_data:
                ConflictImage.objects.create(conflict=instance, image=img)

        return instance
