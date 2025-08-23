####### QUICK GIT MANAGEMENT COMMANDS #############
    git init

    
    git add .
    git commit -m "24 AUG 2025"
    git push origin main

    
    py manage.py runserver


    # If push from other source
    git pull origin main


    py manage.py makemigrations
    py manage.py migrate
    py manage.py runserver


    py manage.py makemigrations
    py manage.py migrate
    py manage.py createsuperuser
    

    py manage.py collectstatic

    # To remove new files that are already deployed use .gitignore first clear caches use command
    git rm --cached -r .
        then do same first step for deployment like i do when i remove .env file to handled by railway.app

########### AWS INSTALL CLI FOR DOWNLOAD WHOLE DIRECTORIES ###############
1. https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
run command
2. C:\Users\PC>aws s3 sync s3://tesmoc/static/ D:\TESMOC_PRJ\static

########### WGET MIRROR COMMAND #################
wget --mirror --convert-links --adjust-extension --page-requisites --no-parent -e robots=off https://www.yas.co.tz/devices/


######## DELETE & INSTALL REQUIREMENTS>TXT VIA PIP #############
    To Install in your terminal or virtual environment Terminal run the followings commands
1. pip install -r requirements.txt # for install all packages
2. pip uninstall -r requirements.txt -y # for uninstall all packages
3. pip show package_name # to see info of package if installed or not

################ IMAGE EDITOR ######################
1. removal.ai
2. https://www.remove.bg
3. https://snapedit.app
4. https://imageresizer.com/


####### MANAGE PSQL DB IN LOCALHOST IMPORTANT COMMANDS ############
    py manage.py makemigrations
    py manage.py migrate
    py manage.py runserver


    postgres=# CREATE DATABASE tespos_prj;
    #### for postgres 14 or even in there never use it postgres=# CREATE USER mussamej WITH PASSWORD 'mj5050mj';
    postgres=# GRANT ALL PRIVILEGES ON DATABASE tespos_prj TO postgres;
    
    
    List Tables: \l
    List Users:  \du
    Delete User: 


    postgres=# DROP DATABASE tespos_prj;

    ########## FOR PSQL 16 AND ABOVE USER WE CREATE LOCALLY NEEDS TO HAVE ADMIN PRIVILEGES TO CREATE TABLES ###########
    ALTER USER mussamej WITH SUPERUSER; or use postgres default user


    # Local PSQL DB in settings.py
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': config('DB_NAME_LOCAL'),
            'USER' : config('DB_USER_LOCAL'),
            'PASSWORD' : config('DB_PASSWORD_LOCAL'),
            'HOST' : config('DB_HOST_LOCAL'),
            'PORT' : config('DB_PORT_LOCAL', cast=int),
        }
    }

    OR 
    ############### CREATE CUSTOM SUPERUSER WITH ADMIN PRIVILEGES IN PSQL 17+ ##########
    1. CREATE ROLE mussamej WITH SUPERUSER CREATEDB CREATEROLE LOGIN PASSWORD 'mj5050mj';
    2. ALTER ROLE mussamej WITH REPLICATION;
    3. ALTER ROLE mussamej WITH BYPASSRLS;

     then use 
         \du
         to see if created successully


####### HOW TO SETUP DJANGO SUNDOMAINS LOCALLY AND IN PRODUCTIONS ######
1. Install package django-hosts in your project environment use command 

        pip install django-hosts

2. Add django-hosts to the INSTALLED_APPS
        
        INSTALLED_APPS = [
            # Other Installed Apps
            'django_hosts'
        ]

3. Add django-hosts middleware at beginning of middleware and at the end like below
        
        MIDDLEWARE = [
            'django_hosts.middleware.HostsRequestMiddleware',
             # Other middlewares
            'django_hosts.middleware.HostsResponseMiddleware',       
        ]

