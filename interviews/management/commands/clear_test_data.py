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
    help = "Clears all test data from the database"

    def handle(self, *args, **kwargs):
        self.stdout.write("Clearing test data...")

        # Delete in reverse order of dependencies
        Interview.objects.all().delete()
        self.stdout.write("Deleted all interviews")

        Candidate.objects.all().delete()
        self.stdout.write("Deleted all candidates")

        ProjectStep.objects.all().delete()
        Step.objects.all().delete()
        self.stdout.write("Deleted all steps")

        Flow.objects.all().delete()
        self.stdout.write("Deleted all flows")

        Recruiter.objects.all().delete()
        self.stdout.write("Deleted all recruiters")

        Company.objects.all().delete()
        self.stdout.write("Deleted all companies")

        # Delete test users (those with username starting with 'recruiter_')
        User.objects.filter(username__startswith="recruiter_").delete()
        self.stdout.write("Deleted all test users")

        self.stdout.write(self.style.SUCCESS("Successfully cleared all test data!"))
