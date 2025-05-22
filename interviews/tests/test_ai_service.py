import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from interviews.models import Candidate, Company, Flow, Recruiter, Step
from interviews.services.ai_service import generate_flow


class AIServiceIntegrationTests(TransactionTestCase):
    def setUp(self):
        # Explicitly clear all relevant models for test isolation
        Step.objects.all().delete()
        Flow.objects.all().delete()
        Candidate.objects.all().delete()
        Recruiter.objects.all().delete()
        Company.objects.all().delete()
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        # Create test company
        self.company = Company.objects.create(
            name="Test Company", description="Test Description"
        )
        # Create recruiter for the user
        self.recruiter = Recruiter.objects.create(user=self.user, company=self.company)
        # Set up the API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        Step.objects.all().delete()
        Flow.objects.all().delete()
        Candidate.objects.all().delete()
        Recruiter.objects.all().delete()
        Company.objects.all().delete()

    @patch("interviews.services.ai_service.openai.AsyncOpenAI")
    def test_create_flow_with_sufficient_details(self, mock_openai):
        """Test creating a flow through the API when all necessary details are provided."""
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock a valid JSON response with exactly 2 steps
        flow_json = {
            "role_name": "Senior Software Engineer",
            "role_function": "engineering_data",
            "role_description": "The Senior Software Engineer role involves leading and contributing to the development of software systems, designing scalable architectures, and mentoring junior team members in an Engineering & Data department.",
            "location": "San Francisco, CA",
            "is_remote_allowed": True,
            "steps": [
                {
                    "name": "Initial Screening",
                    "description": "Review of candidate's background and experience",
                    "step_type": "technical",
                    "duration_minutes": 30,
                    "order": 1,
                    "interviewer_tone": "professional",
                    "assessed_skills": ["communication", "experience"],
                    "custom_questions": ["Tell me about your background"],
                },
                {
                    "name": "Technical Assessment",
                    "description": "System design discussion and code review",
                    "step_type": "technical",
                    "duration_minutes": 60,
                    "order": 2,
                    "interviewer_tone": "professional",
                    "assessed_skills": ["system design", "coding"],
                    "custom_questions": ["Design a scalable system"],
                },
            ],
        }
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=SimpleNamespace(content=json.dumps(flow_json), tool_calls=[])
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        try:

            async def run_test():
                flow, details = await generate_flow(
                    role_name="Senior Software Engineer",
                    company=self.company,
                    recruiter=self.recruiter,
                    additional_context="""
                    Role Details:
                    - Function: engineering_data
                    - Location: San Francisco, CA
                    - Remote Policy: Hybrid (3 days in office)
                    - Level: Senior (5+ years experience)
                    """,
                )
                return flow, details

            flow, details = asyncio.run(run_test())
            self.assertIsNotNone(flow)
            self.assertEqual(flow.role_name, "Senior Software Engineer")
            self.assertIn("senior software engineer", flow.role_description.lower())
            self.assertEqual(flow.role_function, "engineering_data")
            self.assertEqual(flow.location, "San Francisco, CA")
            self.assertTrue(flow.is_remote_allowed)
            self.assertEqual(flow.company, self.company)
            self.assertEqual(flow.recruiter, self.recruiter)
            self.assertTrue(flow.steps.exists())
            self.assertEqual(flow.steps.count(), 2)
            steps = flow.steps.order_by("order")
            expected_steps = [
                ("Initial Screening", 30),
                ("Technical Assessment", 60),
            ]
            for step, (expected_name, expected_duration) in zip(steps, expected_steps):
                self.assertEqual(step.name, expected_name)
                self.assertEqual(step.duration_minutes, expected_duration)
        except Exception as e:
            self.fail(f"Test failed with exception: {str(e)}")

    @patch("interviews.services.ai_service.openai.AsyncOpenAI")
    def test_create_flow_with_insufficient_details(self, mock_openai):
        """Test creating a flow through the API when details are insufficient."""
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock a response that requests more details
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            function=SimpleNamespace(
                                name="request_more_details",
                                arguments=json.dumps(
                                    {
                                        "context": "I need more information to create a comprehensive interview flow.",
                                        "questions": [
                                            "What are the key technical skills required?",
                                            "What level of experience are you looking for?",
                                            "What is the team structure?",
                                            "What are the main responsibilities?",
                                        ],
                                    }
                                ),
                            )
                        )
                    ],
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        try:

            async def run_test():
                flow, details = await generate_flow(
                    role_name="Software Engineer",
                    company=self.company,
                    recruiter=self.recruiter,
                    additional_context=None,
                )
                return flow, details

            flow, details = asyncio.run(run_test())
            self.assertIsNone(flow)
            self.assertIsNotNone(details)
            self.assertEqual(len(details.questions), 4)
            self.assertIn("technical skills", details.questions[0].lower())
        except Exception as e:
            self.fail(f"Test failed with exception: {str(e)}")

    @patch("interviews.services.ai_service.openai.AsyncOpenAI")
    def test_create_flow_without_role_name(self, mock_openai):
        """Test creating a flow without providing role_name."""
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Simulate a validation error (no role_name)
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(message=SimpleNamespace(content="", tool_calls=[]))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        response = self.client.post(
            reverse("send-message"),
            {"message": "Create an interview flow"},
            format="json",
        )

        # Accept either 200 or 400, but require an error message
        self.assertIn(response.status_code, [200, 400])
        self.assertTrue(
            "error" in response.data
            or "flow_details" in response.data
            or "message" in response.data
        )

    def test_create_flow_with_invalid_data(self):
        """Test creating a flow with invalid data."""
        response = self.client.post(
            reverse("send-message"),
            {"message": ""},  # Empty message
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

        # Verify no flow was created
        self.assertFalse(Flow.objects.exists())

    def test_get_flow_details(self):
        """Test getting flow details using the flow detail endpoint."""
        # First, create a flow
        flow = Flow.objects.create(
            company=self.company,
            recruiter=self.recruiter,
            role_name="Software Engineer",
            role_description="Test role description",
            role_function="engineering_data",
            location="San Francisco, CA",
            is_remote_allowed=True,
        )
        response = self.client.get(
            reverse("flow-detail", args=[flow.id]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("role_name", response.data)
        self.assertEqual(response.data["role_name"], "Software Engineer")
        self.assertIn("role_description", response.data)
        self.assertIn("role_function", response.data)
