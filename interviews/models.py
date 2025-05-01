from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Recruiter(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="recruiter"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="recruiters"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.company.name})"


class Flow(models.Model):
    ROLE_CHOICES = [
        ("business_ops", "Business & Operations"),
        ("sales_cs", "Sales & Customer Success"),
        ("marketing_growth", "Marketing & Growth"),
        ("product_design", "Product & Design"),
        ("engineering_data", "Engineering & Data"),
        ("people_hr", "People & HR"),
        ("finance_legal", "Finance & Legal"),
        ("support_services", "Support & Services"),
        ("science_research", "Science & Research"),
        ("executive_leadership", "Executive & Leadership"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    recruiter = models.ForeignKey(
        Recruiter,
        on_delete=models.CASCADE,
        related_name="created_flows",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Step(models.Model):
    STEP_TYPE_CHOICES = [
        ("coding", "Coding Challenge"),
        ("system_design", "System Design"),
        ("behavioral", "Behavioral"),
        ("technical", "Technical Discussion"),
        ("case_study", "Case Study"),
        ("pair_programming", "Pair Programming"),
    ]

    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name="steps")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    step_type = models.CharField(max_length=20, choices=STEP_TYPE_CHOICES)
    duration_minutes = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(480)]
    )
    order = models.IntegerField()  # To maintain the sequence of steps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["flow", "order"]  # Ensure unique order within a flow
        ordering = ["flow", "order"]

    def __str__(self):
        return f"{self.flow.name} - {self.name} ({self.get_step_type_display()})"


class Candidate(models.Model):
    flow = models.ForeignKey(
        Flow, on_delete=models.CASCADE, related_name="candidates", null=True, blank=True
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    resume_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Interview(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="interviews",
        null=True,
        blank=True,
    )
    step = models.ForeignKey(
        Step, on_delete=models.CASCADE, related_name="interviews", null=True, blank=True
    )
    interviewer = models.ForeignKey(
        Recruiter,
        on_delete=models.SET_NULL,
        null=True,
        related_name="conducted_interviews",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    transcript = models.TextField(blank=True)
    overall_score = models.FloatField(null=True, blank=True)
    cheating_flag = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            "candidate",
            "step",
        ]  # A candidate can only do each step once

    def __str__(self):
        return f"{self.step.name} Interview of {self.candidate} for {self.flow}"
