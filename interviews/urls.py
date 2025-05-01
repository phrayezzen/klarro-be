from django.urls import include, path
from rest_framework.authtoken import views as token_views
from rest_framework.routers import DefaultRouter

from .views import (
    CandidateViewSet,
    FlowViewSet,
    InterviewViewSet,
    RecruiterViewSet,
    StepViewSet,
    get_current_user,
)

router = DefaultRouter()
router.register(r"candidates", CandidateViewSet)
router.register(r"flows", FlowViewSet)
router.register(r"interviews", InterviewViewSet)
router.register(r"recruiters", RecruiterViewSet)
router.register(r"steps", StepViewSet)

urlpatterns = [
    path("api/v1/", include(router.urls)),
    path("api/v1/token/", token_views.obtain_auth_token),
    path("api/v1/users/me/", get_current_user, name="current-user"),
]
