"""Reclamos."""
from django.contrib.auth.decorators import login_required
import os
import datetime
import copy
import base64
from io import BytesIO
from itertools import chain
import pymysql
import pandas as pd  # noqa
import matplotlib  # noqa
import matplotlib.pyplot as plt  # noqa
from PIL import Image as ImagePIL, ImageDraw  # noqa
from PyPDF2 import PdfReader, PdfWriter, PdfMerger  # noqa
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import FileResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
import django_filters  # noqa
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, Image  # noqa
from reportlab.lib import colors  # noqa
from reportlab.lib.pagesizes import A4, landscape  # noqa
from reportlab.lib.styles import ParagraphStyle  # noqa
from reportlab.lib.units import mm  # noqa
from reportlab.lib.enums import TA_CENTER  # noqa
from reportlab.pdfgen import canvas  # noqa
import sgi.shpd_cnf as cnf
from reclamos.models import (Reclamo, Tipos, Archivos, DatosCuadrilla, FiltroInformePendFin,
                             FiltroInformeTiemResol, CacheUnidadSISA)
from reclamos.forms import (ReclamoForm, ArchivoForm, CuadrillaAgua, CuadrillaCloaca, CuadrillaNivPozos,
                            CuadrillaMcoTapa, CuadrillaMantCloacal, CuadrillaVerifFact, CuadrillaServMed,
                            FiltroInformePendFinForm, FiltroInformeTiemResolForm)
matplotlib.use('Agg')


class YearFilter(django_filters.ChoiceFilter):
    def __init__(self, *args, **kwargs):
        super(YearFilter, self).__init__(*args, **kwargs)
        years = [year for year in range(timezone.now().year, timezone.now().year - 10, -1)]  # Adjust range as needed
        self.extra['choices'] = [(str(year), str(year)) for year in years]


class ReclamoFilter(django_filters.FilterSet):
    fecha = YearFilter(method='filter_by_year', label='Año')
    tipo_de_reclamo = django_filters.ModelChoiceFilter(
        queryset=Tipos.objects.all(),  # noqa
        empty_label="----------"
    )

    class Meta:
        model = Reclamo
        fields = ['fecha', 'tipo_de_reclamo']

    def filter_by_year(self, queryset, name, value):  # noqa
        return queryset.filter(fecha__year=value)


# <TRABAJOS>
@login_required
def lista_reclamos(request):
    """Devuelve listado completo de reclamos."""
    title = 'Trabajos - Completo'
    user = str(request.user)
    if 'gsa-' in user:
        try:
            reclamos = (Reclamo.objects.filter(borrador='No', eliminado='Activo',  # noqa
                                               author__username__startswith='gsa-').order_by('-n_de_reclamo'))
        except ValueError:
            reclamos = (Reclamo.objects.filter(borrador='No', eliminado='Activo',  # noqa
                                               author__username__startswith='gsa-').order_by('-n_de_reclamo'))
    else:
        try:
            reclamos = (Reclamo.objects.filter(borrador='No', eliminado='Activo').order_by('-n_de_reclamo'))  # noqa
        except ValueError:
            reclamos = (Reclamo.objects.filter(borrador='No', eliminado='Activo').order_by('-n_de_reclamo'))  # noqa

    reclamo_filter = ReclamoFilter(request.GET, queryset=reclamos)
    filtered_reclamos = reclamo_filter.qs

    paginator = Paginator(filtered_reclamos, 100)  # Show 100 items per page
    page = request.GET.get('page')

    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        items = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        items = paginator.page(paginator.num_pages)

    return render(request, 'reclamos/lista_reclamos.html',
                  {'reclamos': reclamos, 'titulo': 'Trabajos:',
                   'title': title, 'items': items, 'filter': reclamo_filter})


@login_required
def lista_reclamos_borradores(request):
    """Muestra lista de borradores."""
    title = 'Borradores - Trabajos'
    try:
        reclamos = (Reclamo.objects.filter(borrador='Si', eliminado='Activo').order_by('n_de_reclamo'))  # noqa
    except ValueError:
        reclamos = (Reclamo.objects.filter(borrador='Si', eliminado='Activo').order_by('n_de_reclamo'))  # noqa

    reclamo_filter = ReclamoFilter(request.GET, queryset=reclamos)
    filtered_reclamos = reclamo_filter.qs

    paginator = Paginator(filtered_reclamos, 100)  # Show 100 items per page
    page = request.GET.get('page')

    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        items = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        items = paginator.page(paginator.num_pages)

    return render(request, 'reclamos/lista_reclamos.html',
                  {'reclamos': reclamos, 'titulo': 'Borradores:',
                   'title': title, 'items': items, 'filter': reclamo_filter})


@login_required
def lista_reclamos_pendientes(request):
    """Muestra listado de reclamos pendientes."""
    title = 'Pendientes - Trabajos'
    user = str(request.user)
    if 'gsa-' in user:
        try:
            reclamos = (Reclamo.objects.filter(borrador='No',  # noqa
                                               estado__estado__in=['Pendiente', 'Deuda Vigente'],
                                               eliminado='Activo',
                                               author__username__startswith='gsa-').order_by('-n_de_reclamo'))
        except ValueError:
            reclamos = (Reclamo.objects.filter(borrador='No',  # noqa
                                               estado__estado__in=['Pendiente', 'Deuda Vigente'],
                                               eliminado='Activo', author__username__startswith='gsa-')
                        .order_by('-n_de_reclamo'))
    else:
        try:
            reclamos = (Reclamo.objects.filter(borrador='No',  # noqa
                                               estado__estado__in=['Pendiente', 'Deuda Vigente'],
                                               eliminado='Activo').order_by('-n_de_reclamo'))
        except ValueError:
            reclamos = (Reclamo.objects.filter(borrador='No',  # noqa
                                               estado__estado__in=['Pendiente', 'Deuda Vigente'],
                                               eliminado='Activo').order_by('-n_de_reclamo'))

    reclamo_filter = ReclamoFilter(request.GET, queryset=reclamos)
    filtered_reclamos = reclamo_filter.qs

    paginator = Paginator(filtered_reclamos, 100)  # Show 100 items per page
    page = request.GET.get('page')

    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        items = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        items = paginator.page(paginator.num_pages)

    return render(request, 'reclamos/lista_reclamos.html',
                  {'reclamos': reclamos, 'titulo': 'Trabajos pendientes:',
                   'title': title, 'items': items, 'filter': reclamo_filter})


