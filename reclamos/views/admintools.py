from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import FileResponse
import os
import datetime
import pymysql
import pandas as pd
import fitz
from smb.SMBConnection import SMBConnection
from reclamos.forms import CorreoForm
from reclamos.models import Reclamos_correo
from reclamos.admintools.procesa_rbc import procesa_rbc
from reclamos.admintools.rend_alberghini import process_alberghini
from reclamos.admintools.process_ret_iibb import process_ret_iibb
from reclamos.admintools.process_perc_iibb import process_perc_iibb
from reclamos.admintools.process_listado_b_c import process_listado_b_c
from reclamos.admintools.filtrar_pmc import process_filtro_pmc
from reclamos.admintools.sicore import process_sicore
from reclamos.admintools.alta_incob import process_alta_incob
from reclamos.admintools.process_liq_iibb import process_liq_iibb
from reclamos.admintools.process_liq_iibb_osebal import process_liq_iibb_osebal
from reclamos.admintools.baja_incob import process_baja_incob
from reclamos.admintools.process_pres_cuat_arba import process_pres_cuat_arba
from reclamos.admintools.process_pres_cuat_arba_osebal import process_pres_cuat_arba_osebal
from reclamos.admintools.process_deuda_proveedores import process_deuda_proveedores
from reclamos.admintools.process_carga_masivo_deuda import process_carga_masivo_deuda
from reclamos.admintools.process_carga_partidas_proveedores import process_carga_partidas_proveedores
from reclamos.admintools.process_rd_generados import process_rd_generados
from reclamos.admintools.process_reporte_sms_masivos import process_reporte_sms_masivos
from reclamos.admintools.dto_int_canon import process_dto_int_canon
from reclamos.admintools.arch_inter_muni import arch_inter_muni
from reclamos.admintools.arch_cons_ctas import arch_cons_ctas
from reclamos.admintools.libro_iva_digital import libro_iva_digital
from reclamos.admintools.desc_precibido import proc_desc_percibido


def to_ar(valor, decimales):
    """Pasa número a formato AR."""
    valo = float(valor)
    formato = '{:,.' + str(decimales) + 'f}'
    val = formato.format(valo).replace(",", "@").replace(".", ",").replace("@", ".")
    return val


@login_required
def conversor_rbc(request):
    """Renderiza página del Conversor de archivos RBC municipalidad."""
    if request.method == "POST" and request.FILES.get('filepath', False) is False:
        if "data_file" not in request.FILES:
            return render(request, 'herramientas/conversor_rbc.html')
        data = request.FILES["data_file"]
        path = default_storage.save('tmp/temp_rbc_', ContentFile(data.read()))
        tmp_file = os.path.join(settings.MEDIA_ROOT, path)
        archivo = procesa_rbc(tmp_file)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/conversor_rbc.html')


@login_required
def rend_alberghini(request):
    """Renderiza página deherramienta Rendición Alberghini."""
    if request.method == "POST":
        if (str(request.POST['year']) == '') or (str(request.POST['month']) == ''):
            return render(request, 'herramientas/rend_alberghini.html')
        try:
            year = int(request.POST["year"])
            month = int(request.POST["month"])
        except (ValueError, TypeError):
            return render(request, 'herramientas/rend_alberghini.html')
        archivo = process_alberghini(year, month)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/rend_alberghini.html')


@login_required
def ret_iibb(request):
    """Renderiza página de herramienta Ret. IIBB."""
    if request.method == "POST":
        if (str(request.POST['anio']) == '') or (str(request.POST['mes']) == '') \
                or (str(request.POST['quincena']) == ''):
            return render(request, 'herramientas/ret_iibb.html')
        try:
            anio = int(request.POST["anio"])
            mes = int(request.POST["mes"])
            quincena = int(request.POST["quincena"])
        except (TypeError, ValueError):
            return render(request, 'herramientas/ret_iibb.html')
        archivo = process_ret_iibb(anio, mes, quincena)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/ret_iibb.html')


@login_required
def perc_iibb(request):
    """Renderiza página de herramienta Perc. IIBB."""
    if request.method == "POST":
        if (str(request.POST['anio']) == '') or (str(request.POST['mes']) == '') \
                or (str(request.POST['quincena']) == ''):
            return render(request, 'herramientas/perc_iibb.html')
        try:
            anio = int(request.POST["anio"])
            mes = int(request.POST["mes"])
            quincena = int(request.POST["quincena"])
        except (TypeError, ValueError):
            return render(request, 'herramientas/perc_iibb.html')
        archivo = process_perc_iibb(anio, mes, quincena)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/perc_iibb.html')


