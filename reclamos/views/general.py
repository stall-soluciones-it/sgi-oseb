"""Views for SGI."""
from time import sleep
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from reclamos.management.commands.carga_reclamos_gsa import carga_reclamos_gsa
from django.contrib.auth import logout


@login_required
def home(request):
    """Página de inicio."""
    return render(request, 'inicio/home.html')


C_GSA = settings.CARGA_GSA
if C_GSA == 'SI':
    while True:
        carga_reclamos_gsa()
        sleep(3000)


@login_required
def custom_logout(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)