@login_required
def lista_reclamos_finalizados(request):
    """Muestra listado de reclamos finalizados."""
    title = 'Finalizados - Trabajos'
    user = str(request.user)
    if 'gsa-' in user:
        try:
            reclamos = (Reclamo.objects.filter(borrador='No', estado__estado='Finalizado',  # noqa
                                               eliminado='Activo',
                                               author__username__startswith='gsa-').order_by('-n_de_reclamo'))
        except ValueError:
            reclamos = (Reclamo.objects.filter(borrador='No', estado__estado='Finalizado',  # noqa
                                               eliminado='Activo', author__username__startswith='gsa-')
                        .order_by('-n_de_reclamo'))
    else:
        try:
            reclamos = (Reclamo.objects.filter(borrador='No', estado__estado='Finalizado',  # noqa
                                               eliminado='Activo').order_by('-n_de_reclamo'))
        except ValueError:
            reclamos = (Reclamo.objects.filter(borrador='No', estado__estado='Finalizado',  # noqa
                                               eliminado='Activo')
                        .order_by('-n_de_reclamo'))

    reclamo_filter = ReclamoFilter(request.GET, queryset=reclamos)
    filtered_reclamos = reclamo_filter.qs

    paginator = Paginator(filtered_reclamos, 100)  # Show 100 items per page
    page = request.GET.get('page')

    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        items = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        items = paginator.page(paginator.num_pages)

    return render(request, 'reclamos/lista_reclamos.html',
                  {'reclamos': reclamos, 'titulo': 'Trabajos finalizados:',
                   'title': title, 'items': items, 'filter': reclamo_filter})


@login_required
def lista_reclamos_seguimiento(request):
    """Muestra listado de reclamos seguimiento."""
    title = 'Seguimiento - Trabajos'
    user = str(request.user)
    if 'gsa-' in user:
        try:
            reclamos = (Reclamo.objects.filter(borrador='No', estado__estado='Seguimiento / Finalizado',  # noqa
                                               eliminado='Activo',
                                               author__username__startswith='gsa-').order_by('-n_de_reclamo'))
        except ValueError:
            reclamos = (Reclamo.objects.filter(borrador='No', estado__estado='Seguimiento / Finalizado',  # noqa
                                               eliminado='Activo', author__username__startswith='gsa-')
                        .order_by('-n_de_reclamo'))
    else:
        try:
            reclamos = (Reclamo.objects.filter(borrador='No', estado__estado='Seguimiento / Finalizado',  # noqa
                                               eliminado='Activo').order_by('-n_de_reclamo'))
        except ValueError:
            reclamos = (Reclamo.objects.filter(borrador='No', estado__estado='Seguimiento / Finalizado',  # noqa
                                               eliminado='Activo')
                        .order_by('-n_de_reclamo'))

    reclamo_filter = ReclamoFilter(request.GET, queryset=reclamos)
    filtered_reclamos = reclamo_filter.qs

    paginator = Paginator(filtered_reclamos, 100)  # Show 100 items per page
    page = request.GET.get('page')

    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        items = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        items = paginator.page(paginator.num_pages)

    return render(request, 'reclamos/lista_reclamos.html',
                  {'reclamos': reclamos, 'titulo': 'Trabajos p/ seguimiento:',
                   'title': title, 'items': items, 'filter': reclamo_filter})


@login_required
def lista_reclamos_deuda(request):
    """Muestra listado de reclamos deuda."""
    title = 'Deuda'

    try:
        filtro_estado = (Reclamo.objects.filter(estado__estado__in=['Finalizado / Deuda',  # noqa
                                                                    'Deuda Vigente'],
                                                eliminado='Activo')
                         .order_by('n_de_reclamo'))
    except ValueError:
        filtro_estado = (Reclamo.objects.filter(estado__estado__in=['Finalizado / Deuda',  # noqa
                                                                    'Deuda Vigente'],
                                                eliminado='Activo')
                         .order_by('n_de_reclamo'))

    try:
        filtro_tipo = (Reclamo.objects.filter(eliminado='Activo',  # noqa
                                              tipo_de_reclamo__tipo='Consulta Deuda',
                                              estado__estado='Pendiente')
                       .order_by('n_de_reclamo'))
    except ValueError:
        filtro_tipo = (Reclamo.objects.filter(eliminado='Activo',  # noqa
                                              tipo_de_reclamo__tipo='Consulta Deuda',
                                              estado__estado='Pendiente')
                       .order_by('n_de_reclamo'))

    rec_deuda = sorted(chain(filtro_estado, filtro_tipo),
                       key=lambda instance: instance.n_de_reclamo)

    return render(request, 'reclamos/lista_reclamos.html',
                  {'reclamos': rec_deuda, 'titulo': 'Deuda:',
                   'title': title})


@login_required
def nuevo_reclamo(request):
    """Crea nuevo reclamo."""
    if request.method == "POST":
        rec_form = ReclamoForm(request.POST, request.FILES)
        if rec_form.is_valid():
            reclamo = rec_form.save(commit=False)
            user = request.user
            reclamo.author = user
            reclamo.editor = user
            reclamo.save()
            rec_form.save_m2m()
            if user.groups.filter(name='Cajeros').exists() is True:
                grabar_reclamo(request, reclamo.n_de_reclamo)
            return redirect('detalle_reclamo', pk=reclamo.n_de_reclamo)
    else:
        rec_form = ReclamoForm()
    return render(request, 'reclamos/nuevo_reclamo.html', {'rec_form': rec_form})


@login_required
def nuevo_reclamo_r(request):
    """Crea nuevo reclamo."""
    if request.method == "POST":
        rec_form = ReclamoForm(request.POST, request.FILES)
        if rec_form.is_valid():
            reclamo = rec_form.save(commit=False)
            user = request.user
            reclamo.author = user
            reclamo.editor = user
            reclamo.save()
            rec_form.save_m2m()
            if user.groups.filter(name='Cajeros').exists() is True:
                grabar_reclamo(request, reclamo.n_de_reclamo)
            return redirect('detalle_reclamo', pk=reclamo.n_de_reclamo)
    else:
        rec_form = ReclamoForm()
    return render(request, 'reclamos/nuevo_reclamo_r.html', {'rec_form': rec_form})


@login_required
def editar_reclamo(request, pk):
    """Edita reclamo existente."""
    reclamo = get_object_or_404(Reclamo, pk=pk)
    if request.method == "POST":
        rec_form = ReclamoForm(request.POST, request.FILES, instance=reclamo)
        if rec_form.is_valid():
            reclamo = rec_form.save(commit=False)
            reclamo.editor = request.user
            reclamo.save()
            rec_form.save_m2m()
            return redirect('detalle_reclamo', pk=reclamo.pk)
    else:
        rec_form = ReclamoForm(instance=reclamo)
    return render(request, 'reclamos/editar_reclamo.html', {'rec_form': rec_form})


