from django.shortcuts import render, redirect

def index(request):
    if request.user.is_authenticated:
        # Redirect to business selection page
        return redirect('index')  # You must define this name in urls.py
    return render(request, 'monitoring/index.html', {'user': None})
