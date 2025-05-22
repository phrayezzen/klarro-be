from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from ..models import Candidate, Company, Flow, Interview, Recruiter, Step


class APIPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create test data
        self.company1 = Company.objects.create(name="Company 1")
        self.company2 = Company.objects.create(name="Company 2")

        # Create users and recruiters
        self.user1 = User.objects.create_user(username="user1", password="pass1")
        self.user2 = User.objects.create_user(username="user2", password="pass2")
        self.user3 = User.objects.create_user(username="user3", password="testpass")

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

        self.interview1 = Interview.objects.create(
            candidate=self.candidate1, step=self.step1, interviewer=self.recruiter1
        )

    def test_company_api_permissions(self):
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

    def test_flow_api_permissions(self):
        # Test without authentication
        response = self.client.get("/api/v1/flows/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with authentication but no recruiter role
        self.client.force_authenticate(user=self.user3)
        response = self.client.get("/api/v1/flows/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test with recruiter role
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/flows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_flow_steps_permissions(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing steps
        response = self.client.get(f"/api/v1/flows/{self.flow1.id}/steps/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Test creating step
        new_step_data = {
            "name": "New Step",
            "type": "technical",
            "duration_minutes": 60,
            "order": 2,
            "interviewer_tone": "professional",
            "description": "",
            "assessed_skills": [],
            "custom_questions": [],
        }
        response = self.client.post(
            f"/api/v1/flows/{self.flow1.id}/steps/", new_step_data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test accessing another company's steps
        response = self.client.get(f"/api/v1/flows/{self.flow2.id}/steps/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_flow_candidates_permissions(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing candidates
        response = self.client.get(f"/api/v1/flows/{self.flow1.id}/candidates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test creating candidate
        new_candidate_data = {
            "first_name": "Test",
            "last_name": "Candidate",
            "email": "test@example.com",
            "flow_id": self.flow1.id,
        }
        response = self.client.post("/api/v1/candidates/", new_candidate_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test accessing another company's candidates
        response = self.client.get(f"/api/v1/flows/{self.flow2.id}/candidates/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_interview_api_permissions(self):
        # Test without authentication
        response = self.client.get("/api/v1/interviews/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with authentication but no recruiter role
        self.client.force_authenticate(user=self.user3)
        response = self.client.get("/api/v1/interviews/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test with recruiter role
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/interviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filtering_permissions(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing flows
        response = self.client.get("/api/v1/flows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 1
        )  # Should only see own company's flows

        # Test filtering candidates
        response = self.client.get("/api/v1/candidates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Use paginated results
        candidates = [
            c for c in response.data["results"] if c["flow_id"] == self.flow1.id
        ]
        self.assertEqual(len(candidates), 1)  # One candidate from setUp

        # Test filtering interviews
        response = self.client.get("/api/v1/interviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)  # One interview from setUp
