from django import forms
from .models import *

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["name", "description"]


class InternFilterForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=False,
        empty_label="--- All Courses ---",
        label="Filter by Course",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    batch = forms.ModelChoiceField(
        # The queryset will be dynamically set in __init__
        queryset=Batch.objects.all(),
        required=False,
        empty_label="--- All Batches ---",
        label="Filter by Batch",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    q = forms.CharField(
        required=False,
        label="Search by Name or Intern ID",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., John Doe or VCLPI001'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get the selected course from the submitted form data (if any)
        selected_course = self.data.get('course')

        if selected_course:
            try:
                # If a course is selected, filter the batch queryset
                self.fields['batch'].queryset = Batch.objects.filter(course_id=int(selected_course)).order_by('name')
            except (ValueError, TypeError):
                # If the course value is invalid, show no batches
                self.fields['batch'].queryset = Batch.objects.none()
        else:
            # If no course is selected (initial page load), ensure all batches are shown
            self.fields['batch'].queryset = Batch.objects.all().order_by('name')
            
            

from django import forms
from .models import Batch, Course, TrainerProfile

class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['name', 'course', 'description', 'trainer', 'start_date', 'end_date']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'trainer': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show trainers in the trainer dropdown
        self.fields['trainer'].queryset = TrainerProfile.objects.all()


from django.contrib.auth.forms import UserChangeForm


class UserUpdateForm(UserChangeForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone']
        exclude = ['password']  # Don't show password field

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove password field completely
        if 'password' in self.fields:
            del self.fields['password']

class InternProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = InternProfile
        exclude = [
            'user', 
            'unique_id', 
            'created_at',
            'undertaking_generated',
            'completion_certificate_generated',
            'lor_generated',
            'internship_status'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'skills': forms.Textarea(attrs={'rows': 3}),
            'prior_experience': forms.Textarea(attrs={'rows': 3}),
            'why_choose': forms.Textarea(attrs={'rows': 3}),
            'expectations': forms.Textarea(attrs={'rows': 3}),
            'career_goals': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class TrainerProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = TrainerProfile
        exclude = ['user', 'created_at']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

class AdminProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = AdminProfile
        exclude = ['user', 'created_at']

class SuperUserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = SuperUserProfile
        exclude = ['user', 'created_at']
        widgets = {
            'privileges': forms.Textarea(attrs={'rows': 4}),
        }