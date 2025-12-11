"""Views for SGI."""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.conf import settings


@login_required
def home(request):
    """Página de inicio."""
    return render(request, 'inicio/home.html')


@login_required
def custom_logout(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)
