# core/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Course, CourseUnit

class SignupForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    role = forms.ChoiceField(choices=[('Student','Student'), ('Teacher','Teacher'), ('Admin','Admin')])
    
    # Teachers apply for entire courses
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select courses to apply for (Teachers only)"
    )
    # Students enroll in specific units
    units = forms.ModelMultipleChoiceField(
        queryset=CourseUnit.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select specific units to enroll in (Students only)"
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
        units = cleaned.get('units')

        if role == 'Teacher' and not courses:
            raise forms.ValidationError("Please select at least one course to teach.")
        if role == 'Student' and not units:
            raise forms.ValidationError("Please select at least one course unit to enroll in.")
        
        # Strip irrelevant information based on roles
        if role == 'Admin':
            cleaned['courses'] = []
            cleaned['units'] = []
        elif role == 'Teacher':
            cleaned['units'] = []
        elif role == 'Student':
            cleaned['courses'] = []
        return cleaned