#!/usr/bin/env python
from django.contrib.sessions.models import Session

Session.objects.all().delete()
