from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from interviews.models import Candidate, Company, Flow, Recruiter

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
        self.company = Company.objects.create(
            name="Test Company", description="Test Description"
        )

        # Create recruiter for the user
        self.recruiter = Recruiter.objects.create(user=self.user, company=self.company)

        # Test flow data
        self.flow_data = {
            "company": self.company.id,
            "name": "Test Flow",
            "description": "A test flow for integration testing",
            "role": "engineering_data",
            "nodes": [
                {
                    "id": "1",
                    "type": "start",
                    "position": {"x": 0, "y": 0},
                    "data": {"label": "Start"},
                },
                {
                    "id": "2",
                    "type": "question",
                    "position": {"x": 100, "y": 100},
                    "data": {
                        "label": "Test Question",
                        "question": "What is your name?",
                        "type": "text",
                    },
                },
            ],
            "edges": [{"id": "e1-2", "source": "1", "target": "2", "type": "default"}],
        }

    def test_create_and_retrieve_flow(self):
        # Test creating a flow
        create_url = reverse("flow-list")
        response = self.client.post(create_url, self.flow_data, format="json")
        print(
            "Create Flow Response:", response.status_code, response.data
        )  # Debug print
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        flow_id = response.data["id"]

        # Test retrieving flow list
        list_url = reverse("flow-list")
        response = self.client.get(list_url)
        print("List Flow Response:", response.status_code, response.data)  # Debug print
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], self.flow_data["name"])

        # Test retrieving flow detail
        detail_url = reverse("flow-detail", kwargs={"pk": flow_id})
        response = self.client.get(detail_url)
        print(
            "Detail Flow Response:", response.status_code, response.data
        )  # Debug print
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.flow_data["name"])
        self.assertEqual(response.data["company"], self.company.id)
        self.assertEqual(
            response.data["recruiter"]["id"], self.recruiter.id
        )  # Check nested recruiter ID

    def test_edit_flow(self):
        # Create initial flow
        create_url = reverse("flow-list")
        response = self.client.post(create_url, self.flow_data, format="json")
        print(
            "Create Flow Response:", response.status_code, response.data
        )  # Debug print
        flow_id = response.data["id"]

        # Edit flow data
        updated_data = self.flow_data.copy()
        updated_data["name"] = "Updated Flow"
        updated_data["description"] = "Updated description"

        # Test updating flow
        detail_url = reverse("flow-detail", kwargs={"pk": flow_id})
        response = self.client.put(detail_url, updated_data, format="json")
        print(
            "Update Flow Response:", response.status_code, response.data
        )  # Debug print
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated Flow")
        self.assertEqual(response.data["description"], "Updated description")

        # Verify changes in list view
        list_url = reverse("flow-list")
        response = self.client.get(list_url)
        print("List Flow Response:", response.status_code, response.data)  # Debug print
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], "Updated Flow")

    def test_create_candidate(self):
        # Create a flow first
        create_flow_url = reverse("flow-list")
        flow_response = self.client.post(create_flow_url, self.flow_data, format="json")
        print(
            "Create Flow Response:", flow_response.status_code, flow_response.data
        )  # Debug print
        flow_id = flow_response.data["id"]

        # Create candidate data
        candidate_data = {
            "flow": flow_id,
            "first_name": "Test",
            "last_name": "Candidate",
            "email": "candidate@example.com",
        }

        # Test creating candidate
        create_candidate_url = reverse("candidate-list")
        response = self.client.post(create_candidate_url, candidate_data, format="json")
        print(
            "Create Candidate Response:", response.status_code, response.data
        )  # Debug print
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["first_name"], candidate_data["first_name"])
        self.assertEqual(response.data["last_name"], candidate_data["last_name"])
        self.assertEqual(response.data["flow"], flow_id)

        # Verify candidate in list view
        list_url = reverse("candidate-list")
        response = self.client.get(list_url)
        print(
            "List Candidate Response:", response.status_code, response.data
        )  # Debug print
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["email"], candidate_data["email"])
