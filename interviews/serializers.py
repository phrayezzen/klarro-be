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


class StepSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="step_type")

    class Meta:
        model = Step
        fields = [
            "id",
            "name",
            "description",
            "type",
            "duration_minutes",
            "order",
            "created_at",
        ]


class FlowSerializer(serializers.ModelSerializer):
    recruiter = RecruiterSerializer(read_only=True)
    recruiter_id = serializers.IntegerField(write_only=True, required=False)
    steps = StepSerializer(many=True, read_only=True)

    class Meta:
        model = Flow
        fields = [
            "id",
            "company",
            "recruiter",
            "recruiter_id",
            "role_name",
            "role_description",
            "role_function",
            "location",
            "is_remote_allowed",
            "is_active",
            "created_at",
            "steps",
        ]


class CandidateSerializer(serializers.ModelSerializer):
    flow_name = serializers.CharField(source="flow.role_name", read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    interview_status = serializers.CharField(source="status", read_only=True)
    job_match_score = serializers.SerializerMethodField()
    experience_score = serializers.SerializerMethodField()
    education_score = serializers.SerializerMethodField()
    behavioral_score = serializers.SerializerMethodField()
    technical_score = serializers.SerializerMethodField()
    preferences_score = serializers.SerializerMethodField()
    experience_evaluation = serializers.SerializerMethodField()
    education_evaluation = serializers.SerializerMethodField()
    behavioral_evaluation = serializers.SerializerMethodField()
    technical_evaluation = serializers.SerializerMethodField()
    preferences_evaluation = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "flow",
            "flow_name",
            "resume_url",
            "profile_picture_url",
            "interview_status",
            "job_match_score",
            "experience_score",
            "education_score",
            "behavioral_score",
            "technical_score",
            "preferences_score",
            "experience_evaluation",
            "education_evaluation",
            "behavioral_evaluation",
            "technical_evaluation",
            "preferences_evaluation",
            "created_at",
        ]

    def get_profile_picture_url(self, obj):
        return f"https://ui-avatars.com/api/?name={obj.first_name}+{obj.last_name}"

    def get_job_match_score(self, obj):
        return 85.5

    def get_experience_score(self, obj):
        return 90.0

    def get_education_score(self, obj):
        return 85.0

    def get_behavioral_score(self, obj):
        return 88.0

    def get_technical_score(self, obj):
        return 92.0

    def get_preferences_score(self, obj):
        return 87.0

    def get_experience_evaluation(self, obj):
        return (
            "Strong experience in full-stack development with 5+ years working on scalable "
            "applications. Demonstrated expertise in React, Node.js, and cloud technologies. "
            "Successfully led multiple projects from conception to deployment."
        )

    def get_education_evaluation(self, obj):
        return (
            "Bachelor's degree in Computer Science from a top-tier university. Relevant "
            "coursework in algorithms, data structures, and software engineering. Additional "
            "certifications in cloud technologies and agile methodologies."
        )

    def get_behavioral_evaluation(self, obj):
        return (
            "Excellent communication skills and team collaboration. Shows strong leadership "
            "potential and problem-solving abilities. Adapts well to changing requirements "
            "and demonstrates emotional intelligence in team interactions."
        )

    def get_technical_evaluation(self, obj):
        return (
            "Outstanding technical skills with deep knowledge of modern web technologies. "
            "Strong problem-solving abilities and clean code practices. Demonstrates good "
            "understanding of system design principles and best practices."
        )

    def get_preferences_evaluation(self, obj):
        return (
            "Prefers collaborative work environments and values continuous learning. "
            "Interested in working on challenging projects with modern technologies. "
            "Looking for opportunities to mentor junior developers and contribute to open source."
        )


class InterviewSerializer(serializers.ModelSerializer):
    interviewer = RecruiterSerializer(read_only=True)
    interviewer_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Interview
        fields = "__all__"

    def get_questions(self, obj):
        """Get questions for the interview."""
        questions = []
        for step in obj.steps.all():
            step_questions = []
            for question in step.questions.all():
                step_questions.append(
                    {
                        "id": question.id,
                        "text": question.text,
                        "type": question.type,
                        "difficulty": question.difficulty,
                        "category": question.category,
                        "subcategory": question.subcategory,
                        "tags": question.tags,
                        "created_at": question.created_at,
                        "updated_at": question.updated_at,
                    }
                )
            questions.append(
                {
                    "step_id": step.id,
                    "step_type": step.type,
                    "questions": step_questions,
                }
            )
        return questions