@login_required
def listado_b_c(request):
    """Renderiza página de herramienta Listado Bomberos y Carenciados."""
    if request.method == "POST":
        if (str(request.POST['anio']) == '') or (str(request.POST['mes']) == ''):
            return render(request, 'herramientas/listado_b_c.html')
        try:
            anio = int(request.POST["anio"])
            mes = int(request.POST["mes"])
        except (ValueError, TypeError):
            return render(request, 'herramientas/listado_b_c.html')
        tipo = str(request.POST["tipo"])
        archivo = process_listado_b_c(tipo, anio, mes)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/listado_b_c.html')


@login_required
def filtro_pmc(request):
    """Renderiza página del Filtro de archivo a subir a PMC."""
    if request.method == "POST" and request.FILES.get('filepath', False) is False:
        if ("archivo" not in request.FILES) or (str(request.POST['anio']) == '') \
                or (str(request.POST['mes']) == ''):
            return render(request, 'herramientas/filtro_pmc.html')
        try:
            anio = int(request.POST["anio"])
            mes = int(request.POST["mes"])
        except (TypeError, ValueError):
            return render(request, 'herramientas/filtro_pmc.html')
        archivo = request.FILES["archivo"]

        try:
            os.remove(settings.MEDIA_ROOT + r'/tmp/' + archivo.name)
        except FileNotFoundError:
            pass

        path = default_storage.save(r'tmp/' + archivo.name, ContentFile(archivo.read()))
        tmp_file = os.path.join(settings.MEDIA_ROOT, path)
        archivo = process_filtro_pmc(anio, mes, tmp_file)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/filtro_pmc.html')


@login_required
def sicore(request):
    """Renderiza página del Filtro de archivo a subir a PMC."""
    if request.method == "POST" and request.FILES.get('filepath', False) is False:
        if ("archivo1" not in request.FILES) or (str(request.POST['quincena']) == '') \
                or ("archivo2" not in request.FILES):
            return render(request, 'herramientas/sicore.html')
        try:
            quincena = int(request.POST["quincena"])
        except (TypeError, ValueError):
            return render(request, 'herramientas/sicore.html')
        archivo1 = request.FILES["archivo1"]
        archivo2 = request.FILES["archivo2"]
        name1 = str(archivo1.name)
        name2 = str(archivo2.name)
        path1 = default_storage.save(r'tmp/' + archivo1.name, ContentFile(archivo1.read()))
        tmp_file1 = os.path.join(settings.MEDIA_ROOT, path1)
        path2 = default_storage.save(r'tmp/' + archivo2.name, ContentFile(archivo2.read()))
        tmp_file2 = os.path.join(settings.MEDIA_ROOT, path2)
        archivo = process_sicore(quincena, tmp_file1, tmp_file2, name1, name2)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/sicore.html')


@login_required
def alta_incob(request):
    """Renderiza página del listado de alta de incobrables."""
    if request.method == "POST":
        # return render(request, 'herramientas/alta_incob.html')
        archivo = process_alta_incob()
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/alta_incob.html')


@login_required
def liq_iibb(request):
    """Renderiza página de herramienta liquidación iibb."""
    if request.method == "POST":
        if (str(request.POST['year']) == '') or (str(request.POST['month']) == ''):
            return render(request, 'herramientas/liq_iibb.html')
        try:
            year = int(request.POST["year"])
            month = (request.POST["month"])
            empresa = str(request.POST["empresa"])
        except (TypeError, ValueError):
            return render(request, 'herramientas/liq_iibb.html')
        archivo = ''
        if empresa == 'adbsa':
            archivo = process_liq_iibb(year, month)
        elif empresa == 'osebal':
            archivo = process_liq_iibb_osebal(year, month)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/liq_iibb.html')


@login_required
def baja_incob(request):
    """Renderiza página del generador de reporte para baja de incobrables."""
    if request.method == "POST" and request.FILES.get('filepath', False) is False:
        if "data_file" not in request.FILES:
            return render(request, 'herramientas/baja_incob.html')
        data = request.FILES["data_file"]
        path = default_storage.save('tmp/temp_baja_incob', ContentFile(data.read()))
        tmp_file = os.path.join(settings.MEDIA_ROOT, path)
        archivo = process_baja_incob(tmp_file)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/baja_incob.html')


@login_required
def pres_cuat_arba(request):
    """Renderiza página de herramienta presentación cuatrimestral Arba."""
    if request.method == "POST":
        if (str(request.POST['anio']) == '') or (str(request.POST['cuatrimestre']) == ''):
            return render(request, 'herramientas/pres_cuat_arba.html')
        try:
            anio = int(request.POST["anio"])
            cuatrimestre = (request.POST["cuatrimestre"])
        except (TypeError, ValueError):
            return render(request, 'herramientas/pres_cuat_arba.html')
        archivo = process_pres_cuat_arba(anio, cuatrimestre)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/pres_cuat_arba.html')


