from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from .models import TrafficOffense
from datetime import datetime


def index(request):
    offenses = TrafficOffense.objects.all().order_by('-issued_date')

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
        offenses = offenses.filter(plate_number__icontains=plate_number)
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
    }
    return render(request, "monitoring/home.html", context)