4. Add these code in any place in settings.py mostly below middleware section.
        
        ROOT_HOSTCONF = 'tesmoc_prj.hosts'
        DEFAULT_HOST = 'www'

        # Determine the environment based on DEBUG
        if DEBUG == True:  # Explicitly checking if DEBUG is True
            ENVIRONMENT = "development"  # Development mode
            PARENT_HOST = "localhost:8000"
        else:  # DEBUG == False
            ENVIRONMENT = "production"  # Production mode
            PARENT_HOST = "tesmoc.com"

5. Create hosts.py file in main project directory where we find main urls.py, settings.py, wsgi.py, asgi.py files
   and add these code into it 

        from django_hosts import patterns, host

        host_patterns = patterns(
            '',
            host(r'www', 'tesmoc_prj.urls', name='www'),
            host(r'chater', 'chater.urls', name='chater'),
            host(r'tesbook', 'tes_book.urls', name='tes_book'),
            host(r'tesmart', 'tes_mart.urls', name='tes_mart'),
            host(r'spectra', 'spectra.urls', name='spectra'),
            host(r'tesads', 'tes_ads.urls', name='tes_ads'),
            host(r'tesdesk', 'tes_desk.urls', name='tes_desk'),
        )

6. Create file middleware.py in main django project directory where we find main urls.py, settings.py, wsgi.py, asgi.py files
   and add these code 
        
        from django.conf import settings
        from django.shortcuts import redirect
        from django.http import HttpResponsePermanentRedirect

        # Mapping subdomains from hosts.py
        SUBDOMAIN_MAP = {
            "chater": "chater",
            "tesbook": "tesbook",
            "tesmart": "tesmart",
            "spectra": "spectra",
            "tesads": "tesads",
            "tesdesk": "tesdesk",
        }

        class SubdomainRedirectMiddleware:
            """Middleware to redirect paths to their correct subdomains."""
            
            def __init__(self, get_response):
                self.get_response = get_response

            def __call__(self, request):
                host = request.get_host().split(":")[0]  # Extract hostname without port

                # Extract first path component
                path_parts = request.path.strip("/").split("/")
                if path_parts:
                    first_path = path_parts[0]
                else:
                    first_path = ""

                # Check if first part of the path is a known subdomain key
                if first_path in SUBDOMAIN_MAP and not host.startswith(SUBDOMAIN_MAP[first_path]):
                    # Determine the correct domain
                    subdomain = SUBDOMAIN_MAP[first_path]
                    parent_domain = settings.PARENT_HOST  # Use `localhost:8000` in development
                    new_url = f"https://{subdomain}.{parent_domain}/{ '/'.join(path_parts[1:]) }"

                    return HttpResponsePermanentRedirect(new_url)

                return self.get_response(request)

        class RedirectToWWW:
            def __init__(self, get_response):
                self.get_response = get_response

            def __call__(self, request):
                host = request.get_host()
                # Redirect 127.0.0.1 to localhost
                if host == '127.0.0.1:8000':
                    return HttpResponsePermanentRedirect(f'http://localhost:8000{request.get_full_path()}')
                # Redirect naked domain to www
                if host.startswith('tesmoc.com') and not host.startswith('www.'):
                    return HttpResponsePermanentRedirect(f'https://www.tesmoc.com{request.get_full_path()}')
                return self.get_response(request)

7. Add in middleware section in settings.py file these code and save
        MIDDLEWARE = [
            'django_hosts.middleware.HostsRequestMiddleware',
            # Other default middleware
            # Custom middleware
            'tesmoc_prj.middleware.RedirectToWWW',    
            'tesmoc_prj.middleware.SubdomainRedirectMiddleware',
            'django_hosts.middleware.HostsResponseMiddleware',       
        ]


8. Visit path C:\Windows\System32\drivers\etc\hosts and open a file in VSCode

