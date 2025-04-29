"""Proveedores."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from reclamos.models import (Proveedores)
from reclamos.forms import (ProveedoresForm)


@login_required
def nuevo_proveedor(request):
    """Crea nuevo proveedor."""
    if request.method == "POST":
        prov_form = ProveedoresForm(request.POST)
        if prov_form.is_valid():
            proveedor = prov_form.save(commit=False)
            user = request.user
            proveedor.author = user
            proveedor.editor = user
            proveedor.save()
            prov_form.save_m2m()
            grabar_proveedor(request, proveedor.id)
            return redirect('detalle_proveedor', pk=proveedor.id)
    else:
        prov_form = ProveedoresForm()
        return render(request, 'stock/nuevo_proveedor.html', {'prov_form': prov_form})


@login_required
def grabar_proveedor(request, pk):
    """Guarda nuevo proveedor."""
    proveedor = get_object_or_404(Proveedores, pk=pk)
    proveedor.guardar()
    return redirect('listado_proveedores')


@login_required
def eliminar_proveedor(request, pk):
    """Elimina proveedor."""
    proveedor = get_object_or_404(Proveedores, pk=pk)
    proveedor.eliminar()
    return redirect('listado_proveedores')


@login_required
def detalle_proveedor(request, pk):
    """Muestra detalle proveedor."""
    proveedor = get_object_or_404(Proveedores, pk=pk)
    return render(request, 'stock/detalle_proveedor.html', {'proveedor': proveedor})


@login_required
def editar_proveedor(request, pk):
    """Edita proveedor existente."""
    proveedor1 = get_object_or_404(Proveedores, pk=pk)
    if request.method == "POST":
        prov_form = ProveedoresForm(request.POST, instance=proveedor1)
        if prov_form.is_valid():
            proveedor = prov_form.save(commit=False)
            proveedor.editor = request.user
            proveedor.save()
            prov_form.save_m2m()
            return redirect('detalle_proveedor', pk=proveedor.pk)
    else:
        prov_form = ProveedoresForm(instance=proveedor1)
    return render(request, 'stock/editar_proveedor.html', {'prov_form': prov_form})


@login_required
def listado_proveedores(request):
    """Muestra lista de proveedores."""
    proveedores = (Proveedores.objects.filter(eliminado='Activo').order_by('razon'))
    return render(request, 'stock/proveedores.html', {'proveedores': proveedores})
