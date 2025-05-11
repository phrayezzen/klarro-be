import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .storage import CandidateProfilePictureStorage, CandidateResumeStorage


class Company(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "companies"


class Recruiter(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="recruiter"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="recruiters"
    )
    is_admin = models.BooleanField(default=False)
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
    role_name = models.CharField(max_length=255)
    role_description = models.TextField()
    role_function = models.CharField(max_length=20, choices=ROLE_CHOICES)
    location = models.CharField(max_length=255, null=True, blank=True)
    is_remote_allowed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.role_name


class Step(models.Model):
    STEP_TYPES = [
        ("technical", "Technical"),
        ("behavioral", "Behavioral"),
        ("project", "Project"),
    ]

    TONE_CHOICES = [
        ("friendly", "Friendly & Supportive"),
        ("professional", "Professional & Neutral"),
        ("challenging", "Challenging & High-Bar"),
        ("casual", "Casual & Conversational"),
    ]

    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name="steps")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    step_type = models.CharField(max_length=20, choices=STEP_TYPES)
    duration_minutes = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(480)]
    )
    order = models.IntegerField()
    interviewer_tone = models.CharField(
        max_length=20, choices=TONE_CHOICES, default="professional"
    )
    assessed_skills = models.JSONField(default=list)  # List of skills to assess
    custom_questions = models.JSONField(default=list)  # List of custom questions
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["flow", "order"]
        ordering = ["flow", "order"]

    def __str__(self):
        return f"{self.flow.role_name} - {self.name} ({self.get_step_type_display()})"


class ProjectStep(Step):
    FILE_FORMAT_CHOICES = [
        ("pdf", "PDF Document"),
        ("zip", "ZIP Archive"),
        ("github", "GitHub Repository"),
        ("doc", "Word Document"),
        ("other", "Other Format"),
    ]

    title = models.CharField(max_length=255)
    instructions = models.TextField()
    file_format = models.CharField(max_length=50, choices=FILE_FORMAT_CHOICES)

    class Meta:
        verbose_name = "Project Step"
        verbose_name_plural = "Project Steps"


class Candidate(models.Model):
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name="candidates")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    resume = models.FileField(
        upload_to="", storage=CandidateResumeStorage(), null=True, blank=True
    )
    profile_picture = models.ImageField(
        upload_to="", storage=CandidateProfilePictureStorage(), null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("complete", "Complete"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="not_started"
    )

    # Score fields
    job_match_score = models.FloatField(null=True, blank=True)
    experience_score = models.FloatField(null=True, blank=True)
    education_score = models.FloatField(null=True, blank=True)
    behavioral_score = models.FloatField(null=True, blank=True)
    technical_score = models.FloatField(null=True, blank=True)
    preferences_score = models.FloatField(null=True, blank=True)

    # Evaluation fields
    experience_evaluation = models.TextField(null=True, blank=True)
    education_evaluation = models.TextField(null=True, blank=True)
    behavioral_evaluation = models.TextField(null=True, blank=True)
    technical_evaluation = models.TextField(null=True, blank=True)
    preferences_evaluation = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ["email", "flow"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def update_status(self):
        if not self.flow:
            self.status = "in_progress"
            self.save(update_fields=["status"])
            return
        total_steps = self.flow.steps.count()
        total_interviews = self.interviews.count()
        completed_interviews = self.interviews.filter(status="completed").count()
        if total_interviews == 0:
            self.status = "not_started"
        elif completed_interviews == total_steps and total_steps > 0:
            self.status = "complete"
        else:
            self.status = "in_progress"
        self.save(update_fields=["status"])


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


# --- SIGNALS ---
@receiver(post_save, sender=Interview)
def update_candidate_status_on_save(sender, instance, **kwargs):
    if instance.candidate:
        instance.candidate.update_status()


@receiver(post_delete, sender=Interview)
def update_candidate_status_on_delete(sender, instance, **kwargs):
    if instance.candidate:
        instance.candidate.update_status()
