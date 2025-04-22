from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Candidate, Flow, Interview, Recruiter
from .permissions import IsCompanyMember, IsRecruiter
from .serializers import (
    CandidateSerializer,
    FlowSerializer,
    InterviewSerializer,
    RecruiterSerializer,
    StepSerializer,
)


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
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated, IsRecruiter, IsCompanyMember]

    def get_queryset(self):
        queryset = super().get_queryset()
        candidate_id = self.request.query_params.get("candidate_id")
        step_id = self.request.query_params.get("step_id")

        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)
        if step_id:
            queryset = queryset.filter(step_id=step_id)

        return queryset.filter(
            Q(step__flow__company_id=self.request.user.recruiter.company_id)
            | Q(interviewer_id=self.request.user.recruiter.id)
        )
