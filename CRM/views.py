from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.template.loader import render_to_string
import io
import datetime
import zipfile
from .models import *
from .forms import *

def home(request):
    return render(request, 'home.html') 

# =====================
# Signup
# =====================
def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        role = request.POST.get('role')

        # validations
        if not username or not first_name or not last_name or not email or not phone or not password1 or not password2 or not role:
            messages.error(request, "All fields are required.")
            return render(request, 'signup.html')

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup.html')

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email address.")
            return render(request, 'signup.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'signup.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already associated with an account.")
            return render(request, 'signup.html')

        if User.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number already associated with an account.")
            return render(request, 'signup.html')

        # create user
        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password=make_password(password1),
            plain_password=password1,
            role=role
        )
        if role == "superuser":
            user.is_staff = True
            user.is_superuser = True
        user.save()

        # create profile based on role
        if role == "intern":
            last_intern = InternProfile.objects.order_by("-id").first()
            if last_intern and last_intern.unique_id:
                last_number = int(last_intern.unique_id.replace("VCLPI", ""))
                new_id = f"VCLPI{last_number + 1:03d}"
            else:
                new_id = "VCLPI001"
            InternProfile.objects.create(user=user, unique_id=new_id)

        elif role == "trainer":
            TrainerProfile.objects.create(user=user)

        elif role == "admin":
            AdminProfile.objects.create(user=user)

        elif role == "superuser":
            SuperUserProfile.objects.create(user=user)

        messages.success(request, "Account created successfully! Please log in.")
        return redirect('login')

    return render(request, 'signup.html', {'role_choices': User.ROLE_CHOICES})


# =====================
# Login / Logout
# =====================
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials.")
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# =====================
# Dashboards
# =====================
@login_required
def dashboard_view(request):
    if request.user.role == "superuser":
        return render(request, "dashboards/superuserdashboard.html")
    elif request.user.role == "admin":
        return render(request, "dashboards/administratordashboard.html")
    elif request.user.role == "trainer":
        return render(request, "dashboards/trainerdashboard.html")
    elif request.user.role == "intern":
        return render(request, "dashboards/interndashboard.html")
    else:
        return render(request, "dashboards/defaultdashboard.html")


# =====================
# Attendance (Trainer)
# =====================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import TrainerProfile, Batch, InternProfile, Attendance

@login_required
def mark_attendance(request):
    # Ensure only trainers can access
    if not hasattr(request.user, "trainer_profile"):
        messages.error(request, "Only trainers can mark attendance.")
        return redirect("dashboard")

    trainer = request.user.trainer_profile
    # ✅ Only batches assigned to this trainer
    batches = Batch.objects.filter(trainer=trainer)  
    interns = None
    selected_batch = None

    if request.method == "POST":
        selected_batch_id = request.POST.get("batch")
        date = request.POST.get("date")

        if selected_batch_id:
            # ✅ Ensure trainer only accesses their own batch
            selected_batch = get_object_or_404(Batch, id=selected_batch_id, trainer=trainer)
            interns = selected_batch.interns.all()

            # Save attendance
            if "save_attendance" in request.POST:
                for intern in interns:
                    status = request.POST.get(f"status_{intern.id}")
                    if status:
                        Attendance.objects.update_or_create(
                            intern=intern,
                            date=date,
                            defaults={"trainer": trainer, "batch": selected_batch, "status": status},
                        )
                messages.success(request, f"Attendance saved for {selected_batch.name} on {date}.")
                return redirect("mark_attendance")

    return render(request, "attendance/mark_attendance.html", {
        "batches": batches,
        "interns": interns,
        "selected_batch": selected_batch,
    })

# =====================
# File Upload / View
# =====================
@login_required
def upload_lesson(request):
    if request.user.role != "trainer":
        return redirect('dashboard')

    trainer = request.user.trainer_profile
    batches = trainer.assigned_batches.all()  # batches assigned to this trainer

    if request.method == "POST" and request.FILES.get("file"):
        title = request.POST.get("title")
        selected_batches = request.POST.getlist("batches")  # get multiple batch IDs
        file = request.FILES["file"]

        lesson = LessonFile.objects.create(trainer=trainer, title=title, file=file)
        lesson.batches.set(selected_batches)  # assign multiple batches
        messages.success(request, "File uploaded successfully.")
        return redirect("upload_lesson")

    return render(request, "files/upload.html", {"batches": batches})

