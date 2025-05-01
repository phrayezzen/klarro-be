from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Candidate, Flow, Interview, InterviewStep, Recruiter, Step
from .permissions import IsCompanyMember, IsRecruiter
from .serializers import (
    CandidateSerializer,
    FlowSerializer,
    InterviewSerializer,
    InterviewStepSerializer,
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

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(company_id=self.request.user.recruiter.company_id)

    def perform_create(self, serializer):
        serializer.save(recruiter=self.request.user.recruiter)

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


class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    permission_classes = [IsAuthenticated, IsRecruiter, IsCompanyMember]

    def get_queryset(self):
        queryset = super().get_queryset()
        flow_id = self.request.query_params.get("flow_id")
        if flow_id:
            queryset = queryset.filter(flow_id=flow_id)
        return queryset.filter(flow__company_id=self.request.user.recruiter.company_id)

    @action(detail=True, methods=["get"])
    def interviews(self, request, pk=None):
        candidate = self.get_object()
        interviews = candidate.interviews.all()
        serializer = InterviewSerializer(interviews, many=True)
        return Response(serializer.data)


class InterviewViewSet(viewsets.ModelViewSet):
    """ViewSet for managing interviews."""

    serializer_class = InterviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get interviews for the current user."""
        return Interview.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create a new interview."""
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """Update an interview."""
        if serializer.instance.user != self.request.user:
            raise PermissionDenied(
                "You don't have permission to update this interview."
            )
        serializer.save()

    def perform_destroy(self, instance):
        """Delete an interview."""
        if instance.user != self.request.user:
            raise PermissionDenied(
                "You don't have permission to delete this interview."
            )
        instance.delete()

    @action(detail=True, methods=["post"])
    def add_step(self, request, pk=None):
        """Add a step to the interview."""
        interview = self.get_object()
        step_data = request.data
        step_data["interview"] = interview.id
        serializer = InterviewStepSerializer(data=step_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=["post"])
    def remove_step(self, request, pk=None):
        """Remove a step from the interview."""
        interview = self.get_object()
        step_id = request.data.get("step_id")
        if not step_id:
            return Response({"error": "step_id is required"}, status=400)

        step = get_object_or_404(InterviewStep, id=step_id, interview=interview)
        step.delete()
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def reorder_steps(self, request, pk=None):
        """Reorder steps in the interview."""
        interview = self.get_object()
        step_ids = request.data.get("step_ids", [])
        if not step_ids:
            return Response({"error": "step_ids is required"}, status=400)

        # Verify all steps belong to this interview
        steps = InterviewStep.objects.filter(id__in=step_ids, interview=interview)
        if len(steps) != len(step_ids):
            return Response({"error": "Invalid step IDs"}, status=400)

        # Update order
        for index, step_id in enumerate(step_ids):
            InterviewStep.objects.filter(id=step_id).update(order=index)

        return Response(status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get the current authenticated user's data."""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)
