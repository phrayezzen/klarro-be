from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
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
            role_name="Test Role",
            role_description="Test Description",
            role_function="engineering_data",
        )

        # Create test client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create test PDF file
        self.test_file = SimpleUploadedFile(
            "test_resume.pdf", b"file_content", content_type="application/pdf"
        )

    def test_create_candidate_with_resume(self):
        """Test creating a candidate with a resume file."""
        url = reverse("candidate-list")
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "flow": self.flow.id,
            "resume": self.test_file,
        }

        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify candidate was created
        candidate = Candidate.objects.get(email="john@example.com")
        self.assertIsNotNone(candidate.resume)
        # Check if the path follows YYYY/MM/DD format
        self.assertRegex(candidate.resume.name, r"^\d{4}/\d{2}/\d{2}/")

        # Verify resume URL is in response
        self.assertIn("resume_url", response.data)
        self.assertIsNotNone(response.data["resume_url"])

    def test_update_candidate_resume(self):
        """Test updating a candidate's resume."""
        # Create initial candidate
        candidate = Candidate.objects.create(
            flow=self.flow, first_name="John", last_name="Doe", email="john@example.com"
        )

        # Update resume
        url = reverse("candidate-detail", args=[candidate.id])
        data = {"resume": self.test_file}

        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify resume was updated
        candidate.refresh_from_db()
        self.assertIsNotNone(candidate.resume)
        # Check if the path follows YYYY/MM/DD format
        self.assertRegex(candidate.resume.name, r"^\d{4}/\d{2}/\d{2}/")

    def test_delete_candidate_resume(self):
        """Test deleting a candidate's resume."""
        # Create candidate with resume
        candidate = Candidate.objects.create(
            flow=self.flow,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            resume=self.test_file,
        )

        # Delete resume
        url = reverse("candidate-detail", args=[candidate.id])
        data = {"resume": ""}

        response = self.client.patch(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify resume was deleted
        candidate.refresh_from_db()
        self.assertFalse(bool(candidate.resume))
