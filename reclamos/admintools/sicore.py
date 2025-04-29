# -*- coding: utf-8 -*-
"""@Shepherd."""
import os
import io
import zipfile
from django.conf import settings


def process_sicore(quincena1, archivo1, archivo2, name1, name2):
    """Filtra archivo SICORE descargado de SISA."""
    error = False
    log = []
    LINES1 = []
    LINES2 = []
    final1 = []
    final2 = []
    cuits = {}
    if quincena1 == 1:
        quincena = 15
    elif quincena1 == 2:
        quincena = 16
    else:
        log.append('El valor para quincena debe ser 1 ó 2.')
        error = True
    try:
        ARCHIVO1 = archivo1
        with open(ARCHIVO1, 'rt') as in_file:
            for line in in_file:
                LINES1.append(line.rstrip('\n'))
    except Exception as expt:
        log.append('Error al crear listado LINES1 a partir del archivo original: ' + repr(expt))
        error = True
    try:
        ARCHIVO2 = archivo2
        with open(ARCHIVO2, 'rt') as in_file:
            for line in in_file:
                if line not in LINES2:
                    LINES2.append(line.rstrip('\n'))
    except Exception as expt:
        log.append('Error al crear listado LINES2 a partir del archivo original: ' + repr(expt))
        error = True
    # FILTRO LINEAS:
    # Creo dic con arch. datos:
    try:
        for line in LINES2:
            cuits[line[0:11]] = line
        # Creo listados finales para arch1 y arch2
        for line in LINES1:
            if quincena == 15:
                if int(line[61:63]) <= quincena:
                    final1.append(line)
                    final2.append(cuits[line[105:116]])
            elif quincena == 16:
                if int(line[61:63]) >= quincena:
                    final1.append(line)
                    final2.append(cuits[line[105:116]])
    except Exception as expt:
        log.append('Error al crear diccionario: ' + repr(expt))
        error = True
    # COMPRUEBO SI HAY RETENCIONES EN LA QUINCENA SELECCIONADA:
    if len(final1) == 0:
        log.append('NO HAY RETENCIONES PARA EL PERIODO SELECCIONADO.')
        error = True
    # ESCRIBO NUEVOS ARCHIVOS (SOLO SI HAY RETENCIONES):
    else:
        try:
            nombre = final1[0][8:12] + final1[0][5:7] + str(quincena1)
            with io.open(settings.MEDIA_ROOT + r'/sicore/' + nombre + '_' + name1,
                         'wt', newline='\r\n') as arch1:
                arch1.write('\n'.join(final1))

            with io.open(settings.MEDIA_ROOT + r'/sicore/' + nombre + '_' + name2,
                         'wt', newline='\r\n') as arch2:
                arch2.write('\n'.join(final2))
        except Exception as expt:
            log.append('Error al crear los archivos: ' + repr(expt))
            error = True

        try:
            os.remove(settings.MEDIA_ROOT + r'/sicore/sicore_' + nombre + '.zip')
        except Exception as expt:
            log.append(repr(expt))

        try:
            ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/sicore/sicore_' + nombre + '.zip',
                                       mode='x', compression=zipfile.ZIP_DEFLATED)
            ARCH_ZIP.write(settings.MEDIA_ROOT + r'/sicore/' + nombre + '_' + name1,
                           os.path.basename(settings.MEDIA_ROOT + r'/sicore/'
                                            + nombre + '_' + name1))
            ARCH_ZIP.write(settings.MEDIA_ROOT + r'/sicore/' + nombre + '_' + name2,
                           os.path.basename(settings.MEDIA_ROOT + r'/sicore/'
                                            + nombre + '_' + name2))
            ARCH_ZIP.close()
        except Exception as expt:
            log.append('Error al crear zip final: ' + repr(expt))
            error = True
    if error is False:
        return settings.MEDIA_ROOT + r'/sicore/sicore_' + nombre + '.zip'
    elif error is True:
        with io.open(settings.MEDIA_ROOT + r'/sicore/Log_' + 'error' + '.txt',
                     'wt', newline='\r\n') as log_arch:
            log_arch.write('\n'.join(log))
        return settings.MEDIA_ROOT + r'/sicore/Log_' + 'error' + '.txt'
