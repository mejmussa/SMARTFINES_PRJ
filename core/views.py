from django.shortcuts import render, redirect
from django.conf import settings
from django.http import FileResponse, Http404
from django.views import View
from django.contrib.auth import login, logout
from django.utils.text import slugify
from accounts.models import User
import os, base64, hashlib, requests, uuid, random, logging
from django.contrib.auth.decorators import login_required
import secrets
from phonenumber_field.modelfields import PhoneNumberField
from django.core.files.base import ContentFile


# ✅ Update this with your real plain text client secret
# PRODUCTION SECRETS
CLIENT_ID = 'z9WF2rpGCegt8JnosLtVpzf2T9HRmuzPTrgQy2qr'
CLIENT_SECRET='VerbwziHwAx0oICxZrdz7tQu4JZMDiYOTWy7t8jBiUCaqkNgXXESlq8LTyppZpKLobhC4X3sevyXzbaAEARf0SeiruxU8y3zRD0GLzGJjdfQUV1Srqqw9Z8S7Ne0SaWr'
REDIRECT_URI = 'https://smartfines.net/oauth/callback/'
AUTH_SERVER_BASE_URL = 'https://www.tecmocsy.com/accounts'  # ❌ no trailing slash



oauth_logger = logging.getLogger('oauth')
PWA_ROOT = os.path.join(settings.BASE_DIR, 'pwa_assets')


class PWAServeView(View):
    def get(self, request, filename):
        filepath = os.path.join(PWA_ROOT, filename)
        if not os.path.exists(filepath):
            raise Http404("File not found")
        return FileResponse(open(filepath, 'rb'))

def login_view(request):
    request.session['next_url'] = request.GET.get('next') or '/'

    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b'=').decode()
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b'=').decode()

    request.session['code_verifier'] = code_verifier

    auth_url = (
        f"{AUTH_SERVER_BASE_URL}/o/authorize/?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=read"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
        f"&state={secrets.token_urlsafe(16)}"
    )
    return redirect(auth_url)


def oauth_callback(request):
    code = request.GET.get('code')
    code_verifier = request.session.get('code_verifier')

    if not code or not code_verifier:
        return redirect('login')

    # Step 1: Exchange code for token
    token_url = f"{AUTH_SERVER_BASE_URL}/o/token/"
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'code_verifier': code_verifier,
        'client_secret': CLIENT_SECRET,
    }

    try:
        token_response = requests.post(token_url, data=data)
        token_response.raise_for_status()
        token_json = token_response.json()
    except Exception as e:
        print("❌ Token exchange failed:", str(e))
        return redirect('login')

    access_token = token_json.get('access_token')
    if not access_token:
        print("❌ No access token received")
        return redirect('login')

    # Step 2: Get user info
    userinfo_url = f"{AUTH_SERVER_BASE_URL}/o/userinfo/"
    try:
        r = requests.get(userinfo_url, headers={'Authorization': f'Bearer {access_token}'})
        r.raise_for_status()
        user_data = r.json()
    except Exception as e:
        print("❌ Failed to fetch user info:", str(e))
        return redirect('login')

    # Step 3: Extract data
    username = user_data.get('username') or f"user-{uuid.uuid4().hex[:6]}"
    email = user_data.get('email')
    phone = user_data.get('phone')
    slug = user_data.get('slug')
    image_url = user_data.get('image')  # URL string or None

    if not email:
        print("❌ No email received from OAuth provider")
        return redirect('login')

    # Step 4: Create or update user
    try:
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'phone': phone,
                'slug': slug or slugify(username),
                'is_active': True,
            }
        )

        if not created:
            updated = False
            if user.username != username:
                user.username = username
                updated = True
            if phone and user.phone != phone:
                user.phone = phone
                updated = True
            if slug and user.slug != slug:
                user.slug = slug
                updated = True
            if updated:
                user.save(update_fields=['username', 'phone', 'slug'])

        # ✅ Step 5: Save image if it's new or changed
        if image_url:
            try:
                # Convert relative URL to full if needed
                if image_url.startswith('/'):
                    image_url = 'https://www.smartfines.net' + image_url  # Use your actual domain in production

                # Save image only if it's new
                if user.provider_image_url != image_url:
                    img_response = requests.get(image_url)
                    img_response.raise_for_status()
                    img_content = ContentFile(img_response.content)

                    # Use original filename from provider URL
                    original_filename = os.path.basename(image_url)
                    if not original_filename or '.' not in original_filename or len(original_filename) > 100:
                        original_filename = f"{slug or slugify(username)}_avatar.jpg"

                    # Save image and update image URL tracker
                    user.image.save(original_filename, img_content, save=False)
                    user.provider_image_url = image_url
                    user.save()
                    print("✅ Profile image saved successfully.")
                else:
                    print("ℹ️ Profile image unchanged. Skipping download.")
            except Exception as e:
                print("⚠️ Failed to save profile image:", str(e))


    except Exception as e:
        print("❌ Error creating or updating user:", str(e))
        return redirect('login')

    # Step 6: Log user in
    try:
        login(request, user)
    except Exception as e:
        print("❌ Login failed:", str(e))
        return redirect('login')

    # Step 7: Redirect to next or home
    return redirect(request.session.pop('next_url', '/'))


def logout_view(request):
    logout(request)
    return redirect('home')

def home(request):
    if request.user.is_authenticated:
        # Redirect to business selection page
        return redirect('index')  # You must define this name in urls.py
    return render(request, 'core/home.html', {'user': None})
