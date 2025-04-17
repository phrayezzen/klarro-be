# interviews/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Company, Recruiter, Flow, Step, Candidate, Interview

# Unregister the default User admin
admin.site.unregister(User)

# Create an inline admin for Recruiter
class RecruiterInline(admin.StackedInline):
    model = Recruiter
    can_delete = False
    verbose_name_plural = 'Recruiter'

# Create a new User admin that includes the Recruiter inline
class CustomUserAdmin(UserAdmin):
    inlines = (RecruiterInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_company')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    def get_company(self, obj):
        if hasattr(obj, 'recruiter'):
            return obj.recruiter.company.name
        return None
    get_company.short_description = 'Company'

# Register the new User admin
admin.site.register(User, CustomUserAdmin)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)

@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'company', 'created_at')
    list_filter = ('company', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Name'

@admin.register(Flow)
class FlowAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'recruiter', 'created_at')
    list_filter = ('company', 'recruiter', 'created_at')
    search_fields = ('name', 'description')
    raw_id_fields = ('recruiter',)

@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ('name', 'flow', 'step_type', 'duration_minutes', 'order')
    list_filter = ('step_type', 'flow', 'created_at')
    search_fields = ('name', 'description')
    raw_id_fields = ('flow',)

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'email', 'flow', 'created_at')
    list_filter = ('flow', 'created_at')
    search_fields = ('first_name', 'last_name', 'email')
    raw_id_fields = ('flow',)

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_full_name.short_description = 'Name'

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'step', 'status', 'interviewer', 'completed_at')
    list_filter = ('status', 'step__flow', 'completed_at')
    search_fields = ('candidate__first_name', 'candidate__last_name', 'candidate__email')
    raw_id_fields = ('candidate', 'step', 'interviewer')
