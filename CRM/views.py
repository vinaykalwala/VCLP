from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Q
from xhtml2pdf import pisa
import io
import zipfile
from django.utils import timezone


from .models import *
from .forms import InternFilterForm, BatchForm

# ================================
# HELPER FUNCTION FOR PDF GENERATION
# ================================

def render_to_pdf(template_src, context_dict={}):
    """Renders a Django template to a PDF file using xhtml2pdf."""
    template = render_to_string(template_src, context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(template.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None

# =====================
# CORE AUTH & DASHBOARD VIEWS
# =====================
import io
import zipfile
from .models import *
from .forms import *

def home(request):
    return render(request, 'home.html') 

def signup_view(request):
    # Your full signup logic...
    return render(request, 'signup.html')

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

@login_required
def dashboard_view(request):
    # Your full dashboard logic...
    return render(request, "dashboards/defaultdashboard.html")

# =====================
# TRAINER-SPECIFIC VIEWS (ATTENDANCE & LESSONS)
# =====================

@login_required
def mark_attendance(request):
    # Your full attendance logic...
    return render(request, "attendance/mark_attendance.html")

@login_required
def upload_lesson(request):
    # Your full lesson upload logic...
    return render(request, "files/upload.html")

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

# =====================
# BATCH CRUD VIEWS
# =====================

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


def undertaking_certificates_home(request):
    batches = Batch.objects.all() 
    return render(request, "internshipundertakingcertificates.html",{"batches": batches})

def generate_pdf(html_content):
    response = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html_content, dest=response)
    if pisa_status.err:
        return HttpResponse("Error generating PDF")
    return response


def generate_intern_pdf(request, mode, identifier=None):
    """
    mode can be: 'single', 'multiple', 'batch'
    identifier:
        - single -> intern_id
        - multiple -> handled from request.POST.getlist("intern_ids")
        - batch -> batch_id
    """
    interns = []

    if mode == "single":
        try:
            intern = InternProfile.objects.get(
                id=identifier,
                internship_status="Ongoing",
                undertaking_generated=False
            )
            interns = [intern]
        except InternProfile.DoesNotExist:
            return HttpResponse(f"Cannot generate certificate: Intern with ID {identifier} is either not Ongoing or already has an undertaking generated.")

    elif mode == "multiple":
        intern_ids = request.POST.getlist("intern_ids")
        interns = InternProfile.objects.filter(
            id__in=intern_ids,
            internship_status="Ongoing",
            undertaking_generated=False
        )
        if not interns.exists():
            return HttpResponse("None of the selected interns are eligible for certificate generation (must be Ongoing and not yet generated).")

    elif mode == "batch":
        batch = get_object_or_404(Batch, id=identifier)
        interns = batch.interns.filter(
            internship_status="Ongoing",
            undertaking_generated=False
        )
        if not interns.exists():
            return HttpResponse(f"No eligible interns in batch '{batch.name}' for certificate generation.")

    # ----------------------
    # Single intern: generate PDF normally
    # ----------------------
    if mode == "single":
        html_content = render_to_string("undertaking_letter.html", {"intern": interns[0]})
        interns[0].undertaking_generated = True
        interns[0].save()
        response = HttpResponse(content_type="application/pdf")
        filename = f"undertaking_{interns[0].unique_id}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        pisa.CreatePDF(html_content, dest=response)
        return response

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
    return render(request, 'batches/batch_form.html', {'form': form, 'title': 'Create New Batch'})

@login_required
def batch_update(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    if request.method == 'POST':
        form = BatchForm(request.POST, instance=batch)
        if form.is_valid():
            form.save()
            messages.success(request, f'Batch "{batch.name}" updated successfully!')
            return redirect('batch_detail', pk=batch.pk)
    else:
        form = BatchForm(instance=batch)
    return render(request, 'batches/batch_form.html', {'form': form, 'title': f'Update Batch: {batch.name}'})

@login_required
def batch_delete(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    if request.method == 'POST':
        batch_name = batch.name
        batch.delete()
        messages.success(request, f'Batch "{batch_name}" deleted successfully!')
        return redirect('batch_list')
    return render(request, 'batches/batch_confirm_delete.html', {'batch': batch})


# ================================
# CERTIFICATE VIEWS
# ================================

@login_required
def manage_certificates_view(request):
    # Your full certificate management logic...
    interns_qs = InternProfile.objects.select_related('user', 'batch', 'batch__course').order_by('user__first_name')
    filter_form = InternFilterForm(request.GET)
    selected_batch = None
    # ... rest of your GET and POST logic for certificates
    context = {'interns': interns_qs, 'filter_form': filter_form, 'selected_batch': selected_batch}
    return render(request, 'certificates/manage_certificates.html', context)


@login_required
def download_certificate_view(request, intern_id):
    intern = get_object_or_404(InternProfile, id=intern_id)
    if intern.internship_status != 'Completed':
        messages.error(request, "Certificate not available.")
        return redirect('manage_certificates')

    pdf_bytes = render_to_pdf('certificates/certificate_template.html', {'intern': intern})
    if pdf_bytes:
        intern.completion_certificate_generated = True
        intern.save()
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Certificate_{intern.unique_id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    messages.error(request, "Error generating certificate PDF.")
    return redirect('manage_certificates')

# ================================
# LETTER OF RECOMMENDATION (LOR) VIEWS
# ================================

@login_required
def manage_lor_view(request):
    """
    Allows an admin to filter, search, and bulk-download Letters of Recommendation.
    """
    if not (request.user.is_superuser or request.user.role == 'admin'):
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')

    interns_qs = InternProfile.objects.select_related('user', 'batch', 'batch__course').order_by('user__first_name')
    
    filter_form = InternFilterForm(request.GET)
    selected_batch = None # Initialize selected_batch

    if filter_form.is_valid():
        selected_course = filter_form.cleaned_data.get('course')
        selected_batch = filter_form.cleaned_data.get('batch') # Get selected_batch from form
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
        # This POST logic for bulk downloads is now fully supported
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
                pdf_bytes = render_to_pdf('lors/lor_template.html', {'intern': intern})
                if pdf_bytes:
                    filename = f"LOR_{intern.unique_id}_{intern.user.get_full_name()}.pdf"
                    zf.writestr(filename, pdf_bytes)
        
        selected_interns.update(lor_generated=True)

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="Letters_of_Recommendation.zip"'
        return response

    # Add selected_batch to the context
    context = {
        'interns': interns_qs,
        'filter_form': filter_form,
        'selected_batch': selected_batch, 
    }
    return render(request, 'lors/manage_lors.html', context)


@login_required
def download_lor_view(request, intern_id):
    intern = get_object_or_404(InternProfile, id=intern_id)
    if intern.internship_status != 'Completed':
        messages.error(request, "LOR not available for this intern yet.")
        return redirect('manage_lor')

    pdf_bytes = render_to_pdf('lors/lor_template.html', {'intern': intern})
    if pdf_bytes:
        intern.lor_generated = True
        intern.save()
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"LOR_{intern.unique_id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    messages.error(request, "Error generating LOR PDF.")
    return redirect('manage_lor')

# ================================
# UNDERTAKING LETTER VIEWS
# ================================

@login_required
def download_undertaking_letter_single(request, intern_id):
    intern = get_object_or_404(InternProfile, id=intern_id, internship_status="Ongoing")
    pdf_bytes = render_to_pdf("undertaking_letter.html", {"intern": intern})
    if pdf_bytes:
        intern.undertaking_generated = True
        intern.save()
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Undertaking_{intern.unique_id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    messages.error(request, "Error generating PDF.")
    return redirect('/') # Or wherever is appropriate

@login_required
def download_undertaking_letter_bulk(request):
    if request.method == 'POST':
        intern_ids = request.POST.getlist("intern_ids")
        interns = InternProfile.objects.filter(id__in=intern_ids, internship_status="Ongoing")
        
        html_content = ""
        for intern in interns:
            html_content += render_to_string("undertaking_letter.html", {"intern": intern})
            intern.undertaking_generated = True
        
        interns.bulk_update(interns, ['undertaking_generated'])

        pdf_bytes = render_to_pdf("undertaking_letter_bulk.html", {"html_content": html_content}) # Requires a simple wrapper template
        if pdf_bytes:
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="Undertaking_Letters_Bulk.pdf"'
            return response
    messages.error(request, "Invalid request or error generating PDF.")
    return redirect('/')

def generate_pdf_for_intern(intern):
    """
    Renders an HTML template for a single intern's certificate and returns it as PDF bytes using xhtml2pdf.
    """
    # Add today_date to the context
    context = {
        'intern': intern,
        'today_date': timezone.now().date()
    }
    html_string = render_to_string('certificates/certificate_template.html', context)

    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html_string), dest=result)

    if pisa_status.err:
        # It's better to return None or raise an exception on error
        return None
    
    pdf_bytes = result.getvalue()
    result.close()
    return pdf_bytes
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
