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
    path("undertaking/", views.undertaking_certificates_home, name="undertaking_home"),
    path("undertaking/single/<int:identifier>/", views.generate_intern_pdf, {"mode": "single"}, name="undertaking_single"),
    path("undertaking/multiple/", views.generate_intern_pdf, {"mode": "multiple"}, name="undertaking_multiple"),
    path("undertaking/batch/<int:identifier>/", views.generate_intern_pdf, {"mode": "batch"}, name="undertaking_batch"),

    path('managecertificates/', views.manage_certificates_view, name='manage_certificates'),
    path('certificate/download/<int:intern_id>/', views.download_certificate_view, name='download_certificate'),
    path('lors/', views.manage_lor_view, name='manage_lor'),
    path('lor/download/<int:intern_id>/', views.download_lor_view, name='download_lor'),
    

    

        # Course CRUD
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
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
