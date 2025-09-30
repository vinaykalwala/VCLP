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

    path('managecertificates/', views.manage_certificates_view, name='manage_certificates'),
    path('certificate/download/<int:intern_id>/', views.download_certificate_view, name='download_certificate'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
