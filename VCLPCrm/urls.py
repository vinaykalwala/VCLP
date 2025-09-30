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
    path("undertaking/", views.undertaking_certificates_home, name="undertaking_home"),
    path("undertaking/single/<int:identifier>/", views.generate_intern_pdf, {"mode": "single"}, name="undertaking_single"),
    path("undertaking/multiple/", views.generate_intern_pdf, {"mode": "multiple"}, name="undertaking_multiple"),
    path("undertaking/batch/<int:identifier>/", views.generate_intern_pdf, {"mode": "batch"}, name="undertaking_batch"),

    path('managecertificates/', views.manage_certificates_view, name='manage_certificates'),
    path('certificate/download/<int:intern_id>/', views.download_certificate_view, name='download_certificate'),
    
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/create/', views.batch_create, name='batch_create'),
    path('batches/<int:pk>/', views.batch_detail, name='batch_detail'),
    path('batches/<int:pk>/update/', views.batch_update, name='batch_update'),
    path('batches/<int:pk>/delete/', views.batch_delete, name='batch_delete'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
