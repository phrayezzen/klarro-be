from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.db import models
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Candidate, Company, Flow, Interview, Recruiter, Step
from .permissions import IsCompanyMember, IsRecruiter
from .serializers import (
    CandidateSerializer,
    CompanySerializer,
    FlowSerializer,
    InterviewSerializer,
    RecruiterSerializer,
    StepSerializer,
)
from .services.ai_service import handle_message
from .services.interview_service import generate_interview_response
from .services.tts_service import text_to_speech as convert_to_speech


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated, IsRecruiter, IsCompanyMember]

    def get_queryset(self):
        return Company.objects.filter(id=self.request.user.recruiter.company_id)


class StepViewSet(viewsets.ModelViewSet):
    queryset = Step.objects.all()
    serializer_class = StepSerializer
    permission_classes = [IsAuthenticated, IsRecruiter, IsCompanyMember]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(flow__company_id=self.request.user.recruiter.company_id)

    def perform_create(self, serializer):
        flow_id = self.request.data.get("flow")
        flow = Flow.objects.get(id=flow_id)
        if flow.company_id != self.request.user.recruiter.company_id:
            raise PermissionDenied("You can only create steps for your company's flows")
        serializer.save()


class RecruiterViewSet(viewsets.ModelViewSet):
    queryset = Recruiter.objects.all()
    serializer_class = RecruiterSerializer
    permission_classes = [IsAuthenticated, IsRecruiter, IsCompanyMember]

    def get_queryset(self):
        return Recruiter.objects.filter(
            company_id=self.request.user.recruiter.company_id
        )


