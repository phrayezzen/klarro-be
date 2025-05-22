from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ..models import Candidate, Company, Flow, Interview, Recruiter, Step


class APITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create test data
        self.company1 = Company.objects.create(name="Company 1")
        self.company2 = Company.objects.create(name="Company 2")

        # Create users and recruiters
        self.user1 = User.objects.create_user(username="user1", password="pass1")
        self.user2 = User.objects.create_user(username="user2", password="pass2")
        self.non_recruiter_user = User.objects.create_user(
            username="regular_user", password="testpass"
        )

        self.recruiter1 = Recruiter.objects.create(
            user=self.user1, company=self.company1
        )
        self.recruiter2 = Recruiter.objects.create(
            user=self.user2, company=self.company2
        )

        # Create flow and related objects
        self.flow1 = Flow.objects.create(
            company=self.company1,
            recruiter=self.recruiter1,
            role_name="Test Flow 1",
            role_description="Test Description 1",
            role_function="engineering_data",
            location="San Francisco, CA",
            is_remote_allowed=True,
        )

        self.flow2 = Flow.objects.create(
            company=self.company2,
            recruiter=self.recruiter2,
            role_name="Test Flow 2",
            role_description="Test Description 2",
            role_function="engineering_data",
            location="New York, NY",
            is_remote_allowed=False,
        )

        self.step1 = Step.objects.create(
            flow=self.flow1,
            name="Technical Interview",
            step_type="technical",
            duration_minutes=60,
            order=1,
            interviewer_tone="professional",
        )

        self.step2 = Step.objects.create(
            flow=self.flow2,
            name="Behavioral Interview",
            step_type="behavioral",
            duration_minutes=45,
            order=1,
            interviewer_tone="professional",
        )

        self.candidate1 = Candidate.objects.create(
            flow=self.flow1,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )

        self.candidate2 = Candidate.objects.create(
            flow=self.flow2,
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
        )

    def test_authentication_required(self):
        """Test that endpoints require authentication"""
        # Test flow endpoint
        response = self.client.get("/api/v1/flows/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test candidate endpoint
        response = self.client.get("/api/v1/candidates/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test interview endpoint
        response = self.client.get("/api/v1/interviews/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_recruiter_access(self):
        """Test that non-recruiter users cannot access the API"""
        self.client.force_authenticate(user=self.non_recruiter_user)
        response = self.client.get("/api/v1/flows/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_api(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing companies
        response = self.client.get("/api/v1/companies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 1
        )  # User should only see their own company

        # Test accessing another company's data
        response = self.client.get(f"/api/v1/companies/{self.company2.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_flow_api(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing flows
        response = self.client.get("/api/v1/flows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        # Test accessing another company's flow
        response = self.client.get(f"/api/v1/flows/{self.flow2.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_flow_steps_api(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing steps for own flow
        response = self.client.get(f"/api/v1/flows/{self.flow1.id}/steps/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Test accessing steps from another company's flow
        response = self.client.get(f"/api/v1/flows/{self.flow2.id}/steps/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test creating a step
        new_step_data = {
            "name": "System Design Interview",
            "type": "technical",
            "duration_minutes": 90,
            "order": 2,
            "description": "System design interview description",
            "interviewer_tone": "professional",
            "assessed_skills": [],
            "custom_questions": [],
        }
        response = self.client.post(
            f"/api/v1/flows/{self.flow1.id}/steps/", new_step_data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], new_step_data["name"])

        # Test creating a step in another company's flow
        response = self.client.post(
            f"/api/v1/flows/{self.flow2.id}/steps/", new_step_data
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_flow_candidates_api(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing candidates for own flow
        response = self.client.get(f"/api/v1/flows/{self.flow1.id}/candidates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Test accessing candidates from another company's flow
        response = self.client.get(f"/api/v1/flows/{self.flow2.id}/candidates/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_interviews_api(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing interviews
        response = self.client.get("/api/v1/interviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 0
        )  # No interviews created in setUp

        # Test creating an interview (use candidate1 and step1 from company1)
        interview_data = {
            "candidate": self.candidate1.id,
            "step": self.step1.id,
            "status": "pending",
        }
        response = self.client.post(
            reverse("interview-list"),
            interview_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test accessing the created interview
        response = self.client.get(f"/api/v1/interviews/{response.data['id']}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