@login_required
def pres_cuat_arba_osebal(request):
    """Renderiza página de herramienta presentación cuatrimestral Arba."""
    if request.method == "POST":
        if (str(request.POST['anio']) == '') or (str(request.POST['cuatrimestre']) == ''):
            return render(request, 'herramientas/pres_cuat_arba_osebal.html')
        try:
            anio = int(request.POST["anio"])
            cuatrimestre = (request.POST["cuatrimestre"])
        except (TypeError, ValueError):
            return render(request, 'herramientas/pres_cuat_arba_osebal.html')
        archivo = process_pres_cuat_arba_osebal(anio, cuatrimestre)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/pres_cuat_arba_osebal.html')


@login_required
def deuda_proveedores(request):
    """Renderiza página deuda proveedores."""
    ahora = datetime.datetime.now()
    if request.method == "POST" and request.FILES.get('filepath', False) is False:
        fecha_masivo = datetime.datetime.fromtimestamp(os.path.getmtime(settings.MEDIA_ROOT +
                                                                        r'/proveedores/' +
                                                                        'deuda_masivo.xls'))
        partidasxprov = datetime.datetime.fromtimestamp(os.path.getmtime(settings.MEDIA_ROOT +
                                                                         r'/proveedores/' +
                                                                         'partidas_x_proveedor' +
                                                                         '.xlsx'))
        if (ahora - fecha_masivo) > datetime.timedelta(days=30):
            vencido = 'si'
        else:
            vencido = 'no'
        if "archivo" not in request.FILES:
            return render(request, 'herramientas/deuda_proveedores.html',
                          {'masivo': fecha_masivo, 'partidas': partidasxprov, 'vencido': vencido})
        archivo = request.FILES["archivo"]
        path = default_storage.save(r'tmp/' + archivo.name, ContentFile(archivo.read()))
        tmp_file = os.path.join(settings.MEDIA_ROOT, path)
        archivo = process_deuda_proveedores(tmp_file)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    fecha_masivo = datetime.datetime.fromtimestamp(os.path.getmtime(settings.MEDIA_ROOT +
                                                                    r'/proveedores/' +
                                                                    'deuda_masivo.xls'))
    partidasxprov = datetime.datetime.fromtimestamp(os.path.getmtime(settings.MEDIA_ROOT +
                                                                     r'/proveedores/' +
                                                                     'partidas_x_proveedor' +
                                                                     '.xlsx'))
    if (ahora - fecha_masivo) > datetime.timedelta(days=30):
        vencido = 'si'
    else:
        vencido = 'no'
    return render(request, 'herramientas/deuda_proveedores.html',
                  {'masivo': fecha_masivo, 'partidas': partidasxprov, 'vencido': vencido})


@login_required
def carga_masivo_deuda(request):
    """Renderiza página carga masivo deuda."""
    if request.method == "POST" and request.FILES.get('filepath', False) is False:
        if "archivo" not in request.FILES:
            return render(request, 'herramientas/carga_masivo_deuda.html')
        archivo = request.FILES["archivo"]
        path = default_storage.save(r'tmp/' + archivo.name, ContentFile(archivo.read()))
        tmp_file = os.path.join(settings.MEDIA_ROOT, path)
        archivo = process_carga_masivo_deuda(tmp_file)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/carga_masivo_deuda.html')


@login_required
def carga_partidas_proveedores(request):
    """Renderiza página carga partidas proveedores."""
    if request.method == "POST" and request.FILES.get('filepath', False) is False:
        if "archivo" not in request.FILES:
            return render(request, 'herramientas/carga_partidas_proveedores.html')
        archivo = request.FILES["archivo"]
        path = default_storage.save(r'tmp/' + archivo.name, ContentFile(archivo.read()))
        tmp_file = os.path.join(settings.MEDIA_ROOT, path)
        archivo = process_carga_partidas_proveedores(tmp_file)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/carga_partidas_proveedores.html')


@login_required
def rd_generados(request):
    """Renderiza página de herramienta Reporte RDs."""
    if request.method == "POST":
        if (str(request.POST['year']) == '') or (str(request.POST['month']) == ''):
            return render(request, 'herramientas/reporte_rd_generados.html')
        try:
            year = int(request.POST["year"])
            month = int(request.POST["month"])
        except (ValueError, TypeError):
            return render(request, 'herramientas/reporte_rd_generados.html')
        archivo = process_rd_generados(year, month)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/reporte_rd_generados.html')


