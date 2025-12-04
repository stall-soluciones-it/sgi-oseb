# -*- coding: utf-8 -*-
"""@Shepherd."""
import os
import io
import datetime
import time
from django.conf import settings


def process_carga_masivo_deuda(archivo, fecha_masivo=None):
    """Carga archivo masivo de deuda.

    Args:
        archivo: Ruta del archivo temporal a procesar
        fecha_masivo: Fecha del masivo (datetime.date o datetime.datetime).
                     Si no se proporciona, usa la fecha actual.
    """
    log = []
    hoy = datetime.datetime.now()
    nombre = (str(hoy.year) + '-' + str(hoy.month) + '-' + str(hoy.day) +
              '_' + str(hoy.hour) + '-' + str(hoy.minute).zfill(2))

    # Convertir fecha_masivo a timestamp si se proporciona
    if fecha_masivo:
        # Si es datetime.date, convertir a datetime
        if isinstance(fecha_masivo, datetime.date) and not isinstance(fecha_masivo, datetime.datetime):
            fecha_masivo = datetime.datetime.combine(fecha_masivo, datetime.time())
        timestamp = time.mktime(fecha_masivo.timetuple())
    else:
        timestamp = None

    # DF PROVEEDORES Y DEUDA DE ADBSA
    archivo_destino = settings.MEDIA_ROOT + r'/proveedores/deuda_masivo.xls'

    try:
        os.remove(archivo_destino)
    except Exception as expt:
        log.append(repr(expt))

    try:
        os.renames(archivo, archivo_destino)
    except Exception as expt:
        log.append(repr(expt))
        with io.open(settings.MEDIA_ROOT + r'/proveedores/Log_' + nombre + '.txt',
                     'wt', newline='\r\n') as log_arch:
            log_arch.write('\n'.join(log))
        return settings.MEDIA_ROOT + r'/proveedores/Log_' + nombre + '.txt'

    # Establecer fecha de modificación del archivo si se proporcionó
    if timestamp:
        try:
            os.utime(archivo_destino, (timestamp, timestamp))
            log.append('Archivo cargado correctamente!')
            log.append(f'Fecha del masivo establecida: {fecha_masivo.strftime("%Y-%m-%d %H:%M:%S")}')
        except Exception as expt:
            log.append('Archivo cargado pero hubo un error al establecer la fecha:')
            log.append(repr(expt))
    else:
        log.append('Archivo cargado correctamente!')

    with io.open(settings.MEDIA_ROOT + r'/proveedores/Log_' + nombre + '.txt',
                 'wt', newline='\r\n') as log_arch:
        log_arch.write('\n'.join(log))
    return settings.MEDIA_ROOT + r'/proveedores/Log_' + nombre + '.txt'
