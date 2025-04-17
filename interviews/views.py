from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from .models import Company, Candidate, Flow, Step, Interview, Recruiter
from .serializers import (
    CompanySerializer, CandidateSerializer, FlowSerializer,
    StepSerializer, InterviewSerializer, RecruiterSerializer, UserSerializer
)

class IsRecruiter(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and hasattr(request.user, 'recruiter')

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsRecruiter]

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(self.request.user, 'recruiter'):
            queryset = queryset.filter(id=self.request.user.recruiter.company_id)
        return queryset

class RecruiterViewSet(viewsets.ModelViewSet):
    queryset = Recruiter.objects.all()
    serializer_class = RecruiterSerializer
    permission_classes = [IsRecruiter]

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(self.request.user, 'recruiter'):
            queryset = queryset.filter(company_id=self.request.user.recruiter.company_id)
        return queryset

class FlowViewSet(viewsets.ModelViewSet):
    queryset = Flow.objects.all()
    serializer_class = FlowSerializer
    permission_classes = [IsRecruiter]

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(self.request.user, 'recruiter'):
            queryset = queryset.filter(recruiter_id=self.request.user.recruiter.id)
        return queryset

    @action(detail=True, methods=['get'])
    def steps(self, request, pk=None):
        flow = self.get_object()
        steps = flow.steps.all()
        serializer = StepSerializer(steps, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def candidates(self, request, pk=None):
        flow = self.get_object()
        candidates = flow.candidates.all()
        serializer = CandidateSerializer(candidates, many=True)
        return Response(serializer.data)

class StepViewSet(viewsets.ModelViewSet):
    queryset = Step.objects.all()
    serializer_class = StepSerializer
    permission_classes = [IsRecruiter]

    def get_queryset(self):
        queryset = super().get_queryset()
        flow_id = self.request.query_params.get('flow_id')
        if flow_id:
            queryset = queryset.filter(flow_id=flow_id)
        return queryset

    @action(detail=True, methods=['get'])
    def interviews(self, request, pk=None):
        step = self.get_object()
        interviews = step.interviews.all()
        serializer = InterviewSerializer(interviews, many=True)
        return Response(serializer.data)

class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    permission_classes = [IsRecruiter]

    def get_queryset(self):
        queryset = super().get_queryset()
        flow_id = self.request.query_params.get('flow_id')
        if flow_id:
            queryset = queryset.filter(flow_id=flow_id)
        return queryset

    @action(detail=True, methods=['get'])
    def interviews(self, request, pk=None):
        candidate = self.get_object()
        interviews = candidate.interviews.all()
        serializer = InterviewSerializer(interviews, many=True)
        return Response(serializer.data)

class InterviewViewSet(viewsets.ModelViewSet):
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer
    permission_classes = [IsRecruiter]

    def get_queryset(self):
        queryset = super().get_queryset()
        candidate_id = self.request.query_params.get('candidate_id')
        step_id = self.request.query_params.get('step_id')
        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)
        if step_id:
            queryset = queryset.filter(step_id=step_id)
        return queryset
