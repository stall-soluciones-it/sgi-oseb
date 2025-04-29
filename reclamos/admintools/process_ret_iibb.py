# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 11:15:02 2020.

@author: Daniel
"""
import os
import io
import zipfile
import hashlib
import pymysql
import sgi.shpd_cnf as cnf
from django.conf import settings


def md5(fname):
    """Genero hash."""
    hash_md5 = hashlib.md5()
    with open(fname, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return str(hash_md5.hexdigest()).upper()


def process_ret_iibb(anio, mes, quincena1):
    """Procesa rendición de ret. de IIBB."""
    log = []
    try:
        anio = int(anio)
        mes = int(mes)
        quincena1 = int(quincena1)
        if 2017 <= anio <= 2040:
            pass
        else:
            log.append('ERROR: El año "' + str(anio) + '" es incorrecto.')
        if 1 <= mes <= 12:
            pass
        else:
            log.append('ERROR: El mes "' + str(mes) + '" es incorrecto.')
        if 1 <= quincena1 <= 2:
            pass
        else:
            log.append('ERROR: La quincena "' + str(quincena1) + '" es incorrecta.')

        if quincena1 == 1:
            quincena = 15
        elif quincena1 == 2:
            quincena = 16
    except Exception as expt:
        log.append('Error en valores de periodo: ' + repr(expt))
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT cuit, fecha, sucursal, numero, imp_ret FROM z20ret_igb"
                 + " WHERE estado = 'C'"
                 + " ORDER BY cuit ASC, fecha ASC;")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as expt:
        log.append('Error en conexión a DB: ' + repr(expt))

    try:
        FINAL = []
        for dic in datos:
            if int(str(dic['fecha'])[0:4]) == anio:
                if int(str(dic['fecha'])[5:7]) == mes:
                    if quincena == 15:
                        if int(str(dic['fecha'])[8:10]) <= quincena:
                            FINAL.append(str(dic['cuit'])[0:2] + '-' + str(dic['cuit'])[2:10] + '-'
                                         + str(dic['cuit'])[10] + str(dic['fecha'])[8:10] + r'/'
                                         + str(dic['fecha'])[5:7] + r'/' + str(dic['fecha'])[0:4]
                                         + str(dic['sucursal']).zfill(4)
                                         + str(dic['numero']).zfill(8)
                                         + str(dic['imp_ret']).zfill(11) + 'A')
                    elif quincena == 16:
                        if int(str(dic['fecha'])[8:10]) >= quincena:
                            FINAL.append(str(dic['cuit'])[0:2] + '-' + str(dic['cuit'])[2:10] + '-'
                                         + str(dic['cuit'])[10] + str(dic['fecha'])[8:10] + r'/'
                                         + str(dic['fecha'])[5:7] + r'/' + str(dic['fecha'])[0:4]
                                         + str(dic['sucursal']).zfill(4)
                                         + str(dic['numero']).zfill(8)
                                         + str(dic['imp_ret']).zfill(11) + 'A')
    except Exception as expt:
        log.append('Error en la creación del listado final: ' + repr(expt))

    NAME = 'AR-30677286314-' + str(anio) + str(mes).zfill(2) + str(quincena1) + '-6-LOTE1'

    try:
        with io.open(settings.MEDIA_ROOT + r'/tmp/'
                     + NAME + '.txt', 'wt', newline='\r\n') as archivo:
            archivo.write('\n'.join(FINAL))

        try:
            ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/ret_iibb/' + NAME + '.zip',
                                       mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/ret_iibb/' + NAME + '.zip')
            ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/ret_iibb/' + NAME + '.zip',
                                       mode='x', compression=zipfile.ZIP_DEFLATED)
        ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/' + NAME + '.txt',
                       os.path.basename(settings.MEDIA_ROOT + r'/tmp/' + NAME + '.txt'))
        ARCH_ZIP.close()

        md5str = str(md5(settings.MEDIA_ROOT + r'/ret_iibb/' + NAME + '.zip'))

        os.rename(settings.MEDIA_ROOT + r'/ret_iibb/' + NAME + '.zip',
                  settings.MEDIA_ROOT + r'/ret_iibb/' + NAME + '_' + md5str + '.zip')
        os.remove(settings.MEDIA_ROOT + r'/tmp/' + NAME + '.txt')
    except Exception as expt:
        log.append('Error al crear archivo: ' + repr(expt))

    if log:
        with io.open(settings.MEDIA_ROOT + r'/ret_iibb/' + 'Log_' + NAME
                     + '.txt', 'wt', newline='\r\n') as logarch:
            logarch.write('\n'.join(log))
        return settings.MEDIA_ROOT + r'/ret_iibb/' + 'Log_' + NAME + '.txt'
    else:
        return settings.MEDIA_ROOT + r'/ret_iibb/' + NAME + '_' + md5str + '.zip'
