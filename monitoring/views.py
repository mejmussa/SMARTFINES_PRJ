from django.core.paginator import Paginator
from django.db.models import Q
from .models import TrafficOffense, Vehicle
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import VehicleForm
import requests
import base64
from django.conf import settings
from monitoring.models import Vehicle
from monitoring.tms_check import run_checker
import asyncio





@login_required
def vehicle_list(request):
    vehicles = request.user.vehicles.all()
    return render(request, "vehicles/list.html", {"vehicles": vehicles})

@login_required
def vehicle_add(request):
    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.user = request.user
            vehicle.save()
            return redirect("vehicle_list")
    else:
        form = VehicleForm()
    return render(request, "vehicles/add_edit.html", {"form": form})

@login_required
def vehicle_edit(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    if request.method == "POST":
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            return redirect("vehicle_list")
    else:
        form = VehicleForm(instance=vehicle)
    return render(request, "vehicles/add_edit.html", {"form": form})

@login_required
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    vehicle.delete()
    return redirect("vehicle_list")


@login_required
def index(request):
    # Get all vehicles owned by the logged-in user
    user_vehicles = Vehicle.objects.filter(user=request.user)
    
    # Get offenses linked to these vehicles
    offenses = TrafficOffense.objects.filter(vehicle__in=user_vehicles).order_by('-issued_date')

    # Get query parameters
    plate_number = request.GET.get('plate_number')
    reference = request.GET.get('reference')
    license = request.GET.get('license')
    location = request.GET.get('location')
    offence = request.GET.get('offence')
    status = request.GET.get('status')
    is_paid = request.GET.get('is_paid')
    issued_date = request.GET.get('issued_date')

    # Build filters
    if plate_number:
        offenses = offenses.filter(vehicle__plate_number__icontains=plate_number)
    if reference:
        offenses = offenses.filter(reference__icontains=reference)
    if license:
        offenses = offenses.filter(license__icontains=license)
    if location:
        offenses = offenses.filter(location__icontains=location)
    if offence:
        offenses = offenses.filter(offence__icontains=offence)
    if status:
        offenses = offenses.filter(status__icontains=status)
    if is_paid is not None and is_paid != '':
        if is_paid.lower() == 'true':
            offenses = offenses.filter(is_paid=True)
        elif is_paid.lower() == 'false':
            offenses = offenses.filter(is_paid=False)
    if issued_date:
        try:
            # Try parsing full datetime first
            parsed_date = datetime.strptime(issued_date, "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            try:
                # Fallback: Try just date
                parsed_date = datetime.strptime(issued_date, "%Y-%m-%d").date()
            except ValueError:
                parsed_date = None

        if parsed_date:
            offenses = offenses.filter(issued_date__date=parsed_date)

    # Pagination
    paginator = Paginator(offenses, 10)  # Show 10 offenses per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "user_vehicles": user_vehicles,  # optional, in case you want to display user's vehicles
    }
    return render(request, "monitoring/home.html", context)

