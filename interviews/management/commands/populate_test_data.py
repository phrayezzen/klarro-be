import random
import uuid
from datetime import timedelta, timezone

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from interviews.models import Candidate, Company, Flow, Interview, Recruiter, Step


class Command(BaseCommand):
    help = "Populates the database with test data"

    def handle(self, *args, **kwargs):
        self.stdout.write("Creating test data...")

        # Create companies
        companies = []
        company_names = ["TechCorp", "InnovateX", "FutureTech"]
        for name in company_names:
            company = Company.objects.create(
                name=name, description=f"Description for {name}"
            )
            companies.append(company)
            self.stdout.write(f"Created company: {name}")

        # Create users and recruiters
        recruiters = []
        for company in companies:
            num_recruiters = random.randint(2, 5)
            for i in range(num_recruiters):
                username = f"recruiter_{company.name.lower()}_{i+1}"
                user = User.objects.create_user(
                    username=username,
                    email=f"{username}@example.com",
                    password="testpass123",
                    first_name=f"Recruiter {i+1}",
                    last_name=company.name,
                )
                recruiter = Recruiter.objects.create(user=user, company=company)
                recruiters.append(recruiter)
                self.stdout.write(f"Created recruiter: {username} for {company.name}")

        # Create flows
        flows = []
        flow_names = [
            "Software Engineer",
            "Data Scientist",
            "Product Manager",
            "DevOps Engineer",
        ]
        for company in companies:
            num_flows = random.randint(1, 2)
            company_recruiters = [r for r in recruiters if r.company == company]
            for i in range(num_flows):
                flow = Flow.objects.create(
                    company=company,
                    recruiter=random.choice(company_recruiters),
                    name=f"{random.choice(flow_names)} Hiring Process",
                    description=f"Interview process for {random.choice(flow_names)} position",
                )
                flows.append(flow)
                self.stdout.write(f"Created flow: {flow.name} for {company.name}")

        # Create steps
        steps = []
        step_types = [
            "technical",
            "behavioral",
            "system_design",
            "coding",
            "case_study",
        ]
        for flow in flows:
            for i in range(3):  # 3 steps per flow
                step = Step.objects.create(
                    flow=flow,
                    name=f"Step {i+1}: {random.choice(step_types).title()} Interview",
                    step_type=random.choice(step_types),
                    duration_minutes=random.choice([30, 45, 60, 90]),
                    order=i + 1,
                    description=f"Description for {random.choice(step_types)} interview",
                )
                steps.append(step)
                self.stdout.write(f"Created step: {step.name} for {flow.name}")

        # Create candidates
        candidates = []
        first_names = [
            "John",
            "Jane",
            "Michael",
            "Emily",
            "David",
            "Sarah",
            "Robert",
            "Jessica",
        ]
        last_names = [
            "Smith",
            "Johnson",
            "Williams",
            "Brown",
            "Jones",
            "Garcia",
            "Miller",
            "Davis",
        ]
        for flow in flows:
            for i in range(5):  # 5 candidates per flow
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                unique_id = str(uuid.uuid4())[
                    :8
                ]  # Use first 8 characters of UUID for uniqueness
                candidate = Candidate.objects.create(
                    flow=flow,
                    first_name=first_name,
                    last_name=last_name,
                    email=f"{first_name.lower()}.{last_name.lower()}.{unique_id}@example.com",
                    resume_url=f"http://example.com/resumes/{first_name.lower()}_{last_name.lower()}_{unique_id}.pdf",
                )
                candidates.append(candidate)
                self.stdout.write(
                    f"Created candidate: {first_name} {last_name} for {flow.name}"
                )

        # Create interviews
        for candidate in candidates:
            flow = random.choice(flows)
            Interview.objects.create(
                candidate=candidate,
                flow=flow,
                status="scheduled",
                scheduled_at=timezone.now() + timedelta(days=random.randint(1, 30)),
            )
            self.stdout.write(
                self.style.SUCCESS("Successfully created test interviews")
            )

        self.stdout.write(self.style.SUCCESS("Successfully populated test data!"))
