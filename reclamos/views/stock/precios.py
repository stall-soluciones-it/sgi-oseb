"""Proveedores."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from reclamos.models import (PrecioMateriales, Materiales)
from reclamos.forms import (PreciosForm)


@login_required
def nuevo_precio(request):
    """Carga nuevo precio."""
    if request.method == "POST":
        price_form = PreciosForm(request.POST)
        if price_form.is_valid():
            precio = price_form.save(commit=False)
            user = request.user
            precio.author = user
            precio.editor = user
            precio.save()
            price_form.save_m2m()
            grabar_precio(request, precio.id)
            return redirect('nuevo_precio')
    else:
        price_form = PreciosForm()
        return render(request, 'stock/nuevo_precio.html', {'price_form': price_form})


@login_required
def grabar_precio(request, pk):
    """Guarda nuevo precio."""
    precio = get_object_or_404(PrecioMateriales, pk=pk)
    precio.guardar()
    return redirect('nuevo_precio')


@login_required
def eliminar_precio(request, pk):
    """Elimina precio."""
    precio = get_object_or_404(PrecioMateriales, pk=pk)
    precio.eliminar()
    return redirect('listado_precios')


@login_required
def listado_precios(request, pk):
    """Muestra precios de material."""
    material = get_object_or_404(Materiales, pk=pk)
    precios = PrecioMateriales.objects.filter(material=pk, eliminado='Activo').order_by('-fecha')
    return render(request, 'stock/precios_mat.html', {'material': material, 'precios': precios})
