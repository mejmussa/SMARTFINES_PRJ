from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponsePermanentRedirect, JsonResponse
from django.contrib import messages
from django.contrib.auth import logout
import time
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseRedirect
from urllib.parse import urlencode

    
   

class RedirectToWWW:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        # Redirect 127.0.0.1 to localhost
        #if host == '127.0.0.1:8000':
        #    return HttpResponsePermanentRedirect(f'http://localhost:8000{request.get_full_path()}')
        # Redirect naked domain to www
        #if host.startswith('tespos.xyz') and not host.startswith('www.'):
        #    return HttpResponsePermanentRedirect(f'https://www.tespos.dev{request.get_full_path()}')

        if host.startswith('smartfines.net') and not host.startswith('www.'):
            return HttpResponsePermanentRedirect(f'https://www.smartfines.net{request.get_full_path()}')
        
        return self.get_response(request)
    
    