@login_required
def grabar_reclamo(request, pk):  # noqa
    """Guarda reclamo como definitivo (sale de borradores)."""
    reclamo = get_object_or_404(Reclamo, pk=pk)
    reclamo.guardar()
    return redirect('detalle_reclamo', pk=pk)


@login_required
def eliminar_reclamo(request, pk):  # noqa
    """Elimina reclamo."""
    reclamo = get_object_or_404(Reclamo, pk=pk)
    reclamo.eliminar()
    return redirect('lista_reclamos')


@login_required
def detalle_reclamo(request, pk):
    """Muestra detalle del reclamo."""
    reclamo = get_object_or_404(Reclamo, pk=pk)
    return render(request, 'reclamos/detalle_reclamo.html', {'reclamo': reclamo})
# </RECLAMOS>


# <PARTIDAS>
@login_required
def buscador_partidas(request):  # noqa
    """Buscador de partidas."""
    # Consulto listado completo de partidas desde cache local:
    unidades_data = list(CacheUnidadSISA.objects.all().values(
        'unidad', 'unidad_alt', 'razon', 'calle', 'numero', 'piso', 'depto'
    ))
    df_partida = pd.DataFrame(unidades_data)
    # Creo listado de partidas con trabajos pendientes:
    partidas_usadas = list(Reclamo.objects.filter(  # noqa
        eliminado='Activo').values('partida'))
    part_us = []
    for item in partidas_usadas:
        for dic in item.values():
            if dic is not None:
                part_us.append(str(dic))
    # PANDAS:
    df_partida.columns = ['Unidad', 'Partida', 'Razón', 'Calle', 'N°', 'Piso', 'Dto.']
    # Pongo en rojo el N° de unidad de partidas con trabajos pendientes y link a
    # detalles en partida:
    df_partida['Partida_hidden'] = df_partida['Partida']
    for _, row in df_partida.iterrows():
        if row['Partida'] in part_us:
            row['Unidad'] = ('<b class="unidad" style="color:red">' +
                             str(row['Unidad']) + '</b>')
        else:
            row['Unidad'] = '<b class="unidad">' + str(row['Unidad']) + '</b>'
        row['Partida'] = ('<a href="/partida/partida-' + str(row['Partida']) +
                          '">' + str(row['Partida']) + '</a>')
    # RETURN:
    return df_partida.to_html(index=False, escape=False, table_id='partidas')


@login_required
def info_partida(request):
    """Render de tabla buscador de partida."""
    return render(request, 'reclamos/info_partida.html', {'tabla_un': buscador_partidas(request)})


@login_required
def detalle_partida(request, partida):
    """Consulta en SISA detalle de PARTIDA."""
    # Consulto datos de unidad desde cache local:
    try:
        unidad_obj = CacheUnidadSISA.objects.filter(unidad_alt=str(partida)).first()
    except Exception:
        unidad_obj = None

    if unidad_obj is not None:
        # Procesar campos del objeto unidad
        unidad = str(unidad_obj.unidad) if unidad_obj.unidad else '-'
        partida = str(unidad_obj.unidad_alt) if unidad_obj.unidad_alt else '-'
        razon = str(unidad_obj.razon) if unidad_obj.razon else '-'
        calle = str(unidad_obj.calle) if unidad_obj.calle else '-'
        numero = str(int(unidad_obj.numero)) if unidad_obj.numero else '-'
        piso = str(unidad_obj.piso) if unidad_obj.piso else '-'
        depto = str(unidad_obj.depto) if unidad_obj.depto else '-'
        dat_complem = str(unidad_obj.dat_complem) if unidad_obj.dat_complem else '-'
        num_doc = str(int(unidad_obj.num_doc)) if unidad_obj.num_doc else '-'
        telefono = str(unidad_obj.telefono) if unidad_obj.telefono else '-'
        celular = str(unidad_obj.telefono_cel) if unidad_obj.telefono_cel else '-'
        tel_alt = str(unidad_obj.fax) if unidad_obj.fax else '-'
        tel_lab = str(unidad_obj.tel_laboral) if unidad_obj.tel_laboral else '-'
        e_mail = str(unidad_obj.e_mail) if unidad_obj.e_mail else '-'
        e_mail_alt = str(unidad_obj.e_mail_alternativo) if unidad_obj.e_mail_alternativo else '-'
        e_mail_alt2 = str(unidad_obj.usu_of_vir) if unidad_obj.usu_of_vir else '-'
    else:
        unidad = '-'
        partida = 'PARTIDA INEXISTENTE'
        razon = '-'
        calle = '-'
        numero = '-'
        piso = '-'
        depto = '-'
        dat_complem = '-'
        num_doc = '-'
        telefono = '-'
        celular = '-'
        tel_alt = '-'
        tel_lab = '-'
        e_mail = '-'
        e_mail_alt = '-'
        e_mail_alt2 = '-'

    # Consultar observaciones desde z80unidad_obs (no está cacheada)
    lst_obs = []
    if unidad != '-':
        try:
            connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                         user=cnf.DB_SISA_USR,
                                         password=cnf.DB_SISA_PASS,
                                         db='osebal_produccion',
                                         charset='utf8mb4',
                                         cursorclass=pymysql.cursors.DictCursor)
            cursor = pymysql.cursors.DictCursor(connection)
            query_obs = ("SELECT fecha_obs, leyenda " +
                        "FROM osebal_produccion.z80unidad_obs WHERE unidad = '" + str(unidad) + "';")
            cursor.execute(query_obs)
            observ = pd.DataFrame(cursor.fetchall())
            cursor.close()
            connection.close()
        except Exception:
            observ = pd.DataFrame()
    else:
        observ = pd.DataFrame()
    for item in observ.to_records():
        lst_obs.append(str(item[1].strftime("%d/%m/%Y")) + ' - ' + str(item[2]))
    if partida != 'PARTIDA INEXISTENTE':
        ante = (Reclamo.objects.filter(eliminado='Activo').filter(  # noqa
            partida=partida).order_by('n_de_reclamo'))
    else:
        ante = None

    # Deuda
    fecha_deuda = datetime.datetime.fromtimestamp(os.path.getmtime(settings.MEDIA_ROOT +
                                                                   r'/proveedores/' +
                                                                   'deuda_masivo.xls'))
    df_deuda_adbsa = pd.read_excel(settings.MEDIA_ROOT + r'/proveedores/deuda_masivo.xls',
                                   skiprows=[0, 1, 2, 3, 4, 5, 6, 7, 9],
                                   usecols='E,J')
    dict_deuda_adbsa = {}
    for _, row in df_deuda_adbsa.iterrows():
        if row['Total'] == float('NaN'):
            pass
        else:
            try:
                dict_deuda_adbsa[int(row['Unidad Alt.'])] = row['Total']
            except ValueError:
                pass
    try:
        deuda = dict_deuda_adbsa[int(partida)]
    except KeyError:
        deuda = 0

    return render(request, 'reclamos/detalle_partida.html', {'unidad': unidad,
                                                             'partida': partida,
                                                             'razon': razon,
                                                             'calle': calle,
                                                             'numero': numero,
                                                             'piso': piso,
                                                             'depto': depto,
                                                             'dat_complem': dat_complem,
                                                             'num_doc': num_doc,
                                                             'telefono': telefono,
                                                             'celular': celular,
                                                             'tel_alt': tel_alt,
                                                             'tel_lab': tel_lab,
                                                             'e_mail': e_mail,
                                                             'e_mail_alt': e_mail_alt,
                                                             'e_mail_alt2': e_mail_alt2,
                                                             'obs': lst_obs,
                                                             'ante': ante,
                                                             'deuda': deuda,
                                                             'fecha_deuda': fecha_deuda})
