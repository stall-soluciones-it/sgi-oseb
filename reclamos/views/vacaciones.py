import json
from datetime import date
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, IntegerField
from reclamos.models import (Empleado, Novedades_vacaciones)
from reclamos.forms import (NovedadesForm, EmpleadoVacacionesForm)
from django.shortcuts import render, get_object_or_404, redirect
from reclamos.admintools.vacaciones import calculo_dias


@login_required
def vacaciones(request):
    """Muestra lista personal-vacaciones."""
    # Traigo listado de empleados desde django y creo dic con total de dias de
    # vacaciones pendientes = {n_legajo: {año: dias}, ...}
    empleados = Empleado.objects.filter(eliminado='Activo')  # noqa
    pendientes = {}
    for empleado in empleados:
        pendientes[empleado.n_legajo] = calculo_dias(empleado.fecha_ingreso, date.today(), empleado.fecha_egreso)
    # Traigo listado de novedades y creo dic tomados {n_legajo: {año: dias}, ...}
    novedades = Novedades_vacaciones.objects.filter(eliminado='Activo')  # noqa
    tomados = {}
    for novedad in novedades:
        if novedad.empleado.n_legajo not in tomados.keys():
            tomados[novedad.empleado.n_legajo] = {novedad.periodo: novedad.dias}
        else:
            if novedad.periodo not in tomados[novedad.empleado.n_legajo]:
                tomados[novedad.empleado.n_legajo][novedad.periodo] = novedad.dias
            else:
                dias = tomados[novedad.empleado.n_legajo][novedad.periodo] + novedad.dias
                tomados[novedad.empleado.n_legajo][novedad.periodo] = dias
    # Completo tomados{} con ceros en años donde no hay novedades, para poder hacer siguiente calculo.
    for key, value in pendientes.items():
        if key not in tomados.keys():
            tomados[key] = {}
            for kei, val in value.items():
                if kei not in tomados[key].keys():
                    tomados[key][kei] = 0
        else:
            for kei, val in value.items():
                if kei not in tomados[key].keys():
                    tomados[key][kei] = 0
    # Con {pendientes} y {tomados} creo restan = {n_legajo: {anio: dias}, ...}
    restan = {}
    for key in pendientes.keys():
        restan[key] = {k: pendientes[key].get(k, 0) - float(tomados[key].get(k, 0)) for k in
                       set(pendientes[key]) | set(tomados[key])}
    for key, value in restan.items():
        restan[key] = dict(sorted(value.items()))
    restan_total = {}
    for key, value in restan.items():
        restan_total[key] = sum(value.values())
    # Agrego "columna" a query de django "empleados" con los dias totales de vacaciones restantes.
    whens = [When(n_legajo=k, then=Value(v)) for k, v in restan_total.items()]
    empleados = empleados.annotate(restan=Case(*whens, output_field=IntegerField(), default=Value(0)))
    return render(request, 'rrhh/vacaciones.html', {'empleados': empleados, 'restan_total': restan_total})


@login_required
def detalle_empleado(request, pk):
    # Traigo listado de empleados desde django y creo dic con total de dias
    # de vacaciones pendientes = {n_legajo: {año: dias}, ...}
    operario = get_object_or_404(Empleado, pk=pk)
    empleados = Empleado.objects.filter(n_de_alta=pk, eliminado='Activo')  # noqa
    pendientes = {}
    for empleado in empleados:
        pendientes[empleado.n_legajo] = calculo_dias(empleado.fecha_ingreso, date.today(), empleado.fecha_egreso)
    # Traigo listado de novedades y creo dic tomados {n_legajo: {año: dias}, ...}
    novedades = Novedades_vacaciones.objects.filter(empleado=pk, eliminado='Activo')  # noqa
    tomados = {}
    for novedad in novedades:
        if novedad.empleado.n_legajo not in tomados.keys():
            tomados[novedad.empleado.n_legajo] = {novedad.periodo: novedad.dias}
        else:
            if novedad.periodo not in tomados[novedad.empleado.n_legajo]:
                tomados[novedad.empleado.n_legajo][novedad.periodo] = novedad.dias
            else:
                dias = tomados[novedad.empleado.n_legajo][novedad.periodo] + novedad.dias
                tomados[novedad.empleado.n_legajo][novedad.periodo] = dias
    # Completo tomados{} con ceros en años donde no hay novedades, para poder hacer siguiente calculo.
    for key, value in pendientes.items():
        if key not in tomados.keys():
            tomados[key] = {}
            for kei, val in value.items():
                if kei not in tomados[key].keys():
                    tomados[key][kei] = 0
        else:
            for kei, val in value.items():
                if kei not in tomados[key].keys():
                    tomados[key][kei] = 0
    # Creo dic detalle {anio: dias, ....}
    detalle = {}
    for key, value in pendientes[empleado.n_legajo].items():  # noqa
        detalle[key] = [pendientes[empleado.n_legajo][key],
                        tomados[empleado.n_legajo][key],
                        pendientes[empleado.n_legajo][key] - float(tomados[empleado.n_legajo][key])]
    total_pend = 0
    for value in detalle.values():
        total_pend += value[2]

    return render(request, 'rrhh/detalle_empleado.html', {'operario': operario, 'detalle': detalle,
                                                          'total_pend': total_pend, 'novedades': novedades})


