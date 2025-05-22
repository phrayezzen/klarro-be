from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Candidate, Company, Flow, Interview, Recruiter, Step


class FlowAPITests(APITestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        # Create test company
        self.company = Company.objects.create(
            name="Test Company", description="Test Description"
        )

        # Create recruiter for the user
        self.recruiter = Recruiter.objects.create(user=self.user, company=self.company)

        # Create test flow
        self.flow = Flow.objects.create(
            company=self.company,
            recruiter=self.recruiter,
            role_name="Test Flow",
            role_description="Test Flow Description",
            role_function="engineering_data",
            location="San Francisco, CA",
            is_remote_allowed=True,
        )

        # Create test steps
        self.step1 = Step.objects.create(
            flow=self.flow,
            name="Technical Screening",
            step_type="technical",
            duration_minutes=60,
            order=1,
        )
        self.step2 = Step.objects.create(
            flow=self.flow,
            name="Coding Challenge",
            step_type="coding",
            duration_minutes=90,
            order=2,
        )

        # Create test candidate
        self.candidate = Candidate.objects.create(
            flow=self.flow, first_name="John", last_name="Doe", email="john@example.com"
        )

    def test_create_flow(self):
        url = reverse("flow-list")
        data = {
            "company": self.company.id,
            "role_name": "New Flow",
            "role_description": "New Flow Description",
            "role_function": "engineering_data",
            "location": "San Francisco, CA",
            "is_remote_allowed": True,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Flow.objects.count(), 2)
        self.assertEqual(Flow.objects.get(id=response.data["id"]).role_name, "New Flow")
        self.assertEqual(
            Flow.objects.get(id=response.data["id"]).recruiter, self.recruiter
        )

    def test_get_flow_steps(self):
        url = reverse("flow-steps", args=[self.flow.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["name"], "Technical Screening")
        self.assertEqual(response.data[1]["name"], "Coding Challenge")

    def test_get_flow_candidates(self):
        url = reverse("flow-candidates", args=[self.flow.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["email"], "john@example.com")

    def test_create_step(self):
        url = reverse("step-list")
        data = {
            "flow": self.flow.id,
            "name": "System Design",
            "step_type": "system_design",
            "duration_minutes": 45,
            "order": 3,
            "description": "System design step",
            "interviewer_tone": "professional",
            "assessed_skills": [],
            "custom_questions": [],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Step.objects.count(), 3)
        self.assertEqual(Step.objects.get(id=response.data["id"]).name, "System Design")

    def test_get_step_interviews(self):
        # Create an interview for the step
        Interview.objects.create(
            candidate=self.candidate,
            step=self.step1,
            interviewer=self.recruiter,
            status="completed",
        )

        url = reverse("step-interviews", args=[self.step1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["status"], "completed")

    def test_create_candidate(self):
        url = reverse("candidate-list")
        data = {
            "flow": self.flow.id,
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Candidate.objects.count(), 2)
        self.assertEqual(
            Candidate.objects.get(id=response.data["id"]).email, "jane@example.com"
        )

    def test_get_candidate_interviews(self):
        # Create an interview for the candidate
        Interview.objects.create(
            candidate=self.candidate,
            step=self.step1,
            interviewer=self.recruiter,
            status="pending",
        )

        url = reverse("candidate-interviews", args=[self.candidate.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["status"], "pending")

    def test_create_interview(self):
        url = reverse("interview-list")
        data = {
            "candidate": self.candidate.id,
            "step": self.step1.id,
            "interviewer": self.recruiter.id,
            "status": "pending",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Interview.objects.count(), 1)
        self.assertEqual(
            Interview.objects.get(id=response.data["id"]).status, "pending"
        )

    def test_filter_interviews(self):
        # Create some interviews
        Interview.objects.create(
            candidate=self.candidate,
            step=self.step1,
            interviewer=self.recruiter,
            status="completed",
        )
        Interview.objects.create(
            candidate=self.candidate,
            step=self.step2,
            interviewer=self.recruiter,
            status="pending",
        )

        # Filter by candidate
        url = reverse("interview-list") + "?candidate_id=" + str(self.candidate.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Filter by step
        url = reverse("interview-list") + "?step_id=" + str(self.step1.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["status"], "completed")

    def test_unauthorized_access(self):
        self.client.force_authenticate(user=None)
        url = reverse("flow-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_step_type(self):
        url = reverse("step-list")
        data = {
            "flow": self.flow.id,
            "name": "Invalid Step",
            "step_type": "invalid_type",
            "duration_minutes": 30,
            "order": 3,
            "description": "Invalid step type",
            "interviewer_tone": "professional",
            "assessed_skills": [],
            "custom_questions": [],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
