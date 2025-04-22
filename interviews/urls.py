from django.urls import include, path
from rest_framework import routers
from rest_framework.authtoken import views as token_views

from .views import CandidateViewSet, FlowViewSet, InterviewViewSet, RecruiterViewSet

router = routers.DefaultRouter()
router.register("recruiters", RecruiterViewSet)
router.register("flows", FlowViewSet)
router.register("candidates", CandidateViewSet)
router.register("interviews", InterviewViewSet)

urlpatterns = [
    path("api/v1/", include(router.urls)),
    path("api/v1/token/", token_views.obtain_auth_token),
]
