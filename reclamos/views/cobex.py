"""Cobranzas externas."""
from django.conf import settings
from django.contrib.auth.decorators import login_required
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import FileResponse
from reclamos.models import (Archivos, Fava, DebDirect)
from reclamos.forms import (FavaForm, DebForm)
from reclamos.admintools.arch_enviar_fava import arch_enviar_fava
from reclamos.admintools.arch_deb_direct import arch_enviar_bind
from reclamos.admintools.link_pf import link_pf


@login_required
def alta_fava(request):
    """Crea alta fava."""
    if request.method == "POST":
        fava_form = FavaForm(request.POST, request.FILES)
        if fava_form.is_valid():
            alta = fava_form.save(commit=False)
            user = request.user
            alta.author = user
            alta.editor = user
            alta.save()
            fava_form.save_m2m()
            grabar_fava(request, alta.n_de_alta)
            return redirect('detalle_fava', pk=alta.n_de_alta)
    else:
        fava_form = FavaForm()
    return render(request, 'fava/fava.html', {'fava_form': fava_form})


@login_required
def detalle_fava(request, pk):
    """Muestra detalle fava."""
    fava = get_object_or_404(Fava, pk=pk)
    return render(request, 'fava/detalle_fava.html', {'fava': fava})


@login_required
def grabar_fava(request, pk):  # noqa
    """Guarda alta de FAVA."""
    fava = get_object_or_404(Fava, pk=pk)
    fava.guardar()
    return redirect('detalle_fava', pk=pk)


@login_required
def eliminar_fava(request, pk):
    """Elimina alta fava."""
    fava = get_object_or_404(Fava, pk=pk)
    fava.eliminar()
    return redirect('alta_fava')


@login_required
def fava_files(request):
    """Renderiza página del generador de archivos FAVA."""
    if request.method == "POST" and request.FILES.get('filepath', False) is False:
        if ("archivo" not in request.FILES) or (str(request.POST['anio']) == '') \
                or (str(request.POST['mes']) == '') or (str(request.POST['dia']) == ''):
            return render(request, 'fava/archs_fava.html')
        try:
            anio = int(request.POST["anio"])
            mes = int(request.POST["mes"])
            dia = int(request.POST["dia"])
        except (TypeError, ValueError):
            return render(request, 'fava/archs_fava.html')
        archivo = request.FILES["archivo"]
        try:
            os.remove(settings.MEDIA_ROOT + r'/tmp/' + archivo.name)
        except FileNotFoundError:
            pass

        path = default_storage.save(r'tmp/' + archivo.name, ContentFile(archivo.read()))
        tmp_file = os.path.join(settings.MEDIA_ROOT, path)
        archivo = arch_enviar_fava(tmp_file, dia, mes, anio)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'fava/archs_fava.html')


@login_required
def alta_deb(request):
    """Crea alta debito directo."""
    if request.method == "POST":
        deb_form = DebForm(request.POST, request.FILES)
        if deb_form.is_valid():
            alta = deb_form.save(commit=False)
            user = request.user
            alta.author = user
            alta.editor = user
            alta.save()
            deb_form.save_m2m()
            grabar_deb(request, alta.n_de_alta)
            return redirect('detalle_debdirect', pk=alta.n_de_alta)
    else:
        deb_form = DebForm()
    return render(request, 'debito/deb.html', {'deb_form': deb_form})


@login_required
def detalle_deb(request, pk):
    """Muestra detalle debito directo."""
    debdirect = get_object_or_404(DebDirect, pk=pk)
    return render(request, 'debito/detalle_deb.html', {'debdirect': debdirect})


@login_required
def grabar_deb(request, pk):
    """Guarda alta de debito directo."""
    debdirect = get_object_or_404(DebDirect, pk=pk)
    debdirect.guardar()
    return redirect('detalle_debdirect', pk=pk)


@login_required
def eliminar_deb(request, pk):
    """Elimina alta debito directo."""
    debdirect = get_object_or_404(DebDirect, pk=pk)
    debdirect.eliminar()
    return redirect('lista_deb_direct')


@login_required
def deb_files(request):
    """Renderiza página del generador de archivos debito directo."""
    if request.method == "POST" and request.FILES.get('filepath', False) is False:
        if ("archivo" not in request.FILES) or (str(request.POST['anio']) == '') \
            or (str(request.POST['mes']) == '') or (str(request.POST['dia']) == '') \
                or (str(request.POST['fecha_vto']) == '') or (str(request.POST['id_cuota']) == ''):
            mensaje = 'Error - Revise los datos cargados.'
            return render(request, 'debito/archs_deb.html', {'mensaje': mensaje})
        try:
            anio = int(request.POST["anio"])
            mes = int(request.POST["mes"])
            dia = int(request.POST["dia"])
            fecha_vto = str(request.POST["fecha_vto"])
            id_cuota = str(request.POST["id_cuota"])
            int(fecha_vto)
        except (TypeError, ValueError):
            mensaje = 'Error - Revise los datos cargados.'
            return render(request, 'debito/archs_deb.html', {'mensaje': mensaje})
        if len(fecha_vto) != 8:
            mensaje = 'El campo "Fecha débito" no respeta el formato "DDMMAAAA".'
            return render(request, 'debito/archs_deb.html', {'mensaje': mensaje})
        if (len(id_cuota) != 11) or ('CUOT' not in id_cuota):
            mensaje = 'El campo "Cuota" no respeta el formato "CUOTAMMAAAA".'
            return render(request, 'debito/archs_deb.html', {'mensaje': mensaje})
        pre_archivo = request.FILES["archivo"]
        try:
            os.remove(settings.MEDIA_ROOT + r'/tmp/' + pre_archivo.name)
        except FileNotFoundError:
            pass

        path = default_storage.save(r'tmp/' + pre_archivo.name, ContentFile(pre_archivo.read()))
        tmp_file = os.path.join(settings.MEDIA_ROOT, path)
        archivo = arch_enviar_bind(tmp_file, dia, mes, anio, id_cuota, fecha_vto)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'debito/archs_deb.html', {'mensaje': ''})


@login_required
def lista_deb_direct(request):
    """Devuelve listado completo de debitos Bind activos."""
    listabind = DebDirect.objects.filter(eliminado='Activo')  # noqa
    return render(request, 'debito/lista_bind.html', {'listabind': listabind})


@login_required
def detalle_archivo_bind(request, pk):
    """Ver detalle de archivo ya cargado, desde aquí se puede eliminar."""
    # request.FILES
    archivo = get_object_or_404(Archivos, pk=pk)
    return render(request, 'reclamos/detalle_archivo.html', {'archivo': archivo})


@login_required
def genera_link_pf(request):
    """Genera link de pago para Pago Fácil."""
    if request.method == "POST":
        if (str(request.POST['barra']) == '') or (str(request.POST['valido']) == ''):
            return render(request, 'herramientas/link_pf.html')
        try:
            barra = int(request.POST["barra"])
            valido = int(request.POST["valido"])
        except (ValueError, TypeError):
            return render(request, 'herramientas/link_pf.html')
        link = link_pf(barra, valido)
        print(link)
        return render(request, 'herramientas/link_pf2.html',
                      {'link': link})
    return render(request, 'herramientas/link_pf.html')
