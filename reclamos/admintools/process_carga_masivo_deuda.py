# -*- coding: utf-8 -*-
"""@Shepherd."""
import os
import io
import datetime
from django.conf import settings


def process_carga_masivo_deuda(archivo):
    """Carga archivo masivo de deuda."""
    log = []
    hoy = datetime.datetime.now()
    nombre = (str(hoy.year) + '-' + str(hoy.month) + '-' + str(hoy.day) +
              '_' + str(hoy.hour) + '-' + str(hoy.minute).zfill(2))
    # DF PROVEEDORES Y DEUDA DE ADBSA
    try:
        os.remove(settings.MEDIA_ROOT + r'/proveedores/deuda_masivo.xls')
    except Exception as expt:
        log.append(repr(expt))

    try:
        os.renames(archivo, settings.MEDIA_ROOT + r'/proveedores/deuda_masivo.xls')
    except Exception as expt:
        log.append(repr(expt))

    if log:
        pass
    else:
        log.append('Archivo cargado correctamente!')

    with io.open(settings.MEDIA_ROOT + r'/proveedores/Log_' + nombre + '.txt',
                 'wt', newline='\r\n') as log_arch:
        log_arch.write('\n'.join(log))
    return settings.MEDIA_ROOT + r'/proveedores/Log_' + nombre + '.txt'
