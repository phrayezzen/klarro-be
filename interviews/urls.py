from django.urls import include, path
from rest_framework.authtoken import views as token_views
from rest_framework.routers import DefaultRouter

from .views import (
    CandidateViewSet,
    CompanyViewSet,
    FlowViewSet,
    InterviewViewSet,
    RecruiterViewSet,
    StepViewSet,
    evaluate_interview,
    get_chat_updates,
    get_csrf_token,
    get_current_user,
    interview_respond,
    save_interview_transcript,
    send_message,
    text_to_speech,
)

router = DefaultRouter()
router.register(r"companies", CompanyViewSet)
router.register(r"candidates", CandidateViewSet)
router.register(r"flows", FlowViewSet)
router.register(r"interviews", InterviewViewSet)
router.register(r"recruiters", RecruiterViewSet)
router.register(r"steps", StepViewSet)

urlpatterns = [
    path("api/v1/", include(router.urls)),
    path("api/v1/token/", token_views.obtain_auth_token),
    path("api/v1/users/me/", get_current_user, name="current-user"),
    path("api/v1/chat/message/", send_message, name="send-message"),
    path("api/v1/chat/updates/", get_chat_updates, name="chat-updates"),
    path("api/v1/interview/respond/", interview_respond, name="interview-respond"),
    path("api/v1/interview/tts/", text_to_speech, name="text-to-speech"),
    path("api/v1/csrf/", get_csrf_token, name="csrf-token"),
    path(
        "api/v1/interviews/save-transcript/",
        save_interview_transcript,
        name="save-transcript",
    ),
    path("api/v1/interviews/evaluate/", evaluate_interview, name="evaluate-interview"),
]
