from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(InternProfile)
admin.site.register(TrainerProfile)
admin.site.register(AdminProfile)
admin.site.register(SuperUserProfile)
admin.site.register(Attendance)
admin.site.register(LessonFile)
admin.site.register(Batch)
admin.site.register(Course)
admin.site.register(Curriculum)
admin.site.register(DailySessionUpdate)
admin.site.register(Assessment)
admin.site.register(AssessmentSubmission)