# views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from .models import LessonFile
import os

@login_required
def view_lessons(request):
    user = request.user

    if user.role == "intern":
        batch = user.intern_profile.batch
        lessons = LessonFile.objects.filter(batches=batch).order_by('-uploaded_at')
    elif user.role == "trainer":
        trainer = user.trainer_profile
        lessons = LessonFile.objects.filter(trainer=trainer).order_by('-uploaded_at')
    else:  # admin or superuser
        lessons = LessonFile.objects.all().order_by('-uploaded_at')

    return render(request, "files/view.html", {"lessons": lessons})

@login_required
def secure_pdf_view(request, lesson_id):
    """Serve PDF with security headers to prevent download"""
    lesson = get_object_or_404(LessonFile, id=lesson_id)
    
    # Read the file
    with open(lesson.file.path, 'rb') as pdf_file:
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        
        # Security headers to discourage downloading
        response['Content-Disposition'] = 'inline; filename="document.pdf"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate,private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response

@login_required
def pdf_viewer_page(request, lesson_id):
    """Render a custom PDF viewer page"""
    lesson = get_object_or_404(LessonFile, id=lesson_id)
    return render(request, 'files/pdf_viewer.html', {'lesson': lesson})

# -------------------------
# Helper function to generate PDF
# -------------------------

@login_required
def undertaking_certificates_home(request):
    """
    Manage Undertaking Certificates page
    """
    courses = Course.objects.all()
    batches = Batch.objects.all()

    interns = InternProfile.objects.select_related("batch", "batch__course")

    # Apply filters
    course_id = request.GET.get("course_id")
    batch_id = request.GET.get("batch_id")
    search = request.GET.get("search")

    if course_id:
        interns = interns.filter(batch__course_id=course_id)
    if batch_id:
        interns = interns.filter(batch_id=batch_id)
    if search:
        interns = interns.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(unique_id__icontains=search)
        )

    return render(
        request,
        "internshipundertakingcertificates.html",
        {"courses": courses, "batches": batches, "interns": interns},
    )


def generate_pdf_from_html(html_content):
    """
    Utility: Generate PDF bytes from HTML
    """
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
    if pisa_status.err:
        return None
    pdf_buffer.seek(0)
    return pdf_buffer