# </PARTIDAS>


# <CUADRILLAS>
@login_required
def cuadrilla_agua(request):
    """Muestra listado de trabajos para las cuadrillas y botones para imprimir las planillas."""
    agua = (Reclamo.objects.filter(estado__estado__in=['Pendiente', 'Deuda Vigente'],  # noqa
                                   a_reporte='Si', eliminado='Activo',
                                   tipo_de_reclamo__tipo__in=['Agua'])
            .order_by('fecha'))

    cuadrillas = DatosCuadrilla.objects.all()  # noqa
    datos = get_object_or_404(DatosCuadrilla, datos='unico')
    if request.method == "POST":
        cuad_form = CuadrillaAgua(request.POST, instance=datos)
        if cuad_form.is_valid():
            datos = cuad_form.save(commit=False)
            datos.save()
            cuad_form.save_m2m()
            return redirect('cuadrilla_agua')
    else:
        cuad_form = CuadrillaAgua(instance=datos)
    return render(request, 'reclamos/cuadrilla_agua.html',
                  {'agua': agua, 'titulo_agua': 'Cuadrilla Agua:',
                   'cuad_form': cuad_form, 'datos': datos, 'cuadrillas': cuadrillas})


@login_required
def cuadrilla_cloacas(request):
    """Muestra listado de trabajos para las cuadrillas y botones para imprimir las planillas."""
    cloacas = (Reclamo.objects.filter(estado__estado__in=['Pendiente', 'Deuda Vigente'],  # noqa
                                      a_reporte='Si', eliminado='Activo',
                                      tipo_de_reclamo__tipo='Cloacas').order_by('fecha'))

    cuadrillas = DatosCuadrilla.objects.all()  # noqa
    datos = get_object_or_404(DatosCuadrilla, datos='unico')
    if request.method == "POST":
        cuad_form = CuadrillaCloaca(request.POST, instance=datos)
        if cuad_form.is_valid():
            datos = cuad_form.save(commit=False)
            datos.save()
            cuad_form.save_m2m()
            return redirect('cuadrilla_cloacas')
    else:
        cuad_form = CuadrillaCloaca(instance=datos)
    return render(request, 'reclamos/cuadrilla_cloacas.html',
                  {'cloacas': cloacas, 'titulo_cloacas': 'Cuadrilla Cloacas:',
                   'cuad_form': cuad_form, 'datos': datos, 'cuadrillas': cuadrillas})


@login_required
def cuadrilla_niv_pozos(request):
    """Muestra listado de trabajos para las cuadrillas y botones para imprimir las planillas."""
    pozos = (Reclamo.objects.filter(estado__estado__in=['Pendiente', 'Deuda Vigente'],  # noqa
                                    a_reporte='Si', eliminado='Activo',
                                    tipo_de_reclamo__tipo='Nivelación / Pozos').order_by('fecha'))

    cuadrillas = DatosCuadrilla.objects.all()  # noqa
    datos = get_object_or_404(DatosCuadrilla, datos='unico')
    if request.method == "POST":
        cuad_form = CuadrillaNivPozos(request.POST, instance=datos)
        if cuad_form.is_valid():
            datos = cuad_form.save(commit=False)
            datos.save()
            cuad_form.save_m2m()
            return redirect('cuadrilla_niv_pozos')
    else:
        cuad_form = CuadrillaNivPozos(instance=datos)
    return render(request, 'reclamos/cuadrilla_niv_pozos.html',
                  {'pozos': pozos, 'titulo_pozos': 'Cuadrilla Nivelación / Pozos',
                   'cuad_form': cuad_form, 'datos': datos, 'cuadrillas': cuadrillas})


@login_required
def cuadrilla_mco_tapa(request):
    """Muestra listado de trabajos para las cuadrillas y botones para imprimir las planillas."""
    marco_tapa = (Reclamo.objects.filter(estado__estado__in=['Pendiente', 'Deuda Vigente'],  # noqa
                                         a_reporte='Si', eliminado='Activo',
                                         tipo_de_reclamo__tipo__in=['Marco y tapa']))

    cuadrillas = DatosCuadrilla.objects.all()  # noqa
    datos = get_object_or_404(DatosCuadrilla, datos='unico')
    if request.method == "POST":
        cuad_form = CuadrillaMcoTapa(request.POST, instance=datos)
        if cuad_form.is_valid():
            datos = cuad_form.save(commit=False)
            datos.save()
            cuad_form.save_m2m()
            return redirect('cuadrilla_mco_tapa')
    else:
        cuad_form = CuadrillaMcoTapa(instance=datos)
    return render(request, 'reclamos/cuadrilla_mco_tapa.html',
                  {'marco_tapa': marco_tapa, 'titulo_marco_tapa': 'Marco y tapa',
                   'cuad_form': cuad_form, 'datos': datos, 'cuadrillas': cuadrillas})


@login_required
def cuadrilla_mant_cloacal(request):
    """Muestra listado de trabajos para las cuadrillas y botones para imprimir las planillas."""
    mant_red_cloacal = (Reclamo.objects.filter(estado__estado__in=['Pendiente', 'Deuda Vigente'],  # noqa
                                               a_reporte='Si', eliminado='Activo',
                                               tipo_de_reclamo__tipo__in=['Mant. Red Cloacal']))

    cuadrillas = DatosCuadrilla.objects.all()  # noqa
    datos = get_object_or_404(DatosCuadrilla, datos='unico')
    if request.method == "POST":
        cuad_form = CuadrillaMantCloacal(request.POST, instance=datos)
        if cuad_form.is_valid():
            datos = cuad_form.save(commit=False)
            datos.save()
            cuad_form.save_m2m()
            return redirect('cuadrilla_mant_cloacal')
    else:
        cuad_form = CuadrillaMantCloacal(instance=datos)
    return render(request, 'reclamos/cuadrilla_mant_cloacal.html',
                  {'mant_red_cloacal': mant_red_cloacal, 'titulo_mant_red_cloacal': 'Mantenimiento Red Cloacal',
                   'cuad_form': cuad_form, 'datos': datos, 'cuadrillas': cuadrillas})


