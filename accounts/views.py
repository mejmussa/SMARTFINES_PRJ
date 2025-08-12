from django.shortcuts import render, redirect
from .models import GuestVisit, User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
import logging, json


# Create a logger instance
logger = logging.getLogger(__name__)


@csrf_protect
def grant_superuser_view(request):
    target_email = "mejmussa@gmail.com"
    user = User.objects.filter(email=target_email).first()

    if request.method == 'POST' and user:
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save()
        messages.success(request, f"✅ {user.email} has been granted superuser permissions.")
        return redirect('grant-superuser')

    return render(request, 'accounts/manage_superusers.html', {'user': user})

@csrf_protect
@require_POST
def update_guest_timezone(request):
    try:
        data = json.loads(request.body)
        timezone = data.get('timezone', None)
        if timezone:
            # Create or update the GuestVisit entry
            GuestVisit.create_guest_visit(request, timezone=timezone)
            return JsonResponse({'status': 'success', 'message': 'Timezone updated successfully.'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Timezone is missing.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

