from django.db import models
from django.contrib.auth.models import AbstractUser

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


# =====================
# Profiles
# =====================
class InternProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="intern_profile")
    unique_id = models.CharField(max_length=20, unique=True, editable=False)
    batch = models.CharField(max_length=100, default="Not Assigned")

    def __str__(self):
        return f"{self.unique_id} - {self.user.username}"


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
