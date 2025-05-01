from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Runs the Django shell with all models pre-imported"

    def handle(self, *args, **options):
        call_command("shell_plus")
