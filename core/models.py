import os
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class App(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        SUPERUSER = "SUPERUSER", "Superuser"
        ADMIN = "ADMIN", "Admin"
        STAFF = "STAFF", "Staff"
        CUSTOMER = "CUSTOMER", "Customer"

    class Gender(models.TextChoices):
        MALE = "MALE", "Nam"
        FEMALE = "FEMALE", "Nữ"
        OTHER = "OTHER", "Khác"

    class Language(models.TextChoices):
        VI = "vi", "Tiếng Việt"
        EN = "en", "English"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=False, null=True, blank=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    avatar = models.ImageField(upload_to="users/images/", blank=True, null=True)
    gender = models.CharField(
        max_length=10, choices=Gender.choices, default=Gender.OTHER
    )
    birthday = models.DateField(blank=True, null=True)
    language = models.CharField(
        max_length=10, choices=Language.choices, default=Language.VI
    )

    apps = models.ManyToManyField(App, related_name="users", blank=True)

    def has_app_access(self, app_code):
        if self.is_superuser or self.role == "SUPERUSER":
            return True
        return self.apps.filter(code=app_code, is_active=True).exists()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.email} ({self.role})"


class UserAppPermission(BaseModel):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="app_permissions"
    )
    app = models.ForeignKey(
        App, on_delete=models.CASCADE, related_name="user_permissions"
    )

    permissions = models.JSONField(default=list)

    class Meta:
        unique_together = ("user", "app")

    def __str__(self):
        return f"{self.user.username} -> {self.app.code}: {self.permissions}"


class Project(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    image = models.ImageField(upload_to="projects/image/", blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    users = models.ManyToManyField(
        CustomUser, related_name="allowed_projects", blank=True
    )

    def __str__(self):
        return self.name


class Zone(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="zones")

    def __str__(self):
        return f"{self.name} - {self.project.name}"


class Floor(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="floors")

    def __str__(self):
        return f"{self.name} - {self.zone.name}"


class DesignConflict(BaseModel):
    STATUS_CHOICES = (
        ("NEW", "Mới"),
        ("PENDING", "Chờ"),
        ("DONE", "Xong"),
    )

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="conflicts"
    )
    zone = models.ForeignKey(
        Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name="conflicts"
    )
    floor = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conflicts",
    )

    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, null=True, blank=True)
    axis = models.CharField(max_length=255, null=True, blank=True)

    description = models.TextField(null=True, blank=True)
    solution = models.TextField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NEW")

    def __str__(self):
        return f"[{self.code}] {self.name}"


class ConflictImage(models.Model):
  conflict = models.ForeignKey(
      DesignConflict, on_delete=models.CASCADE, related_name="images"
  )
  image = models.ImageField(upload_to="conflicts/images/")
  uploaded_at = models.DateTimeField(auto_now_add=True)
