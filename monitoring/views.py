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
from monitoring.tasks import run_checker_task
import json
import logging
from monitoring.tasks import run_checker_task
from celery.result import AsyncResult
from django.http import JsonResponse





logger = logging.getLogger(__name__)





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




logger = logging.getLogger(__name__)

@login_required
def index(request):
    user_vehicles = Vehicle.objects.filter(user=request.user)
    offenses = TrafficOffense.objects.filter(vehicle__in=user_vehicles).order_by('-issued_date')

    plate_number = request.GET.get('plate_number')
    reference = request.GET.get('reference')
    license = request.GET.get('license')
    location = request.GET.get('location')
    offence = request.GET.get('offence')
    status = request.GET.get('status')
    is_paid = request.GET.get('is_paid')
    issued_date = request.GET.get('issued_date')

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
            parsed_date = datetime.strptime(issued_date, "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            try:
                parsed_date = datetime.strptime(issued_date, "%Y-%m-%d").date()
            except ValueError:
                parsed_date = None
        if parsed_date:
            offenses = offenses.filter(issued_date__date=parsed_date)

    paginator = Paginator(offenses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST' and 'trigger_check' in request.POST:
        task = run_checker_task.delay(request.user.id)
        logger.info(f"Triggered check for user {request.user.id}, task ID: {task.id}")
        request.session['check_task_id'] = task.id
        request.session['check_logs'] = []
        request.session['check_status'] = 'running'

    context = {
        "page_obj": page_obj,
        "user_vehicles": user_vehicles,
        "check_status": request.session.get('check_status'),
        "check_logs": request.session.get('check_logs', []),
    }
    return render(request, "monitoring/home.html", context)

@login_required
def check_status(request):
    task_id = request.GET.get('task_id')
    if not task_id:
        return JsonResponse({'status': 'ERROR', 'message': 'No task ID provided'})
    
    task = AsyncResult(task_id)
    logs = request.session.get('check_logs', [])
    
    if task.state == 'PENDING':
        status = 'running'
    elif task.state == 'SUCCESS':
        status = 'SUCCESS'
        request.session['check_status'] = 'completed'
        request.session['check_logs'] = logs + [f"Check completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
    elif task.state == 'FAILURE':
        status = 'FAILURE'
        request.session['check_status'] = 'failed'
        request.session['check_logs'] = logs + [f"Check failed: {str(task.result)}"]
    else:
        status = task.state
    
    return JsonResponse({'status': status, 'logs': request.session.get('check_logs', [])})