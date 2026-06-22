from django import forms
from django.contrib.auth.models import User
from .models import Course

class SignupForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    role = forms.ChoiceField(choices=[('Student','Student'), ('Teacher','Teacher'), ('Admin','Admin')])
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select courses to apply for (Student/Teacher only)"
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role')
        courses = cleaned.get('courses')
        if role in ['Student', 'Teacher'] and not courses:
            raise forms.ValidationError("Please select at least one course.")
        if role == 'Admin' and courses:
            cleaned['courses'] = []  # ignore courses for admin
        return cleaned