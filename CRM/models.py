from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

User = settings.AUTH_USER_MODEL

# =====================
# Custom User Model
# =====================
class User(AbstractUser):
    ROLE_CHOICES = (
        ('superuser', 'SuperUser'),
        ('admin', 'Administrator'),
        ('trainer', 'Trainer'),
        ('intern', 'Intern'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='intern')
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    plain_password = models.CharField(max_length=128, blank=True, null=True)  # ⚠️ unsafe in prod

    def __str__(self):
        return f"{self.username} ({self.role})"

class Course(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Batch(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="batches")
    description = models.TextField(blank=True, null=True)
    trainer = models.ForeignKey("TrainerProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_batches")
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        unique_together = ('name', 'course')  # batch name should be unique inside a course

    def __str__(self):
        return f"{self.name} ({self.course.name})"
    

# =====================
# Profiles
# =====================

class InternProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="intern_profile")
    unique_id = models.CharField(max_length=20, unique=True, editable=False)

    # Basic Info
    profile_photo = models.ImageField(upload_to="intern_profiles/", null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=(("Male", "Male"), ("Female", "Female"), ("Other", "Other")), blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    # Academic Info
    qualification = models.CharField(max_length=100, blank=True, null=True)  # e.g., B.Tech, MBA
    specialization = models.CharField(max_length=100, blank=True, null=True)
    college = models.CharField(max_length=200, blank=True, null=True)
    university = models.CharField(max_length=200, blank=True, null=True)
    graduation_year = models.PositiveIntegerField(blank=True, null=True)
    aggregate_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    # Skills & Experience
    skills = models.TextField(blank=True, null=True)  # comma-separated or JSON if advanced
    prior_experience = models.TextField(blank=True, null=True)

    # Internship Motivation
    why_choose = models.TextField(blank=True, null=True)
    expectations = models.TextField(blank=True, null=True)
    career_goals = models.TextField(blank=True, null=True)

    # Internship Details
    batch = models.ForeignKey("Batch", on_delete=models.SET_NULL, null=True, blank=True, related_name="interns")
    project_title = models.CharField(max_length=255, blank=True, null=True)

    # Device & Docs
    device_access = models.BooleanField(default=False)  # True if intern has laptop/PC
    resume = models.FileField(upload_to="intern_docs/resume/", null=True, blank=True)
    cover_letter = models.FileField(upload_to="intern_docs/cover_letters/", null=True, blank=True)
    college_id_card = models.FileField(upload_to="intern_docs/id_cards/", null=True, blank=True)

    # Emergency & Guardian Info
    emergency_contact_name = models.CharField(max_length=150, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    guardian_name = models.CharField(max_length=150, blank=True, null=True)
    guardian_contact = models.CharField(max_length=15, blank=True, null=True)

    # Links
    linkedin_profile = models.URLField(blank=True, null=True)
    portfolio_link = models.URLField(blank=True, null=True)

    # Reference 
    reference = models.CharField(max_length=200, blank=True, null=True)  # "How did you hear about us?"


    # Certificates & Status
    undertaking_generated = models.BooleanField(default=False)
    completion_certificate_generated = models.BooleanField(default=False)
    lor_generated = models.BooleanField(default=False)
    internship_status = models.CharField(
        max_length=20,
        choices=(("Ongoing", "Ongoing"), ("Completed", "Completed"), ("Dropped", "Dropped")),
        default="Ongoing"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.unique_id} - {self.user.get_full_name()}"


class TrainerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="trainer_profile")
    expertise = models.CharField(max_length=150, blank=True, null=True)
    

    def __str__(self):
        return self.user.username


class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    office_location = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return self.user.username


class SuperUserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="superuser_profile")
    privileges = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username


# =====================
# Attendance
# =====================
class Attendance(models.Model):
    intern = models.ForeignKey(InternProfile, on_delete=models.CASCADE, related_name="attendance_records")
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="attendance_marked")
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=(("Present", "Present"), ("Absent", "Absent")))

    class Meta:
        unique_together = ('intern', 'date')  # prevent duplicate entries

    def __str__(self):
        return f"{self.intern.unique_id} - {self.date} - {self.status}"


# =====================
# File Sharing (Lessons)
# =====================
class LessonFile(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="uploaded_files")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="lessons/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


