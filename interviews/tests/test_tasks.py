import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from interviews.models import Candidate, Company, Flow, Interview, Step
from interviews.tasks import evaluate_interview_task, evaluate_resume_task

User = get_user_model()


class TaskTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        # Create test company
        self.company = Company.objects.create(name="Test Company")

        # Create test flow
        self.flow = Flow.objects.create(
            company=self.company,
            role_name="Software Engineer",
            role_description="Test Description",
            role_function="engineering_data",
            location="San Francisco, CA",
            is_remote_allowed=True,
        )

        # Create test candidate
        self.candidate = Candidate.objects.create(
            flow=self.flow, first_name="John", last_name="Doe", email="john@example.com"
        )

        # Create test step
        self.step = Step.objects.create(
            flow=self.flow,
            name="Technical Interview",
            description="Test technical interview",
            step_type="technical",
            duration_minutes=60,
            order=1,
            interviewer_tone="professional",
            assessed_skills=[],
            custom_questions=[],
        )

        # Create test interview
        self.interview = Interview.objects.create(
            candidate=self.candidate,
            step=self.step,
            status="completed",
            transcript="Test transcript",
        )

        # Mock OpenAI responses
        self.mock_resume_response = json.dumps(
            {
                "education": {"score": 85, "evaluation": "Good educational background"},
                "experience": {"score": 90, "evaluation": "Strong relevant experience"},
            }
        )

        self.mock_interview_response = json.dumps(
            {
                "overall_score": 85,
                "education": {"score": 85, "evaluation": "Good educational background"},
                "experience": {"score": 90, "evaluation": "Strong relevant experience"},
                "technical": {"score": 88, "evaluation": "Strong technical skills"},
                "behavioral": {"score": 82, "evaluation": "Good communication skills"},
                "cheating_flag": False,
            }
        )

    @patch("interviews.tasks.openai.ChatCompletion.create")
    def test_evaluate_resume_task(self, mock_openai):
        # Mock OpenAI response
        mock_openai.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=self.mock_resume_response))]
        )

        # Run task synchronously
        result = evaluate_resume_task(self.candidate.id)

        # Verify results
        self.assertEqual(result, "Resume evaluation completed")
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.education_score, 85)
        self.assertEqual(self.candidate.experience_score, 90)

    @patch("interviews.tasks.openai.ChatCompletion.create")
    def test_evaluate_resume_task_error_handling(self, mock_openai):
        # Test with non-existent candidate
        result = evaluate_resume_task(999)
        self.assertEqual(result, "Candidate not found")

    @patch("interviews.tasks.openai.ChatCompletion.create")
    def test_evaluate_interview_task(self, mock_openai):
        # Mock OpenAI response
        mock_openai.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=self.mock_interview_response))]
        )

        # Run task synchronously
        result = evaluate_interview_task(self.interview.id)

        # Verify results
        self.assertEqual(result, "Interview evaluation completed")
        self.interview.refresh_from_db()
        self.assertEqual(self.interview.overall_score, 85)
        self.assertFalse(self.interview.cheating_flag)

    @patch("interviews.tasks.openai.ChatCompletion.create")
    def test_evaluate_interview_task_error_handling(self, mock_openai):
        # Test with non-existent interview
        result = evaluate_interview_task(999)
        self.assertEqual(result, "Interview not found")
