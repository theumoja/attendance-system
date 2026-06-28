from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from attendance.models import User

def custom_login_view(request):
    # If user is already authenticated, send them to their dashboard right away
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect_user_by_role(user)
    else:
        form = AuthenticationForm()
        
    return render(request, 'attendance/login.html', {'form': form})

def redirect_user_by_role(user):
    """Helper function to route users to their specific hub."""
    if user.role == User.IS_ADMIN:
        return redirect('attendance:admin_dashboard')
    elif user.role == User.IS_TEACHER:
        return redirect('attendance:teacher_dashboard')
    else:
        return redirect('attendance:student_dashboard')