# -*- coding: utf-8 -*-
"""
@Shepherd.

v2_prod: Usa dos archivos; archivo original de PMC (ubicado en la carpeta /Archivos) y
         el archivo "H:/PARA IMPRESION/Sin_Servicio.csv" para generar el filtro de unidades
         a quitar.
v3_prod: Se arreglaron bugs.
v4_prod: Se agregó func dc() para trabajar en sistema decimal.
"""
import os
import io
from decimal import Decimal
import psycopg2
import zipfile
import sgi.shpd_cnf as cnf
from django.conf import settings


# Func. para trabajar en sistema decimal:
def dec(numero):
    """Formato de numero decimal redondeado a dos decimales."""
    num = Decimal(numero)
    dos_decimales = Decimal("0.01")
    return num.quantize(dos_decimales)


def process_filtro_pmc(anio, mes, archivo):
    """Filtro archivo PMC."""
    error = False
    log = []
    LINES = []
    try:
        ARCHIVO = archivo
        name = str(os.path.basename(archivo)).replace('FAC0296.', 'FACOSEB.')
        with open(ARCHIVO, 'rt') as in_file:
            for line in in_file:
                LINES.append(line.rstrip('\n'))
    except Exception as expt:
        log.append('Error al crear listado LINES a partir del archivo original: ' + repr(expt))
        error = True

    # CREO FILTRO:
    try:
        query = "SELECT unidad FROM per" + str(anio) + str(mes).zfill(2) + ";"
        connection = psycopg2.connect(user=cnf.DB_SHPD_USR,
                                      password=cnf.DB_SHPD_PASS,
                                      host=cnf.DB_SHPD_HOST,
                                      port="5432",
                                      database="external_data")
        cursor = connection.cursor()
        cursor.execute(query)
        datos = cursor.fetchall()
    except Exception as expt:
        log.append('Error al obtener "Sin servicio": ' + repr(expt))
        error = True
    finally:
        if (connection):
            cursor.close()
            connection.close()
    try:
        FILTRO = []
        for tup in datos:
            FILTRO.append(int(tup[0]))
    except Exception as expt:
        log.append('Error al crear el filtro: ' + repr(expt))
        error = True
    # SEPARO ENCABEZADO Y PIE DEL CONTENIDO:
    try:
        FIRST = LINES[0].replace('0296', 'OSEB')
        LAST = LINES[-1].replace('0296', 'OSEB')
        del LINES[0]
        del LINES[-1]
    except Exception as expt:
        log.append('Error al trabajar el contenido del archivo: ' + repr(expt))
        error = True

    # APLICO EL FILTRO:
    try:
        CONTENT = []
        FILTRADO = []
        for line in LINES:
            mont = int(line[70:79])
            mont_cod = int(line[212:220])
            if (int(line[4:11]) not in FILTRO) and ( mont == mont_cod):
                CONTENT.append(line)
            else:
                log.append(str(mont) + '-' + str(mont_cod))
                FILTRADO.append(line)
    except Exception as expt:
        log.append('Error al aplicar filtro: ' + repr(expt))
        error = True
    # CONTROL DE VALORES Y CANTIDAD:
    try:
        TOTAL_ORIGINAL = dec(0)
        for line in LINES:
            TOTAL_ORIGINAL += dec(line[212:220]) / dec(100)

        TOTAL_CONTENT = dec(0)
        for line in CONTENT:
            TOTAL_CONTENT += dec(line[212:220]) / dec(100)

        TOTAL_FILTRADO = dec(0)
        for line in FILTRADO:
            TOTAL_FILTRADO += dec(line[212:220]) / dec(100)

        CANT_FILE = int(LAST[17:23])
        MONTO_FILE = dec(int(LAST[26:41])) / dec(100)
    except Exception as expt:
        log.append('Error al calcular totales: ' + repr(expt))
        error = True

    try:
        log.append('')
        log.append('Cantidad de facturas según archivo original: ' + str(CANT_FILE))
        log.append('Cantidad de facturas (original): ' + str(len(LINES)))
        log.append('Cantidad de facturas (a enviar): ' + str(len(CONTENT)))
        log.append('Cantidad de facturas (filtrado): ' + str(len(FILTRADO)))
        log.append('Suma de montos según archivo original: ' + str(MONTO_FILE))
        log.append('Suma de montos (original): ' + str(TOTAL_ORIGINAL))
        log.append('Suma de montos (a enviar): ' + str(TOTAL_CONTENT))
        log.append('Suma de montos (filtrado): ' + str(TOTAL_FILTRADO))
        if CANT_FILE == len(LINES):
            if (len(CONTENT) + len(FILTRADO)) == CANT_FILE:
                log.append('-> Comprobación de cantidades exitosa!')
        else:
            log.append('-> Error en comprobación de cantidades!')
        if MONTO_FILE == TOTAL_ORIGINAL:
            if TOTAL_CONTENT + TOTAL_FILTRADO == TOTAL_ORIGINAL:
                log.append('-> Comprobación de montos exitosa!')
        else:
            log.append('-> Error en comprobación de montos!')
        for line in FILTRADO:
            log.append(line)
    except Exception as expt:
        log.append('Error al insertar lineas finales al log: ' + repr(expt))
        error = True
    # CREO NUEVO PIE:
    try:
        NEW_LAST = (LAST.replace(LAST[17:23],
                                 str(len(CONTENT)).zfill(6))).replace(LAST[26:46],
                                                                      str(int(TOTAL_CONTENT *
                                                                              100)).zfill(20))
        # ESCRIBO EL NUEVO ARCHIVO:
        with io.open(settings.MEDIA_ROOT + r'/filtro_pmc/' + name, 'wt', newline='\r\n') as arch:
            arch.write(FIRST + '\n')
            for item in CONTENT:
                arch.write("%s\n" % item)
            arch.write(NEW_LAST)
            arch.close()
    except Exception as expt:
        log.append('Error al crear el archivo final: ' + repr(expt))
        error = True

    with io.open(settings.MEDIA_ROOT + r'/filtro_pmc/Log_' + str(anio) + str(mes).zfill(2) + '.txt',
                 'wt', newline='\r\n') as log_arch:
        log_arch.write('\n'.join(log))

    if error is False:
        try:
            try:
                ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/filtro_pmc/' + name + '.zip',
                                           mode='x', compression=zipfile.ZIP_DEFLATED)
            except FileExistsError:
                os.remove(settings.MEDIA_ROOT + r'/filtro_pmc/' + name + '.zip')
                ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/filtro_pmc/' + name + '.zip',
                                           mode='x', compression=zipfile.ZIP_DEFLATED)
            ARCH_ZIP.write(settings.MEDIA_ROOT + r'/filtro_pmc/' + name,
                           os.path.basename(settings.MEDIA_ROOT + r'/filtro_pmc/' + name))
            ARCH_ZIP.write(settings.MEDIA_ROOT + r'/filtro_pmc/Log_' + str(anio) + str(mes).zfill(2) +
                           '.txt', os.path.basename(settings.MEDIA_ROOT +
                                                    r'/filtro_pmc/Log_' + str(anio) +
                                                    str(mes).zfill(2) + '.txt'))
            ARCH_ZIP.close()
            return settings.MEDIA_ROOT + r'/filtro_pmc/' + name + '.zip'
        except Exception as expt:
            log.append('Error al crear archivos finales: ' + repr(expt))
            error = True

    if error is True:
        return settings.MEDIA_ROOT + r'/filtro_pmc/Log_' + str(anio) + str(mes).zfill(2) + '.txt'
