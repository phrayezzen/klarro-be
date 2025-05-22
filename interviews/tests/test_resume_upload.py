from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from ..models import Candidate, Company, Flow, Recruiter


class ResumeUploadTests(TestCase):
    def setUp(self):
        # Create test user and company
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.company = Company.objects.create(name="Test Company")
        self.recruiter = Recruiter.objects.create(user=self.user, company=self.company)

        # Create test flow
        self.flow = Flow.objects.create(
            company=self.company,
            recruiter=self.recruiter,
            role_name="Test Flow",
            role_description="Test Description",
            role_function="engineering_data",
            location="San Francisco, CA",
            is_remote_allowed=True,
        )

        # Create test client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create test PDF file
        self.resume_file = SimpleUploadedFile(
            "test_resume.pdf", b"Test resume content", content_type="application/pdf"
        )

        # Create test candidate
        self.candidate = Candidate.objects.create(
            flow=self.flow, first_name="John", last_name="Doe", email="test@example.com"
        )

    def test_create_candidate_with_resume(self):
        """Test creating a candidate with a resume file."""
        url = "/api/v1/candidates/"
        data = {
            "flow_id": self.flow.id,
            "first_name": "John",
            "last_name": "Doe",
            "email": "unique_test@example.com",
            "resume": self.resume_file,
        }
        with patch("interviews.tasks.evaluate_resume_task") as mock_task:
            mock_task.delay = lambda *a, **kw: None
            response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("resume", response.data)
        self.assertRegex(
            response.data["resume"],
            r"(https?://[^/]+)?/\d{4}/\d{2}/\d{2}/[a-zA-Z0-9_-]+\.pdf$",
        )

    def test_update_candidate_resume(self):
        """Test updating a candidate's resume."""
        url = f"/api/v1/candidates/{self.candidate.id}/"
        data = {"resume": self.resume_file}
        with patch("interviews.tasks.evaluate_resume_task") as mock_task:
            mock_task.delay = lambda *a, **kw: None
            response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("resume", response.data)
        self.assertRegex(
            response.data["resume"],
            r"(https?://[^/]+)?/\d{4}/\d{2}/\d{2}/[a-zA-Z0-9_-]+\.pdf$",
        )

    def test_delete_candidate_resume(self):
        """Test deleting a candidate's resume."""
        url = f"/api/v1/candidates/{self.candidate.id}/"
        data = {"resume": ""}
        with patch("interviews.tasks.evaluate_resume_task") as mock_task:
            mock_task.delay = lambda *a, **kw: None
            response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["resume"])
        self.candidate.refresh_from_db()
        self.assertFalse(self.candidate.resume.name)
