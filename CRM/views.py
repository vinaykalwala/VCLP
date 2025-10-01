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
import zipfile
import datetime
import os
from django.conf import settings

from .models import User, InternProfile, TrainerProfile, AdminProfile, SuperUserProfile, Attendance, LessonFile,Batch,Course

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

    if request.method == "POST" and request.FILES.get("file"):
        trainer = request.user.trainer_profile
        title = request.POST.get("title")
        file = request.FILES["file"]
        LessonFile.objects.create(trainer=trainer, title=title, file=file)
        messages.success(request, "File uploaded successfully.")
        return redirect("upload_lesson")

    return render(request, "files/upload.html")


@login_required
def view_lessons(request):
    lessons = LessonFile.objects.all()
    return render(request, "files/view.html", {"lessons": lessons})


# -------------------------
# Helper function to generate PDF
# -------------------------

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
                    "cin": "U12345XYZ",
                    "address": "123 Legal Street, City, State, ZIP",
                    "phone": "+91-1234567890",
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

# -------------------------
# Single intern PDF
# -------------------------




# ================================
# Certificate Management View (Admin)
# ================================


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

    # ----------------------
    # Multiple/batch: generate separate PDFs in a ZIP
    # ----------------------
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for intern in interns:
            html_content = render_to_string("undertaking_letter.html", {"intern": intern})
            pdf_buffer = io.BytesIO()
            pisa.CreatePDF(html_content, dest=pdf_buffer)
            pdf_buffer.seek(0)

            # Add to ZIP
            pdf_name = f"{intern.unique_id}_undertaking.pdf"
            zip_file.writestr(pdf_name, pdf_buffer.read())

            # Update status
            intern.undertaking_generated = True
            intern.save()

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="interns_undertakings.zip"'
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