@login_required
def generate_intern_pdf(request, mode, identifier=None):
    """
    Generate Undertaking Certificates
    mode:
        - single: one intern (identifier=intern_id)
        - multiple: many interns (ids in POST)
        - batch: all interns in a batch (identifier=batch_id)
    """
    interns = []

    if mode == "single":
        try:
            intern = InternProfile.objects.get(
                id=identifier,
                internship_status="Ongoing",
                undertaking_generated=False,
            )
            interns = [intern]
        except InternProfile.DoesNotExist:
            return HttpResponse(
                f"Cannot generate certificate: Intern with ID {identifier} "
                "is either not Ongoing or already has an undertaking generated."
            )

    elif mode == "multiple":
        intern_ids = request.POST.getlist("intern_ids")
        interns = list(
            InternProfile.objects.filter(
                id__in=intern_ids,
                internship_status="Ongoing",
                undertaking_generated=False,
            )
        )
        if not interns:
            return HttpResponse(
                "None of the selected interns are eligible for certificate generation "
                "(must be Ongoing and not yet generated)."
            )

    elif mode == "batch":
        batch = get_object_or_404(Batch, id=identifier)
        interns = list(
            batch.interns.filter(
                internship_status="Ongoing",
                undertaking_generated=False
            )
        )
        if not interns:
            return HttpResponse(
                f"No eligible interns in batch '{batch.name}' for certificate generation."
            )

    # ----------------------
    # SINGLE PDF
    # ----------------------
    if len(interns) == 1:
        intern = interns[0]
        logo_path = os.path.join(settings.BASE_DIR, 'static/images/vinduslogo.jpg')
        context = {
            "intern_name": intern.user.get_full_name(),
            "course": intern.batch.course,
            "batch": intern.batch,
            "company": {
                "name": "VINDUS ENVIRONMENT PRIVATE LIMITED",
                "cin": "U62099TS2023PTC179794",
                "address": "#9-110, Shanti Nagar, Dilsukhnagar, Hyderabad- 500 060",
                "phone": "+914049525396",
                "website": "www.vindusenvironment.com"
            },
            "today_date": datetime.date.today().strftime("%d-%m-%Y"),
            "logo_path": logo_path 
        }

        html_content = render_to_string("undertaking_letter.html", context)
        pdf_buffer = generate_pdf_from_html(html_content)
        if not pdf_buffer:
            return HttpResponse("Error generating PDF")

        intern.undertaking_generated = True
        intern.save()

        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        filename = f"{intern.unique_id}_{intern.user.get_full_name()}_undertaking.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # ----------------------
    # MULTIPLE/BATCH => ZIP
    # ----------------------
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for intern in interns:
            logo_path = os.path.join(settings.BASE_DIR, 'static/images/vinduslogo.jpg')
            context = {
                "intern_name": intern.user.get_full_name(),
                "course": intern.batch.course,
                "batch": intern.batch,
                "company": {
                    "name": "VINDUS ENVIRONMENT PRIVATE LIMITED",
                    "cin": "U62099TS2023PTC179794",
                    "address": "#9-110, Shanti Nagar, Dilsukhnagar, Hyderabad- 500 060",
                    "phone": "+914049525396",
                    "website": "www.vindusenvironment.com"
                },
                "today_date": datetime.date.today().strftime("%d-%m-%Y"),
                "logo_path": logo_path
            }
            html_content = render_to_string("undertaking_letter.html", context)
            pdf_buffer = generate_pdf_from_html(html_content)
            if not pdf_buffer:
                continue

            filename = f"{intern.unique_id}_{intern.user.get_full_name()}_undertaking.pdf"
            zip_file.writestr(filename, pdf_buffer.read())

            intern.undertaking_generated = True
            intern.save()

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type="application/zip")
    if mode == "batch":
        response["Content-Disposition"] = f'attachment; filename="{batch.name}_undertakings.zip"'
    else:
        response["Content-Disposition"] = 'attachment; filename="undertakings.zip"'
    return response


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Batch
from .forms import BatchForm

# Function-based views approach
@login_required
def batch_list(request):
    batches = Batch.objects.all().select_related('course', 'trainer__user')
    return render(request, 'batches/batch_list.html', {'batches': batches})

@login_required
def batch_detail(request, pk):
    batch = get_object_or_404(Batch.objects.select_related('course', 'trainer__user'), pk=pk)
    return render(request, 'batches/batch_detail.html', {'batch': batch})

@login_required
def batch_create(request):
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if form.is_valid():
            batch = form.save()
            messages.success(request, f'Batch "{batch.name}" created successfully!')
            return redirect('batch_detail', pk=batch.pk)
    else:
        form = BatchForm()
    
    return render(request, 'batches/batch_form.html', {
        'form': form,
        'title': 'Create New Batch'
    })

