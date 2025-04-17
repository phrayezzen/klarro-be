from django.urls import path, include
from rest_framework import routers
from .views import (
    CompanyViewSet, CandidateViewSet, FlowViewSet,
    StepViewSet, InterviewViewSet, RecruiterViewSet
)

router = routers.DefaultRouter()
router.register('companies', CompanyViewSet)
router.register('recruiters', RecruiterViewSet)
router.register('candidates', CandidateViewSet)
router.register('flows', FlowViewSet)
router.register('steps', StepViewSet)
router.register('interviews', InterviewViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
