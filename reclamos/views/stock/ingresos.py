"""Ingresos."""
import psycopg2
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import FileResponse
from reclamos.models import (MovimientoMateriales, Ingreso)
from reclamos.forms import (IngresosForm, MovimientoIngFormIN)
import sgi.shpd_cnf as cnf
from django.conf import settings


@login_required
def nuevo_ingreso(request):
    """Crea nueva entrada de materiales."""
    if request.method == "POST":
        ing_form = IngresosForm(request.POST)
        if ing_form.is_valid():
            ingreso = ing_form.save(commit=False)
            user = request.user
            ingreso.author = user
            ingreso.editor = user
            ingreso.save()
            ing_form.save_m2m()
            grabar_ingreso(request, ingreso.id)
            return redirect('detalle_ingreso', pk=ingreso.pk)
    else:
        ing_form = IngresosForm()
        return render(request, 'stock/ingreso_material.html',
                      {'ing_form': ing_form, 'boton': ''})


@login_required
def grabar_ingreso(request, pk):
    """Guarda nuevo ingreso."""
    ingreso = get_object_or_404(Ingreso, pk=pk)
    ingreso.guardar()
    return redirect('listado_ingresos')


@login_required
def eliminar_ingreso(request, pk):
    """Elimina ingreso."""
    ingreso = get_object_or_404(Ingreso, pk=pk)
    ingreso.eliminar()
    MovimientoMateriales.objects.filter(ing_asoc=pk).update(eliminado='Eliminado')
    return redirect('listado_ingresos')


@login_required
def detalle_ingreso(request, pk):
    """Muestra detalle ingreso."""
    ingreso = get_object_or_404(Ingreso, pk=pk)
    movimiento = MovimientoMateriales.objects.filter(ing_asoc=pk, eliminado='Activo')
    return render(request, 'stock/detalle_ingreso.html', {'ingreso': ingreso, 'movimiento': movimiento})


@login_required
def editar_ingreso(request, pk):
    """Edita ingreso existente."""
    ingreso1 = get_object_or_404(Ingreso, pk=pk)
    if request.method == "POST":
        ing_form = IngresosForm(request.POST, instance=ingreso1)
        if ing_form.is_valid():
            ingreso = ing_form.save(commit=False)
            ingreso.editor = request.user
            ingreso.save()
            ing_form.save_m2m()
            return redirect('detalle_ingreso', pk=ingreso.pk)
    else:
        ing_form = IngresosForm(instance=ingreso1)
    return render(request, 'stock/editar_ingreso.html', {'ing_form': ing_form})


@login_required
def listado_ingresos(request):
    """Muestra lista de entradas."""
    ingresos = (Ingreso.objects.filter(eliminado='Activo')
                .order_by('-created_date'))
    return render(request, 'stock/listado_ingresos.html', {'ingresos': ingresos})


@login_required
def ingreso_articulos(request, pk):
    """Cargar articulos asociados a un ingreso."""
    ingreso = get_object_or_404(Ingreso, pk=pk)
    if request.method == "POST":
        ing_form = MovimientoIngFormIN(request.POST)
        if ing_form.is_valid():
            articulo = ing_form.save(commit=False)
            user = request.user
            articulo.author = user
            articulo.editor = user
            articulo.ing_asoc_id = ingreso.pk
            articulo.tipo = 'ingreso'
            articulo.save()
            ing_form.save_m2m()
            grabar_ing_art(request, articulo.id)
            return redirect('carga_articulo_in', pk=ingreso.pk)
    else:
        ing_form = MovimientoIngFormIN()
    return render(request, 'stock/ingreso_material.html', {'ing_form': ing_form, 'boton': True, 'ingreso': ingreso})


@login_required
def grabar_ing_art(request, pk):
    """Guarda nueva entrada."""
    ingreso = get_object_or_404(MovimientoMateriales, pk=pk)
    ingreso.guardar()
    return redirect('listado_ingresos')


@login_required
def eliminar_ing_art(request, pk):
    """Elimina ingreso."""
    mov = get_object_or_404(MovimientoMateriales, pk=pk)
    ingreso = mov.ing_asoc.id
    mov.eliminar()
    return redirect('detalle_ingreso', pk=ingreso)


def process_exportar_ingresos(desde, hasta):
    d_anio = str(desde)[0:4]
    d_mes = str(desde)[4:6]
    d_dia = str(desde)[6:8]
    h_anio = str(hasta)[0:4]
    h_mes = str(hasta)[4:6]
    h_dia = str(hasta)[6:8]

    query = f"""
    SELECT 
        ri.fecha,
        ri.id AS egreso_id,
        rm.id AS material_id,
        rm.descripcion,
        rmm.cantidad
    FROM 
        reclamos_movimientomateriales rmm
    JOIN 
        reclamos_ingreso ri ON rmm.ing_asoc_id = ri.id
    JOIN 
        reclamos_materiales rm ON rmm.material_id = rm.id
    WHERE 
        ri.fecha BETWEEN '{d_anio}-{d_mes}-{d_dia}' AND '{h_anio}-{h_mes}-{h_dia}'
        AND ri.eliminado = 'Activo';
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
    df.columns = ['Fecha', 'Nº ingreso', 'Cod. Material', 'Descripción', 'Cantidad']
    df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce')

    with pd.ExcelWriter(settings.MEDIA_ROOT + r'/tmp/Ingresos_' + str(desde) + '_a_' + str(hasta) + '.xlsx',
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

    return settings.MEDIA_ROOT + r'/tmp/Ingresos_' + str(desde) + '_a_' + str(hasta) + '.xlsx'


@login_required
def exportar_ingresos(request):  # noqa
    """Eporta ingresos."""
    if request.method == "POST":
        if (str(request.POST['desde']) == '') or (str(request.POST['hasta']) == ''):
            return render(request, 'stock/exportar_ingresos.html')
        try:
            desde = int(request.POST["desde"])
            hasta = int(request.POST["hasta"])
        except (ValueError, TypeError):
            return render(request, 'stock/exportar_ingresos.html')
        archivo = process_exportar_ingresos(desde, hasta)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'stock/exportar_ingresos.html')
