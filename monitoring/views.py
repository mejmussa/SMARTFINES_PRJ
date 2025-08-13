from django.shortcuts import render, redirect
from .models import Vehicle
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    if request.method == "POST":
        name = request.POST.get("name")
        plate_number = request.POST.get("plate_number")
        description = request.POST.get("description")
        Vehicle.objects.create(
            user=request.user,
            name=name,
            plate_number=plate_number,
            description=description
        )
        return redirect("index")

    vehicles = Vehicle.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "monitoring/index.html", {"vehicles": vehicles})

