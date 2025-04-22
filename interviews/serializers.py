# serializers.py

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Candidate, Company, Flow, Interview, Recruiter, Step


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class RecruiterSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    company = CompanySerializer(read_only=True)
    company_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Recruiter
        fields = ["id", "user", "user_id", "company", "company_id", "created_at"]


class FlowSerializer(serializers.ModelSerializer):
    recruiter = RecruiterSerializer(read_only=True)
    recruiter_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Flow
        fields = "__all__"


class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Step
        fields = "__all__"


class CandidateSerializer(serializers.ModelSerializer):
    flow_name = serializers.CharField(source="flow.name", read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "flow",
            "flow_name",
            "created_at",
        ]


class InterviewSerializer(serializers.ModelSerializer):
    interviewer = RecruiterSerializer(read_only=True)
    interviewer_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Interview
        fields = "__all__"