9. Add these code 

        127.0.0.1 localhost
        255.255.255.255 broadcasthost
        ::1 localhost

        127.0.0.1 tesbook.tesmoc_prj.local
        127.0.0.1 spectra.tesmoc_prj.local
        127.0.0.1 chater.tesmoc_prj.local
        127.0.0.1 tesmart.tesmoc_prj.local
        127.0.0.1 tesads.tesmoc_prj.local
        127.0.0.1 tesdesk.tesmoc_prj.local
        127.0.0.1 tespay.tesmoc_prj.local
        127.0.0.1 voucha.tesmoc_prj.local
        127.0.0.1 tesposter.tesmoc_prj.local

        Then save file as admin as it admin privileges to saved then in allowed host in django
    add DJANGO_ALLOWED_HOSTS=['127.0.0.1', '.localhost', '.tesmoc.com', 'tesmoc.com', 'localhost']

10. Lastly clean DNS use this code on cmd

        ipconfig /flushdns
    
    After clean dns refresh page and visit your site

11. In Production run code with DEBUG = False to use actual domain redirects separate from localhost in your
    .env file




#################### HOW TO SETUP THE ACTUAL DOMAIN ON WINDOWS FOR DEVELOPMENT LIKE www.tesmoc.xyz ########################
Ensure the domain you use is not used by another site as this will lead to be redircted in that site instead of your local development project ot buy it then
1. Go to C:\Windows\System32\drivers\etc  
    and open file hosts and add the code match your django allowd url or your local dns
     
    127.0.0.1 localhost
    255.255.255.255 broadcasthost
    ::1             localhost

    127.0.0.1 www.tesmoc.xyz
    127.0.0.1 accounts.tesmoc.xyz
    127.0.0.1 chater.tesmoc.xyz
    127.0.0.1 tesbook.tesmoc.xyz
    127.0.0.1 tesmart.tesmoc.xyz
    127.0.0.1 spectra.tesmoc.xyz
    127.0.0.1 tesads.tesmoc.xyz
    127.0.0.1 tesdesk.tesmoc.xyz
    127.0.0.1 tespay.tesmoc.xyz
    127.0.0.1 tesposter.tesmoc.xyz
    127.0.0.1 voucha.tesmoc.xyz
    127.0.0.1 tesnest.tesmoc.xyz

2. Then search for another cmd and run it as administrator then pass this command 
        netsh interface portproxy add v4tov4 listenport=80 listenaddress=127.0.0.1 connectport=8000 connectaddress=127.0.0.1

3. Run command to flush cached local DNS on your project cmd
       ipconfig /flushdns
       

4. then go to your django project run django runserver use this command
        python manage.py runserver 127.0.0.1:8000

5. Then visit your pages on browser like 
       http://www.tesmoc.xyz/


############ ADD HTTPS TO THE DOMAIN ON LOCALHOST LIKE RAILWAY DOES ##################
1. Download ngix stable version at https://nginx.org/en/download.html 
2. Extract zip file take it go to C:\ directory past it
3. cd into the nginx directry via cmd 
4. create directory ngnix where nginx.exe found call it ssl
5. cd into ssl directory in cmd
6. run command as adminstrator in separate terminal
    1. winget install mkcert  # Install mkcert on your Windows machine using Chocolatey or winget. in our case we use winget if its not search and install it manually
    2. mkcert -install        # This will create a local CA and install it into your system trust store.
Run this on nginx ssl folder to install the certificates in there
    3.  mkcert tesmoc.xyz www.tesmoc.xyz accounts.tesmoc.xyz tesbook.tesmoc.xyz chater.tesmoc.xyz tesmart.tesmoc.xyz spectra.tesmoc.xyz tesads.tesmoc.xyz tespay.tesmoc.xyz admin.tesmoc.xyz    # To install ssl certificates for your subdomains or domains

