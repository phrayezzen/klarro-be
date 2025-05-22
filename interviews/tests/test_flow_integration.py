from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from interviews.models import Company, Flow, Recruiter

User = get_user_model()


class FlowIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        # Create test company
        self.company = Company.objects.create(name="Test Company")

        # Create recruiter for the user
        self.recruiter = Recruiter.objects.create(user=self.user, company=self.company)

        # Test flow data
        self.flow = Flow.objects.create(
            company=self.company,
            recruiter=self.recruiter,
            role_name="Test Flow",
            role_description="Test Description",
            role_function="engineering_data",
            location="San Francisco, CA",
            is_remote_allowed=True,
        )

    def test_create_and_retrieve_flow(self):
        """Test creating and retrieving a flow."""
        url = "/api/v1/flows/"
        data = {
            "company": self.company.id,
            "role_name": "Test Flow",
            "role_description": "Test Description",
            "role_function": "engineering_data",
            "location": "San Francisco, CA",
            "is_remote_allowed": True,
            "steps": [
                {
                    "name": "Initial Screening",
                    "description": "Initial screening interview",
                    "type": "behavioral",
                    "duration_minutes": 30,
                    "order": 1,
                    "interviewer_tone": "professional",
                },
                {
                    "name": "Technical Assessment",
                    "description": "Technical skills assessment",
                    "type": "technical",
                    "duration_minutes": 60,
                    "order": 2,
                    "interviewer_tone": "professional",
                },
            ],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role_name"], "Test Flow")
        self.assertEqual(len(response.data["steps"]), 2)

    def test_edit_flow(self):
        """Test editing a flow."""
        url = f"/api/v1/flows/{self.flow.id}/"
        data = {
            "role_name": "Updated Flow",
            "role_description": "Updated Description",
            "steps": [
                {
                    "name": "Updated Screening",
                    "description": "Updated screening interview",
                    "type": "behavioral",
                    "duration_minutes": 45,
                    "order": 1,
                    "interviewer_tone": "professional",
                }
            ],
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role_name"], "Updated Flow")
        self.assertEqual(len(response.data["steps"]), 1)

    def test_create_candidate(self):
        """Test creating a candidate for a flow."""
        url = "/api/v1/candidates/"
        data = {
            "flow_id": self.flow.id,
            "first_name": "John",
            "last_name": "Doe",
            "email": "test@example.com",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["first_name"], "John")
        self.assertEqual(response.data["last_name"], "Doe")
