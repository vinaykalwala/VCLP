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

    def get_role_display(self):
        """Get human-readable role name"""
        return dict(self.ROLE_CHOICES).get(self.role, self.role)
    
    
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
    timings=models.CharField(max_length=100, blank=True, null=True)  

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

    def delete(self, *args, **kwargs):
        # Delete associated user first
        if self.user:
            self.user.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.unique_id} - {self.user.get_full_name()}"


class TrainerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="trainer_profile")
    profile_photo = models.ImageField(upload_to="trainer_profiles/", null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    expertise = models.CharField(max_length=150, blank=True, null=True)  # e.g., Python, ML, DevOps
    years_of_experience = models.PositiveIntegerField(blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)  # e.g., Senior Trainer, Tech Lead
    highest_qualification = models.CharField(max_length=100, blank=True, null=True)

    availability = models.CharField(
        max_length=50,
        choices=(("Full-time", "Full-time"), ("Part-time", "Part-time"), ("Guest", "Guest")),
        default="Full-time"
    )
    linkedin_profile = models.URLField(blank=True, null=True)
    portfolio_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    profile_photo = models.ImageField(upload_to="admin_profiles/", null=True, blank=True)
    office_location = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class SuperUserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="superuser_profile")
    profile_photo = models.ImageField(upload_to="superuser_profiles/", null=True, blank=True)
    privileges = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
    batches = models.ManyToManyField("Batch", related_name="lessons")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="lessons/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class DailySessionUpdate(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="daily_updates")
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="daily_updates")
    date = models.DateField(auto_now_add=True)
    topic_covered = models.TextField()
    summary = models.TextField(blank=True, null=True)
    challenges = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trainer', 'batch', 'date')

    def __str__(self):
        return f"{self.batch.name} - {self.date}"


class Doubt(models.Model):
    intern = models.ForeignKey(InternProfile, on_delete=models.CASCADE, related_name="doubts")
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="received_doubts")
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="doubts")
    question = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Doubt by {self.intern.unique_id} - {self.trainer.user.username}"


class DoubtResolution(models.Model):
    doubt = models.OneToOneField(Doubt, on_delete=models.CASCADE, related_name="resolution")
    answer = models.TextField()
    resolved_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resolution for {self.doubt.id}"


class RecordedSession(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="recorded_sessions")
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="recorded_sessions")
    title = models.CharField(max_length=255)
    video = models.FileField(upload_to="recorded_sessions/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} - {self.batch.name}"


class Assignment(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="assignments")
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="created_assignments")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="assignments/", null=True, blank=True)
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    intern = models.ForeignKey(InternProfile, on_delete=models.CASCADE, related_name="assignment_submissions")
    file = models.FileField(upload_to="assignment_submissions/")
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded = models.BooleanField(default=False)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('assignment', 'intern')

    def __str__(self):
        return f"{self.intern.unique_id} - {self.assignment.title}"


class Assessment(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="assessments")
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="assessments")
    title = models.CharField(max_length=255)
    question_file = models.FileField(upload_to="assessments/questions/")
    created_at = models.DateTimeField(auto_now_add=True)
    total_marks = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.title} - {self.batch.name}"


class AssessmentMCQ(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="mcqs")
    question_text = models.TextField()
    option_1 = models.CharField(max_length=255)
    option_2 = models.CharField(max_length=255)
    option_3 = models.CharField(max_length=255, blank=True, null=True)
    option_4 = models.CharField(max_length=255, blank=True, null=True)
    correct_option = models.IntegerField(choices=((1, "Option 1"), (2, "Option 2"), (3, "Option 3"), (4, "Option 4")))

    def __str__(self):
        return self.question_text


class AssessmentSubmission(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="submissions")
    intern = models.ForeignKey(InternProfile, on_delete=models.CASCADE, related_name="assessment_submissions")
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Store answers in JSON: {mcq_id: selected_option}
    answers = models.JSONField()

    class Meta:
        unique_together = ('assessment', 'intern')

    def __str__(self):
        return f"{self.intern.unique_id} - {self.assessment.title}"


class Curriculum(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="curriculums")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="curriculums/")
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(TrainerProfile, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.course.name}"
