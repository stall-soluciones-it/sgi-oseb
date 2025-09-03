# -*- coding: utf-8 -*-
"""@Shepherd."""
import os
import io
import zipfile
import re
from datetime import datetime
import calendar
from pymysql import connect, cursors
import unicodedata
import sgi.shpd_cnf as cnf
from django.conf import settings

def clean_txt(texto):
    # Normalizar para manejar acentos correctamente
    texto_norm = unicodedata.normalize('NFD', texto)
    texto_sin_acentos = ''.join(char for char in texto_norm if unicodedata.category(char) != 'Mn')
    # Mantener solo letras, números, espacios puntos y guiones
    return re.sub(r'[^a-zA-Z0-9\s\.-]', '', texto_sin_acentos)


def process_sicore(quincena, mes, anio):
    """Filtra archivo SICORE descargado de SISA."""
    error = False
    log = []

    if quincena == 1:
        desde = f"{anio:04d}-{mes:02d}-01"
        hasta = f"{anio:04d}-{mes:02d}-15"
    elif quincena == 2:
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        desde = f"{anio:04d}-{mes:02d}-16"
        hasta = f"{anio:04d}-{mes:02d}-{ultimo_dia:02d}"

    # Abrir una sola conexión para todas las consultas
    connection = connect(host=cnf.DB_OSEBAL_HOST,
                         user=cnf.DB_SISA_USR,
                         password=cnf.DB_SISA_PASS,
                         db='osebal_produccion',
                         charset='utf8mb4',
                         cursorclass=cursors.DictCursor)

    try:
        cursor = connection.cursor()
        
        # Consulta 1: Traigo Nº de OPs a procesar
        query = f"SELECT num_com \
                FROM mov_ren \
                WHERE tpo_com = 'OP' \
                AND categoria = '3' \
                AND fecha BETWEEN '{desde}' AND '{hasta}';"
        cursor.execute(query)
        ops_mov_ren = cursor.fetchall()
        
        num_ops = [str(dic['num_com']) for dic in ops_mov_ren]
        num_ops_str = ", ".join(num_ops)

        # Consulta 2: Traigo datos de z20ret_gan
        query = f"SELECT z20.fecha, z20.num_ord_pag, z20.imp_acu_ret, z20.ret_pag, \
                z20.cuit, z20.numero, z20.proveedor, z10.reg_dgi \
                FROM z20ret_gan z20 \
                LEFT JOIN z10con_gan z10 ON z20.con_gan = z10.con_gan \
                WHERE z20.num_ord_pag IN ({num_ops_str});"
        cursor.execute(query)
        data_z20ret_gan = cursor.fetchall()

        # Consulta 3: Traigo datos de mov_ren
        query = f"SELECT num_com, imp_bas, fecha \
                FROM mov_ren \
                WHERE tpo_com = 'OP' \
                AND categoria = '3' \
                AND num_com in ({num_ops_str});"
        cursor.execute(query)
        data_mov_ren = cursor.fetchall()
        
        dic_mov_ren = {int(dic['num_com']): [dic['imp_bas'], dic['fecha']] 
                       for dic in data_mov_ren}

        # Consulta 4: Traigo datos de z10provincia
        query = "SELECT provincia, cod_pcia_dgi FROM z10provincia;"
        cursor.execute(query)
        data_z10provincia = cursor.fetchall()
        
        provincias = {dic['provincia']: str(dic['cod_pcia_dgi']) 
                      for dic in data_z10provincia}

        # Preparar lista de proveedores para la siguiente consulta
        n_proveedores = [dic['proveedor'] for dic in data_z20ret_gan]
        n_proveedores_str = ", ".join(map(str, n_proveedores))

        # Consulta 5: Traigo datos de z10proveedor
        query = f"SELECT proveedor, cuit, descripcion, direccion, localidad, cod_pos, provincia \
                FROM z10proveedor \
                WHERE proveedor IN ({n_proveedores_str});"
        cursor.execute(query)
        data_z10proveedor = cursor.fetchall()
        
        proveedores = {}
        for dic in data_z10proveedor:
            proveedores[dic['proveedor']] = {
                'cuit': dic['cuit'],
                'descripcion': dic['descripcion'],
                'direccion': dic['direccion'],
                'localidad': dic['localidad'],
                'cod_pos': dic['cod_pos'],
                'provincia': dic['provincia']
            }

    finally:
        # Cerrar cursor y conexión al final
        cursor.close()
        connection.close()

    # AAAAMMQ_OSEBAL_scomp_retQMMAA.txt
    arch_comp = []
    for dic in data_z20ret_gan:
        cod_comp = '6 '  # fijo
        fec_emi_com = datetime.strptime(str(dic['fecha']), "%Y-%m-%d").strftime("%d/%m/%Y")  # 'DD/MM/YYYY' fecha.z20ret_gan
        num_com = str(dic['num_ord_pag'])[:16].zfill(16)  # '0000000000009959' num_ord_pag.z20ret_gan
        imp_com = str(dic_mov_ren[dic['num_ord_pag']][0]).replace('-', '')[:16].rjust(16)  # '       505992.17'  # imp_bas.mov_ren
        cod_imp = '0217'  # fijo
        cod_reg = str(dic['reg_dgi']).split("/")[0].zfill(3)  # '078' (z10con_gan 03) = Loc. obra = ("94" en z20ret_gan)
        cod_op = '1'  # fijo
        base_calc = str(dic['imp_acu_ret'])[:14].rjust(14)  # '     418175.35' # imp_acu_ret.z20ret_gan 
        fec_emi_ret = fec_emi_com  #  datetime.strptime(str(dic_mov_ren[dic['num_ord_pag']][1]), "%Y-%m-%d").strftime("%d/%m/%Y")  # '01/07/2025' # fecha.mov_ren
        cod_con = '01' #  fijo
        ret_prac = '0'  # fijo
        imp_ret = str(dic['ret_pag'])[:14].rjust(14)  # '       3883.51'  # ret_pag.z20ret_gan
        perc_exc = '  0.00' # fijo
        fec_pub = '          ' # fijo
        tpo_doc = '80' # fijo
        num_doc = str(dic['cuit'])[:20].zfill(20)  # '00000000030717406881'  # cuit.z20ret_gan
        num_cert = str(dic['numero'])[:14].zfill(14)  # '00000000000821'  # numero.z20ret_gan
        linea_comp = f"{cod_comp}{fec_emi_com}{num_com}{imp_com}{cod_imp}{cod_reg}{cod_op}{base_calc}{fec_emi_ret}{cod_con}{ret_prac}{imp_ret}{perc_exc}{fec_pub}{tpo_doc}{num_doc}{num_cert}"
        arch_comp.append(linea_comp)

    # AAAAMMQ_OSEBAL_ssuj_retQMMAA.txt
    arch_suj = []
    for dic in data_z20ret_gan:
        proveedor = dic['proveedor']
        n_doc = str(proveedores[proveedor]['cuit'])[:11].ljust(11)  # '30717406881' cuit.z10proveedor
        razon = clean_txt(str(proveedores[proveedor]['descripcion']))[:20].ljust(20)  # 'TODO BOMBAS SRL     ' z10proveedor.descripcion
        domicilio = clean_txt(str(proveedores[proveedor]['direccion']))[:20].ljust(20)  # 'AV. COLON N  6821   ' z10proveedor.direccion
        localidad = clean_txt(str(proveedores[proveedor]['localidad']))[:20].ljust(20)  # 'MAR DEL PLATA       ' z10proveedor.localidad
        provincia = provincias[str(proveedores[proveedor]['provincia'])][:2].zfill(2)  # '01' z10provincia (BA, CA...)
        cod_pos = clean_txt(str(proveedores[proveedor]['cod_pos']))[:8].ljust(8)  # '7600    ' z10proveedor.cod_pos
        tipo_doc = '80'  # fijo
        linea_suj = f"{n_doc}{razon}{domicilio}{localidad}{provincia}{cod_pos}{tipo_doc}"
        arch_suj.append(linea_suj)

    # Generar nombres de archivo basados en las fechas
    fecha_desde_obj = datetime.strptime(desde, "%Y-%m-%d")
    fecha_hasta_obj = datetime.strptime(hasta, "%Y-%m-%d")
    
    # Formato AAAAMMDD para identificar el período
    periodo_desde = fecha_desde_obj.strftime("%Y%m%d")
    periodo_hasta = fecha_hasta_obj.strftime("%Y%m%d")
    
    nombre_comp = f"{periodo_desde}_{periodo_hasta}_OSEBAL_scomp_ret.txt"
    nombre_suj = f"{periodo_desde}_{periodo_hasta}_OSEBAL_ssuj_ret.txt"

    # COMPRUEBO SI HAY RETENCIONES EN LA QUINCENA SELECCIONADA:
    if len(arch_comp) == 0:
        log.append('NO HAY RETENCIONES PARA EL PERIODO SELECCIONADO.')
        error = True

    # ESCRIBO NUEVOS ARCHIVOS (SOLO SI HAY RETENCIONES):
    else:
        try:
            with io.open(settings.MEDIA_ROOT + r'/sicore/' + nombre_comp,
                         'wt', newline='\r\n') as arch1:
                arch1.write('\n'.join(arch_comp) + '\n')

            with io.open(settings.MEDIA_ROOT + r'/sicore/' + nombre_suj,
                         'wt', newline='\r\n') as arch2:
                arch2.write('\n'.join(arch_suj) + '\n')
        except Exception as expt:
            log.append('Error al crear los archivos: ' + repr(expt))
            error = True

        try:
            os.remove(settings.MEDIA_ROOT + r'/sicore/sicore_' + f'{periodo_desde}_{periodo_hasta}' + '.zip')
        except Exception as expt:
            log.append(repr(expt))

        try:
            ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/sicore/sicore_' + f'{periodo_desde}_{periodo_hasta}' + '.zip',
                                       mode='x', compression=zipfile.ZIP_DEFLATED)
            ARCH_ZIP.write(settings.MEDIA_ROOT + r'/sicore/' + nombre_comp,
                           os.path.basename(settings.MEDIA_ROOT + r'/sicore/'
                                            + nombre_comp))
            ARCH_ZIP.write(settings.MEDIA_ROOT + r'/sicore/' + nombre_suj,
                           os.path.basename(settings.MEDIA_ROOT + r'/sicore/'
                                            + nombre_suj))
            ARCH_ZIP.close()
        except Exception as expt:
            log.append('Error al crear zip final: ' + repr(expt))
            error = True
    if error is False:
        return settings.MEDIA_ROOT + r'/sicore/sicore_' + f'{periodo_desde}_{periodo_hasta}' + '.zip'
    elif error is True:
        with io.open(settings.MEDIA_ROOT + r'/sicore/Log_' + 'error' + '.txt',
                     'wt', newline='\r\n') as log_arch:
            log_arch.write('\n'.join(log) + '\n')
        return settings.MEDIA_ROOT + r'/sicore/Log_' + 'error' + '.txt'