@login_required
def batch_update(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    
    if request.method == 'POST':
        form = BatchForm(request.POST, instance=batch)
        if form.is_valid():
            batch = form.save()
            messages.success(request, f'Batch "{batch.name}" updated successfully!')
            return redirect('batch_detail', pk=batch.pk)
    else:
        form = BatchForm(instance=batch)
    
    return render(request, 'batches/batch_form.html', {
        'form': form,
        'title': f'Update Batch: {batch.name}',
        'batch': batch
    })

@login_required
def batch_delete(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    
    if request.method == 'POST':
        batch_name = batch.name
        batch.delete()
        messages.success(request, f'Batch "{batch_name}" deleted successfully!')
        return redirect('batch_list')
    
    return render(request, 'batches/batch_confirm_delete.html', {'batch': batch})


# Add these imports to the top of your views.py file
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
import io
import zipfile
from .models import InternProfile
from django.db.models import Q
from .forms import InternFilterForm
from xhtml2pdf import pisa

# ==================================
# Helper Function for PDF Generation
# ==================================

def generate_pdf_for_intern(intern):
    """
    Renders an HTML template for a single intern's certificate and returns it as PDF bytes using xhtml2pdf.
    """

    context = {'intern': intern}
    html_string = render_to_string('certificates/certificate_template.html', context)

    # Create a BytesIO buffer to hold PDF
    result = io.BytesIO()

    # Convert HTML to PDF
    pisa_status = pisa.CreatePDF(io.StringIO(html_string), dest=result)

    # Check for errors
    if pisa_status.err:
        raise Exception('Error generating PDF')

    # Get PDF bytes
    pdf_bytes = result.getvalue()
    result.close()
    return pdf_bytes

# ================================
# Certificate Management View (Admin)
# ================================
@login_required
def manage_certificates_view(request):
    """
    Allows an admin to filter by course/batch, search, and download certificates.
    """
    if not (request.user.is_superuser or request.user.role == 'admin'):
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')

    interns_qs = InternProfile.objects.select_related('user', 'batch', 'batch__course').order_by('user__first_name')
    
    # Use the new form
    filter_form = InternFilterForm(request.GET)
    selected_batch = None

    if filter_form.is_valid():
        selected_course = filter_form.cleaned_data.get('course')
        selected_batch = filter_form.cleaned_data.get('batch')
        query = filter_form.cleaned_data.get('q')

        if selected_course:
            interns_qs = interns_qs.filter(batch__course=selected_course)
            # Dynamically update the batch dropdown to show only batches from the selected course
            filter_form.fields['batch'].queryset = Batch.objects.filter(course=selected_course)

        if selected_batch:
            interns_qs = interns_qs.filter(batch=selected_batch)

        if query:
            interns_qs = interns_qs.filter(
                Q(unique_id__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query)
            )

    # The POST logic for downloading remains the same
    if request.method == 'POST':
        # ... (Your existing POST logic for downloading certificates does not need to change)
        action = request.POST.get('action')
        selected_interns = None

        if action == 'download_selected':
            intern_ids = request.POST.getlist('intern_ids')
            if not intern_ids:
                messages.error(request, "Please select at least one intern.")
                return redirect(request.get_full_path())
            selected_interns = InternProfile.objects.filter(id__in=intern_ids, internship_status='Completed')

        elif action == 'download_batch':
            batch_id = request.POST.get('batch_id')
            if not batch_id:
                messages.error(request, "Please filter by a batch first.")
                return redirect(request.get_full_path())
            selected_interns = InternProfile.objects.filter(batch_id=batch_id, internship_status='Completed')

        if selected_interns and selected_interns.exists():
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for intern in selected_interns:
                    pdf_bytes = generate_pdf_for_intern(intern)
                    filename = f"Certificate_{intern.unique_id}_{intern.user.get_full_name()}.pdf"
                    zf.writestr(filename, pdf_bytes)
            
            selected_interns.update(completion_certificate_generated=True)
            
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer, content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="certificates.zip"'
            messages.success(request, f"Successfully generated {selected_interns.count()} certificates.")
            return response
        else:
            messages.warning(request, "No completed interns were found for the selected action.")
            return redirect(request.get_full_path())


    context = {
        'interns': interns_qs,
        'filter_form': filter_form,
        'selected_batch': selected_batch,
    }
    return render(request, 'certificates/manage_certificates.html', context)


# ================================
# Helper Functions
# ================================
def render_to_pdf(template_path, context_dict):
    template = render_to_string(template_path, context_dict)
    pdf_bytes = io.BytesIO()
    pisa_status = pisa.CreatePDF(template, dest=pdf_bytes)
    if pisa_status.err:
        return None
    pdf_bytes.seek(0)
    return pdf_bytes.getvalue()

# ================================
# Individual Certificate Download View
# ================================
@login_required
def download_certificate_view(request, intern_id):
    """
    Generates and serves a single PDF certificate for a specific intern.
    """
    if not (request.user.is_superuser or request.user.role == 'admin'):
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('dashboard')

    intern = get_object_or_404(InternProfile, id=intern_id)

    if intern.internship_status != 'Completed':
        messages.error(request, f"Cannot generate certificate. {intern.user.get_full_name()}'s internship is not marked as completed.")
        return redirect('manage_certificates')

    pdf_bytes = generate_pdf_for_intern(intern)
    intern.completion_certificate_generated = True
    intern.save()
    
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"Certificate_{intern.unique_id}_{intern.user.get_full_name()}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response



@login_required
def profile_view(request):
    user = request.user
    context = {
        'user': user,
    }
    
    # Add profile-specific data based on role
    if hasattr(user, 'intern_profile'):
        intern_profile = user.intern_profile
        context.update({
            'profile': intern_profile,
            'batch': intern_profile.batch,
            'course': intern_profile.batch.course if intern_profile.batch else None,
            'trainer': intern_profile.batch.trainer if intern_profile.batch else None,
        })
    elif hasattr(user, 'trainer_profile'):
        context['profile'] = user.trainer_profile
    elif hasattr(user, 'admin_profile'):
        context['profile'] = user.admin_profile
    elif hasattr(user, 'superuser_profile'):
        context['profile'] = user.superuser_profile
    
    return render(request, 'profile.html', context)

@login_required
def edit_profile_view(request):
    user = request.user
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        
        # Get the appropriate profile form based on user role
        if hasattr(user, 'intern_profile'):
            profile_form = InternProfileUpdateForm(request.POST, request.FILES, instance=user.intern_profile)
        elif hasattr(user, 'trainer_profile'):
            profile_form = TrainerProfileUpdateForm(request.POST, request.FILES, instance=user.trainer_profile)
        elif hasattr(user, 'admin_profile'):
            profile_form = AdminProfileUpdateForm(request.POST, request.FILES, instance=user.admin_profile)
        elif hasattr(user, 'superuser_profile'):
            profile_form = SuperUserProfileUpdateForm(request.POST, request.FILES, instance=user.superuser_profile)
        else:
            profile_form = None

        if user_form.is_valid() and (profile_form is None or profile_form.is_valid()):
            user_form.save()
            if profile_form:
                profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=user)
        
        # Initialize the appropriate profile form
        if hasattr(user, 'intern_profile'):
            profile_form = InternProfileUpdateForm(instance=user.intern_profile)
        elif hasattr(user, 'trainer_profile'):
            profile_form = TrainerProfileUpdateForm(instance=user.trainer_profile)
        elif hasattr(user, 'admin_profile'):
            profile_form = AdminProfileUpdateForm(instance=user.admin_profile)
        elif hasattr(user, 'superuser_profile'):
            profile_form = SuperUserProfileUpdateForm(instance=user.superuser_profile)
        else:
            profile_form = None

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'edit_profile.html', context)

