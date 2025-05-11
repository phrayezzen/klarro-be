import asyncio
import json
from unittest.mock import AsyncMock, patch

from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from interviews.models import Company, Flow, Recruiter, Step
from interviews.services.ai_service import (
    create_flow_prompt,
    generate_flow,
    get_flow_details,
    get_flow_details_prompt,
    handle_message,
)


class AIServiceIntegrationTests(TransactionTestCase):
    def setUp(self):
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

    @patch("interviews.services.ai_service.openai.OpenAI")
    def test_create_flow_with_sufficient_details(self, mock_openai):
        """Test creating a flow through the API when all necessary details are provided."""
        # Mock the OpenAI response
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock the chat completion response
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    content="""1. Initial Screening (30 minutes)
                    - Review of candidate's background and experience
                    - Discussion of role requirements and expectations
                    - Assessment of communication skills
                    
                    2. Technical Assessment (60 minutes)
                    - System design discussion
                    - Code review exercise
                    - Problem-solving scenarios
                    
                    3. Team Fit Interview (45 minutes)
                    - Team collaboration experience
                    - Leadership style and approach
                    - Cultural alignment
                    
                    4. Final Interview (60 minutes)
                    - Architecture and technical leadership
                    - Project management experience
                    - Career goals and growth""",
                    tool_calls=[],
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Test data
        role_name = "Senior Software Engineer"
        role_description = "Senior Software Engineer position focusing on backend development and system design"
        role_function = "engineering_data"
        location = "San Francisco, CA"
        is_remote_allowed = True

        try:
            # Run the async function
            async def run_test():
                flow, details = await generate_flow(
                    role_name=role_name,
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

            # Assert flow was created
            self.assertIsNotNone(flow, "Flow should not be None")
            self.assertEqual(flow.role_name, role_name)
            self.assertEqual(
                flow.role_description,
                f"{role_name} position with focus on technical excellence and team collaboration",
            )
            self.assertEqual(flow.role_function, "engineering_data")
            self.assertIsNone(flow.location)
            self.assertTrue(flow.is_remote_allowed)
            self.assertEqual(flow.company, self.company)
            self.assertEqual(flow.recruiter, self.recruiter)

            # Assert steps were created
            self.assertTrue(flow.steps.exists())
            self.assertEqual(
                flow.steps.count(), 4
            )  # Should have 4 steps as per mock response

            # Verify step details
            steps = flow.steps.order_by("order")
            expected_steps = [
                ("Initial Screening", 30),
                ("Technical Assessment", 60),
                ("Team Fit Interview", 45),
                ("Final Interview", 60),
            ]

            for step, (expected_name, expected_duration) in zip(steps, expected_steps):
                self.assertIn(expected_name, step.name)
                self.assertEqual(step.duration_minutes, expected_duration)

        except Exception as e:
            self.fail(f"Test failed with exception: {str(e)}")

    @patch("interviews.services.ai_service.openai.OpenAI")
    def test_create_flow_with_insufficient_details(self, mock_openai):
        """Test creating a flow through the API when details are insufficient."""
        # Mock the OpenAI response
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock the chat completion response to request more details
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    content="",
                    tool_calls=[
                        AsyncMock(
                            **{
                                "function.name": "request_more_details",
                                "function.arguments": json.dumps(
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
                            }
                        )
                    ],
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        try:
            # Run the async function
            async def run_test():
                flow, details = await generate_flow(
                    role_name="Software Engineer",
                    company=self.company,
                    recruiter=self.recruiter,
                    additional_context=None,
                )
                return flow, details

            flow, details = asyncio.run(run_test())

            # Assert no flow was created
            self.assertIsNone(flow)
            self.assertIsNotNone(details)
            self.assertEqual(len(details.questions), 4)
            self.assertIn("technical skills", details.questions[0].lower())

        except Exception as e:
            self.fail(f"Test failed with exception: {str(e)}")

    @patch("interviews.services.ai_service.openai.OpenAI")
    def test_create_flow_without_role_name(self, mock_openai):
        """Test creating a flow without providing role_name."""
        # Mock the OpenAI response
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client

        # Mock the chat completion response to request role name
        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                message=AsyncMock(
                    tool_calls=[
                        AsyncMock(
                            function=AsyncMock(
                                name="request_more_details",
                                arguments=json.dumps(
                                    {
                                        "context": "I need to know what role you're hiring for.",
                                        "questions": [
                                            "What is the role title?",
                                            "What department is this role in?",
                                            "What level of seniority are you looking for?",
                                        ],
                                    }
                                ),
                            )
                        )
                    ]
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        response = self.client.post(
            reverse("send-message"),
            {"message": "Create an interview flow"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text", response.data)
        self.assertIn("need to know what role", response.data["text"].lower())

        # Verify no flow was created
        self.assertFalse(Flow.objects.exists())

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
        """Test getting additional details for flow creation."""
        response = self.client.post(
            reverse("get-flow-details"),
            {"role_name": "Software Engineer"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("questions", response.data)
        self.assertIsInstance(response.data["questions"], list)
        self.assertTrue(len(response.data["questions"]) > 0)
