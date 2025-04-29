# -*- coding: utf-8 -*-
"""
@Shepherd.

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


def arch_enviar_fava(archivo, dia, mes, anio):
    """Genero archivo p/ enviar a FAVA."""
    error = False
    log = []

    # Creo listado LINES con el contenido del archivo de PMC.
    LINES = []
    try:
        ARCHIVO = archivo
        # name = os.path.basename(archivo)
        with open(ARCHIVO, 'rt') as in_file:
            for line in in_file:
                LINES.append(line.rstrip('\n'))
    except Exception as expt:
        log.append('Error al crear listado LINES a partir del archivo PMC: ' + repr(expt))
        error = True

    # Traigo datos de adheridos desde DB_SHPD:
    try:
        query = "SELECT cuenta_osebal, tarjeta_fava FROM reclamos_fava WHERE eliminado IN ('Activo');"
        connection = psycopg2.connect(user=cnf.DB_SHPD_USR,
                                      password=cnf.DB_SHPD_PASS,
                                      host=cnf.DB_SHPD_HOST,
                                      port="5432",
                                      database="sgi_db")
        cursor = connection.cursor()
        cursor.execute(query)
        datos = cursor.fetchall()
    except Exception as expt:
        log.append('Error al obtener datos de tabla reclamos_fava: ' + repr(expt))
        error = True
    finally:
        if (connection):
            cursor.close()
            connection.close()

    # Creo dic {'COD_PAGO_ELEC': 'linea archivo enviar FAVA (solo falta el monto)'}
    try:
        lineas = {}
        for tup in datos:
            lineas['001' + str(tup[0]).zfill(7)] = '0401738200,' + str(tup[1]) + ',' + str(tup[0]) + ','
        # Agrego el monto a todas las lineas creadas en el paso anterior.
        for key, value in lineas.items():
            for line in LINES:
                if key == str(line[1:11]):
                    lineas[key] += str(int(line[212:218])) + '.' + str(line[218:220])
        # Creo listado final para crear el archivo ENVIAR FAVA.
        LINES_SEND = []
        for _, value in lineas.items():
            LINES_SEND.append(value)
    except Exception as expt:
        log.append('Error al crear listado LINEAS_SEND: ' + repr(expt))
        error = True

    # Creo listado de códigos de barra para el archivo a cargar en SISA.
    try:
        LINES_SISA = []
        for key, value in lineas.items():
            for line in LINES:
                if key == str(line[1:11]):
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
                      '03000000003000' + str(dia).zfill(2) + str(mes).zfill(2) +
                      str(anio) + str(dia).zfill(2) + str(mes).zfill(2) + str(anio) +
                      str(total).zfill(16) + str(cantidad).zfill(8) + '00')
    except Exception as expt:
        log.append('Error al crear encabezado: ' + repr(expt))
        error = True
    LINES_SISA.insert(0, encabezado)

    try:
        # ESCRIBO EL NUEVO ARCHIVO FAVA_SEND:
        with io.open(settings.MEDIA_ROOT + r'/tmp/' + 'DEBITOS_' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2) + '.txt', 'wt', newline='\r\n') as arch:
            for item in LINES_SEND:
                arch.write("%s\n" % item)
            arch.close()
    except Exception as expt:
        log.append('Error al crear el archivo FAVA_SEND: ' + repr(expt))
        error = True
    try:
        # ESCRIBO EL NUEVO ARCHIVO FAVA_SISA:
        with io.open(settings.MEDIA_ROOT + r'/tmp/' + 'FAVA_SISA_' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2) + '.txt', 'wt', newline='\r\n') as arch:
            for item in LINES_SISA:
                arch.write("%s\n" % item)
            arch.close()
    except Exception as expt:
        log.append('Error al crear el archivo FAVA_SISA: ' + repr(expt))
        error = True

    # Armo ZIP con archivos finales O LOG si error.
    if error is False:
        try:
            nombre = 'FAVA_' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2)
            try:
                ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/' + nombre + '.zip',
                                           mode='x', compression=zipfile.ZIP_DEFLATED)
            except FileExistsError:
                os.remove(settings.MEDIA_ROOT + r'/tmp/' + nombre + '.zip')
                ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/' + nombre + '.zip',
                                           mode='x', compression=zipfile.ZIP_DEFLATED)
            ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/' + 'DEBITOS_' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2) + '.txt',
                           os.path.basename(settings.MEDIA_ROOT + r'/tmp/' + 'DEBITOS_' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2) + '.txt'))
            ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/' + 'FAVA_SISA_' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2) + '.txt',
                           os.path.basename(settings.MEDIA_ROOT +
                                            r'/tmp/' + 'FAVA_SISA_' + str(anio) + str(mes).zfill(2) + str(dia).zfill(2) + '.txt'))
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
