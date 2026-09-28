from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"projects", views.ProjectViewSet, basename="project")
router.register(r"conflicts", views.DesignConflictViewSet, basename="conflict")
router.register("apps", views.AppViewSet, basename="apps")

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="api_login"),
    path("me/", views.MeView.as_view(), name="api_me"),
    path("", include(router.urls)),
]
