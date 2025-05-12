import random
import uuid
from datetime import timedelta, timezone

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from interviews.models import (
    Candidate,
    Company,
    Flow,
    Interview,
    ProjectStep,
    Recruiter,
    Step,
)


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
                username = f"recruiter_{company.name.lower()}_{i + 1}"
                user = User.objects.create_user(
                    username=username,
                    email=f"{username}@example.com",
                    password="testpass123",
                    first_name=f"Recruiter {i + 1}",
                    last_name=company.name,
                )
                recruiter = Recruiter.objects.create(
                    user=user,
                    company=company,
                    is_admin=(i == 0),  # First recruiter is admin
                )
                recruiters.append(recruiter)
                self.stdout.write(f"Created recruiter: {username} for {company.name}")

        # Create flows
        flows = []
        role_functions = [choice[0] for choice in Flow.ROLE_CHOICES]
        role_names = [
            "Senior Software Engineer",
            "Data Scientist",
            "Product Manager",
            "DevOps Engineer",
            "Frontend Developer",
            "Backend Developer",
            "Full Stack Developer",
            "Machine Learning Engineer",
        ]
        locations = [
            "San Francisco, CA",
            "New York, NY",
            "Remote",
            "London, UK",
            "Berlin, Germany",
        ]

        for company in companies:
            num_flows = random.randint(1, 3)
            company_recruiters = [r for r in recruiters if r.company == company]
            for i in range(num_flows):
                role_name = random.choice(role_names)
                flow = Flow.objects.create(
                    company=company,
                    recruiter=random.choice(company_recruiters),
                    role_name=role_name,
                    role_description=f"Looking for a {role_name} to join our team",
                    role_function=random.choice(role_functions),
                    location=random.choice(locations),
                    is_remote_allowed=random.choice([True, False]),
                    is_active=True,
                )
                flows.append(flow)
                self.stdout.write(f"Created flow: {flow.role_name} for {company.name}")

        # Create steps
        steps = []
        step_types = [choice[0] for choice in Step.STEP_TYPES]
        tones = [choice[0] for choice in Step.TONE_CHOICES]
        skills = [
            "Python",
            "JavaScript",
            "React",
            "Django",
            "AWS",
            "Docker",
            "Kubernetes",
            "Machine Learning",
            "Data Analysis",
            "System Design",
            "Problem Solving",
            "Communication",
            "Leadership",
            "Teamwork",
        ]

        for flow in flows:
            # Create 2-3 steps per flow
            num_steps = random.randint(2, 3)
            for i in range(num_steps):
                step_type = random.choice(step_types)
                assessed_skills = random.sample(skills, random.randint(2, 4))
                custom_questions = [
                    "Tell me about your experience with {skill}",
                    "How would you approach {skill} in a real-world scenario?",
                    "What's the most challenging {skill} problem you've solved?",
                ]

                if step_type == "project":
                    step = ProjectStep.objects.create(
                        flow=flow,
                        name=f"Project Assignment {i + 1}",
                        description=f"Complete a project demonstrating your {', '.join(assessed_skills)} skills",
                        step_type=step_type,
                        duration_minutes=random.choice([60, 90, 120]),
                        order=i + 1,
                        interviewer_tone=random.choice(tones),
                        assessed_skills=assessed_skills,
                        custom_questions=custom_questions,
                        title=f"Project {i + 1}: {random.choice(['Web Application', 'API Design', 'Data Analysis'])}",
                        instructions="Create a project that demonstrates your technical skills and problem-solving abilities.",
                        file_format=random.choice(["pdf", "zip", "github"]),
                    )
                else:
                    step = Step.objects.create(
                        flow=flow,
                        name=f"{step_type.title()} Interview {i + 1}",
                        description=f"Interview focusing on {', '.join(assessed_skills)}",
                        step_type=step_type,
                        duration_minutes=random.choice([30, 45, 60]),
                        order=i + 1,
                        interviewer_tone=random.choice(tones),
                        assessed_skills=assessed_skills,
                        custom_questions=custom_questions,
                    )
                steps.append(step)
                self.stdout.write(f"Created step: {step.name} for {flow.role_name}")

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
            "William",
            "Emma",
            "James",
            "Olivia",
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
            "Rodriguez",
            "Martinez",
            "Hernandez",
            "Lopez",
        ]

        for flow in flows:
            # Create 3-5 candidates per flow
            num_candidates = random.randint(3, 5)
            for i in range(num_candidates):
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                unique_id = str(uuid.uuid4())[:8]
                candidate = Candidate.objects.create(
                    flow=flow,
                    first_name=first_name,
                    last_name=last_name,
                    email=f"{first_name.lower()}.{last_name.lower()}.{unique_id}@example.com",
                    status=random.choice(["not_started", "in_progress", "complete"]),
                )
                candidates.append(candidate)
                self.stdout.write(
                    f"Created candidate: {first_name} {last_name} for {flow.role_name}"
                )

        # Create interviews
        for candidate in candidates:
            flow = candidate.flow
            for step in flow.steps.all():
                status = random.choice(
                    ["pending", "in_progress", "completed", "cancelled"]
                )
                interview = Interview.objects.create(
                    candidate=candidate,
                    step=step,
                    interviewer=random.choice(
                        [r for r in recruiters if r.company == flow.company]
                    ),
                    status=status,
                    transcript=(
                        "Sample interview transcript" if status == "completed" else ""
                    ),
                    overall_score=(
                        random.uniform(1, 5) if status == "completed" else None
                    ),
                    cheating_flag=False,
                    completed_at=timezone.now() if status == "completed" else None,
                )
                self.stdout.write(f"Created interview: {interview}")

        self.stdout.write(self.style.SUCCESS("Successfully populated test data!"))
