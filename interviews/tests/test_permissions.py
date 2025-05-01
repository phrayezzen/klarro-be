from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView

from ..models import Candidate, Company, Flow, Interview, Recruiter, Step
from ..permissions import IsCompanyMember, IsFlowOwner, IsRecruiter


class PermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = APIView()

        # Create test data
        self.company1 = Company.objects.create(name="Test Company 1")
        self.company2 = Company.objects.create(name="Test Company 2")

        self.user1 = User.objects.create_user(username="user1", password="testpass")
        self.user2 = User.objects.create_user(username="user2", password="testpass")
        self.user3 = User.objects.create_user(username="user3", password="testpass")

        self.recruiter1 = Recruiter.objects.create(
            user=self.user1, company=self.company1
        )
        self.recruiter2 = Recruiter.objects.create(
            user=self.user2, company=self.company2
        )

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

    def test_is_recruiter_permission(self):
        # Test with recruiter user
        request = self.factory.get("/")
        request.user = self.user1
        permission = IsRecruiter()
        self.assertTrue(permission.has_permission(request, self.view))

        # Test with non-recruiter user
        request.user = self.user3
        self.assertFalse(permission.has_permission(request, self.view))

        # Test with anonymous user
        request.user = None
        self.assertFalse(permission.has_permission(request, self.view))

    def test_is_company_member_permission(self):
        permission = IsCompanyMember()

        # Test list/create permission with company_id
        request = self.factory.get("/", {"company_id": self.company1.id})
        request.user = self.user1
        self.assertTrue(permission.has_permission(request, self.view))

        request = self.factory.get("/", {"company_id": self.company2.id})
        request.user = self.user1
        self.assertFalse(permission.has_permission(request, self.view))

        # Test object permission for Company
        request = self.factory.get("/")
        request.user = self.user1
        self.assertTrue(
            permission.has_object_permission(request, self.view, self.company1)
        )
        self.assertFalse(
            permission.has_object_permission(request, self.view, self.company2)
        )

        # Test object permission for Flow
        self.assertTrue(
            permission.has_object_permission(request, self.view, self.flow1)
        )

        # Test object permission for Step
        self.assertTrue(
            permission.has_object_permission(request, self.view, self.step1)
        )

        # Test object permission for Candidate
        self.assertTrue(
            permission.has_object_permission(request, self.view, self.candidate1)
        )

        # Test object permission for Interview
        self.assertTrue(
            permission.has_object_permission(request, self.view, self.interview1)
        )

    def test_is_flow_owner_permission(self):
        permission = IsFlowOwner()
        request = self.factory.get("/")

        # Test with flow owner
        request.user = self.user1
        self.assertTrue(
            permission.has_object_permission(request, self.view, self.flow1)
        )

        # Test with non-owner
        request.user = self.user2
        self.assertFalse(
            permission.has_object_permission(request, self.view, self.flow1)
        )

    def test_company_member_permission_without_company_id(self):
        permission = IsCompanyMember()

        # Test list/create permission without company_id
        request = self.factory.get("/")
        request.user = self.user1
        self.assertTrue(permission.has_permission(request, self.view))

        # Test with non-recruiter user
        request.user = self.user3
        self.assertFalse(permission.has_permission(request, self.view))

    def test_company_member_permission_with_invalid_company_id(self):
        permission = IsCompanyMember()

        # Test with invalid company_id
        request = self.factory.get("/", {"company_id": 999})
        request.user = self.user1
        self.assertFalse(permission.has_permission(request, self.view))

        # Test with non-integer company_id
        request = self.factory.get("/", {"company_id": "invalid"})
        request.user = self.user1
        self.assertFalse(permission.has_permission(request, self.view))


class IsCompanyAdminTestCase(TestCase):
    """Test cases for IsCompanyAdmin permission class."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.company = Company.objects.create(name="Test Company")
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password="testpass123"
        )
        self.non_admin = User.objects.create_user(
            username="nonadmin", email="nonadmin@example.com", password="testpass123"
        )
        self.company.admins.add(self.admin)

    def test_admin_access(self):
        """Test that company admin has access."""
        self.client.force_authenticate(user=self.admin)
        flow = Flow.objects.create(
            name="Test Flow", description="Test Description", company=self.company
        )
        url = f"/api/flows/{flow.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_admin_access(self):
        """Test that non-admin user does not have access."""
        self.client.force_authenticate(user=self.non_admin)
        flow = Flow.objects.create(
            name="Test Flow", description="Test Description", company=self.company
        )
        url = f"/api/flows/{flow.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class IsRecruiterTestCase(TestCase):
    """Test cases for IsRecruiter permission class."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.company = Company.objects.create(name="Test Company")
        self.recruiter = User.objects.create_user(
            username="recruiter", email="recruiter@example.com", password="testpass123"
        )
        self.non_recruiter = User.objects.create_user(
            username="nonrecruiter",
            email="nonrecruiter@example.com",
            password="testpass123",
        )
        self.company.recruiters.add(self.recruiter)

    def test_recruiter_access(self):
        """Test that recruiter has access."""
        self.client.force_authenticate(user=self.recruiter)
        flow = Flow.objects.create(
            name="Test Flow", description="Test Description", company=self.company
        )
        url = f"/api/flows/{flow.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_recruiter_access(self):
        """Test that non-recruiter user does not have access."""
        self.client.force_authenticate(user=self.non_recruiter)
        flow = Flow.objects.create(
            name="Test Flow", description="Test Description", company=self.company
        )
        url = f"/api/flows/{flow.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class IsCompanyMemberTestCase(TestCase):
    """Test cases for IsCompanyMember permission class."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.company = Company.objects.create(name="Test Company")
        self.member = User.objects.create_user(
            username="member", email="member@example.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@example.com", password="testpass123"
        )
        self.company.recruiters.add(self.member)

    def test_member_access(self):
        """Test that company member has access."""
        self.client.force_authenticate(user=self.member)
        flow = Flow.objects.create(
            name="Test Flow", description="Test Description", company=self.company
        )
        url = f"/api/flows/{flow.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_member_access(self):
        """Test that non-member user does not have access."""
        self.client.force_authenticate(user=self.non_member)
        flow = Flow.objects.create(
            name="Test Flow", description="Test Description", company=self.company
        )
        url = f"/api/flows/{flow.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
