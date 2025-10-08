from django.shortcuts import redirect
from django.contrib import messages

def allowed_roles(roles=[]):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):
            if request.user.role in roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "🚫 You are not authorized to access this page.")
                return redirect("dashboard")  # redirect interns
        return wrapper_func
    return decorator