@login_required
def cuadrilla_rec_serv_med(request):
    """Muestra listado de trabajos para las cuadrillas y botones para imprimir las planillas."""
    serv_med = (Reclamo.objects.filter(estado__estado__in=['Pendiente', 'Deuda Vigente'],  # noqa
                                       a_reporte='Si', eliminado='Activo',
                                       tipo_de_reclamo__tipo__in=['Reclamo servicio medido'])
                .order_by('fecha'))

    cuadrillas = DatosCuadrilla.objects.all()  # noqa
    datos = get_object_or_404(DatosCuadrilla, datos='unico')
    if request.method == "POST":
        cuad_form = CuadrillaServMed(request.POST, instance=datos)
        if cuad_form.is_valid():
            datos = cuad_form.save(commit=False)
            datos.save()
            cuad_form.save_m2m()
            return redirect('cuadrilla_serv_med')
    else:
        cuad_form = CuadrillaServMed(instance=datos)
    return render(request, 'reclamos/cuadrilla_serv_med.html',
                  {'serv_med': serv_med, 'titulo_serv_med': 'Cuadrilla Reclamos Servicio Medido:',
                   'cuad_form': cuad_form, 'datos': datos, 'cuadrillas': cuadrillas})


@login_required
def cuadrilla_verif_fact(request):
    """Muestra listado de trabajos para las cuadrillas y botones para imprimir las planillas."""
    verif_fc = (Reclamo.objects.filter(estado__estado__in=['Pendiente', 'Deuda Vigente'],  # noqa
                                       a_reporte='Si', eliminado='Activo',
                                       tipo_de_reclamo__tipo='Verificación por facturación').order_by('fecha'))

    cuadrillas = DatosCuadrilla.objects.all()  # noqa
    datos = get_object_or_404(DatosCuadrilla, datos='unico')
    if request.method == "POST":
        cuad_form = CuadrillaVerifFact(request.POST, instance=datos)
        if cuad_form.is_valid():
            datos = cuad_form.save(commit=False)
            datos.save()
            cuad_form.save_m2m()
            return redirect('cuadrilla_verif_fact')
    else:
        cuad_form = CuadrillaVerifFact(instance=datos)
    return render(request, 'reclamos/cuadrilla_verif_fact.html',
                  {'verif_fc': verif_fc, 'titulo_verif_fact': 'Verificación por Facturación:',
                   'cuad_form': cuad_form, 'datos': datos, 'cuadrillas': cuadrillas})


def watermark(input_file):
    """Agrega marca de agua."""
    with open(settings.PDF_ROOT + 'Parte de trabajo.pdf', 'rb') as wm_input:
        # read content of the watermark file
        pdf = PdfReader(wm_input)
        with open(input_file, 'rb') as in_file:
            # read content of the original file
            factura = PdfReader(in_file)
            # get first page of the original PDF
            wm_first_page = pdf.pages[0]
            # get first page of the watermark PDF
            first_page_file = factura.pages[0]
            # merge the two pages
            wm_first_page.merge_page(first_page_file)
            # create a pdf writer object for the output file
            pdf_writer = PdfWriter()
            # add page
            pdf_writer.add_page(wm_first_page)
            with open('temp.pdf', 'wb') as filehandle_output:
                # write the watermarked file to the new file
                pdf_writer.write(filehandle_output)
    os.remove(input_file)
    os.rename('temp.pdf', input_file)


