"""Egresos."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import FileResponse
import psycopg2
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter
from reclamos.models import (MovimientoMateriales, Egreso)
from reclamos.forms import (EgresosForm, MovimientoEgrFormOUT)
import sgi.shpd_cnf as cnf
from django.conf import settings


@login_required
def nuevo_egreso(request):
    """Crea nueva salida de materiales."""
    if request.method == "POST":
        egr_form = EgresosForm(request.POST)
        if egr_form.is_valid():
            egreso = egr_form.save(commit=False)
            user = request.user
            egreso.author = user
            egreso.editor = user
            egreso.save()
            egr_form.save_m2m()
            grabar_egreso(request, egreso.id)
            return redirect('detalle_egreso', pk=egreso.pk)
    else:
        egr_form = EgresosForm()
        return render(request, 'stock/egreso_material.html', {'egr_form': egr_form, 'boton': ''})


@login_required
def grabar_egreso(request, pk):
    """Guarda nueva salida."""
    egreso = get_object_or_404(Egreso, pk=pk)
    egreso.guardar()
    return redirect('listado_egresos')


@login_required
def eliminar_egreso(request, pk):
    """Elimina egreso."""
    egreso = get_object_or_404(Egreso, pk=pk)
    egreso.eliminar()
    MovimientoMateriales.objects.filter(egr_asoc=pk).update(eliminado='Eliminado')  # noqa
    return redirect('listado_egresos')


@login_required
def detalle_egreso(request, pk):
    """Muestra detalle egreso."""
    egreso = get_object_or_404(Egreso, pk=pk)
    movimiento = MovimientoMateriales.objects.filter(egr_asoc=pk, eliminado='Activo')  # noqa
    return render(request, 'stock/detalle_egreso.html', {'egreso': egreso, 'movimiento': movimiento})


@login_required
def editar_egreso(request, pk):
    """Edita proveedor existente."""
    egreso1 = get_object_or_404(Egreso, pk=pk)
    if request.method == "POST":
        egr_form = EgresosForm(request.POST, instance=egreso1)
        if egr_form.is_valid():
            egreso = egr_form.save(commit=False)
            egreso.editor = request.user
            egreso.save()
            egr_form.save_m2m()
            return redirect('detalle_egreso', pk=egreso.pk)
    else:
        egr_form = EgresosForm(instance=egreso1)
    return render(request, 'stock/editar_egreso.html', {'egr_form': egr_form})


@login_required
def listado_egresos(request):
    """Muestra lista de salidas."""
    egresos = (Egreso.objects.filter(eliminado='Activo')  # noqa
               .order_by('-created_date'))
    return render(request, 'stock/listado_egresos.html', {'egresos': egresos})


@login_required
def egreso_articulos(request, pk):
    """Cargar articulos asociados a un egreso."""
    egreso = get_object_or_404(Egreso, pk=pk)
    if request.method == "POST":
        egr_form = MovimientoEgrFormOUT(request.POST)
        if egr_form.is_valid():
            articulo = egr_form.save(commit=False)
            user = request.user
            articulo.author = user
            articulo.editor = user
            articulo.cantidad = articulo.cantidad * -1
            articulo.egr_asoc_id = egreso.pk
            articulo.tipo = 'egreso'
            articulo.save()
            egr_form.save_m2m()
            grabar_egr_art(request, articulo.id)
            return redirect('carga_articulo_out', pk=egreso.pk)
    else:
        egr_form = MovimientoEgrFormOUT()
    return render(request, 'stock/egreso_material.html', {'egr_form': egr_form, 'boton': True, 'egreso': egreso})


@login_required
def grabar_egr_art(request, pk):  # noqa
    """Guarda nueva salida."""
    egreso = get_object_or_404(MovimientoMateriales, pk=pk)
    egreso.guardar()
    return redirect('listado_egresos')


@login_required
def eliminar_egr_art(request, pk):  # noqa
    """Elimina egreso."""
    mov = get_object_or_404(MovimientoMateriales, pk=pk)
    egreso = mov.egr_asoc.id
    mov.eliminar()
    return redirect('detalle_egreso', pk=egreso)


def process_exportar_egresos(desde, hasta):
    d_anio = str(desde)[0:4]
    d_mes = str(desde)[4:6]
    d_dia = str(desde)[6:8]
    h_anio = str(hasta)[0:4]
    h_mes = str(hasta)[4:6]
    h_dia = str(hasta)[6:8]

    query = f"""
    SELECT 
        re.fecha,
        re.id AS egreso_id,
        rm.id AS material_id,
        rm.descripcion,
        rmm.cantidad,
        STRING_AGG(ro.operario, ' - ') AS operario
    FROM 
        reclamos_movimientomateriales rmm
    JOIN 
        reclamos_egreso re ON rmm.egr_asoc_id = re.id
    JOIN 
        reclamos_materiales rm ON rmm.material_id = rm.id
    JOIN 
        reclamos_egreso_personal rep ON rmm.egr_asoc_id = rep.egreso_id
    JOIN 
        reclamos_operarios ro ON rep.operarios_id = ro.id
    WHERE 
        re.fecha BETWEEN '{d_anio}-{d_mes}-{d_dia}' AND '{h_anio}-{h_mes}-{h_dia}'
        AND re.eliminado = 'Activo'
    GROUP BY 
        re.fecha, re.id, rm.id, rm.descripcion, rmm.cantidad;
    """
    try:
        connection = psycopg2.connect(user=cnf.DB_SHPD_USR,
                                      password=cnf.DB_SHPD_PASS,
                                      host=cnf.DB_SHPD_HOST,
                                      port="5432",
                                      database="sgi_db")
        cursor = connection.cursor()
        cursor.execute(query)
        datos = cursor.fetchall()
    except Exception as expt:
        print('Error al obtener datos: ' + repr(expt))
    finally:
        if (connection):
            cursor.close()
            connection.close()

    df = pd.DataFrame(datos)
    df.columns = ['Fecha', 'Nº egreso', 'Cod. Material', 'Descripción', 'Cantidad', 'Operario/s']
    df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce')

    with pd.ExcelWriter(settings.MEDIA_ROOT + r'/tmp/Egresos_' + str(desde) + '_a_' + str(hasta) + '.xlsx',
                        engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Hoja1', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Hoja1']

        # Aplicar formato con coma como separador decimal a la columna 'cantidad' (columna E)
        for cell in worksheet['E']:  # 'E' es la quinta columna (cantidad)
            cell.number_format = '#,##0.00'  # Formato con coma como separador decimal

        # Ajustar automáticamente el ancho de las columnas
        for col_idx, column in enumerate(df.columns, 1):  # Enumerate empieza en 1 para coincidir con Excel
            # Calcular el ancho máximo basado en el contenido de la columna
            max_length = max(
                df[column].astype(str).map(len).max(),  # Longitud máxima de los datos
                len(str(column))  # Longitud del encabezado
            )
            # Ajustar el ancho de la columna (agregar un pequeño margen)
            worksheet.column_dimensions[get_column_letter(col_idx)].width = max_length + 2
    return settings.MEDIA_ROOT + r'/tmp/Egresos_' + str(desde) + '_a_' + str(hasta) + '.xlsx'


@login_required
def exportar_egresos(request):  # noqa
    """Eporta egresos."""
    if request.method == "POST":
        if (str(request.POST['desde']) == '') or (str(request.POST['hasta']) == ''):
            return render(request, 'stock/exportar_egresos.html')
        try:
            desde = int(request.POST["desde"])
            hasta = int(request.POST["hasta"])
        except (ValueError, TypeError):
            return render(request, 'stock/exportar_egresos.html')
        archivo = process_exportar_egresos(desde, hasta)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'stock/exportar_egresos.html')
