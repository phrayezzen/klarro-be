from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from ..models import Candidate, Company, Flow, Interview, Recruiter, Step


class APITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create test data
        self.company1 = Company.objects.create(
            name="Test Company 1", description="Test Description 1"
        )
        self.company2 = Company.objects.create(
            name="Test Company 2", description="Test Description 2"
        )

        # Create users and recruiters
        self.user1 = User.objects.create_user(username="user1", password="testpass")
        self.user2 = User.objects.create_user(username="user2", password="testpass")
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
            name="Test Flow 1",
            description="Flow Description 1",
        )

        self.flow2 = Flow.objects.create(
            company=self.company2,
            recruiter=self.recruiter2,
            name="Test Flow 2",
            description="Flow Description 2",
        )

        self.step1 = Step.objects.create(
            flow=self.flow1,
            name="Technical Interview",
            step_type="technical",
            duration_minutes=60,
            order=1,
            description="Technical interview description",
        )

        self.step2 = Step.objects.create(
            flow=self.flow1,
            name="Behavioral Interview",
            step_type="behavioral",
            duration_minutes=45,
            order=2,
            description="Behavioral interview description",
        )

        self.candidate1 = Candidate.objects.create(
            flow=self.flow1,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            resume_url="http://example.com/resume1.pdf",
        )

        self.candidate2 = Candidate.objects.create(
            flow=self.flow1,
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            resume_url="http://example.com/resume2.pdf",
        )

        self.interview1 = Interview.objects.create(
            candidate=self.candidate1,
            step=self.step1,
            interviewer=self.recruiter1,
            status="completed",
            transcript="Interview transcript here",
            overall_score=4.5,
            completed_at="2024-03-20T10:00:00Z",
        )

    def test_authentication_required(self):
        """Test that endpoints require authentication"""
        # Test without authentication
        endpoints = [
            "/api/companies/",
            "/api/flows/",
            f"/api/flows/{self.flow1.id}/steps/",
            f"/api/flows/{self.flow1.id}/candidates/",
            "/api/interviews/",
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_recruiter_access(self):
        """Test that non-recruiter users cannot access the API"""
        self.client.force_authenticate(user=self.non_recruiter_user)

        endpoints = [
            "/api/companies/",
            "/api/flows/",
            f"/api/flows/{self.flow1.id}/steps/",
            f"/api/flows/{self.flow1.id}/candidates/",
            "/api/interviews/",
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_api(self):
        # Test company access for recruiter1
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/companies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Should only see their own company
        self.assertEqual(response.data[0]["name"], self.company1.name)

        # Test company access for recruiter2
        self.client.force_authenticate(user=self.user2)
        response = self.client.get("/api/companies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Should only see their own company
        self.assertEqual(response.data[0]["name"], self.company2.name)

    def test_flow_api(self):
        # Test flow access for recruiter1
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/flows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Should only see their company's flows
        self.assertEqual(response.data[0]["name"], self.flow1.name)

        # Test flow creation
        new_flow_data = {
            "name": "New Flow",
            "description": "New Flow Description",
            "company": self.company1.id,
        }
        response = self.client.post("/api/flows/", new_flow_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["recruiter"], self.recruiter1.id)

        # Test flow access for recruiter2
        self.client.force_authenticate(user=self.user2)
        response = self.client.get("/api/flows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Should only see their company's flows
        self.assertEqual(response.data[0]["name"], self.flow2.name)

    def test_flow_steps_api(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing steps for own flow
        response = self.client.get(f"/api/flows/{self.flow1.id}/steps/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Test accessing steps from another company's flow
        response = self.client.get(f"/api/flows/{self.flow2.id}/steps/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test creating a step
        new_step_data = {
            "name": "System Design Interview",
            "step_type": "system_design",
            "duration_minutes": 90,
            "order": 2,
            "description": "System design interview description",
        }
        response = self.client.post(f"/api/flows/{self.flow1.id}/steps/", new_step_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], new_step_data["name"])

        # Test creating a step in another company's flow
        response = self.client.post(f"/api/flows/{self.flow2.id}/steps/", new_step_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_flow_candidates_api(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing candidates for own flow
        response = self.client.get(f"/api/flows/{self.flow1.id}/candidates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Test accessing candidates from another company's flow
        response = self.client.get(f"/api/flows/{self.flow2.id}/candidates/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test creating a candidate
        new_candidate_data = {
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice@example.com",
            "resume_url": "http://example.com/resume3.pdf",
        }
        response = self.client.post(
            f"/api/flows/{self.flow1.id}/candidates/", new_candidate_data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["first_name"], new_candidate_data["first_name"])

        # Test creating a candidate in another company's flow
        response = self.client.post(
            f"/api/flows/{self.flow2.id}/candidates/", new_candidate_data
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_interviews_api(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing interviews
        response = self.client.get("/api/interviews/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data), 1
        )  # Should only see interviews from their company

        # Test creating an interview
        new_interview_data = {
            "candidate": self.candidate1.id,
            "step": self.step1.id,
            "status": "scheduled",
            "scheduled_at": "2024-03-21T10:00:00Z",
        }
        response = self.client.post("/api/interviews/", new_interview_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["interviewer"], self.recruiter1.id)

        # Test accessing interview detail
        response = self.client.get(f"/api/interviews/{self.interview1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["candidate"], self.candidate1.id)
