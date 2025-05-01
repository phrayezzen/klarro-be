from django.contrib.auth.models import User

from interviews.models import Company, Recruiter


def create_test_user():
    # Create a test company
    company = Company.objects.create(
        name="Test Company", description="A test company for development"
    )

    # Create a test user
    user = User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )

    # Create a recruiter profile for the user
    Recruiter.objects.create(user=user, company=company)

    print("Test user created successfully!")
    print("Username: testuser")
    print("Password: testpass123")


if __name__ == "__main__":
    create_test_user()