@login_required
def trainer_profile_view(request, trainer_id):
    trainer_profile = get_object_or_404(TrainerProfile, id=trainer_id)
    return render(request, 'trainer_profile.html', {'trainer': trainer_profile})

# ================================
# LETTER OF RECOMMENDATION (LOR) VIEWS
# ================================

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from datetime import date
import io
import zipfile
from .models import InternProfile, Course, Batch
from .forms import InternFilterForm
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import io

def render_to_pdf(template_path, context_dict):
    """
    Utility function to render HTML template to PDF
    """
    html = render_to_string(template_path, context_dict)
    result = io.BytesIO()
    pdf = pisa.CreatePDF(html, dest=result)
    
    if not pdf.err:
        return result.getvalue()
    return None 

@login_required
def manage_lor_view(request):
    """
    Allows an admin to filter, search, and bulk-download Letters of Recommendation.
    """
    if not (request.user.is_superuser or request.user.role == 'admin'):
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')

    interns_qs = InternProfile.objects.select_related('user', 'batch', 'batch__course').order_by('user__first_name')
    courses = Course.objects.all()
    batches = Batch.objects.all()
    
    filter_form = InternFilterForm(request.GET)
    selected_batch = None

    if filter_form.is_valid():
        selected_course = filter_form.cleaned_data.get('course')
        selected_batch = filter_form.cleaned_data.get('batch')
        query = filter_form.cleaned_data.get('q')

        if selected_course:
            interns_qs = interns_qs.filter(batch__course=selected_course)
        if selected_batch:
            interns_qs = interns_qs.filter(batch=selected_batch)
        if query:
            interns_qs = interns_qs.filter(
                Q(unique_id__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query)
            )

    if request.method == 'POST':
        intern_ids = request.POST.getlist('intern_ids')
        if not intern_ids:
            messages.error(request, "Please select at least one intern.")
            return redirect('manage_lor')

        selected_interns = InternProfile.objects.filter(id__in=intern_ids, internship_status='Completed')

        if not selected_interns.exists():
            messages.warning(request, "No completed interns were selected for LOR generation.")
            return redirect('manage_lor')

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for intern in selected_interns:
                # Get logo path from settings
                logo_path = os.path.join(settings.BASE_DIR, 'static/images/vinduslogo.png')
                
                context = {
                    'intern': intern,
                    "company": {
                        "name": "VINDUS ENVIRONMENT PRIVATE LIMITED",
                        "cin": "U62099TS2023PTC179794",
                        "address": "#9-110, Shanti Nagar, Dilsukhnagar, Hyderabad- 500 060",
                        "phone": "+914049525396",
                        "website": "www.vindusenvironment.com"
                    },
                    "today_date": datetime.date.today().strftime("%d-%m-%Y"),
                    "logo_path": logo_path 
                }
                pdf_bytes = render_to_pdf('lors/lor_template.html', context)
                if pdf_bytes:
                    filename = f"LOR_{intern.unique_id}_{intern.user.get_full_name()}.pdf"
                    zf.writestr(filename, pdf_bytes)
        
        selected_interns.update(lor_generated=True)

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="Letters_of_Recommendation.zip"'
        return response

    context = {
        'interns': interns_qs,
        'courses': courses,
        'batches': batches,
        'filter_form': filter_form,
        'selected_batch': selected_batch,
    }
    return render(request, 'lors/manage_lors.html', context)

