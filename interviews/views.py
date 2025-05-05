from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Candidate, Flow, Interview, Recruiter, Step
from .permissions import IsCompanyMember, IsRecruiter
from .serializers import (
    CandidateSerializer,
    FlowSerializer,
    InterviewSerializer,
    RecruiterSerializer,
    StepSerializer,
    UserSerializer,
)


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
        queryset = super().get_queryset()
        return queryset.filter(company_id=self.request.user.recruiter.company_id)


class FlowViewSet(viewsets.ModelViewSet):
    queryset = Flow.objects.all()
    serializer_class = FlowSerializer
    permission_classes = [IsAuthenticated, IsRecruiter, IsCompanyMember]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["role_name", "role_function", "location", "created_at"]
    ordering = ["-created_at"]

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
    serializer = UserSerializer(request.user)
    return Response(serializer.data)
