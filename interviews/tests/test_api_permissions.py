from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ..models import Candidate, Company, Flow, Interview, Recruiter, Step


class APIPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create test data
        self.company1 = Company.objects.create(name="Test Company 1")
        self.company2 = Company.objects.create(name="Test Company 2")

        # Create users and recruiters
        self.user1 = User.objects.create_user(username="user1", password="testpass")
        self.user2 = User.objects.create_user(username="user2", password="testpass")
        self.user3 = User.objects.create_user(username="user3", password="testpass")

        self.recruiter1 = Recruiter.objects.create(
            user=self.user1, company=self.company1
        )
        self.recruiter2 = Recruiter.objects.create(
            user=self.user2, company=self.company2
        )

        # Create flow and related objects
        self.flow1 = Flow.objects.create(
            company=self.company1, recruiter=self.recruiter1, name="Test Flow 1"
        )

        self.step1 = Step.objects.create(
            flow=self.flow1,
            name="Test Step",
            step_type="technical",
            duration_minutes=60,
            order=1,
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
        # Test unauthenticated access
        response = self.client.get(reverse("company-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test non-recruiter access
        self.client.force_authenticate(user=self.user3)
        response = self.client.get(reverse("company-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test recruiter access to own company
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse("company-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.company1.id)

        # Test recruiter access to other company
        response = self.client.get(reverse("company-detail", args=[self.company2.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_flow_api_permissions(self):
        # Test unauthenticated access
        response = self.client.get(reverse("flow-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test non-recruiter access
        self.client.force_authenticate(user=self.user3)
        response = self.client.get(reverse("flow-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test recruiter access to own flows
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse("flow-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.flow1.id)

        # Test creating flow with different company
        data = {
            "company": self.company2.id,
            "name": "New Flow",
            "description": "Test description",
        }
        response = self.client.post(reverse("flow-list"), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_flow_steps_permissions(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing steps through flow endpoint
        response = self.client.get(reverse("flow-steps", args=[self.flow1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.step1.id)

        # Test creating step through flow endpoint
        data = {
            "name": "New Step",
            "step_type": "technical",
            "duration_minutes": 30,
            "order": 2,
        }
        response = self.client.post(reverse("flow-steps", args=[self.flow1.id]), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test updating step through flow endpoint
        data = {"name": "Updated Step Name"}
        response = self.client.patch(
            reverse("flow-steps-detail", args=[self.flow1.id, self.step1.id]), data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated Step Name")

        # Test deleting step through flow endpoint
        response = self.client.delete(
            reverse("flow-steps-detail", args=[self.flow1.id, self.step1.id])
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Test direct access to steps endpoint (should be forbidden)
        response = self.client.get(reverse("step-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_flow_candidates_permissions(self):
        self.client.force_authenticate(user=self.user1)

        # Test listing candidates through flow endpoint
        response = self.client.get(reverse("flow-candidates", args=[self.flow1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.candidate1.id)

        # Test creating candidate through flow endpoint
        data = {"first_name": "Jane", "last_name": "Smith", "email": "jane@example.com"}
        response = self.client.post(
            reverse("flow-candidates", args=[self.flow1.id]), data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test updating candidate through flow endpoint
        data = {"first_name": "Updated Name"}
        response = self.client.patch(
            reverse("flow-candidates-detail", args=[self.flow1.id, self.candidate1.id]),
            data,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Updated Name")

        # Test deleting candidate through flow endpoint
        response = self.client.delete(
            reverse("flow-candidates-detail", args=[self.flow1.id, self.candidate1.id])
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Test direct access to candidates endpoint (should be forbidden)
        response = self.client.get(reverse("candidate-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_interview_api_permissions(self):
        # Test unauthenticated access
        response = self.client.get(reverse("interview-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test non-recruiter access
        self.client.force_authenticate(user=self.user3)
        response = self.client.get(reverse("interview-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test recruiter access to own company's interviews
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse("interview-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.interview1.id)

        # Test creating interview
        data = {
            "candidate": self.candidate1.id,
            "step": self.step1.id,
            "interviewer": self.recruiter1.id,
        }
        response = self.client.post(reverse("interview-list"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_filtering_permissions(self):
        self.client.force_authenticate(user=self.user1)

        # Test filtering interviews by candidate and step
        response = self.client.get(
            reverse("interview-list"),
            {"candidate_id": self.candidate1.id, "step_id": self.step1.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