from datetime import datetime

@login_required
def download_lor_view(request, intern_id):
    """
    Download a Letter of Recommendation for a specific intern.
    """
    intern = get_object_or_404(InternProfile, id=intern_id)
    if intern.internship_status != 'Completed':
        messages.error(request, "LOR not available for this intern yet.")
        return redirect('manage_lor')
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/vinduslogo.png')
    # Context matching the template requirements
    context = {
        'intern': intern,
        'company': {
            "name": "VINDUS ENVIRONMENT PRIVATE LIMITED",
                        "cin": "U62099TS2023PTC179794",
                        "address": "#9-110, Shanti Nagar, Dilsukhnagar, Hyderabad- 500 060",
                        "phone": "+914049525396",
                        "website": "www.vindusenvironment.com"
        },
        "today_date": date.today().strftime("%d-%m-%Y"),
        "logo_path": logo_path 
    }
    
    pdf_bytes = render_to_pdf('lors/lor_template.html', context)
    if pdf_bytes:
        intern.lor_generated = True
        intern.save()
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"LOR_{intern.unique_id}_{intern.user.get_full_name()}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    messages.error(request, "Error generating LOR PDF.")
    return redirect('manage_lor')
from django.db.models import Q
from .models import InternProfile

@login_required
def intern_list(request):
    interns = InternProfile.objects.all()

    query = request.GET.get('q')  # single search bar
    batch_start = request.GET.get('batch_start')
    batch_end = request.GET.get('batch_end')
    internship_status = request.GET.get('internship_status')

    if query:
        interns = interns.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(batch__name__icontains=query) |
            Q(batch__trainer__user__first_name__icontains=query) |
            Q(unique_id__icontains=query) |
            Q(gender__icontains=query) |
            Q(undertaking_generated__icontains=query) |
            Q(completion_certificate_generated__icontains=query) |
            Q(lor_generated__icontains=query)
        )

    if batch_start:
        interns = interns.filter(batch__start_date__gte=batch_start)
    if batch_end:
        interns = interns.filter(batch__end_date__lte=batch_end)
    if internship_status:
        interns = interns.filter(internship_status=internship_status)

    return render(request, "interns/intern_list.html", {"interns": interns})

@login_required
def intern_create(request):
    if request.method == "POST":
        form = InternProfileForm(request.POST, request.FILES)
        if form.is_valid():
            intern = form.save(commit=False)
            
            # Optional: create a User for this intern
            if not intern.user_id:
                user = User.objects.create_user(
                    username=request.POST.get("username"),
                    password=request.POST.get("password"),
                    first_name=request.POST.get("first_name"),
                    last_name=request.POST.get("last_name"),
                    email=request.POST.get("email"),
                )
                intern.user = user

            intern.save()
            messages.success(request, "Intern profile created successfully.")
            return redirect("intern_list")
    else:
        form = InternProfileForm()
    return render(request, "interns/intern_form.html", {"form": form})