class FlowViewSet(viewsets.ModelViewSet):
    queryset = Flow.objects.all()
    serializer_class = FlowSerializer
    permission_classes = [IsAuthenticated, IsRecruiter, IsCompanyMember]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["role_name", "role_function", "location", "created_at"]
    ordering = ["-created_at"]
    pagination_class = LimitOffsetPagination

    def get_paginator(self):
        paginator = super().get_paginator()
        paginator.default_limit = 10
        return paginator

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(company_id=self.request.user.recruiter.company_id)

    def perform_create(self, serializer):
        serializer.save(
            recruiter=self.request.user.recruiter,
            company_id=self.request.user.recruiter.company_id,
        )

    def perform_update(self, serializer):
        if (
            "company" in self.request.data
            and self.request.data["company"] != self.request.user.recruiter.company_id
        ):
            raise PermissionDenied("You can only update flows within your company")
        serializer.save()

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        flow = self.get_object()
        flow.is_active = not flow.is_active
        flow.save()
        serializer = self.get_serializer(flow)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"])
    def steps(self, request, pk=None):
        flow = self.get_object()
        if request.method == "GET":
            steps = flow.steps.all()
            serializer = StepSerializer(steps, many=True)
            return Response(serializer.data)
        elif request.method == "POST":
            serializer = StepSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(flow=flow)
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)

    @action(detail=True, methods=["get"])
    def candidates(self, request, pk=None):
        flow = self.get_object()
        candidates = flow.candidates.all()
        serializer = CandidateSerializer(candidates, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            raise


class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    permission_classes = [IsAuthenticated, IsRecruiter, IsCompanyMember]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["first_name", "last_name", "status", "created_at"]
    ordering = ["created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        flow_id = self.request.query_params.get("flow_id")
        if flow_id:
            queryset = queryset.filter(flow_id=flow_id)
        # Only filter by company if the candidate has a flow assigned
        return queryset.filter(
            models.Q(flow__company_id=self.request.user.recruiter.company_id)
            | models.Q(flow__isnull=True)
        )

    def get_object(self):
        return super().get_object()

    @action(detail=True, methods=["get"])
    def interviews(self, request, pk=None):
        candidate = self.get_object()
        interviews = candidate.interviews.all()
        serializer = InterviewSerializer(interviews, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            raise


class InterviewViewSet(viewsets.ModelViewSet):
    """ViewSet for managing interviews."""

    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get interviews for the current user."""
        return Interview.objects.filter(interviewer__user=self.request.user)

    def perform_create(self, serializer):
        """Create a new interview."""
        serializer.save(interviewer=self.request.user.recruiter)

    def perform_update(self, serializer):
        """Update an interview."""
        if serializer.instance.interviewer.user != self.request.user:
            raise PermissionDenied(
                "You don't have permission to update this interview."
            )
        serializer.save()

    def perform_destroy(self, instance):
        """Delete an interview."""
        if instance.interviewer.user != self.request.user:
            raise PermissionDenied(
                "You don't have permission to delete this interview."
            )
        instance.delete()

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        """Update the status of an interview."""
        interview = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return Response({"error": "status is required"}, status=400)

        if new_status not in dict(Interview.STATUS_CHOICES):
            return Response({"error": "Invalid status"}, status=400)

        interview.status = new_status
        if new_status == "completed":
            interview.completed_at = timezone.now()
        interview.save()

        serializer = self.get_serializer(interview)
        return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get the current authenticated user's data."""
    print("get_current_user called")
    print("User:", request.user)
    print("Auth header:", request.headers.get("Authorization"))
    try:
        serializer = RecruiterSerializer(request.user.recruiter)
        print("Serialized data:", serializer.data)
        response = Response(serializer.data)
        print("Response created:", response)
        return response
    except Exception as e:
        print("Error in get_current_user:", str(e))
        raise


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_message(request):
    """Send a message to the AI assistant."""
    try:
        message = request.data.get("message", "").strip()
        if not message:
            return Response(
                {"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get current user and company
        recruiter = request.user.recruiter
        company = recruiter.company

        # Store user message in session
        messages = request.session.get("messages", [])
        user_message = {
            "id": timezone.now().timestamp(),
            "text": message,
            "sender": "user",
            "timestamp": timezone.now().isoformat(),
        }
        messages.append(user_message)
        request.session["messages"] = messages

        # Let GPT handle the message using async_to_sync
        response_text, flow, flow_details, redirect_to = async_to_sync(handle_message)(
            message=message,
            company=company,
            recruiter=recruiter,
        )

        # Store assistant response in session
        assistant_message = {
            "id": timezone.now().timestamp() + 1,
            "text": response_text,
            "sender": "assistant",
            "timestamp": timezone.now().isoformat(),
        }
        messages.append(assistant_message)
        request.session["messages"] = messages

        # Prepare response
        response_data = {
            "message": assistant_message,
        }

        # Add flow details if available
        if flow:
            # Add success message about flow creation
            success_message = {
                "id": timezone.now().timestamp() + 2,
                "text": f"I've created an interview flow for {flow.role_name}. You can review and edit it if needed.",
                "sender": "assistant",
                "timestamp": timezone.now().isoformat(),
            }
            messages.append(success_message)
            request.session["messages"] = messages

            response_data.update(
                {
                    "flow": FlowSerializer(flow).data,
                    "success_message": success_message,
                    "redirect_to": f"/flows/{flow.id}/edit",  # Frontend will handle this
                }
            )
        elif flow_details:
            # Add message about needing more details
            details_message = {
                "id": timezone.now().timestamp() + 2,
                "text": "I need some more information to create the flow. Please answer these questions:",
                "sender": "assistant",
                "timestamp": timezone.now().isoformat(),
            }
            messages.append(details_message)
            request.session["messages"] = messages

            response_data.update(
                {
                    "flow_details": {
                        "context": flow_details.context,
                        "questions": flow_details.questions,
                    },
                    "details_message": details_message,
                }
            )
        elif redirect_to:
            # Add redirect_to to response if provided
            response_data["redirect_to"] = redirect_to

        return Response(response_data)

    except Exception as e:
        error_message = f"Error processing your request: {str(e)}"
        print(f"Error in send_message: {str(e)}")

        # Add error message to chat
        messages = request.session.get("messages", [])
        error_chat_message = {
            "id": timezone.now().timestamp() + 1,
            "text": error_message,
            "sender": "assistant",
            "timestamp": timezone.now().isoformat(),
        }
        messages.append(error_chat_message)
        request.session["messages"] = messages

        return Response(
            {"error": error_message, "message": error_chat_message},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_chat_updates(request):
    """Get any new chat messages."""
    # Return all messages from session
    messages = request.session.get("messages", [])
    return Response(messages)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def interview_respond(request):
    try:
        # Extract data from request
        message = request.data.get("message")
        flow_id = request.data.get("flowId")
        conversation_history = request.data.get("conversationHistory", [])

        # Validate required fields
        if not message or not flow_id:
            return Response(
                {"error": "Message and flow ID are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get flow
        try:
            flow = Flow.objects.get(id=flow_id)
        except Flow.DoesNotExist:
            return Response(
                {"error": "Flow not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Generate interview response
        response = generate_interview_response(
            user_message=message, flow=flow, conversation_history=conversation_history
        )

        # Prepare response data
        response_data = {"response": response["text"], "audio": response["audio"]}

        return Response(response_data)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def text_to_speech(request):
    """
    Convert text to speech without AI processing.
    """
    try:
        # Get text from request data
        text = request.data.get("text")
        if not text:
            return Response(
                {"error": "Text is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Convert text to speech
        audio_format, audio_base64 = convert_to_speech(text)

        return Response({"audio": {"format": audio_format, "data": audio_base64}})
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"Error in text_to_speech view: {str(e)}")
        return Response(
            {"error": "Failed to convert text to speech"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_csrf_token(request):
    """Get a CSRF token cookie."""
    # Get the token
    token = get_token(request)

    # Create response
    response = Response({"detail": "CSRF cookie set"})

    # Set cookie with domain for subdomains
    response.set_cookie(
        "csrftoken",
        token,
        domain=".klarro.ai",  # Allow subdomains
        path="/",
        secure=True,
        httponly=False,  # Must be False for CSRF token
        samesite="Lax",
    )

    return response