7. modify default ngnix.conf file delte everything its has and replace it with this 

  
# user nobody;
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  65;

    # Global limit
    client_max_body_size 2048M;

    server {
        listen 80;
        server_name tesmoc.xyz www.tesmoc.xyz accounts.tesmoc.xyz tesbook.tesmoc.xyz chater.tesmoc.xyz tesmart.tesmoc.xyz spectra.tesmoc.xyz tesads.tesmoc.xyz tespay.tesmoc.xyz;

        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        server_name tesmoc.xyz www.tesmoc.xyz accounts.tesmoc.xyz tesbook.tesmoc.xyz chater.tesmoc.xyz tesmart.tesmoc.xyz spectra.tesmoc.xyz tesads.tesmoc.xyz tespay.tesmoc.xyz;

        ssl_certificate      C:/nginx/ssl/tesmoc.xyz+8.pem;
        ssl_certificate_key  C:/nginx/ssl/tesmoc.xyz+8-key.pem;

        ssl_protocols        TLSv1.2 TLSv1.3;
        ssl_ciphers          HIGH:!aNULL:!MD5;

        # Reinforce limit inside the server block
        client_max_body_size 2048M;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Reinforce again just in case
            client_max_body_size 2048M;
        }
    }
}



8. Run command in another cmd to start it
      nginx.exe 

9. Remember to set django CORS allowed origin for all subdomains and CSRF allowed origins for all subdomains so you can navigate well in the platform.

NB; Before run ngix dont forget to run django on port 80 use command 
    netsh interface portproxy add v4tov4 listenport=80 listenaddress=127.0.0.1 connectport=8000 connectaddress=127.0.0.1
to allow domains run as if its in production but locally mean other people who are not in my machine they wont be able to access it 

10. To allow my site be shared on router or LAN just add in hosts file and nginx.conf file as follows
     
    127.0.0.1 localhost
    255.255.255.255 broadcasthost
    ::1             localhost

    192.168.0.80 tesmoc.xyz
    192.168.0.80 www.tesmoc.xyz
    192.168.0.80 accounts.tesmoc.xyz
    
    And update nginx file when you see
    
    proxy_pass http://127.0.0.1:8000; to proxy_pass http://192.168.0.80:8000; 
        

11. To go on world mean my computer is server itself we need to do this 
       
    1. Port Forwarding on Router
            Go to your router settings and:

            External Port	Internal IP (your PC)	Internal Port	Protocol
                80	         your PC's local IP	         80	         TCP
                443	         your PC's local IP	         443	     TCP

            Example:Forward port 443 to your computer (e.g., 192.168.0.105) if your PC is running Nginx.
        
    2. Use a Static Public IP (or Dynamic DNS)
            Static IP: Get it from your ISP so your IP won’t change.

            OR use Dynamic DNS (like No-IP or DuckDNS) to update your IP when it changes.

    3. Update DNS A Record
            Log in to your domain registrar (e.g., Namecheap, GoDaddy, etc.), and update the A record of your domain:

            Type	   Name	      Value
            A	        @	       your public IP
            A	        www	       your public IP
            This tells the world to point tesmoc.xyz to your public IP address (your home network).
        
    4. Ensure Firewall Allows Traffic
            Open ports 80 and 443 in your Windows Firewall:

            # Open Command Prompt as Admin
            netsh advfirewall firewall add rule name="Nginx HTTP" protocol=TCP dir=in localport=80 action=allow
            netsh advfirewall firewall add rule name="Nginx HTTPS" protocol=TCP dir=in localport=443 action=allow

    5. Run Nginx as Administrator
            Make sure Nginx is running as Admin, otherwise it can’t bind to ports 80/443.

    6. Start Django Server
            python manage.py runserver 127.0.0.1:8000

    7. Optional But Recommended
            Set up Gunicorn or Daphne behind Nginx instead of Django’s built-in server for better performance.

            Use HTTPS certificates from Let's Encrypt (you can use Win-ACME on Windows). Coz certs not work on internet its only for LAN and not acceptable for all browser

            Use a UPS/power backup if your machine will serve as a 24/7 server.


############# Quick Fix of ENV FILE ####################
# COOKIES 
CSRF_USE_SESSIONS=False
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
CSRF_COOKIE_HTTPONLY=False
SESSION_COOKIE_AGE=1209600
SECURE_CONTENT_TYPE_NOSNIFF=True


Mean Update 
CSRF_USE_SESSIONS=False
CSRF_COOKIE_HTTPONLY=False


https://mlocati.github.io/articles/gettext-iconv-windows.html


https://zeptomail.zoho.com/