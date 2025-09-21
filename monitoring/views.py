from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import TrafficOffense, Vehicle, Balance, Transaction
from .forms import VehicleForm, DepositForm
from datetime import datetime

@login_required
def index(request):
    user_vehicles = Vehicle.objects.filter(user=request.user)
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
            parsed_date = datetime.strptime(issued_date, "%Y-%m-%d").date()
            offenses = offenses.filter(issued_date__date=parsed_date)
        except ValueError:
            pass

    # Pagination
    paginator = Paginator(offenses, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Dashboard stats
    total_vehicles = user_vehicles.count()
    balance, created = Balance.objects.get_or_create(user=request.user, defaults={'amount': 0.00})
    total_balance = balance.amount
    pending_offenses = TrafficOffense.objects.filter(vehicle__in=user_vehicles, status='Pending').count()
    paid_offenses = TrafficOffense.objects.filter(vehicle__in=user_vehicles, is_paid=True).count()
    total_penalty = TrafficOffense.objects.filter(vehicle__in=user_vehicles, penalty__gt=0).aggregate(Sum('penalty'))['penalty__sum'] or 0

    context = {
        "page_obj": page_obj,
        "user_vehicles": user_vehicles,
        "total_vehicles": total_vehicles,
        "total_balance": total_balance,
        "pending_offenses": pending_offenses,
        "paid_offenses": paid_offenses,
        "total_penalty": total_penalty,
    }
    return render(request, "monitoring/home.html", context)


@login_required
def vehicle_list(request):
    vehicles = Vehicle.objects.filter(user=request.user)
    return render(request, "monitoring/vehicle_list.html", {"vehicles": vehicles})

@login_required
def vehicle_add(request):
    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.user = request.user
            vehicle.save()
            messages.success(request, "Vehicle added successfully.")
            return redirect("vehicle_list")
    else:
        form = VehicleForm()
    return render(request, "monitoring/vehicle_form.html", {"form": form, "title": "Add Vehicle"})

@login_required
def vehicle_edit(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    if request.method == "POST":
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle updated successfully.")
            return redirect("vehicle_list")
    else:
        # Prepopulate check_interval_value and check_interval_unit
        check_interval = vehicle.check_interval
        if check_interval >= 86400:  # Days
            form = VehicleForm(
                instance=vehicle,
                initial={'check_interval_value': check_interval // 86400, 'check_interval_unit': 'days'}
            )
        elif check_interval >= 3600:  # Hours
            form = VehicleForm(
                instance=vehicle,
                initial={'check_interval_value': check_interval // 3600, 'check_interval_unit': 'hours'}
            )
        else:  # Minutes
            form = VehicleForm(
                instance=vehicle,
                initial={'check_interval_value': check_interval // 60, 'check_interval_unit': 'minutes'}
            )
    return render(request, "monitoring/vehicle_form.html", {"form": form, "title": "Edit Vehicle"})

@login_required
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    if request.method == "POST":
        vehicle.delete()
        messages.success(request, "Vehicle deleted successfully.")
        return redirect("vehicle_list")
    return render(request, "monitoring/vehicle_confirm_delete.html", {"vehicle": vehicle})

@login_required
def pending_offenses(request):
    user_vehicles = Vehicle.objects.filter(user=request.user)
    offenses = TrafficOffense.objects.filter(vehicle__in=user_vehicles, status='Pending').order_by('-issued_date')
    paginator = Paginator(offenses, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "monitoring/offense_list.html", {"page_obj": page_obj, "title": "Pending Offenses"})

@login_required
def paid_offenses(request):
    user_vehicles = Vehicle.objects.filter(user=request.user)
    offenses = TrafficOffense.objects.filter(vehicle__in=user_vehicles, is_paid=True).order_by('-issued_date')
    paginator = Paginator(offenses, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "monitoring/offense_list.html", {"page_obj": page_obj, "title": "Paid Offenses"})

@login_required
def penalty_offenses(request):
    user_vehicles = Vehicle.objects.filter(user=request.user)
    offenses = TrafficOffense.objects.filter(vehicle__in=user_vehicles, penalty__gt=0).order_by('-issued_date')
    paginator = Paginator(offenses, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "monitoring/offense_list.html", {"page_obj": page_obj, "title": "Offenses with Penalty"})

@login_required
def balance_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(transactions, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "monitoring/balance_history.html", {"page_obj": page_obj, "title": "Balance History"})

@login_required
def deposit(request):
    if request.method == "POST":
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            balance, created = Balance.objects.get_or_create(user=request.user, defaults={'amount': 0.00})
            balance.amount += amount
            balance.save()
            Transaction.objects.create(
                user=request.user,
                amount=amount,
                transaction_type='DEPOSIT',
                description=f"Deposit of TZS {amount}"
            )
            messages.success(request, f"Deposited TZS {amount} successfully.")
            return redirect("balance_history")
    else:
        form = DepositForm()
    return render(request, "monitoring/deposit_form.html", {"form": form, "title": "Deposit Funds"})