@login_required
def intern_update(request, pk):
    intern = get_object_or_404(InternProfile, pk=pk)
    if request.method == "POST":
        form = InternProfileForm(request.POST, request.FILES, instance=intern)
        if form.is_valid():
            form.save()
            messages.success(request, "Intern profile updated successfully.")
            return redirect("intern_list")
    else:
        form = InternProfileForm(instance=intern)
    return render(request, "interns/intern_form.html", {"form": form})

@login_required
def intern_delete(request, pk):
    intern = get_object_or_404(InternProfile, pk=pk)
    if request.method == "POST":
        intern.delete()  # This will also delete the user
        messages.success(request, "Intern profile and associated user deleted.")
        return redirect("intern_list")
    return render(request, "interns/intern_confirm_delete.html", {"intern": intern})

@login_required
def intern_detail(request, pk):
    intern = get_object_or_404(InternProfile, pk=pk)
    return render(request, "interns/intern_detail.html", {"intern": intern})

from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Attendance, Batch
from datetime import datetime
import calendar
import openpyxl
from xhtml2pdf import pisa
from django.template.loader import get_template

@login_required
def attendance_report(request):
    batches = Batch.objects.all()
    selected_batch_id = request.GET.get('batch')
    date_input = request.GET.get('date')
    month_input = request.GET.get('month')
    export_type = request.GET.get('export')

    attendances = Attendance.objects.none()
    summary = []
    today = datetime.today().date()
    batch = None

    if selected_batch_id:
        batch = get_object_or_404(Batch, pk=selected_batch_id)
        attendances = Attendance.objects.filter(batch=batch)

        # Default or specific date
        if date_input:
            try:
                selected_date = datetime.strptime(date_input, "%Y-%m-%d").date()
            except ValueError:
                selected_date = today
        else:
            selected_date = today

        attendances = attendances.filter(date=selected_date)

        # Monthwise report
        if month_input and month_input != "None":
            try:
                month_number = list(calendar.month_name).index(month_input)
                attendances = Attendance.objects.filter(
                    batch=batch,
                    date__month=month_number
                )
                selected_date = None
            except ValueError:
                pass

        # Summary
        summary = attendances.values(
            'intern__unique_id',
            'intern__user__first_name',
            'intern__user__last_name'
        ).annotate(
            present_count=Count('id', filter=Q(status='Present')),
            absent_count=Count('id', filter=Q(status='Absent'))
        )

    # ---------- Excel Export ----------
    if export_type == 'excel' and attendances.exists():
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=attendance_report.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Attendance Report"

        # Header for attendance
        ws.append(["Attendance Report"])
        ws.append(["Batch", batch.name if batch else ""])
        ws.append([])
        ws.append(['Date', 'Intern Name', 'Unique ID', 'Status', 'Trainer'])

        # Attendance Data
        for att in attendances:
            ws.append([
                att.date.strftime("%Y-%m-%d"),
                att.intern.user.get_full_name(),
                att.intern.unique_id,
                att.status,
                att.trainer.user.get_full_name()
            ])

        # Add spacing
        ws.append([])
        ws.append([])

        # Summary Section
        ws.append(["Summary"])
        ws.append(['Intern Name', 'Unique ID', 'Present Days', 'Absent Days'])

        for s in summary:
            ws.append([
                f"{s['intern__user__first_name']} {s['intern__user__last_name']}",
                s['intern__unique_id'],
                s['present_count'],
                s['absent_count']
            ])

        wb.save(response)
        return response

    # ---------- PDF Export ----------
    if export_type == 'pdf' and attendances.exists():
        template = get_template('attendance/attendance_report_pdf.html')
        html = template.render({
            'attendances': attendances,
            'summary': summary,
            'batch': batch,
            'selected_date': date_input or today,
            'month_input': month_input
        })
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="attendance_report.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse("Error generating PDF")
        return response

    # ---------- Render HTML Page ----------
    return render(request, "attendance/attendance_report.html", {
        "batches": batches,
        "attendances": attendances,
        "summary": summary,
        "selected_batch_id": selected_batch_id,
        "selected_date": date_input if date_input else today,
        "month_input": month_input,
        "months": list(calendar.month_name)[1:],  # January–December
    })


