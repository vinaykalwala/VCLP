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



from .models import User, InternProfile, TrainerProfile, AdminProfile, SuperUserProfile, Attendance, LessonFile,Batch

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