@login_required
def reporte_sms_masivos(request):
    """Renderiza página de herramienta Reporte SMS Masivos."""
    if request.method == "POST" and request.FILES.get('filepath', False) is False:
        if (str(request.POST['year']) == '') or (str(request.POST['month']) == '') or \
           (str(request.POST['day']) == '') or ("listado" not in request.FILES):
            return render(request, 'herramientas/reporte_sms_masivos.html')
        try:
            listado = request.FILES["listado"]
            year = int(request.POST["year"])
            month = int(request.POST["month"])
            day = int(request.POST["day"])
        except (ValueError, TypeError):
            return render(request, 'herramientas/reporte_sms_masivos.html')
        path = default_storage.save(r'tmp/' + listado.name, ContentFile(listado.read()))
        tmp_file = os.path.join(settings.MEDIA_ROOT, path)
        archivo = process_reporte_sms_masivos(tmp_file, year, month, day)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/reporte_sms_masivos.html')


@login_required
def dto_int_canon(request):
    """Renderiza página de herramienta descuento intereses canon."""
    if request.method == "POST":
        if (str(request.POST['year']) == '') or (str(request.POST['month']) == ''):
            return render(request, 'herramientas/dto_int_canon.html')
        try:
            year = int(request.POST["year"])
            month = (request.POST["month"])
        except (TypeError, ValueError):
            return render(request, 'herramientas/dto_int_canon.html')
        archivo = process_dto_int_canon(year, month)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/dto_int_canon.html')


@login_required
def list_cort_dism(request):
    """Renderiza página listado de cortes y disminuciones."""
    if request.method == "POST":
        if str(request.POST['partida']) == '':
            return render(request, 'herramientas/list_cort_dism.html')
        try:
            partida = int(request.POST["partida"])
        except (ValueError, TypeError):
            return render(request, 'herramientas/list_cort_dism.html')

        userid = 'admin'
        password = 'admin'
        client_machine_name = 'remota'
        server_name = 'FILESERVER'
        server_ip = '172.16.29.3'
        domain_name = r'\\FILESERVER\DATOS'
        conn = SMBConnection(userid, password, client_machine_name, server_name, domain=domain_name,
                             use_ntlm_v2=True, is_direct_tcp=True)
        conn.connect(server_ip, 445)

        with open(settings.MEDIA_ROOT + r'/tmp/cor_dism_tmp.xlsx', 'wb') as fpp:
            conn.retrieveFile('DATOS',
                              'VER DEUDA/DISMINUCIONES ACTIVAS.xlsx',
                              fpp)
        with open(settings.MEDIA_ROOT + r'/tmp/deuda_ant_tmp.xlsx', 'wb') as fpp2:
            conn.retrieveFile('DATOS',
                              'VER DEUDA/deuda_ant.xlsx',
                              fpp2)
        conn.close()

        df_cort = pd.read_excel(settings.MEDIA_ROOT + r'/tmp/cor_dism_tmp.xlsx',  # noqa
                                sheet_name='Hoja1',
                                engine='openpyxl', usecols=['PARTIDA EN MORA', 'STATUS'])
        df_cort = df_cort[(df_cort['STATUS'] ==
                           'CORTE DEL SERVICIO') | (df_cort['STATUS'] ==
                                                    'DISMINUCION DEL SERVICIO')]
        lista = df_cort['PARTIDA EN MORA'].tolist()
        lista = [str(i) for i in lista]
        if str(partida) in lista:
            resultado = 'PARTIDA CON DISMINUCIÓN.'
        else:
            resultado = 'NORMAL.'

        df_deu = pd.read_excel(settings.MEDIA_ROOT + r'/tmp/deuda_ant_tmp.xlsx')
        dct_deu = df_deu.to_dict(orient='records')
        dct_deu_final_orig = {}
        dct_deu_final_reca = {}
        for dic in dct_deu:
            dct_deu_final_orig[dic['partida']] = "{:.2f}".format(dic['saldo'])
            dct_deu_final_reca[dic['partida']] = "{:.2f}".format(dic['recargo'])
        if int(partida) in dct_deu_final_orig.keys():
            deuda_orig = str(dct_deu_final_orig[int(partida)])
        else:
            deuda_orig = '0'
        if int(partida) in dct_deu_final_reca.keys():
            deuda_reca = str(dct_deu_final_reca[int(partida)])
        else:
            deuda_reca = '0'

        return render(request, 'herramientas/result_list_cort_dism.html',
                      {'partida': partida, 'resultado': resultado,
                       'deuda_orig': deuda_orig, 'deuda_reca': deuda_reca})
    return render(request, 'herramientas/list_cort_dism.html')


