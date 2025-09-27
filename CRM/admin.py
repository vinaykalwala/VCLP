from django.contrib import admin
from .models import User, InternProfile, TrainerProfile, AdminProfile, SuperUserProfile, Attendance, LessonFile

admin.site.register(User)
admin.site.register(InternProfile)
admin.site.register(TrainerProfile)
admin.site.register(AdminProfile)
admin.site.register(SuperUserProfile)
admin.site.register(Attendance)
admin.site.register(LessonFile)