@login_required
def carga_novedad(request, pk):
    # Traigo listado de empleados desde django y creo dic con total de dias de vacaciones
    # pendientes = {n_legajo: {año: dias}, ...}
    operario = get_object_or_404(Empleado, pk=pk)
    empleados = Empleado.objects.filter(n_de_alta=pk, eliminado='Activo')  # noqa
    pendientes = {}
    for empleado in empleados:
        pendientes[empleado.n_legajo] = calculo_dias(empleado.fecha_ingreso, date.today(), empleado.fecha_egreso)
    # Traigo listado de novedades y creo dic tomados {n_legajo: {año: dias}, ...}
    novedades = Novedades_vacaciones.objects.filter(empleado=pk, eliminado='Activo')  # noqa
    tomados = {}
    for novedad in novedades:
        if novedad.empleado.n_legajo not in tomados.keys():
            tomados[novedad.empleado.n_legajo] = {novedad.periodo: novedad.dias}
        else:
            if novedad.periodo not in tomados[novedad.empleado.n_legajo]:
                tomados[novedad.empleado.n_legajo][novedad.periodo] = novedad.dias
            else:
                dias = tomados[novedad.empleado.n_legajo][novedad.periodo] + novedad.dias
                tomados[novedad.empleado.n_legajo][novedad.periodo] = dias
    # Completo tomados{} con ceros en años donde no hay novedades, para poder hacer siguiente calculo.
    for key, value in pendientes.items():
        if key not in tomados.keys():
            tomados[key] = {}
            for kei, val in value.items():
                if kei not in tomados[key].keys():
                    tomados[key][kei] = 0
        else:
            for kei, val in value.items():
                if kei not in tomados[key].keys():
                    tomados[key][kei] = 0
    # Creo dic detalle {anio: dias, ....}
    detalle = {}
    for key, value in pendientes[empleado.n_legajo].items():  # noqa
        detalle[key] = float(pendientes[empleado.n_legajo][key] - tomados[empleado.n_legajo][key])
    context = json.dumps(detalle)

    if request.method == "POST":
        vac_form = NovedadesForm(request.POST)
        if vac_form.is_valid():
            novedad = vac_form.save(commit=False)
            user = request.user
            novedad.author = user
            novedad.editor = user
            novedad.empleado = operario
            novedad.save()
            vac_form.save_m2m()
            grabar_novedad(request, novedad.pk)
            return redirect('detalle_empleado', pk=operario.pk)
    else:
        vac_form = NovedadesForm()
        return render(request, 'rrhh/novedad.html',
                      {'operario': operario, 'vac_form': vac_form, 'detalle': context})
    return render(request, 'rrhh/novedad.html', {'operario': operario, 'vac_form': vac_form, 'detalle': detalle})


@login_required
def grabar_novedad(request, pk):  # noqa
    """Guarda nueva novedad."""
    novedad = get_object_or_404(Novedades_vacaciones, pk=pk)
    novedad.guardar()
    return redirect('vacaciones')


@login_required
def editar_novedad(request, pk):
    """Edita novedad existente."""
    novedad = get_object_or_404(Novedades_vacaciones, pk=pk)
    if request.method == "POST":
        novedad_form = NovedadesForm(request.POST, instance=novedad)
        if novedad_form.is_valid():
            novedad = novedad_form.save(commit=False)
            novedad.editor = request.user
            novedad.save()
            novedad_form.save_m2m()
            return redirect('detalle_empleado', pk=novedad.empleado.pk)
    else:
        novedad_form = NovedadesForm(instance=novedad)
    return render(request, 'rrhh/editar_novedad.html', {'novedad_form': novedad_form})


@login_required
def alta_empleado(request):
    """Crea nuevo empleado."""
    if request.method == "POST":
        emp_form = EmpleadoVacacionesForm(request.POST, request.FILES)
        if emp_form.is_valid():
            alta = emp_form.save(commit=False)
            user = request.user
            alta.author = user
            alta.editor = user
            alta.save()
            emp_form.save_m2m()
            grabar_empleado(request, alta.n_de_alta)
            return redirect('vacaciones')
    else:
        emp_form = EmpleadoVacacionesForm()
    return render(request, 'rrhh/nuevo_empleado.html', {'emp_form': emp_form})


@login_required
def editar_empleado(request, pk):
    """Edita empleado existente."""
    empleado = get_object_or_404(Empleado, pk=pk)
    if request.method == "POST":
        emp_form = EmpleadoVacacionesForm(request.POST, request.FILES, instance=empleado)
        if emp_form.is_valid():
            empleado = emp_form.save(commit=False)
            empleado.editor = request.user
            empleado.save()
            emp_form.save_m2m()
            return redirect('vacaciones')
    else:
        emp_form = EmpleadoVacacionesForm(instance=empleado)
    return render(request, 'rrhh/editar_empleado.html', {'emp_form': emp_form})


@login_required
def grabar_empleado(request, pk):
    """Guarda alta empleado."""
    fava = get_object_or_404(Empleado, pk=pk)
    fava.guardar()
    return redirect('vacaciones')
