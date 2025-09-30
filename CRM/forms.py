from django import forms
from .models import Course

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["name", "description"]


from django import forms
from .models import Course, Batch

class InternFilterForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=False,
        empty_label="--- All Courses ---",
        label="Filter by Course",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.none(),  # We will populate this dynamically in the view
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
        if 'course' in self.data:
            try:
                course_id = int(self.data.get('course'))
                self.fields['batch'].queryset = Batch.objects.filter(course_id=course_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from browser; ignore and fallback to empty queryset
        elif 'batch' in self.initial:
             self.fields['batch'].queryset = Batch.objects.filter(pk=self.initial['batch'].pk)