from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Sitemap for static views like login and register."""
    priority = 0.8
    changefreq = 'monthly' #'monthly'
    
    def items(self):
        # Include the static views like login, register, pricing, privacy policy, terms of service, contact us, and service list
        return ['home'] #['login', 'register', 'pricing', 'privacy_policy', 'terms_of_service', 'contact_us', 'service_list', 'about_us', 'password_reset_request']

    def location(self, item):
        # Return the full URL by reversing the item
        return reverse(item)
