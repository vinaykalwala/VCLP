from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from xhtml2pdf import pisa
from django.template.loader import render_to_string
import io
from datetime import date
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
        return redirect('signup')

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
            if user.is_active:  # check if user is active
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Your account is inactive. Please contact admin.")
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
def edit_lesson(request, pk):
    lesson = get_object_or_404(LessonFile, pk=pk)

    # Only the trainer who uploaded it or admin can edit
    if request.user.role == "trainer" and lesson.trainer != request.user.trainer_profile:
        return HttpResponseForbidden("You are not allowed to edit this lesson.")

    batches = request.user.trainer_profile.assigned_batches.all() if request.user.role == "trainer" else []

    if request.method == "POST":
        title = request.POST.get("title")
        selected_batches = request.POST.getlist("batches")
        file = request.FILES.get("file")

        lesson.title = title
        if file:
            lesson.file = file
        if selected_batches:
            lesson.batches.set(selected_batches)
        lesson.save()

        messages.success(request, "Lesson updated successfully.")
        return redirect("view_lessons")

    return render(request, "files/edit.html", {"lesson": lesson, "batches": batches})


# =====================
# Delete Lesson
# =====================
@login_required
def delete_lesson(request, pk):
    lesson = get_object_or_404(LessonFile, pk=pk)

    # Only the trainer who uploaded it or admin can delete
    if request.user.role == "trainer" and lesson.trainer != request.user.trainer_profile:
        return HttpResponseForbidden("You are not allowed to delete this lesson.")

    if request.method == "POST":
        lesson.delete()
        messages.success(request, "Lesson deleted successfully.")
        return redirect("view_lessons")

    return render(request, "files/confirm_delete.html", {"lesson": lesson})

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
            "today_date": date.today().strftime("%d-%m-%Y"),  # ✅ Fixed
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
                "today_date": date.today().strftime("%d-%m-%Y"),  # ✅ Fixed
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
    from datetime import date
    
    # ✅ Get absolute path to logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'vinduslogo.jpg')
    
    context = {
        'intern': intern,
        'today_date': date.today().strftime("%d-%m-%Y"),
        'logo_path': logo_path  # ✅ Add logo path here inside the context dict
    }
    
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





# =====================
# Course CRUD (Admin/Trainer/Superuser only)
# =====================
from .models import Course
from .forms import CourseForm
from .decorators import allowed_roles
from django.http import JsonResponse

@login_required
@allowed_roles(roles=["admin", "trainer", "superuser"])
def course_list(request):
    courses = Course.objects.all()
    return render(request, "courses/course_list.html", {"courses": courses})

@login_required
@allowed_roles(roles=["admin", "trainer", "superuser"])
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Course created successfully.")
            return redirect("course_list")
    else:
        form = CourseForm()
    return render(request, "courses/course_form.html", {"form": form, "title": "Add Course"})

@login_required
@allowed_roles(roles=["admin", "trainer", "superuser"])
def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "✏️ Course updated successfully.")
            return redirect("course_list")
    else:
        form = CourseForm(instance=course)
    return render(request, "courses/course_form.html", {"form": form, "title": "Edit Course"})

@login_required
@allowed_roles(roles=["admin", "trainer", "superuser"])
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        course.delete()
        messages.success(request, "🗑️ Course deleted successfully.")
        return redirect("course_list")
    return render(request, "courses/course_confirm_delete.html", {"course": course})