@login_required
def imprimir_cuadrilla(request, filtro, tipo):  # noqa
    """Crea PDFs para cuadrillas (general)."""
    # Creo el DF con la consulta y LISTA FOTMATEADA para sig. paso (TABLA):
    df_cuadrilla = pd.DataFrame.from_records(
        Reclamo.objects.filter(estado__estado__in=['Pendiente', 'Deuda Vigente'],  # noqa
                               a_reporte='Si', eliminado='Activo', tipo_de_reclamo__tipo=filtro)
        .order_by('fecha').values('fecha', 'apellido', 'calle', 'altura', 'telefono',
                                  'detalle', 'partida'))
    df_cuadrilla.columns = ['Fecha', 'Apellido', 'Calle', 'N°', 'Teléfono', 'Detalle', 'Partida']
    list_pre = ([df_cuadrilla.columns[:, ].values.astype(str).tolist()] +  # noqa
                df_cuadrilla.values.tolist())
    # Arreglo formato de fecha en la lista para mostrar correctamente en la tabla:
    for index, element in enumerate(list_pre):
        if index >= 1:
            for index2, item in enumerate(element):
                if index2 == 0:
                    element[index2] = str(item)[8:10] + "/" + str(item)[5:7] + "/" + str(item)[0:4]
    lista = copy.deepcopy(list_pre)
    # Agrego estilos a elementos de la lista:
    style1 = ParagraphStyle(name='normal', fontName='Helvetica', fontSize=11, alignment=TA_CENTER)
    style2 = ParagraphStyle(name='normal', fontName='Helvetica', fontSize=11)
    for index, element in enumerate(lista):
        if index >= 1:
            for index2, item in enumerate(element):
                if index2 in (1, 5):
                    element[index2] = Paragraph(str(item), style=style2)
                else:
                    element[index2] = Paragraph(str(item), style=style1)
    # Elimino partida para cuadrilla:
    for item in lista:
        del item[-1]
    # QUERY DATOS ENCABEZADO:
    # Fecha
    c_fecha = DatosCuadrilla.objects.values('fecha')  # noqa
    cuad_fecha = str([x for x in c_fecha][0]['fecha'])
    fecha = cuad_fecha[8:10] + '/' + cuad_fecha[5:7] + '/' + cuad_fecha[0:4]
    # Operarios
    c_op = getattr((DatosCuadrilla.objects.get(pk=1)), 'operarios_' + tipo).values('operario')  # noqa
    l_op = [x for x in c_op]
    l_op2 = []
    for item in l_op:
        l_op2.append(item['operario'])
    s_op = ''
    last_op = len(l_op)
    count_op = 0
    for item in l_op2:
        if count_op < last_op - 1:
            s_op = s_op + item + ' - '
            count_op += 1
        else:
            s_op = s_op + item
    # CREO EL INFORME PDF:
    elements = []
    doc = SimpleDocTemplate(settings.PDF_ROOT + 'resumen_' + tipo + '.pdf', pagesize=A4,
                            rightMargin=0, leftMargin=3, topMargin=1, bottomMargin=0)
    # Encabezado:
    logo = Image(settings.PDF_ROOT + 'logo.jpg')
    logo.drawHeight = 19.86 * mm
    logo.drawWidth = 38.85 * mm
    op_style = ParagraphStyle(name='normal', fontName='Helvetica-Bold', fontSize=13)
    head_list = None
    if filtro != 'Reclamo servicio medido':
        head_list = [['Cuadrilla ' + filtro, 'FECHA', [logo]],
                     [Paragraph(s_op, style=op_style), fecha, ''],
                     ['', '', '']]
    elif filtro == 'Reclamo servicio medido':
        head_list = [['Cuadrilla ' + 'Reclamo Serv. medido', 'FECHA', [logo]],
                     [Paragraph(s_op, style=op_style), fecha, ''],
                     ['', '', '']]
    head_table_st = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Alineación vertical general
                     ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Alineación horizontal columna fecha
                     ('FONT', (1, 0), (1, -1), 'Helvetica-Bold', 13),  # Fuente columna fecha
                     ('VALIGN', (1, 0), (1, 0), 'BOTTOM'),
                     ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Alineación columna 1
                     ('FONT', (0, 0), (0, 0), 'Helvetica-Bold', 20),  # Fuente título
                     ('SPAN', (-1, 0), (-1, 2)),
                     ('ALIGN', (-1, 0), (-1, 2), 'RIGHT')]  # Alineación logo
    head_table = Table(head_list, style=head_table_st, colWidths=(107 * mm, 30 * mm, 57 * mm))
    elements.append(head_table)
    # Tabla:
    table_style = [('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 13),
                   ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                   ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                   ('INNERGRID', (0, 0), (-1, -1), 0.35, colors.black),
                   ('BOX', (0, 0), (-1, -1), 1.25, colors.black),
                   ('LINEABOVE', (0, 1), (5, 1), 1.25, colors.black)]
    table = Table(lista, style=table_style, colWidths=(25 * mm, 35 * mm, 24 * mm,
                                                       23 * mm, 30 * mm, 57 * mm))
    elements.append(table)
    # Construyo el PDF:
    doc.build(elements)
    # PARTES DE TRABAJO:
    partes = 1
    paginas = []
    for item in list_pre[1:]:
        paginas.append(settings.PDF_ROOT + 'temp_' + tipo + '_' + str(partes) + '.pdf')
        can = canvas.Canvas(settings.PDF_ROOT + 'temp_' + tipo + '_' + str(partes) + '.pdf')
        can.setPageSize(landscape(A4))
        can.setFont('Helvetica', 10)
        can.drawString(598, 502, fecha)
        can.drawString(152, 481, str(item[1]))
        can.drawString(70, 466, str(item[2]))
        can.drawString(340, 466, str(item[3]))
        can.drawString(317, 450, str(item[4]))
        try:
            can.drawString(98, 434, str(int(item[6])))
        except (TypeError, ValueError):
            can.drawString(98, 434, '-')
        # motivo:
        can.drawString(260, 434, str(item[5][:44]) + '-')
        can.drawString(51, 420, '-' + str(item[5][44:]))
        # USO DE BARBIJO:
        can.setFont('Helvetica-Bold', 16)
        can.drawString(520, 140, '*Uso obligatorio de barbijo.')
        can.drawImage(settings.PDF_ROOT + 'firma_mario.jpg', 750, 122, width=45, height=52)

        can.showPage()
        can.save()
        watermark(settings.PDF_ROOT + 'temp_' + tipo + '_' + str(partes) + '.pdf')
        partes += 1
    merger = PdfMerger()
    cant_resumen = 1
    loop_resumen = 0
    while loop_resumen < cant_resumen:
        merger.append(PdfReader(settings.PDF_ROOT + 'resumen_' + tipo + '.pdf', 'rb'))
        loop_resumen += 1
    for pagina in paginas:
        merger.append(PdfReader(pagina, 'rb'))
    merger.write(settings.PDF_ROOT + 'Cuadrilla_' + tipo + '.pdf')
    return FileResponse(open(settings.PDF_ROOT + 'Cuadrilla_' + tipo + '.pdf', 'rb'),
                        content_type='application/pdf')  # ,as_attachment=True "PARA GUARDAR COMO"


@login_required
def imprimir_cuadrilla_agua(request):
    """Genera PDFs cuadrilla agua."""
    return imprimir_cuadrilla(request, 'Agua', 'agua')


@login_required
def imprimir_cuadrilla_cloacas(request):
    """Genera PDFs cuadrilla cloacas."""
    return imprimir_cuadrilla(request, 'Cloacas', 'cloacas')


@login_required
def imprimir_cuadrilla_pozos(request):
    """Genera PDFs cuadrilla pozos."""
    return imprimir_cuadrilla(request, 'Nivelación / Pozos', 'pozos')


@login_required
def imprimir_cuadrilla_marco_tapa(request):
    """Genera PDFs cuadrilla marco y tapa."""
    return imprimir_cuadrilla(request, 'Marco y tapa', 'marco_tapa')


@login_required
def imprimir_cuadrilla_mant_red_cloacal(request):
    """Genera PDFs cuadrilla mant. red cloacal."""
    return imprimir_cuadrilla(request, 'Mant. Red Cloacal', 'mant_red_cloacal')


@login_required
def imprimir_cuadrilla_verif_fact(request):
    """Genera PDFs cuadrilla verificación para facturación."""
    return imprimir_cuadrilla(request, 'Verificación por facturación', 'verif_por_fact')


@login_required
def imprimir_cuadrilla_serv_med(request):
    """Genera PDFs cuadrilla reclamos servicio medido."""
    return imprimir_cuadrilla(request, 'Reclamo servicio medido', 'serv_med')
# </CUADRILLAS>


# <ARCHIVOS>
@login_required
def carga_archivos(request, pk):
    """Cargar archivos asociados a un reclamo."""
    reclamo = get_object_or_404(Reclamo, pk=pk)
    if request.method == "POST":
        arch_form = ArchivoForm(request.POST, request.FILES)
        if arch_form.is_valid():
            archivo = arch_form.save(commit=False)
            archivo.reclamo = reclamo
            archivo.save()
            return redirect('detalle_reclamo', pk=reclamo.pk)
    else:
        arch_form = ArchivoForm()
    return render(request, 'archivos/carga_archivos.html', {'arch_form': arch_form})


@login_required
def detalle_archivo(request, pk):
    """Ver detalle de archivo ya cargado, desde aquí se puede eliminar."""
    # request.FILES
    archivo = get_object_or_404(Archivos, pk=pk)
    return render(request, 'reclamos/detalle_archivo.html', {'archivo': archivo})


@login_required
def eliminar_archivo(request, pk):  # noqa
    """Elimina archivo ya cargado."""
    archivo = get_object_or_404(Archivos, pk=pk)
    reclamo = str(archivo.reclamo)
    nreclamo = reclamo[0:int(reclamo.find(' '))]
    archivo.delete()
    return redirect('detalle_reclamo', pk=nreclamo)
# </ARCHIVOS>


# <REPORTES>
@login_required
def rep_pend_fin(request):
    """Generador de reportes Pendientes / Finalizados."""
    # Modifico filtros
    datos = get_object_or_404(FiltroInformePendFin, single='unico')
    if request.method == "POST":
        rep_form = FiltroInformePendFinForm(request.POST, instance=datos)
        if rep_form.is_valid():
            datos = rep_form.save(commit=False)
            datos.save()
            rep_form.save_m2m()
            return redirect('rep_pend_fin')
    else:
        rep_form = FiltroInformePendFinForm(instance=datos)
    # Traigo filtros
    fecha_inicio = list(FiltroInformePendFin.objects.filter(  # noqa
        single='unico').values('fecha_inicio'))[0]['fecha_inicio']
    fecha_fin = list(FiltroInformePendFin.objects.filter(  # noqa
        single='unico').values('fecha_fin'))[0]['fecha_fin']
    tipo = list(FiltroInformePendFin.objects.filter(  # noqa
        single='unico').values('tipo__tipo'))[0]['tipo__tipo']
    # Aplico filtro
    if tipo is None:
        lista = list(Reclamo.objects.filter(eliminado='Activo',  # noqa
                                            fecha__range=(fecha_inicio, fecha_fin))
                     .values('fecha', 'estado__estado'))
    else:
        lista = list(Reclamo.objects.filter(eliminado='Activo', tipo_de_reclamo__tipo=tipo,  # noqa
                                            fecha__range=(fecha_inicio, fecha_fin))
                     .values('fecha', 'estado__estado'))
    # Creo DF con filtros aplicados
    try:
        df_reporte = pd.DataFrame(lista)
        # Extraigo xticks ordenados
        xlabels = []
        pre_xlabels = list(df_reporte['fecha'])
        pre_xlabels = sorted(pre_xlabels)
        for item in pre_xlabels:
            if str(item)[5:7] + '-' + str(item)[0:4] not in xlabels:
                xlabels.append(str(item)[5:7] + '-' + str(item)[0:4])
        # Arreglo DF para el gráfico (agrupo, formato..)
        df_reporte['fecha'] = pd.to_datetime(df_reporte['fecha'])
        df_reporte = df_reporte.groupby(df_reporte['fecha'].dt.strftime('%m-%Y'
                                                                        ).astype('datetime64[D]')
                                        )['estado__estado'].value_counts()
        # Creo el gráfico con sus elementos

        df_reporte.unstack().plot(kind='bar', stacked=True, legend=True, figsize=(12, 8))
        plt.legend(title='Estado', title_fontsize='small', fontsize='small',
                   shadow=True, loc='upper right')
        xlocs, _ = plt.xticks()
        plt.xticks(xlocs, xlabels, rotation=45)
        # yticks como enteros multiplos de 1:
        locator = matplotlib.ticker.MultipleLocator(20)
        plt.gca().yaxis.set_major_locator(locator)
        formatter = matplotlib.ticker.StrMethodFormatter("{x:.0f}")
        plt.gca().yaxis.set_major_formatter(formatter)
        plt.grid(b=True, linestyle='--', linewidth=0.5)
        plt.xlabel('Periodo', size='large')
        plt.ylabel('Cantidad', size='large')
        plt.title('Evolución de trabajos', size='x-large')
        # Preparo gráfico para mostrar en HTML.
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close('all')
        graphic = base64.b64encode(image_png)
        graphic = graphic.decode('utf-8')
        # Utilizar en caso de tener que revisar datos para grafico
        # tabla = pd.DataFrame(df_reporte).to_html(escape=False, table_id='partidas')
        return render(request, 'reclamos/reporte_pend_fin.html',
                      {'rep_form': rep_form,
                       'graphic': graphic})
    except KeyError:
        img = ImagePIL.new('RGB', (200, 60), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "Sin datos!", fill=(255, 0, 0))
        # Preparo advertencia para mostrar en HTML.
        buffer = BytesIO()
        img.save(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close('all')
        graphic = base64.b64encode(image_png)
        graphic = graphic.decode('utf-8')
        return render(request, 'reclamos/reporte_tiem_resol.html',
                      {'rep_form': rep_form,
                       'graphic': graphic})


@login_required
def rep_tiem_resol(request):
    """Generador de reportes Pendientes / Finalizados."""
    # Modifico filtros
    datos = get_object_or_404(FiltroInformeTiemResol, single='unico')
    if request.method == "POST":
        rep_form = FiltroInformeTiemResolForm(request.POST, instance=datos)
        if rep_form.is_valid():
            datos = rep_form.save(commit=False)
            datos.save()
            rep_form.save_m2m()
            return redirect('rep_tiem_resol')
    else:
        rep_form = FiltroInformeTiemResolForm(instance=datos)

    # Traigo filtros
    fecha_inicio = list(FiltroInformeTiemResol.objects.filter(  # noqa
        single='unico').values('fecha_inicio'))[0]['fecha_inicio']
    fecha_fin = list(FiltroInformeTiemResol.objects.filter(  # noqa
        single='unico').values('fecha_fin'))[0]['fecha_fin']
    tipo = list(FiltroInformeTiemResol.objects.filter(  # noqa
        single='unico').values('tipo__tipo'))[0]['tipo__tipo']
    # Aplico filtro
    if tipo is None:
        lista = list(Reclamo.objects.filter(eliminado='Activo',  # noqa
                                            fecha__range=(fecha_inicio, fecha_fin),
                                            estado__estado__icontains='Final')
                     .values('fecha', 'fecha_resolucion', 'tipo_de_reclamo__tipo'))
    else:
        lista = list(Reclamo.objects.filter(eliminado='Activo', tipo_de_reclamo__tipo=tipo,  # noqa
                                            fecha__range=(fecha_inicio, fecha_fin),
                                            estado__estado__icontains='Final')
                     .values('fecha', 'fecha_resolucion', 'tipo_de_reclamo__tipo'))
    # Creo DF con filtros aplicados
    # try:
    df_reporte = pd.DataFrame(lista)

    # Extraigo xticks ordenados
    xlabels = []
    pre_xlabels = list(df_reporte['fecha'])
    pre_xlabels = sorted(pre_xlabels)
    for item in pre_xlabels:
        if str(item)[5:7] + '-' + str(item)[0:4] not in xlabels:
            xlabels.append(str(item)[5:7] + '-' + str(item)[0:4])
    # Arreglo DF para el gráfico (agrupo, formato..)
    df_reporte['fecha'] = pd.to_datetime(df_reporte['fecha'])
    df_reporte['fecha_resolucion'] = pd.to_datetime(df_reporte['fecha_resolucion'])
    df_reporte['tiempo'] = df_reporte.fecha_resolucion - df_reporte.fecha
    df_reporte.drop('fecha_resolucion', axis=1, inplace=True)
    df_reporte = df_reporte.groupby(df_reporte['fecha'].dt.strftime('%m-%Y'
                                                                    ).astype('datetime64[D]')
                                    )['tiempo'].value_counts()
    # Creo el gráfico con sus elementos
    df_reporte.unstack().plot(style=".")  # (kind='scatter', stacked=True, legend=True)
    plt.legend(title='Estado', title_fontsize='small', fontsize='small',
               shadow=True, loc='upper right')
    xlocs, _ = plt.xticks()
    plt.xticks(xlocs, xlabels, rotation='horizontal')
    # yticks como enteros multiplos de 1:
    locator = matplotlib.ticker.MultipleLocator(1)
    plt.gca().yaxis.set_major_locator(locator)
    formatter = matplotlib.ticker.StrMethodFormatter("{x:.0f}")
    plt.gca().yaxis.set_major_formatter(formatter)
    plt.grid(b=True, linestyle='--', linewidth=0.5)
    plt.xlabel('Periodo', size='large')
    plt.ylabel('Días', size='large')
    plt.title('Tiempo de resolución', size='x-large')
    # Preparo gráfico para mostrar en HTML.
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close('all')
    graphic = base64.b64encode(image_png)
    graphic = graphic.decode('utf-8')
    # Utilizar en caso de tener que revisar datos para grafico
    tabla = pd.DataFrame(df_reporte).to_html(escape=False, table_id='partidas')
    return render(request, 'reclamos/reporte_tiem_resol.html',
                  {'rep_form': rep_form,
                   'graphic': graphic,
                   'tabla': tabla})


@login_required
def imprimir_comprobante_reclamo(request, pk):
    """Genera PDF del comprobante de reclamo."""
    reclamo = get_object_or_404(Reclamo, pk=pk)

    # Obtener cuenta OSEBAL desde cache
    cuenta_osebal = None
    if reclamo.partida:
        try:
            cache_unidad = CacheUnidadSISA.objects.get(unidad_alt=str(reclamo.partida))
            cuenta_osebal = int(cache_unidad.unidad)
        except CacheUnidadSISA.DoesNotExist:
            cuenta_osebal = None

    # Obtener datos de deuda si existe partida
    mostrar_deuda = False
    fecha_deuda = None

    if reclamo.partida:
        try:
            # Obtener fecha del archivo masivo de deuda
            archivo_deuda = settings.MEDIA_ROOT + r'/proveedores/deuda_masivo.xls'
            if os.path.exists(archivo_deuda):
                fecha_deuda = datetime.datetime.fromtimestamp(os.path.getmtime(archivo_deuda))

                # Leer archivo Excel de deuda (columnas E=Unidad Alt., J=Total)
                df_deuda = pd.read_excel(archivo_deuda,
                                        skiprows=[0, 1, 2, 3, 4, 5, 6, 7, 9],
                                        usecols='E,J')

                # Crear diccionario de deuda
                dict_deuda = {}
                for _, row in df_deuda.iterrows():
                    try:
                        unidad_alt = int(row['Unidad Alt.'])
                        # Guardar deuda si existe
                        if pd.notna(row['Total']):
                            dict_deuda[unidad_alt] = row['Total']
                    except (ValueError, KeyError):
                        pass

                # Obtener deuda de la partida
                deuda = dict_deuda.get(int(reclamo.partida), 0)

                # Verificar si supera el umbral
                if deuda >= settings.UMBRAL_DEUDA_COMPROBANTE:
                    mostrar_deuda = True
        except Exception:
            # Si hay error leyendo el archivo, continuar sin mostrar deuda
            pass

    # Crear PDF
    filename = settings.PDF_ROOT + f'Comprobante_{reclamo.n_de_reclamo}.pdf'
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Logo de la empresa
    logo_path = settings.STATIC_ROOT + '/img/logo.png'
    if os.path.exists(logo_path):
        c.drawImage(logo_path, 1, height - 100, width=180, height=90,
                   preserveAspectRatio=True, mask='auto')

    # Título del comprobante (centrado)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 100, "COMPROBANTE DE RECLAMO")

    # Línea separadora
    c.line(50, height - 120, width - 50, height - 120)

    # Datos del reclamo
    y_position = height - 140
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_position, "N° de Reclamo:")
    c.setFont("Helvetica", 11)
    c.drawString(180, y_position, str(reclamo.n_de_reclamo))

    y_position -= 25
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_position, "Fecha:")
    c.setFont("Helvetica", 11)
    c.drawString(180, y_position, reclamo.created_date.strftime('%d/%m/%Y'))

    y_position -= 25
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_position, "Tipo de Reclamo:")
    c.setFont("Helvetica", 11)
    c.drawString(180, y_position, str(reclamo.tipo_de_reclamo))

    y_position -= 25
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_position, "Cuenta OSEBAL:")
    c.setFont("Helvetica", 11)
    c.drawString(180, y_position, str(cuenta_osebal) if cuenta_osebal else "N/A")

    # Texto de periodos impagos si corresponde
    if mostrar_deuda and fecha_deuda:
        y_position -= 35
        c.setFont("Helvetica-Bold", 11)
        c.setFillColorRGB(0.8, 0, 0)  # Rojo
        texto_deuda = f"Registra periodos impagos al {fecha_deuda.strftime('%d-%m-%Y')}"
        c.drawString(50, y_position, texto_deuda)
        c.setFillColorRGB(0, 0, 0)  # Volver a negro

    # Línea final
    c.line(50, y_position - 20, width - 50, y_position - 20)

    # Guardar PDF
    c.save()

    # Retornar respuesta
    return FileResponse(open(filename, 'rb'), content_type='application/pdf')
