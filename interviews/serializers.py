# serializers.py

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Candidate, Company, Flow, Interview, Recruiter, Step


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField(source="recruiter.company_id", read_only=True)
    company_name = serializers.CharField(
        source="recruiter.company.name", read_only=True
    )
    recruiter_id = serializers.IntegerField(source="recruiter.id", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "recruiter_id",
            "company_id",
            "company_name",
        ]


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
            "interviewer_tone",
            "assessed_skills",
            "custom_questions",
        ]


class RecruiterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    company_id = serializers.IntegerField(source="company.id", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Recruiter
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "company_id",
            "company_name",
            "created_at",
        ]


class FlowSerializer(serializers.ModelSerializer):
    recruiter = RecruiterSerializer(read_only=True)
    recruiter_id = serializers.IntegerField(write_only=True, required=False)
    company_id = serializers.IntegerField(source="company.id", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    steps = StepSerializer(many=True)

    class Meta:
        model = Flow
        fields = [
            "id",
            "company_id",
            "company_name",
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

    def create(self, validated_data):
        steps_data = validated_data.pop("steps", [])
        flow = Flow.objects.create(**validated_data)

        for step_data in steps_data:
            # Convert type back to step_type for the model
            if "type" in step_data:
                step_data["step_type"] = step_data.pop("type")
            step_data["flow"] = flow
            Step.objects.create(**step_data)

        return flow

    def update(self, instance, validated_data):
        steps_data = validated_data.pop("steps", [])
        # Update flow fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update steps
        if steps_data:
            # Delete existing steps that are not in the update
            existing_step_ids = [step["id"] for step in steps_data if "id" in step]
            instance.steps.exclude(id__in=existing_step_ids).delete()

            # Update or create steps
            for step_data in steps_data:
                step_id = step_data.pop("id", None)
                if step_id:
                    # Update existing step
                    step = instance.steps.get(id=step_id)
                    for attr, value in step_data.items():
                        setattr(step, attr, value)
                    step.save()
                else:
                    # Create new step
                    step_data["flow"] = instance
                    Step.objects.create(**step_data)

        return instance


class CandidateSerializer(serializers.ModelSerializer):
    flow_id = serializers.PrimaryKeyRelatedField(
        source="flow", queryset=Flow.objects.all()
    )
    resume = serializers.FileField(required=False)
    resume_url = serializers.SerializerMethodField()
    role_name = serializers.CharField(source="flow.role_name", read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    interview_status = serializers.CharField(source="status", read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "status",
            "flow_id",
            "resume",
            "resume_url",
            "created_at",
            "role_name",
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
        ]
        read_only_fields = ["id", "created_at"]

    def get_resume_url(self, obj):
        if obj.resume:
            base_url = self.context["request"].build_absolute_uri("/").rstrip("/")
            file_url = obj.resume.url
            return f"{base_url}{file_url}"
        return None

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            base_url = self.context["request"].build_absolute_uri("/").rstrip("/")
            file_url = obj.profile_picture.url
            return f"{base_url}{file_url}"
        return f"https://ui-avatars.com/api/?name={obj.first_name}+{obj.last_name}"


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


class EvaluationCriterionSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    weight = serializers.FloatField(min_value=0, max_value=1)


class FlowStepSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    type = serializers.CharField()
    duration_minutes = serializers.IntegerField(min_value=1)
    order = serializers.IntegerField(min_value=0)


class GPTFlowResponseSerializer(serializers.Serializer):
    role_name = serializers.CharField()
    role_function = serializers.CharField()
    role_description = serializers.CharField()
    location = serializers.CharField(allow_null=True)
    is_remote_allowed = serializers.BooleanField()
    steps = FlowStepSerializer(many=True)
    evaluation_criteria = EvaluationCriterionSerializer(many=True)


class GPTFlowDetailsResponseSerializer(serializers.Serializer):
    questions = serializers.ListField(child=serializers.CharField())