@login_required
@allowed_roles(roles=["admin", "trainer", "superuser"])
def course_delete_ajax(request, pk):
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        course = get_object_or_404(Course, pk=pk)
        course.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
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
    Allows an admin to filter by course/batch, search, and download Letters of Recommendation (LORs).
    """
    if not (request.user.is_superuser or request.user.role == 'admin'):
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')

    interns_qs = InternProfile.objects.select_related('user', 'batch', 'batch__course').order_by('user__first_name')

    # Using the same filter form as certificates view
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

    # POST: Handle LOR downloads
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_interns = None

        if action == 'download_selected':
            intern_ids = request.POST.getlist('intern_ids')
            if not intern_ids:
                messages.error(request, "Please select at least one intern.")
                return redirect(request.get_full_path())
            selected_interns = InternProfile.objects.filter(
                id__in=intern_ids, internship_status='Completed'
            )

        elif action == 'download_batch':
            batch_id = request.POST.get('batch_id')
            if not batch_id:
                messages.error(request, "Please filter by a batch first.")
                return redirect(request.get_full_path())
            selected_interns = InternProfile.objects.filter(
                batch_id=batch_id, internship_status='Completed'
            )

        # Generate ZIP of LOR PDFs
        if selected_interns and selected_interns.exists():
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                logo_path = os.path.join(settings.BASE_DIR, 'static/images/vinduslogo.png')

                for intern in selected_interns:
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
            messages.success(request, f"Successfully generated {selected_interns.count()} LORs.")
            return response
        else:
            messages.warning(request, "No completed interns were found for the selected action.")
            return redirect(request.get_full_path())

    context = {
        'interns': interns_qs,
        'filter_form': filter_form,
        'selected_batch': selected_batch,
    }
    return render(request, 'lors/manage_lors.html', context)

from datetime import datetime

@login_required
def download_lor_view(request, intern_id):
    """
    Download a Letter of Recommendation for a specific intern,
    only if internship is completed and project_title is filled.
    """
    intern = get_object_or_404(InternProfile, id=intern_id)

    # Check internship completion
    if intern.internship_status != 'Completed':
        messages.error(request, "LOR not available for this intern yet.")
        return redirect('manage_lor')

    # Check if project_title is filled
    if not intern.project_title or intern.project_title.strip() == "":
        messages.error(request, "The student hasn't completed the project yet.")
        return redirect('manage_lor')

    # Generate PDF only when both conditions are met
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/vinduslogo.png')
    context = {
        'intern': intern,
        'company': {
            "name": "VINDUS ENVIRONMENT PRIVATE LIMITED",
            "cin": "U62099TS2023PTC179794",
            "address": "#9-110, Shanti Nagar, Dilsukhnagar, Hyderabad-500060",
            "phone": "+91 40 49525396",
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
from datetime import datetime,date
import calendar
import openpyxl
from xhtml2pdf import pisa
from django.template.loader import get_template
import os
from django.conf import settings

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
        logo_path = os.path.join(settings.BASE_DIR, 'static/images/vinduslogo.jpg')
        today_date = datetime.now().strftime('%d-%m-%Y')
        
        html = template.render({
            'attendances': attendances,
            'summary': summary,
            'batch': batch,
            'selected_date': (datetime.strptime(date_input, "%Y-%m-%d").strftime('%d-%m-%Y') if date_input else today.strftime('%d-%m-%Y')),
            'month_input': month_input,
            'logo_path': logo_path,
            'today_date': today_date,
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




from django.db.models.functions import TruncMonth
from django.utils.dateformat import format

@login_required
def daily_update_list(request):
    user = request.user
    user_role = getattr(user, 'role', None)

    # Base queryset
    if user_role in ["admin", "superuser"]:
        updates = DailySessionUpdate.objects.all().order_by('-date')

        # Prepare months list from existing updates
        months_qs = updates.annotate(month=TruncMonth('date')).values('month').distinct()
        month_options = [(m['month'].strftime('%Y-%m'), m['month'].strftime('%B %Y')) for m in months_qs]

        # Filters
        date_filter = request.GET.get('date')
        month_filter = request.GET.get('month')  # format: YYYY-MM

        if date_filter:
            updates = updates.filter(date=date_filter)
        elif month_filter:
            year, month = map(int, month_filter.split('-'))
            updates = updates.filter(date__year=year, date__month=month)

    # Trainer view
    elif user_role == "trainer":
        trainer_profile = get_object_or_404(TrainerProfile, user=user)
        updates = DailySessionUpdate.objects.filter(trainer=trainer_profile).order_by('-date')
        month_options = []

    # Intern view
    elif user_role == "intern":
        try:
            intern_batch = user.intern_profile.batch
            updates = DailySessionUpdate.objects.filter(batch=intern_batch).order_by('-date')
        except AttributeError:
            updates = DailySessionUpdate.objects.none()
        month_options = []

    else:
        updates = DailySessionUpdate.objects.none()
        month_options = []

    return render(request, 'daily_updates/daily_update_list.html', {
        'updates': updates,
        'user_role': user_role,
        'month_options': month_options,
        'date_filter': date_filter if 'date_filter' in locals() else '',
        'month_filter': month_filter if 'month_filter' in locals() else '',
    })



@login_required
def daily_update_create(request):
    trainer_profile = get_object_or_404(TrainerProfile, user=request.user)

    if request.method == "POST":
        form = DailySessionUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.trainer = trainer_profile
            update.save()
            messages.success(request, "Daily session update submitted successfully!")
            return redirect('daily_update_list')
    else:
        form = DailySessionUpdateForm()

    return render(request, 'daily_updates/daily_update_form.html', {'form': form, 'title': 'Add Daily Session Update'})


@login_required
def daily_update_edit(request, pk):
    update = get_object_or_404(DailySessionUpdate, pk=pk)
    trainer_profile = get_object_or_404(TrainerProfile, user=request.user)

    # Only the trainer who created can edit
    if update.trainer != trainer_profile:
        messages.error(request, "You are not authorized to edit this entry.")
        return redirect('daily_update_list')

    if request.method == "POST":
        form = DailySessionUpdateForm(request.POST, instance=update)
        if form.is_valid():
            form.save()
            messages.success(request, "Session update edited successfully!")
            return redirect('daily_update_list')
    else:
        form = DailySessionUpdateForm(instance=update)

    return render(request, 'daily_updates/daily_update_form.html', {'form': form, 'title': 'Edit Daily Session Update'})


@login_required
def daily_update_delete(request, pk):
    update = get_object_or_404(DailySessionUpdate, pk=pk)
    trainer_profile = get_object_or_404(TrainerProfile, user=request.user)

    if update.trainer != trainer_profile:
        messages.error(request, "You are not authorized to delete this entry.")
        return redirect('daily_update_list')

    if request.method == "POST":
        update.delete()
        messages.success(request, "Session update deleted successfully!")
        return redirect('daily_update_list')

    return render(request, 'daily_updates/daily_update_confirm_delete.html', {'update': update})


@login_required
def daily_update_dashboard(request):
    user = request.user
    user_role = getattr(user, 'role', None)

    if user_role not in ["admin", "superuser"]:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('daily_update_list')

    # Filters from GET request
    selected_trainer = request.GET.get('trainer')
    selected_batch = request.GET.get('batch')
    selected_month = request.GET.get('month')  # format: YYYY-MM

    # Dropdown options
    trainers = TrainerProfile.objects.all().order_by('user__username')
    batches = Batch.objects.all().order_by('name')

    # Prepare months from existing updates
    all_updates = DailySessionUpdate.objects.all()
    months_qs = all_updates.annotate(month=TruncMonth('date')).values('month').distinct()
    month_options = [(m['month'].strftime('%Y-%m'), m['month'].strftime('%B %Y')) for m in months_qs]

    # Filtered trainer updates
    trainer_updates = []

    for trainer in trainers:
        updates = DailySessionUpdate.objects.filter(trainer=trainer).order_by('-date')

        if selected_trainer and str(trainer.id) != selected_trainer:
            updates = DailySessionUpdate.objects.none()
        if selected_batch:
            updates = updates.filter(batch_id=selected_batch)
        if selected_month:
            year, month = map(int, selected_month.split('-'))
            updates = updates.filter(date__year=year, date__month=month)

        trainer_updates.append({
            'trainer': trainer,
            'updates': updates
        })

    return render(request, 'daily_updates/daily_update_dashboard.html', {
        'trainer_updates': trainer_updates,
        'trainers': trainers,
        'batches': batches,
        'month_options': month_options,
        'selected_trainer': selected_trainer,
        'selected_batch': selected_batch,
        'selected_month': selected_month
    })





@login_required
def doubt_list(request):
    user = request.user
    role = getattr(user, 'role', None)

    # ============= INTERN =============
    if role == "intern":
        intern_profile = getattr(user, 'intern_profile', None)
        doubts = Doubt.objects.filter(intern=intern_profile).order_by('-created_at')
        return render(request, 'doubts/intern_doubt_list.html', {'doubts': doubts})

    # ============= TRAINER =============
    elif role == "trainer":
        trainer_profile = getattr(user, 'trainer_profile', None)
        unresolved_doubts = Doubt.objects.filter(trainer=trainer_profile, resolved=False).order_by('-created_at')
        resolved_doubts = Doubt.objects.filter(trainer=trainer_profile, resolved=True).order_by('-created_at')

        return render(request, 'doubts/trainer_doubt_list.html', {
            'unresolved_doubts': unresolved_doubts,
            'resolved_doubts': resolved_doubts
        })

    # ============= ADMIN / SUPERUSER =============
    else:
        doubts = Doubt.objects.all().order_by('-created_at')
        return render(request, 'doubts/admin_doubt_list.html', {'doubts': doubts})


@login_required
def doubt_create(request):
    user = request.user
    role = getattr(user, 'role', None)
    if role != "intern":
        messages.error(request, "Only interns can create doubts.")
        return redirect('doubt_list')

    intern_profile = getattr(user, 'intern_profile', None)
    if not intern_profile:
        messages.error(request, "Intern profile missing.")
        return redirect('doubt_list')

    # get intern's batch (adjust attribute name if different)
    batch = getattr(intern_profile, 'batch', None)
    if batch is None:
        messages.error(request, "Your batch is not set. Contact admin.")
        return redirect('doubt_list')

    # -------------------------
    # Robust trainer lookup:
    # TrainerProfile might use 'assigned_batches' (ManyToMany) or 'batch' (FK).
    # Check model fields and choose the correct lookup.
    # -------------------------
    field_names = [f.name for f in TrainerProfile._meta.get_fields()]
    if 'assigned_batches' in field_names:
        trainers = TrainerProfile.objects.filter(assigned_batches=batch)
    elif 'batch' in field_names:
        trainers = TrainerProfile.objects.filter(batch=batch)
    else:
        # fall back to empty queryset if no relationship found
        trainers = TrainerProfile.objects.none()

    if request.method == 'POST':
        form = DoubtForm(request.POST, trainers_qs=trainers)
        if form.is_valid():
            doubt = form.save(commit=False)
            doubt.intern = intern_profile
            doubt.batch = batch
            doubt.save()
            messages.success(request, "Your doubt has been submitted successfully!")
            return redirect('doubt_list')
    else:
        form = DoubtForm(trainers_qs=trainers)

    return render(request, 'doubts/doubt_form.html', {'form': form, 'title': 'Ask Doubt'})


@login_required
def resolve_doubt(request, pk):
    """Trainer resolves a doubt"""
    doubt = get_object_or_404(Doubt, pk=pk)
    user = request.user

    if getattr(user, 'role', None) != "trainer":
        messages.error(request, "Only trainers can resolve doubts.")
        return redirect('doubt_list')

    trainer_profile = user.trainer_profile
    if doubt.trainer != trainer_profile:
        messages.error(request, "This doubt is not assigned to you.")
        return redirect('doubt_list')

    # If already resolved, redirect
    if hasattr(doubt, 'resolution'):
        messages.info(request, "This doubt is already resolved.")
        return redirect('doubt_list')

    if request.method == 'POST':
        form = DoubtResolutionForm(request.POST)
        if form.is_valid():
            resolution = form.save(commit=False)
            resolution.doubt = doubt
            doubt.resolved = True
            doubt.save()
            resolution.save()
            messages.success(request, "Doubt resolved successfully!")
            return redirect('doubt_list')
    else:
        form = DoubtResolutionForm()

    return render(request, 'doubts/resolve_doubt.html', {'form': form, 'doubt': doubt})

@login_required
def recorded_session_list(request):
    user = request.user
    role = getattr(user, 'role', None)

    if role == "trainer":
        sessions = RecordedSession.objects.filter(trainer=user.trainer_profile).order_by('-uploaded_at')
    elif role == "intern":
        sessions = RecordedSession.objects.filter(batch=request.user.intern_profile.batch).order_by('-uploaded_at')
    else:  # Admin / Superuser
        sessions = RecordedSession.objects.all().order_by('-uploaded_at')

    return render(request, 'sessions/recorded_session_list.html', {'sessions': sessions})

# ----------------------
# CREATE RECORDED SESSION
# ----------------------
@login_required
def recorded_session_create(request):
    user = request.user
    role = getattr(user, 'role', None)

    if role not in ["trainer", "admin", "superuser"]:
        messages.error(request, "You are not authorized to upload sessions.")
        return redirect('recorded_session_list')

    if request.method == "POST":
        form = RecordedSessionForm(request.POST, request.FILES, user=user)
        if form.is_valid():
            session = form.save(commit=False)
            if role == "trainer":
                session.trainer = user.trainer_profile
            elif role in ["admin", "superuser"]:
                # Admin/Superuser must select trainer manually (optional: assign default trainer)
                session.trainer = form.cleaned_data.get('trainer') if 'trainer' in form.cleaned_data else None
            session.save()
            messages.success(request, "Recorded session uploaded successfully!")
            return redirect('recorded_session_list')
    else:
        form = RecordedSessionForm(user=user)

    return render(request, 'sessions/recorded_session_form.html', {'form': form, 'title': 'Upload Recorded Session'})

# ----------------------
# UPDATE RECORDED SESSION
# ----------------------
@login_required
def recorded_session_update(request, pk):
    session = get_object_or_404(RecordedSession, pk=pk)
    user = request.user
    role = getattr(user, 'role', None)

    if role == "trainer" and session.trainer != user.trainer_profile:
        messages.error(request, "You are not authorized to edit this session.")
        return redirect('recorded_session_list')

    if role not in ["trainer", "admin", "superuser"]:
        messages.error(request, "You are not authorized to edit sessions.")
        return redirect('recorded_session_list')

    if request.method == "POST":
        form = RecordedSessionForm(request.POST, request.FILES, instance=session, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Recorded session updated successfully!")
            return redirect('recorded_session_list')
    else:
        form = RecordedSessionForm(instance=session, user=user)

    return render(request, 'sessions/recorded_session_form.html', {'form': form, 'title': 'Edit Recorded Session'})

# ----------------------
# DELETE RECORDED SESSION
# ----------------------
@login_required
def recorded_session_delete(request, pk):
    session = get_object_or_404(RecordedSession, pk=pk)
    user = request.user
    role = getattr(user, 'role', None)

    if role == "trainer" and session.trainer != user.trainer_profile:
        messages.error(request, "You are not authorized to delete this session.")
        return redirect('recorded_session_list')

    if role not in ["trainer", "admin", "superuser"]:
        messages.error(request, "You are not authorized to delete sessions.")
        return redirect('recorded_session_list')

    if request.method == "POST":
        session.delete()
        messages.success(request, "Recorded session deleted successfully!")
        return redirect('recorded_session_list')

    return render(request, 'sessions/recorded_session_confirm_delete.html', {'session': session})



@login_required
def trainer_list(request):
    trainers = TrainerProfile.objects.all()
    query = request.GET.get('q')
    availability = request.GET.get('availability')

    if query:
        trainers = trainers.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(expertise__icontains=query) |
            Q(designation__icontains=query) |
            Q(highest_qualification__icontains=query)
        )

    if availability:
        trainers = trainers.filter(availability=availability)

    return render(request, "trainers/trainer_list.html", {"trainers": trainers})


# =======================
# Trainer Detail
# =======================
@login_required
def trainer_detail(request, pk):
    trainer = get_object_or_404(TrainerProfile, pk=pk)
    return render(request, "trainers/trainer_detail.html", {"trainer": trainer})


# =======================
# Trainer Create
# =======================
@login_required
def trainer_create(request):
    if request.method == "POST":
        form = TrainerProfileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Trainer profile created successfully.")
            return redirect("trainer_list")
    else:
        form = TrainerProfileForm()
    return render(request, "trainers/trainer_form.html", {"form": form})


# =======================
# Trainer Update
# =======================
@login_required
def trainer_update(request, pk):
    trainer = get_object_or_404(TrainerProfile, pk=pk)
    if request.method == "POST":
        form = TrainerProfileForm(request.POST, request.FILES, instance=trainer)
        if form.is_valid():
            form.save()
            messages.success(request, "Trainer profile updated successfully.")
            return redirect("trainer_list")
    else:
        form = TrainerProfileForm(instance=trainer)
    return render(request, "trainers/trainer_form.html", {"form": form})


# =======================
# Trainer Delete
# =======================
@login_required
def trainer_delete(request, pk):
    trainer = get_object_or_404(TrainerProfile, pk=pk)
    if request.method == "POST":
        trainer.delete()
        messages.success(request, "Trainer profile deleted successfully.")
        return redirect("trainer_list")
    return render(request, "trainers/trainer_confirm_delete.html", {"trainer": trainer})

from django.contrib.auth.decorators import user_passes_test
def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)

from django.db.models import Q, Count

@login_required
def user_list(request):
    if not request.user.is_superuser:
        return render(request, "users/no_access.html")
    
    users = User.objects.all()
    query = request.GET.get('q')
    role_filter = request.GET.get('role')
    
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )
    if role_filter:
        users = users.filter(role=role_filter)

    # Summary counts
    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    inactive_users = users.filter(is_active=False).count()
    role_counts = users.values('role').annotate(count=Count('role'))

    return render(request, "users/user_list.html", {
        "users": users,
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "role_counts": role_counts,
    })

# =======================
# User Detail/Edit View
# =======================
@superuser_required
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "User updated successfully.")
            return redirect("user_list")
    else:
        form = UserForm(instance=user)
    return render(request, "users/user_form.html", {"form": form})

# =======================
# Delete User
# =======================
@superuser_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        user.delete()
        messages.success(request, "User deleted successfully.")
        return redirect("user_list")
    return render(request, "users/user_confirm_delete.html", {"user": user})


from django.utils import timezone

@login_required
def create_assignment(request):
    if request.user.role != "trainer":
        return redirect('dashboard')

    trainer = request.user.trainer_profile
    batches = trainer.assigned_batches.all()

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        batch_id = request.POST.get("batch")
        file = request.FILES.get("file")
        deadline = request.POST.get("deadline")

        if not title or not batch_id or not deadline:
            messages.error(request, "All fields except file are required.")
            return redirect("create_assignment")

        assignment = Assignment.objects.create(
            trainer=trainer,
            batch_id=batch_id,
            title=title,
            description=description,
            file=file,
            deadline=deadline
        )
        messages.success(request, "Assignment created successfully!")
        return redirect("view_assignments")

    return render(request, "assignments/create_assignment.html", {"batches": batches})


@login_required
def view_assignments(request):
    user = request.user

    if user.role == "trainer":
        trainer = user.trainer_profile
        assignments = Assignment.objects.filter(trainer=trainer).order_by("-created_at")
    elif user.role in ["admin", "superuser"]:
        assignments = Assignment.objects.all().order_by("-created_at")
    else:
        return redirect("dashboard")

    return render(request, "assignments/view_assignments.html", {"assignments": assignments})

@login_required
def edit_assignment(request, pk):
    if request.user.role != "trainer":
        return redirect("dashboard")

    trainer = request.user.trainer_profile
    assignment = get_object_or_404(Assignment, pk=pk, trainer=trainer)
    batches = trainer.assigned_batches.all()

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        batch_id = request.POST.get("batch")
        file = request.FILES.get("file")
        deadline = request.POST.get("deadline")

        if not title or not batch_id or not deadline:
            messages.error(request, "All fields except file are required.")
            return redirect("edit_assignment", pk=assignment.id)

        assignment.title = title
        assignment.description = description
        assignment.batch_id = batch_id
        assignment.deadline = deadline

        if file:
            assignment.file = file

        assignment.save()
        messages.success(request, "Assignment updated successfully!")
        return redirect("view_assignments")

    return render(request, "assignments/edit_assignment.html", {
        "assignment": assignment,
        "batches": batches,
    })


@login_required
def delete_assignment(request, pk):
    if request.user.role != "trainer":
        return redirect("dashboard")

    trainer = request.user.trainer_profile
    assignment = get_object_or_404(Assignment, pk=pk, trainer=trainer)

    if request.method == "POST":
        assignment.delete()
        messages.success(request, "Assignment deleted successfully!")
        return redirect("view_assignments")

    return render(request, "assignments/delete_assignment.html", {"assignment": assignment})
# ==============================================
# Trainer: View Submissions & Grade
# ==============================================
@login_required
def view_submissions(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)

    if request.user.role == "trainer" and assignment.trainer != request.user.trainer_profile:
        return HttpResponseForbidden("You are not allowed to view these submissions.")

    submissions = assignment.submissions.select_related("intern").all()
    return render(request, "assignments/view_submissions.html", {
        "assignment": assignment,
        "submissions": submissions
    })


@login_required
def grade_submission(request, pk):
    submission = get_object_or_404(AssignmentSubmission, pk=pk)
    assignment = submission.assignment

    if request.user.role == "trainer" and assignment.trainer != request.user.trainer_profile:
        return HttpResponseForbidden("You are not allowed to grade this submission.")

    if request.method == "POST":
        score = request.POST.get("score")
        feedback = request.POST.get("feedback")

        submission.score = score
        submission.feedback = feedback
        submission.graded = True
        submission.save()

        messages.success(request, "Submission graded successfully!")
        return redirect("view_submissions", pk=assignment.id)

    return render(request, "assignments/grade_submission.html", {"submission": submission})
    

# ==============================================
# Intern: View Assignments & Submit
# ==============================================
@login_required
def intern_assignments(request):
    if request.user.role != "intern":
        return redirect("dashboard")

    intern = request.user.intern_profile
    batch = intern.batch

    # Get all assignments for the intern's batch
    assignments = Assignment.objects.filter(batch=batch).order_by("-created_at")

    # Get all submissions by this intern
    submissions = AssignmentSubmission.objects.filter(intern=intern)

    # Create a dictionary mapping assignment_id → submission object
    submission_map = {sub.assignment_id: sub for sub in submissions}

    # Combine both datasets
    assignment_data = []
    for assignment in assignments:
        submission = submission_map.get(assignment.id)
        assignment_data.append({
            "assignment": assignment,
            "submission": submission,
            "is_submitted": submission is not None,
            "is_graded": submission.graded if submission else False,
            "score": submission.score if submission and submission.graded else None,
            "feedback": submission.feedback if submission and submission.graded else None,
        })

    return render(request, "assignments/intern_assignments.html", {
        "assignment_data": assignment_data,
    })


@login_required
def submit_assignment(request, assignment_id):
    if request.user.role != "intern":
        return redirect("dashboard")

    intern = request.user.intern_profile
    assignment = get_object_or_404(Assignment, pk=assignment_id)

    # check if submission already exists
    if AssignmentSubmission.objects.filter(assignment=assignment, intern=intern).exists():
        messages.error(request, "You already submitted this assignment.")
        return redirect("intern_assignments")

    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]

        if timezone.now() > assignment.deadline:
            messages.warning(request, "Deadline has passed. Submission may be late.")

        AssignmentSubmission.objects.create(
            assignment=assignment,
            intern=intern,
            file=file
        )
        messages.success(request, "Assignment submitted successfully!")
        return redirect("intern_assignments")

    return render(request, "assignments/submit_assignment.html", {"assignment": assignment})


from django.db.models import Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Batch, Assignment, AssignmentSubmission, InternProfile, TrainerProfile

@login_required
def batch_scores(request):
    user = request.user
    selected_batch = None
    scoreboard = []
    total_assignments = 0

    # Determine available batches based on role
    if user.role == "intern":
        batches = Batch.objects.filter(id=user.intern_profile.batch.id)
    elif user.role == "trainer":
        batches = user.trainer_profile.assigned_batches.all()
    elif user.role in ["admin", "superuser"]:
        batches = Batch.objects.all()
    else:
        return redirect("dashboard")

    # If a batch is selected via GET
    batch_id = request.GET.get("batch_id")
    if batch_id:
        # Ensure the selected batch is in the user's accessible batches
        selected_batch = get_object_or_404(batches, id=batch_id)
        interns = selected_batch.interns.all()
        total_assignments = Assignment.objects.filter(batch=selected_batch).count()

        for intern in interns:
            submissions = AssignmentSubmission.objects.filter(
                intern=intern, assignment__batch=selected_batch
            )

            submitted_count = submissions.count()
            graded_count = submissions.filter(graded=True).count()
            total_score = submissions.aggregate(Sum("score"))["score__sum"] or 0
            avg_score = total_score / graded_count if graded_count > 0 else 0
            completion_rate = (submitted_count / total_assignments) * 100 if total_assignments > 0 else 0

            scoreboard.append({
                "intern": intern,
                "total_assignments": total_assignments,
                "submitted_count": submitted_count,
                "graded_count": graded_count,
                "total_score": round(total_score, 2),
                "average_score": round(avg_score, 2),
                "completion_rate": round(completion_rate, 2),
            })

    return render(request, "assignments/batch_scores.html", {
        "batches": batches,
        "selected_batch": selected_batch,
        "scoreboard": scoreboard,
    })


import io
import pdfplumber

def parse_mcq_txt(file):
    """Parses a TXT file into MCQ dicts"""
    mcqs = []
    content = file.read().decode("utf-8")
    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        question_text = lines[0]
        options = lines[1:5]
        correct_option = int(lines[5].split(":")[1].strip())
        mcqs.append({
            "question_text": question_text,
            "options": options,
            "correct_option": correct_option
        })
    return mcqs

def parse_mcq_pdf(file):
    """Parses PDF into MCQ dicts using pdfplumber"""
    mcqs = []
    with pdfplumber.open(file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
        blocks = text.strip().split("\n\n")
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 6:  # skip invalid blocks
                continue
            question_text = lines[0]
            options = lines[1:5]
            correct_option = int(lines[5].split(":")[1].strip())
            mcqs.append({
                "question_text": question_text,
                "options": options,
                "correct_option": correct_option
            })
    return mcqs

@login_required
def create_assessment(request):
    if request.user.role != "trainer":
        return redirect("dashboard")

    trainer = request.user.trainer_profile
    batches = trainer.assigned_batches.all()

    if request.method == "POST":
        title = request.POST.get("title")
        batch_id = request.POST.get("batch")
        file = request.FILES.get("file")

        if not title or not batch_id or not file:
            messages.error(request, "All fields are required.")
            return redirect("create_assessment")

        # Parse file
        if file.name.endswith(".txt"):
            mcqs = parse_mcq_txt(file)
        elif file.name.endswith(".pdf"):
            mcqs = parse_mcq_pdf(file)
        else:
            messages.error(request, "Only TXT or PDF files are supported.")
            return redirect("create_assessment")

        # Create assessment
        assessment = Assessment.objects.create(
            batch_id=batch_id,
            trainer=trainer,
            title=title,
            question_file=file,
            total_marks=len(mcqs)
        )

        # Save MCQs
        for mcq in mcqs:
            AssessmentMCQ.objects.create(
                assessment=assessment,
                question_text=mcq["question_text"],
                option_1=mcq["options"][0],
                option_2=mcq["options"][1],
                option_3=mcq["options"][2] if len(mcq["options"]) > 2 else "",
                option_4=mcq["options"][3] if len(mcq["options"]) > 3 else "",
                correct_option=mcq["correct_option"]
            )

        messages.success(request, f"Assessment '{title}' created successfully!")
        return redirect("view_assessments")

    return render(request, "assessments/create_assessment.html", {"batches": batches})


@login_required
def take_assessment(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)

    # Only intern of batch can take
    if request.user.role != "intern" or request.user.intern_profile.batch != assessment.batch:
        return redirect("dashboard")

    intern = request.user.intern_profile

    # Check if submission already exists
    submission = AssessmentSubmission.objects.filter(assessment=assessment, intern=intern).first()
    if submission:
        # Redirect to result if already submitted
        messages.info(request, "You have already submitted this assessment.")
        return redirect("assessment_result", submission.id)

    mcqs = assessment.mcqs.all()

    if request.method == "POST":
        answers = {}
        score = 0
        for mcq in mcqs:
            selected_option = int(request.POST.get(f"mcq_{mcq.id}", 0))
            answers[str(mcq.id)] = selected_option
            if selected_option == mcq.correct_option:
                score += 1

        # Create submission (no update)
        submission = AssessmentSubmission.objects.create(
            assessment=assessment,
            intern=intern,
            answers=answers,
            score=score
        )

        messages.success(request, "Assessment submitted successfully!")
        return redirect("assessment_result", submission.id)

    return render(request, "assessments/take_assessment.html", {"assessment": assessment, "mcqs": mcqs})

@login_required
def assessment_result(request, submission_id):
    submission = get_object_or_404(AssessmentSubmission, id=submission_id)
    mcqs = submission.assessment.mcqs.all()

    # Precompute selected answers for template
    for mcq in mcqs:
        # JSONField keys are strings, so cast mcq.id to string
        mcq.selected_answer = submission.answers.get(str(mcq.id), None)

    return render(request, "assessments/result.html", {
        "submission": submission,
        "mcqs": mcqs,
    })

@login_required
def view_assessments(request):
    user = request.user
    if user.role == "trainer":
        assessments = Assessment.objects.filter(trainer=user.trainer_profile)
    elif user.role in ["admin", "superuser"]:
        assessments = Assessment.objects.all()
    else:
        return redirect("dashboard")
    return render(request, "assessments/view_assessments.html", {"assessments": assessments})


@login_required
def edit_assessment(request, pk):
    assessment = get_object_or_404(Assessment, id=pk)
    # Optional: only trainer or admin can edit
    if request.user.role not in ["trainer", "admin", "superuser"]:
        return redirect("dashboard")

    if request.method == "POST":
        assessment.title = request.POST.get("title")
        assessment.total_marks = request.POST.get("total_marks")
        assessment.save()
        messages.success(request, "Assessment updated successfully!")
        return redirect("view_assessments")

    return render(request, "assessments/edit_assessment.html", {"assessment": assessment})


@login_required
def delete_assessment(request, pk):
    assessment = get_object_or_404(Assessment, id=pk)
    if request.user.role not in ["trainer", "admin", "superuser"]:
        return redirect("dashboard")

    assessment.delete()
    messages.success(request, "Assessment deleted successfully!")
    return redirect("view_assessments")


@login_required
def view_assessments_submissions(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    submissions = assessment.submissions.all()
    return render(request, "assessments/view_assessments_submissions.html", {
        "assessment": assessment,
        "submissions": submissions,
    })


@login_required
def intern_assessments(request):
    if request.user.role != "intern":
        return redirect("dashboard")

    intern = request.user.intern_profile
    batch = intern.batch

    # All assessments for the intern's batch
    assessments = Assessment.objects.filter(batch=batch).order_by("-created_at")

    # Collect submission info
    assessment_data = []
    for a in assessments:
        submission = AssessmentSubmission.objects.filter(assessment=a, intern=intern).first()
        assessment_data.append({
            "assessment": a,
            "is_submitted": bool(submission),
            "submission": submission,
            "score": submission.score if submission else None
        })

    return render(request, "assessments/intern_assessments.html", {"assignment_data": assessment_data})


@login_required
def batch_assessment_scores(request):
    user = request.user
    selected_batch = None
    scoreboard = []
    total_assessments = 0
    total_possible_score = 0

    # Determine accessible batches
    if user.role == "intern":
        batches = Batch.objects.filter(id=user.intern_profile.batch.id)
    elif user.role == "trainer":
        batches = user.trainer_profile.assigned_batches.all()
    elif user.role in ["admin", "superuser"]:
        batches = Batch.objects.all()
    else:
        return redirect("dashboard")

    # If batch selected via GET
    batch_id = request.GET.get("batch_id")
    if batch_id:
        selected_batch = get_object_or_404(batches, id=batch_id)
        interns = selected_batch.interns.all()
        assessments = Assessment.objects.filter(batch=selected_batch)
        total_assessments = assessments.count()
        total_possible_score = assessments.aggregate(Sum("total_marks"))["total_marks__sum"] or 0

        for intern in interns:
            submissions = AssessmentSubmission.objects.filter(
                intern=intern, assessment__batch=selected_batch
            )
            submitted_count = submissions.count()
            total_score = submissions.aggregate(Sum("score"))["score__sum"] or 0

            scoreboard.append({
                "intern": intern,
                "total_assessments": total_assessments,
                "submitted_count": submitted_count,
                "total_possible_score": total_possible_score,
                "score_secured": round(total_score, 2),
            })

    return render(request, "assessments/batch_assessment_scores.html", {
        "batches": batches,
        "selected_batch": selected_batch,
        "scoreboard": scoreboard,
    })
