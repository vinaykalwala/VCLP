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

@login_required
def view_lessons(request):
    lessons = LessonFile.objects.all()
    return render(request, "files/view.html", {"lessons": lessons})

# =====================
# BATCH CRUD VIEWS
# =====================

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