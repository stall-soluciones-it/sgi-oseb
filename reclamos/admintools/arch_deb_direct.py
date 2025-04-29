# -*- coding: utf-8 -*-
"""
Created on Fri Jun  3 12:02:56 2022

@author: Daniel
"""
import os
import io
from decimal import Decimal
import psycopg2
import zipfile
import sgi.shpd_cnf as cnf
from django.conf import settings


# VARIABLES:
# fecha_vto_fc = '02082022'  # Se debita un día antes del 1er vto de la FC.
# id_cuota_pre = 'CUOTA072022'  # Siempre mayusculas.


# Func. para trabajar en sistema decimal:
def dec(numero):
    """Formato de numero decimal redondeado a dos decimales."""
    num = Decimal(numero)
    dos_decimales = Decimal("0.01")
    return num.quantize(dos_decimales)


def arch_enviar_bind(archivo, dia, mes, anio, id_cuota_pre, fecha_vto_fc):
    """Genero archivo p/ enviar a BIND."""
    error = False
    log = []

    # Creo listado PMC con el contenido del archivo de PMC.
    PMC = []
    try:
        ARCHIVO = archivo
        # name = os.path.basename(archivo)
        with open(ARCHIVO, 'rt') as in_file:
            for line in in_file:
                PMC.append(line.rstrip('\n'))
    except Exception as expt:
        log.append('Error al crear listado PMC a partir del archivo PMC: ' + repr(expt))
        error = True

    # Traigo datos de adheridos desde DB_SHPD:
    try:
        query = "SELECT cuenta_osebal, cbu FROM reclamos_debdirect WHERE eliminado IN ('Activo');"
        connection = psycopg2.connect(user=cnf.DB_SHPD_USR,
                                      password=cnf.DB_SHPD_PASS,
                                      host=cnf.DB_SHPD_HOST,
                                      port="5432",
                                      database="sgi_db")
        cursor = connection.cursor()
        cursor.execute(query)
        datos = cursor.fetchall()
    except Exception as expt:
        log.append('Error al obtener datos de tabla reclamos_debdirect: ' + repr(expt))
        error = True
    finally:
        if (connection):
            cursor.close()
            connection.close()
    CODELEC_MONTO = {}
    for line in PMC:
        CODELEC_MONTO[str(line[1:11])] = str(int(line[212:218])) + '.' + str(line[218:220])

    # Controlo CUENTAS DUPLICADAS.
    base_control = []
    for tup in datos:
        base_control.append(str(tup[0]))
    print(base_control)
    ctas_dup = list(set([x for x in base_control if base_control.count(x) > 1]))
    if ctas_dup:
        log.append('Cta. duplicada: ' + str(ctas_dup))
        error = True
    # Controlo formato de CBUs.
    base_control2 = []
    for tup in datos:
        base_control2.append(str(tup[1]))
    print(base_control2)
    for cbu in base_control2:
        if len(cbu) != 22:
            print(cbu)
            log.append('CBU con error: ' + str(cbu) + '\n')
            error = True

    # Creo lista DATOS = [cod_pag_elec, cuenta, cbu] (solo falta el monto)
    try:
        DATOS = []
        for tup in datos:
            pre_dato = ['001' + str(tup[0]).zfill(7), tup[0], tup[1]]
            # Agrego monto desde PMC.
            try:
                pre_dato.append(CODELEC_MONTO[pre_dato[0]])
                DATOS.append(pre_dato)
            except KeyError:
                pass
    except Exception as expt:
        log.append('Error al crear listado DATOS: ' + repr(expt))
        error = True

    # Creo listado LINEAS con lineas finales del archivo a enviar.
    LINEAS = []
    TOTAL = dec(0)
    CANT = 0
    for dato in DATOS:
        # Datos variables (pre)
        cbu_pre = dato[2]
        cuenta_oseb_pre = str(dato[1])
        importe_pre = dato[3]

        # Datos fijos
        tipo_novedad = 'D'
        cuit_oseb = '33717445509'
        sector = '001'
        prestacion = 'IMPUESTO  '
        vto_deb_orig = ''.zfill(8)
        id_cuota = id_cuota_pre.ljust(15)
        moneda = '80'
        otros_vtos = '00000000'
        imp_otros_vtos = ''.zfill(14)
        id_nuevo_pagador = ''.ljust(22)
        cod_rech = ''.ljust(3)
        n_orden = ''.zfill(10)
        n_mov = ''.zfill(10)
        filler = ''.ljust(54)
        zfiller = ''.zfill(18)

        # Datos variables
        vencimiento = str(int(fecha_vto_fc[0:2])).zfill(2) + fecha_vto_fc[2:]
        cbu = str(cbu_pre)[0:8] + '000' + str(cbu_pre)[8:]
        cuenta_osebal = str(cuenta_oseb_pre).rjust(22)
        importe = str(importe_pre).replace('.', '').zfill(14)

        linea = (tipo_novedad + cuit_oseb + sector + prestacion + vencimiento + cbu +
                 cuenta_osebal + vto_deb_orig + id_cuota + importe + moneda + otros_vtos +
                 imp_otros_vtos + zfiller + id_nuevo_pagador + cod_rech + n_orden + n_mov + filler)

        LINEAS.append(linea)
        CANT += 1
        TOTAL += dec(importe)

    # Footer archivo BIND
    FOOTER = ('T' + str(CANT).zfill(10) + str(CANT).zfill(7) + ''.zfill(7) +
              str(dia).zfill(2) + str(mes).zfill(2) + str(anio) + ''.ljust(70) +
              str(TOTAL / dec(100)).replace('.', '').zfill(14) + ''.ljust(137))
    LINEAS.append(FOOTER)
    # Creo listado de códigos de barra para el archivo a cargar en SISA.
    try:
        LINES_SISA = []
        for item in DATOS:
            for line in PMC:
                if item[0] == str(line[1:11]):
                    LINES_SISA.append(line[191:224].replace(' ', ''))
    except Exception as expt:
        log.append('Error al crear listado LINEAS_SISA: ' + repr(expt))
        error = True
    # Ceo encabezado para LINEAS_SISA:
    try:
        total = 0
        cantidad = len(LINES_SISA)
        for line in LINES_SISA:
            total += int(line[21:29])

        encabezado = ('99999' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2) +
                      '04000000004000' + str(dia).zfill(2) + str(mes).zfill(2) +
                      str(anio) + str(dia).zfill(2) + str(mes).zfill(2) + str(anio) +
                      str(total).zfill(16) + str(cantidad).zfill(8) + '00')
        LINES_SISA.insert(0, encabezado)
    except Exception as expt:
        log.append('Error al crear encabezado: ' + repr(expt))
        error = True

    try:
        # ESCRIBO EL NUEVO ARCHIVO BIND_SEND:
        with io.open(settings.MEDIA_ROOT + r'/tmp/' + 'DOSEBIMPUESTO' + str(dia).zfill(2) + str(mes).zfill(2) + '.txt', 'wt', newline='\r\n') as arch:
            for item in LINEAS:
                arch.write("%s\n" % item)
            arch.close()
    except Exception as expt:
        log.append('Error al crear el archivo DOSEBIMPUESTOddmm.txt: ' + repr(expt))
        error = True
    try:
        # ESCRIBO EL NUEVO ARCHIVO FAVA_SISA:
        with io.open(settings.MEDIA_ROOT + r'/tmp/' + 'BIND_SISA_' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2) + '.txt', 'wt', newline='\r\n') as arch:
            for item in LINES_SISA:
                arch.write("%s\n" % item)
            arch.close()
    except Exception as expt:
        log.append('Error al crear el archivo BIND_SISA: ' + repr(expt))
        error = True

    # Armo ZIP con archivos finales O LOG si error.
    if error is False:
        try:
            nombre = 'BIND_' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2)
            try:
                ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/' + nombre + '.zip',
                                           mode='x', compression=zipfile.ZIP_DEFLATED)
            except FileExistsError:
                os.remove(settings.MEDIA_ROOT + r'/tmp/' + nombre + '.zip')
                ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/' + nombre + '.zip',
                                           mode='x', compression=zipfile.ZIP_DEFLATED)
            ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/' + 'DOSEBIMPUESTO' + str(dia).zfill(2) + str(mes).zfill(2) + '.txt',
                           os.path.basename(settings.MEDIA_ROOT + r'/tmp/' + 'DOSEBIMPUESTO' + str(dia).zfill(2) + str(mes).zfill(2) + '.txt'))
            ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/' + 'BIND_SISA_' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2) + '.txt',
                           os.path.basename(settings.MEDIA_ROOT +
                                            r'/tmp/' + 'BIND_SISA_' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2) + '.txt'))
            ARCH_ZIP.close()
            return settings.MEDIA_ROOT + r'/tmp/' + nombre + '.zip'
        except Exception as expt:
            log.append('Error al crear archivos finales: ' + repr(expt))
            error = True

    elif error is True:
        with io.open(settings.MEDIA_ROOT + r'/tmp/Log_' + str(anio) + str(mes).zfill(2) + '.txt',
                     'wt', newline='\r\n') as log_arch:
            log_arch.write('\n'.join(log))
        return settings.MEDIA_ROOT + r'/tmp/Log_' + str(anio) + str(mes).zfill(2) + '.txt'
