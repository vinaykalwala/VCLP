from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from CRM import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),  
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('attendance/', views.mark_attendance, name='mark_attendance'),
    path('lessons/upload/', views.upload_lesson, name='upload_lesson'),
    path('lessons/view/', views.view_lessons, name='view_lessons'),
    path('lessons/<int:lesson_id>/secure-view/', views.secure_pdf_view, name='secure_pdf_view'),
    path('lessons/<int:lesson_id>/viewer/', views.pdf_viewer_page, name='pdf_viewer_page'),
    path("lessons/edit/<int:pk>/", views.edit_lesson, name="edit_lesson"),
    path("lessons/delete/<int:pk>/", views.delete_lesson, name="delete_lesson"),
    path("undertaking/", views.undertaking_certificates_home, name="undertaking_home"),
    path("undertaking/single/<int:identifier>/", views.generate_intern_pdf, {"mode": "single"}, name="undertaking_single"),
    path("undertaking/multiple/", views.generate_intern_pdf, {"mode": "multiple"}, name="undertaking_multiple"),
    path("undertaking/batch/<int:identifier>/", views.generate_intern_pdf, {"mode": "batch"}, name="undertaking_batch"),

    path('managecertificates/', views.manage_certificates_view, name='manage_certificates'),
    path('certificate/download/<int:intern_id>/', views.download_certificate_view, name='download_certificate'),
    path('lors/', views.manage_lor_view, name='manage_lor'),
    path('lor/download/<int:intern_id>/', views.download_lor_view, name='download_lor'),
      
    path("courses/", views.course_list, name="course_list"),
    path("courses/add/", views.course_create, name="course_create"),
    path("courses/<int:pk>/edit/", views.course_update, name="course_update"),
    path("courses/delete/<int:pk>/", views.course_delete_ajax, name="course_delete_ajax"),

    path('batches/', views.batch_list, name='batch_list'),
    path('batches/create/', views.batch_create, name='batch_create'),
    path('batches/<int:pk>/', views.batch_detail, name='batch_detail'),
    path('batches/<int:pk>/update/', views.batch_update, name='batch_update'),
    path('batches/<int:pk>/delete/', views.batch_delete, name='batch_delete'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/trainer/<int:trainer_id>/', views.trainer_profile_view, name='trainer_profile'),

    path("interns/", views.intern_list, name="intern_list"),
    path("intern_create/", views.intern_create, name="intern_create"),
    path("intern_update/<int:pk>/", views.intern_update, name="intern_update"),
    path("intern_delete/<int:pk>/", views.intern_delete, name="intern_delete"),
    path("intern_detail/<int:pk>/", views.intern_detail, name="intern_detail"),
    path('attendance-report/', views.attendance_report, name='attendance_report'),
    path('attendance-list/', views.attendance_list, name='attendance_list'),
    path('attendance/edit/<int:attendance_id>/', views.edit_attendance, name='edit_attendance'),

    path('curriculums/', views.curriculum_list, name='curriculum_list'),
    path('curriculums/add/', views.create_curriculum, name='create_curriculum'),
    path('curriculums/edit/<int:pk>/', views.update_curriculum, name='update_curriculum'),
    path('curriculums/delete/<int:pk>/', views.delete_curriculum, name='delete_curriculum'),

    path('daily_update_list/', views.daily_update_list, name='daily_update_list'),
    path('daily_update_add/', views.daily_update_create, name='daily_update_create'),
    path('daily_update_edit/<int:pk>/', views.daily_update_edit, name='daily_update_edit'),
    path('daily_update_delete/<int:pk>/', views.daily_update_delete, name='daily_update_delete'),
    path('daily_update_dashboard/', views.daily_update_dashboard, name='daily_update_dashboard'),


    path('doubts/', views.doubt_list, name='doubt_list'),
    path('doubts/create/', views.doubt_create, name='doubt_create'),
    path('doubts/<int:pk>/resolve/', views.resolve_doubt, name='resolve_doubt'),

    path('sessions/', views.recorded_session_list, name='recorded_session_list'),
    path('sessions/create/', views.recorded_session_create, name='recorded_session_create'),
    path('sessions/<int:pk>/edit/', views.recorded_session_update, name='recorded_session_update'),
    path('sessions/<int:pk>/delete/', views.recorded_session_delete, name='recorded_session_delete'),

    path('trainers/', views.trainer_list, name='trainer_list'),
    path('trainers/create/', views.trainer_create, name='trainer_create'),
    path('trainers/<int:pk>/', views.trainer_detail, name='trainer_detail'),
    path('trainers/<int:pk>/update/', views.trainer_update, name='trainer_update'),
    path('trainers/<int:pk>/delete/', views.trainer_delete, name='trainer_delete'),

    path('users/', views.user_list, name='user_list'),
    path('users/<int:pk>/edit/', views.user_update, name='user_update'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    path("assignments/create/", views.create_assignment, name="create_assignment"),
    path("assignments/edit/<int:pk>/", views.edit_assignment, name="edit_assignment"),
    path("assignments/delete/<int:pk>/", views.delete_assignment, name="delete_assignment"),
    path("assignments/", views.view_assignments, name="view_assignments"),
    path("assignments/<int:pk>/submissions/", views.view_submissions, name="view_submissions"),
    path("submissions/<int:pk>/grade/", views.grade_submission, name="grade_submission"),

    # Intern
    path("my-assignments/", views.intern_assignments, name="intern_assignments"),
    path("submit-assignment/<int:assignment_id>/", views.submit_assignment, name="submit_assignment"),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
