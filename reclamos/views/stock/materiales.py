"""Materiales."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Q
from reclamos.forms import (MaterialesForm)
from reclamos.models import (Materiales)


@login_required
def nuevo_material(request):
    """Crea nuevo material."""
    if request.method == "POST":
        mat_form = MaterialesForm(request.POST, request.FILES)
        if mat_form.is_valid():
            material = mat_form.save(commit=False)
            user = request.user
            material.author = user
            material.editor = user
            material.save()
            mat_form.save_m2m()
            grabar_material(request, material.id)
            return redirect('nuevo_material')  # ('detalle_material', pk=material.id)
    else:
        mat_form = MaterialesForm()
        return render(request, 'stock/nuevo_item.html', {'mat_form': mat_form})


@login_required
def editar_material(request, pk):
    """Edita material existente."""
    material1 = get_object_or_404(Materiales, pk=pk)
    if request.method == "POST":
        mat_form = MaterialesForm(request.POST, request.FILES, instance=material1)
        if mat_form.is_valid():
            material = mat_form.save(commit=False)
            material.editor = request.user
            material.save()
            mat_form.save_m2m()
            return redirect('detalle_material', pk=material.pk)
    else:
        mat_form = MaterialesForm(instance=material1)
    return render(request, 'stock/editar_material.html', {'mat_form': mat_form})


@login_required
def grabar_material(request, pk):
    """Guarda nuevo material."""
    material = get_object_or_404(Materiales, pk=pk)
    material.guardar()
    return redirect('listado_materiales')


@login_required
def eliminar_material(request, pk):
    """Elimina material."""
    material = get_object_or_404(Materiales, pk=pk)
    material.eliminar()
    return redirect('listado_materiales')


@login_required
def detalle_material(request, pk):
    """Muestra detalle material."""
    material = get_object_or_404(Materiales, pk=pk)
    return render(request, 'stock/detalle_material.html', {'material': material})


@login_required
def listado_materiales(request):
    """Muestra lista de materiales."""
    existencia = Sum("movimientomateriales__cantidad", filter=Q(movimientomateriales__eliminado='Activo'))
    materiales = Materiales.objects.filter(eliminado='Activo') \
        .annotate(existencia=existencia).order_by('descripcion')

    return render(request, 'stock/materiales.html', {'materiales': materiales})
