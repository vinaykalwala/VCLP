from django.shortcuts import render

def home(request):
    return render(request, 'home.html')  # Template we will create