@login_required
def arch_muni(request):
    """Renderiza página p/ generación archivos municipalidad."""
    if request.method == "POST":
        if (str(request.POST['tabla']) == '') or (str(request.POST['desde']) == '') or (str(request.POST['hasta']) == ''):
            return render(request, 'herramientas/arch_inter_muni.html')
        try:
            tabla = int(request.POST["tabla"])
            desde = int(request.POST["desde"])
            hasta = int(request.POST["hasta"])
            tipo = str(request.POST["tipo"])
        except (ValueError, TypeError):
            return render(request, 'herramientas/arch_inter_muni.html')
        archivo = arch_inter_muni(tipo, tabla, desde, hasta)
        if archivo != 'nodata':
            return FileResponse(open(archivo, 'rb'),
                                content_type='application/txt', as_attachment=True)
        else:
            error = '<b><span style="color: red;">· No hay datos para la consulta realizada.</span></b>'
            return render(request, 'herramientas/arch_inter_muni.html', {'error': error})
    return render(request, 'herramientas/arch_inter_muni.html')


@login_required
def cons_ctas(request):
    """Consulta movimientos de una cuenta contable en mov_ren en determinado periodo."""
    if request.method == "POST":
        if (str(request.POST['cuenta']) == '') or (str(request.POST['desde']) == '') or (str(request.POST['hasta']) == ''):
            return render(request, 'herramientas/cons_ctas.html')
        try:
            cuenta = int(request.POST["cuenta"])
            desde = int(request.POST["desde"])
            hasta = int(request.POST["hasta"])
        except (ValueError, TypeError):
            return render(request, 'herramientas/cons_ctas.html')
        archivo = arch_cons_ctas(cuenta, desde, hasta)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/cons_ctas.html')


