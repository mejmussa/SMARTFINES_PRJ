from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from phonenumber_field.modelfields import PhoneNumberField
import random, string, shutil, os, phonenumbers, pytz, uuid, logging, csv, random, time
from datetime import date
from django_countries.fields import CountryField
from phonenumbers import parse, carrier, NumberParseException
from django.utils.html import mark_safe
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.conf import settings
from user_agents import parse
from datetime import timedelta, datetime
from django.core.files.storage import default_storage



logger = logging.getLogger(__name__)  


# ✅ Image path generator
def user_directory_path(instance, filename):
    """
    Generate a unique file path for the user's uploaded image.
    """
    user_id = instance.pk or 'anonymous'
    extension = os.path.splitext(filename)[-1] or '.jpg'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    unique_filename = f"{timestamp}_{random_string}{extension}"
    file_path = f"user_profile_files/user_{user_id}/{unique_filename}"

    # Optional: avoid duplication
    if default_storage.exists(file_path):
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        unique_filename = f"{timestamp}_{random_string}{extension}"
        file_path = f"user_profile_files/user_{user_id}/{unique_filename}"

    return file_path


# ✅ Custom user manager
class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, password, **extra_fields)


# ✅ Custom user model
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=20, unique=True)
    phone = PhoneNumberField(blank=True, null=True)
    carrier_name = models.CharField(max_length=200, blank=True, null=True)
    image = models.ImageField(upload_to=user_directory_path, default="default.jpg")
    provider_image_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)    # Updates every time the model instance is saved
    slug = models.SlugField(unique=True, blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone']

    def save(self, *args, **kwargs):
        # 🧠 Automatically set carrier name based on phone
        if self.phone:
            try:
                parsed_number = phonenumbers.parse(str(self.phone), None)
                name = phonenumbers.carrier.name_for_number(parsed_number, "en")
                self.carrier_name = name[:198] if name else "Unknown"
            except phonenumbers.NumberParseException:
                self.carrier_name = "Unknown"
        else:
            self.carrier_name = "Unknown"

        super().save(*args, **kwargs)

    def Image(self):
        # ✅ Safe admin image preview
        if self.image:
            return mark_safe(f'<img src="{self.image.url}" width="40" height="40" />')
        return "No Image"

    def __str__(self):
        return self.email

class GuestVisit(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=45)
    platform = models.CharField(max_length=100)
    browser = models.CharField(max_length=100)
    browser_version = models.CharField(max_length=50)
    timezone = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Visit from {self.ip_address} at {self.timestamp}"

    @classmethod
    def create_guest_visit(cls, request, timezone=None):
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        user_agent_parsed = parse(user_agent)

        platform = user_agent_parsed.os.family
        browser = user_agent_parsed.browser.family
        browser_version = user_agent_parsed.browser.version_string

        # Handle timezone
        if timezone:
            try:
                user_timezone = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                user_timezone = pytz.utc
                #print(f"Invalid timezone provided, defaulting to UTC: {timezone}")
        else:
            user_timezone = pytz.utc  # Default to UTC if no timezone is provided
           # print("No timezone provided, defaulting to UTC")

        # Check if the same IP + User-Agent combination exists in the last 24 hours
        last_visit = cls.objects.filter(
            ip_address=ip_address,
            platform=platform,
            browser=browser,
            browser_version=browser_version,
            timezone=timezone or 'Unknown',
            timestamp__gte=user_timezone.localize(datetime.now()) - timedelta(hours=24)
        ).first()

        if last_visit:
            #print(f"Duplicate visit detected: {last_visit}")
            return None  # Skip saving if it's a duplicate visit

        #print(f"Creating new guest visit with details: IP Address: {ip_address}, Platform: {platform}, Browser: {browser}, Browser Version: {browser_version}, Timezone: {timezone or 'Unknown'}")

        return cls.objects.create(
            ip_address=ip_address,
            platform=platform,
            browser=browser,
            browser_version=browser_version,
            timezone=timezone or 'Unknown'
        )