from django.shortcuts import redirect
from django.contrib import messages

@login_required
def attendance_list(request):
    """Displays all attendance records for a selected batch (with edit option)."""
    batches = Batch.objects.all()
    selected_batch_id = request.GET.get('batch')
    attendances = Attendance.objects.none()
    batch = None

    if selected_batch_id:
        batch = get_object_or_404(Batch, pk=selected_batch_id)
        attendances = Attendance.objects.filter(batch=batch).order_by('-date')

    return render(request, "attendance/attendance_list.html", {
        "batches": batches,
        "selected_batch_id": selected_batch_id,
        "attendances": attendances,
        "batch": batch,
    })


@login_required
def edit_attendance(request, attendance_id):
    """Allows trainer/admin to edit attendance status."""
    attendance = get_object_or_404(Attendance, id=attendance_id)

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in ["Present", "Absent"]:
            attendance.status = new_status
            attendance.save()
            messages.success(request, "Attendance updated successfully!")
            return redirect('attendance_list')
        else:
            messages.error(request, "Invalid status selected.")

    return render(request, "attendance/edit_attendance.html", {
        "attendance": attendance
    })


from .forms import CurriculumForm

# Create Curriculum
@login_required
def create_curriculum(request):
    if request.method == "POST":
        form = CurriculumForm(request.POST, request.FILES)
        if form.is_valid():
            curriculum = form.save(commit=False)
            curriculum.uploaded_by = request.user.trainer_profile  # assuming trainer logged in
            curriculum.save()
            return redirect('curriculum_list')
    else:
        form = CurriculumForm()
    return render(request, 'curriculum/curriculum_form.html', {'form': form, 'title': 'Add Curriculum'})

# List & Filter by Batch
@login_required
def curriculum_list(request):
    user = request.user
    user_role = getattr(user, 'role', None)

    if user_role == "intern":
        # Show only curriculums for the intern's batch
        try:
            intern_batch = user.intern_profile.batch  # assuming intern_profile has a batch field
            curriculums = Curriculum.objects.filter(batch=intern_batch)
        except AttributeError:
            curriculums = Curriculum.objects.none()  # fallback if batch not set
        batches = None  # No batch filter for interns
        selected_batch = None
    else:
        # Trainers/Admins see all curriculums, optional batch filter
        batches = Batch.objects.all()
        selected_batch = request.GET.get('batch')
        if selected_batch:
            curriculums = Curriculum.objects.filter(batch_id=selected_batch)
        else:
            curriculums = Curriculum.objects.all()

    return render(request, 'curriculum/curriculum_list.html', {
        'curriculums': curriculums,
        'batches': batches,
        'selected_batch': selected_batch,
        'user_role': user_role,
    })

# Update
@login_required
def update_curriculum(request, pk):
    curriculum = get_object_or_404(Curriculum, pk=pk)

    # Restrict interns
    if request.user.role == "intern":
        return redirect('curriculum_list')

    # Only allow trainers who uploaded or admins
    if request.user.role == "trainer" and curriculum.uploaded_by.user != request.user:
        return redirect('curriculum_list')

    if request.method == "POST":
        form = CurriculumForm(request.POST, request.FILES, instance=curriculum)
        if form.is_valid():
            form.save()
            return redirect('curriculum_list')
    else:
        form = CurriculumForm(instance=curriculum)
    return render(request, 'curriculum/curriculum_form.html', {'form': form, 'title': 'Edit Curriculum'})

# Delete
@login_required
def delete_curriculum(request, pk):
    curriculum = get_object_or_404(Curriculum, pk=pk)

    if request.user.role == "intern":
        return redirect('curriculum_list')

    if request.user.role == "trainer" and curriculum.uploaded_by.user != request.user:
        return redirect('curriculum_list')

    if request.method == "POST":
        curriculum.delete()
        return redirect('curriculum_list')
    return render(request, 'curriculum/curriculum_confirm_delete.html', {'curriculum': curriculum})