@login_required
def calculadora_intereses(request):
    """Muestra página de caluladora de intereses."""
    if request.method == "POST":
        cuenta = int(request.POST["cuenta"])
        condicion = str(request.POST["condicion"])
        capital = float(request.POST["capital"])
        recargo = float(request.POST["recargo"])
        anticipo1 = float(request.POST["anticipo1"])
        cuotas1 = float(request.POST["cuotas1"])
        anticipo2 = float(request.POST["anticipo2"])
        cuotas2 = float(request.POST["cuotas2"])
        hoy = (datetime.date.today().strftime("%d/%m/%y"))
        deuda = capital + recargo
        pago_contado = capital
        desc_int70 = recargo * (70 / 100)
        total_plan = deuda - desc_int70
        val_cuota1 = (total_plan - anticipo1) / cuotas1
        desc_int30 = recargo * (30 / 100)
        desc_int50 = recargo * (50 / 100)
        if condicion == 'consfin':
            int_fin48 = ((deuda - desc_int30) * 0.48 / 12 * cuotas2) * 1.21
        else:
            int_fin48 = ((deuda - desc_int30) * 0.48 / 12 * cuotas2) * 1.27
        total_plan2 = (deuda - desc_int30) + int_fin48
        val_cuota2 = (total_plan2 - anticipo2) / cuotas2

        if condicion == 'consfin':
            precio3cuo_tot = total_plan * 1.3095 * 1.21
        else:
            precio3cuo_tot = total_plan * 1.3095 * 1.27
        precio3cuo = precio3cuo_tot / 3

        if condicion == 'consfin':
            precio6cuo_tot = (deuda - desc_int50) * 1.5855 * 1.21
        else:
            precio6cuo_tot = (deuda - desc_int50) * 1.5855 * 1.27
        precio6cuo = precio6cuo_tot / 6

        if condicion == 'consfin':
            precio12cuo_tot = (total_plan2 - int_fin48) * 2.2956 * 1.21
        else:
            precio12cuo_tot = (total_plan2 - int_fin48) * 2.2956 * 1.27
        precio12cuo = precio12cuo_tot / 12

        cuenta = str(cuenta)
        hoy = str(hoy)
        deuda = '$' + to_ar(deuda, 2)
        pago_contado = '$' + to_ar(pago_contado, 2)
        anticipo1 = '$' + to_ar(anticipo1, 2)
        cuotas1 = to_ar(cuotas1, 0)
        val_cuota1 = '$' + to_ar(val_cuota1, 2)
        total_plan1 = '$' + to_ar(total_plan, 2)
        anticipo2 = '$' + to_ar(anticipo2, 2)
        cuotas2 = to_ar(cuotas2, 0)
        val_cuota2 = '$' + to_ar(val_cuota2, 2)
        total_plan2 = '$' + to_ar(total_plan2, 2)
        precio3cuo = '$' + to_ar(precio3cuo, 2)
        precio3cuo_tot = '$' + to_ar(precio3cuo_tot, 2)
        precio6cuo = '$' + to_ar(precio6cuo, 2)
        precio6cuo_tot = '$' + to_ar(precio6cuo_tot, 2)
        precio12cuo = '$' + to_ar(precio12cuo, 2)
        precio12cuo_tot = '$' + to_ar(precio12cuo_tot, 2)
        # Creo PDF
        doc = fitz.open(settings.PDF_ROOT + 'Propuesta.pdf')
        r1 = fitz.Rect(293, 142, 388, 156)
        t1 = cuenta
        r2 = fitz.Rect(293, 156, 388, 170)
        t2 = hoy
        r3 = fitz.Rect(293, 170, 388, 184)
        t3 = deuda
        r4 = fitz.Rect(137, 230, 476, 244)
        t4 = pago_contado
        r5 = fitz.Rect(137, 289, 209, 303)
        t5 = anticipo1
        r6 = fitz.Rect(137, 303, 209, 317)
        t6 = anticipo2
        r7 = fitz.Rect(210, 289, 292, 303)
        t7 = cuotas1
        r8 = fitz.Rect(210, 303, 292, 317)
        t8 = cuotas2
        r9 = fitz.Rect(293, 289, 388, 303)
        t9 = val_cuota1
        r10 = fitz.Rect(293, 303, 388, 317)
        t10 = val_cuota2
        r11 = fitz.Rect(388, 289, 477, 303)
        t11 = total_plan1
        r12 = fitz.Rect(388, 303, 477, 317)
        t12 = total_plan2
        r13 = fitz.Rect(137, 363, 292, 377)
        t13 = '3'
        r14 = fitz.Rect(137, 378, 292, 392)
        t14 = '6'
        r15 = fitz.Rect(137, 394, 292, 408)
        t15 = '12'
        r16 = fitz.Rect(292, 363, 387, 377)
        t16 = precio3cuo
        r17 = fitz.Rect(292, 378, 387, 392)
        t17 = precio6cuo
        r18 = fitz.Rect(292, 394, 387, 408)
        t18 = precio12cuo
        r19 = fitz.Rect(388, 363, 477, 377)
        t19 = precio3cuo_tot
        r20 = fitz.Rect(388, 378, 477, 392)
        t20 = precio6cuo_tot
        r21 = fitz.Rect(388, 394, 477, 408)
        t21 = precio12cuo_tot
        page = doc[0]
        shape = page.new_shape()
        shape.draw_rect(r1)
        shape.draw_rect(r2)
        shape.draw_rect(r3)
        shape.draw_rect(r4)
        shape.draw_rect(r5)
        shape.draw_rect(r6)
        shape.draw_rect(r7)
        shape.draw_rect(r8)
        shape.draw_rect(r9)
        shape.draw_rect(r10)
        shape.draw_rect(r11)
        shape.draw_rect(r12)
        shape.draw_rect(r13)
        shape.draw_rect(r14)
        shape.draw_rect(r15)
        shape.draw_rect(r16)
        shape.draw_rect(r17)
        shape.draw_rect(r18)
        shape.draw_rect(r19)
        shape.draw_rect(r20)
        shape.draw_rect(r21)
        shape.finish(color=(1, 1, 1), stroke_opacity=0)
        shape.insert_textbox(r1, t1, align=1)
        shape.insert_textbox(r2, t2, align=1)
        shape.insert_textbox(r3, t3, align=1)
        shape.insert_textbox(r4, t4, align=1)
        shape.insert_textbox(r5, t5, align=1)
        shape.insert_textbox(r6, t6, align=1)
        shape.insert_textbox(r7, t7, align=1)
        shape.insert_textbox(r8, t8, align=1)
        shape.insert_textbox(r9, t9, align=1)
        shape.insert_textbox(r10, t10, align=1)
        shape.insert_textbox(r11, t11, align=1)
        shape.insert_textbox(r12, t12, align=1)
        shape.insert_textbox(r13, t13, align=1)
        shape.insert_textbox(r14, t14, align=1)
        shape.insert_textbox(r15, t15, align=1)
        shape.insert_textbox(r16, t16, align=1)
        shape.insert_textbox(r17, t17, align=1)
        shape.insert_textbox(r18, t18, align=1)
        shape.insert_textbox(r19, t19, align=1)
        shape.insert_textbox(r20, t20, align=1)
        shape.insert_textbox(r21, t21, align=1)
        shape.commit()
        doc.save(settings.PDF_ROOT + 'Propuesta1.pdf')
        return FileResponse(open(settings.PDF_ROOT + 'Propuesta1.pdf', 'rb'),
                            content_type='application/pdf')  # ,as_attachment=True "PARA GUARDAR COMO"

    return render(request, 'herramientas/calculadora_intereses.html')


@login_required
def libro_iva_digital_rend(request):
    """Renderiza página de Libro de IVA digital."""
    if request.method == "POST" and request.FILES.get('filepath', False) is False:
        if ("vtas" not in request.FILES) or ("vtasa" not in request.FILES) \
                or ("vtasb" not in request.FILES) or \
                ("compras" not in request.FILES) or (str(request.POST['periodo']) == '') \
                or (str(request.POST['n_perc']) == ''):
            return render(request, 'herramientas/libro_iva_digital.html')
        try:
            periodo = int(request.POST["periodo"])
            n_perc = int(request.POST["n_perc"])
        except (TypeError, ValueError):
            return render(request, 'herramientas/libro_iva_digital.html')
        vtas = request.FILES["vtas"]
        vtasa = request.FILES["vtasa"]
        vtasb = request.FILES["vtasb"]
        compras = request.FILES["compras"]

        try:
            os.remove(settings.MEDIA_ROOT + r'/tmp/' + vtas.name)
        except FileNotFoundError:
            pass
        try:
            os.remove(settings.MEDIA_ROOT + r'/tmp/' + vtasa.name)
        except FileNotFoundError:
            pass
        try:
            os.remove(settings.MEDIA_ROOT + r'/tmp/' + vtasb.name)
        except FileNotFoundError:
            pass
        try:
            os.remove(settings.MEDIA_ROOT + r'/tmp/' + compras.name)
        except FileNotFoundError:
            pass

        path_vtas = default_storage.save(r'tmp/' + vtas.name, ContentFile(vtas.read()))
        tmp_vtas = os.path.join(settings.MEDIA_ROOT, path_vtas)
        path_vtasa = default_storage.save(r'tmp/' + vtasa.name, ContentFile(vtasa.read()))
        tmp_vtasa = os.path.join(settings.MEDIA_ROOT, path_vtasa)
        path_vtasb = default_storage.save(r'tmp/' + vtasb.name, ContentFile(vtasb.read()))
        tmp_vtasb = os.path.join(settings.MEDIA_ROOT, path_vtasb)
        path_compras = default_storage.save(r'tmp/' + compras.name, ContentFile(compras.read()))
        tmp_compras = os.path.join(settings.MEDIA_ROOT, path_compras)
        archivo_salida = libro_iva_digital(periodo, tmp_vtas, tmp_vtasa,
                                           tmp_vtasb, tmp_compras, n_perc)
        return FileResponse(open(archivo_salida, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/libro_iva_digital.html')


@login_required
def reclamos_correo(request):
    """Crea nuevo reclamo correo."""
    if request.method == "POST":
        if str(request.POST['cuenta']) == '':
            return redirect('reclamos_correo')
        try:
            cuenta = int(request.POST["cuenta"])
            observaciones = str(request.POST["observaciones"])
        except (TypeError, ValueError):
            return redirect('reclamos_correo')
        rec_correo_form = CorreoForm(request.POST)
        if rec_correo_form.is_valid():
            recorreo = rec_correo_form.save(commit=False)
            user = request.user
            recorreo.author = user
            recorreo.editor = user
            recorreo.cuenta = cuenta

            def domicilios(cta):
                """Trae domicilio."""
                # CREACION DE LISTAS A PARTIR DE SQL SISA:
                cuenta = str(cta)
                connection0 = pymysql.connect(host=settings.DB_OSEBAL_HOST,
                                              user=settings.DB_SISA_USR,
                                              password=settings.DB_SISA_PASS,
                                              db='osebal_produccion',
                                              charset='utf8mb4',
                                              cursorclass=pymysql.cursors.DictCursor)  # noqa
                cursor0 = pymysql.cursors.DictCursor(connection0)  # noqa
                query0 = ('SELECT osebal_produccion.z80dir_usu.calle, osebal_produccion.z80dir_usu.numero, '
                          'osebal_produccion.z80unidad.e_mail, osebal_produccion.z80unidad.e_mail_alternativo, '
                          'osebal_produccion.z80unidad.usu_of_vir '
                          'FROM osebal_produccion.z80unidad '
                          'JOIN osebal_produccion.z80dir_usu '
                          'ON osebal_produccion.z80unidad.usuario = osebal_produccion.z80dir_usu.usuario '
                          'AND osebal_produccion.z80unidad.dir_env = osebal_produccion.z80dir_usu.num_dir '
                          f"WHERE osebal_produccion.z80unidad.UNIDAD = '{cuenta}';")
                cursor0.execute(query0)
                cursor0.close()
                connection0.close()
                datos0 = cursor0.fetchall()
                if (str(datos0[0]['e_mail']) == 'None') and (str(datos0[0]['e_mail_alternativo']) == 'None')\
                        and (str(datos0[0]['usu_of_vir']) == 'None'):
                    imprime = 'Si'
                else:
                    imprime = 'No'
                salida = {'calle': datos0[0]['calle'], 'altura': datos0[0]['numero'], 'imprime': imprime}
                return salida
            domicilio = domicilios(int(cuenta))
            observaciones = observaciones
            calle = domicilio['calle']
            altura = domicilio['altura']
            imprime = domicilio['imprime']
            recorreo.calle = calle
            recorreo.altura = altura
            recorreo.observaciones = observaciones
            recorreo.imprime = imprime
            recorreo.save()
            rec_correo_form.save_m2m()
            return redirect('reclamos_correo')
    else:
        rec_correo_form = CorreoForm()
        lista = Reclamos_correo.objects.filter(eliminado='Activo').order_by('-created_date').values()[:10]
        return render(request, 'herramientas/reclamos_correo.html', {'rec_correo_form': rec_correo_form, 'lista': lista})


@login_required
def eliminar_rec_correo(request, pk):
    """Elimina rec_correo."""
    ingreso = get_object_or_404(Reclamos_correo, pk=pk)
    ingreso.eliminar()
    return redirect('reclamos_correo')


@login_required
def reporte_rec_correo(request):
    """Genera reporte reclamo correo."""
    if request.method == "POST":
        if str(request.POST['desde']) == '' or str(request.POST['hasta']) == '' or str(request.POST['tipo']) == '':
            return redirect('reporte_rec_correo')
        try:
            pre_desde = str(int(request.POST["desde"]))
            desde = f"{pre_desde[:4]}-{pre_desde[4:6]}-{pre_desde[6:8]}T00:00:00+03:00"
            pre_hasta = str(int(request.POST["hasta"]))
            hasta = f"{pre_hasta[:4]}-{pre_hasta[4:6]}-{pre_hasta[6:8]}T23:59:59+03:00"
            tipo = str(request.POST["tipo"])
        except (TypeError, ValueError):
            return redirect('reporte_rec_correo')
        if tipo == 'imprime':
            lista = list(Reclamos_correo.objects.filter(eliminado='Activo')
                         .filter(created_date__range=[desde, hasta])
                         .filter(imprime='Si')
                         .order_by('created_date').values())
        elif tipo == 'noimprime':
            lista = list(Reclamos_correo.objects.filter(eliminado='Activo')
                         .filter(created_date__range=[desde, hasta])
                         .filter(imprime='No')
                         .order_by('created_date').values())
        elif tipo == 'todo':
            lista = list(Reclamos_correo.objects.filter(eliminado='Activo')
                         .filter(created_date__range=[desde, hasta])
                         .order_by('created_date').values())
        df_recorreo = pd.DataFrame.from_records(lista)  # noqa
        df_recorreo = df_recorreo.drop('n_rec_correo', axis=1)
        df_recorreo = df_recorreo.drop('author_id', axis=1)
        df_recorreo = df_recorreo.drop('editor_id', axis=1)
        df_recorreo = df_recorreo.drop('updated_date', axis=1)
        df_recorreo = df_recorreo.drop('eliminado', axis=1)
        df_recorreo = df_recorreo.rename(columns={'created_date': 'Fecha', 'cuenta': 'Cuenta',
                                                  'calle': 'Calle', 'altura': 'Altura',
                                                  'observaciones': 'Observaciones', 'imprime': 'Imprime'})
        if tipo != 'todo':
            df_recorreo = df_recorreo.drop('Imprime', axis=1)
        df_recorreo['Fecha'] = df_recorreo['Fecha'].dt.tz_localize(None)
        df_recorreo['Fecha'] = df_recorreo['Fecha'].apply(lambda x: str(x)[:10])
        df_recorreo.to_excel(settings.MEDIA_ROOT + r'/tmp/Reclamos-correo_' + pre_desde + '-' + pre_hasta + '_' + tipo + '.xlsx',
                             index=False)
        return FileResponse(open(settings.MEDIA_ROOT + r'/tmp/Reclamos-correo_' + pre_desde + '-' + pre_hasta + '_' + tipo + '.xlsx', 'rb'),
                            content_type='application/txt', as_attachment=True)
    else:
        return render(request, 'herramientas/reporte_rec_correo.html')


@login_required
def desc_percibido(request):
    """Renderiza página p/ descarga de percibido."""
    if request.method == "POST":
        if str(request.POST['tabla']) == '':
            return render(request, 'herramientas/desc_percibido.html')
        try:
            tabla = int(request.POST["tabla"])
        except (ValueError, TypeError):
            return render(request, 'desc_percibido.html')
        archivo = proc_desc_percibido(tabla)
        return FileResponse(open(archivo, 'rb'),
                            content_type='application/txt', as_attachment=True)
    return render(request, 'herramientas/desc_percibido.html')
