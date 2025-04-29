# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 13:22:35 2020.

@author: Daniel
"""
import os
import io
import datetime
import psycopg2
import pymysql
import zipfile
import sgi.shpd_cnf as cnf
from django.conf import settings


hoy = datetime.datetime.today()


def process_alta_incob():
    """Busca cambios en incobrables para dar de alta."""
    log = []
    # CREO FILTRO:
    try:
        print('Consulta DB postrgesql para crear filtro')
        connection = psycopg2.connect(user=cnf.DB_SHPD_USR,
                                      password=cnf.DB_SHPD_PASS,
                                      host=cnf.DB_SHPD_HOST,
                                      port="5432",
                                      database="external_data")
        cursor = connection.cursor()
        query = "SELECT unidad FROM incobrables;"
        cursor.execute(query)
        datos = cursor.fetchall()
    except Exception as expt:
        print(log.append('Error al obtener DB "Incobrables": ' + repr(expt)))
        
    finally:
        print('done')
        if (connection):
            cursor.close()
            connection.close()
    try:
        print('Creo listado filtro')
        incob_lst = []
        incob_str = ''
        for tup in datos:
            incob_lst.append(str(tup[0]))
            incob_str += str(tup[0]) + ', '
        incob_str += 'ult'
        incob_str = incob_str.replace(', ult', '')
        print('done')
    except Exception as expt:
        print(log.append('Error al crear el filtro: ' + repr(expt)))
    # No controlar:
    try:
        print('Consulto DB SISA z80servi')
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT unidad, cod_ser, fec_vig FROM z80servi"
                 + " WHERE unidad IN (" + incob_str + ")"
                 + " AND fec_vig_h IS NULL;")
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        final = []
        for dic in datos:
            final.append(str(dic['unidad']))
        print('done')
    except Exception as expt:
        print(log.append('Error al consultar DB z80servi y crear listado final: ' + repr(expt)))

    # Con plan de pagos:
    try:
        print('Consulto DB SISA "con plan de pago" z80pen_fac')
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT unidad FROM z80pen_fac"
                 + " WHERE unidad IN (" + incob_str + ")"
                 + " AND estado = 'P'"
                 + " AND cod_con = 'PP';")
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        final2 = []
        for dic in datos:
            if str(dic['unidad']) not in final2:
                if str(dic['unidad']) not in final:
                    final2.append(str(dic['unidad']))
        print('done')
    except Exception as expt:
        print(log.append('Error al consultar DB z80pen_fac y crear listado final2: ' + repr(expt)))

    # Ingresó pago:
    tablas = 200
    tablasok = 0
    final3 = []

    try:
        print('Itero z80cpd_pi buscando pagos')
        while tablasok != 2:
            try:
                connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                             user=cnf.DB_SISA_USR,
                                             password=cnf.DB_SISA_PASS,
                                             db='osebal_produccion',
                                             charset='utf8mb4',
                                             cursorclass=pymysql.cursors.DictCursor)
                cursor = pymysql.cursors.DictCursor(connection)
                query = ("SELECT unidad, fec_cob FROM z80cpd_pi_" + str(tablas).zfill(7)
                         + " WHERE unidad IN (" + incob_str + ")"
                         + " AND estado = 'C'"
                         + " AND cod_ser <> 'IRBC';")
                cursor.execute(query)
                datos = cursor.fetchall()
                cursor.close()
                connection.close()
                for dic in datos:
                    if str(dic['unidad']) not in final3:
                        if str(dic['unidad']) not in final:
                            final3.append(str(dic['unidad']))
                if datos:
                    tablasok += 1
                tablas -= 1
                print('tablasok', tablasok)
                print('tablas', tablas)
            except:
                tablas -= 1
                continue
        print('done')
    except Exception as expt:
        print(log.append('Error al traer tablas z80cpd_pi_### y crear listado final3:' + repr(expt)))

    try:
        print('Creo salida {}')
        salida = {}
        for item in final2:
            salida[item] = '{:<17}'.format('-Plan de pagos')
        for item in final3:
            if item in list(salida.keys()):
                salida[item] += '{:<17}'.format('-Ingresó pago')
            else:
                salida[item] = '                 ' + '{:<17}'.format('-Ingresó pago')
        lineas = []
        for key, value in salida.items():
            line = ''
            line += '{:<17}'.format(str(key))
            line += str(value)
            lineas.append(line)
        print('done')
    except Exception as expt:
        print(log.append('Error al crear dict salida o listado final lineas: ' + repr(expt)))

    # Incobrables pendientes:
    try:
        print('incob pend')
        pendientes = []
        for item in incob_lst:
            if item not in final:
                pendientes.append(item)
        total_pendientes = 'Total de unidades incobrables pendientes: ' + str(len(pendientes))
        pendientes.insert(0, total_pendientes)
        print('done')
    except Exception as expt:
        print(log.append('Error al crear listado de pendientes: ' + repr(expt)))

    # Creo archivos finales:
    try:
        with io.open(settings.MEDIA_ROOT + r'/tmp/'
                     + 'Altas_' + str(hoy.year) + str(hoy.month).zfill(2)
                     + str(hoy.day).zfill(2) + '.txt', 'wt', newline='\r\n') as archivo:
            archivo.write('\n'.join(lineas))

        with io.open(settings.MEDIA_ROOT + r'/tmp/'
                     + 'Pendientes_' + str(hoy.year) + str(hoy.month).zfill(2)
                     + str(hoy.day).zfill(2) + '.txt', 'wt', newline='\r\n') as archivo:
            archivo.write('\n'.join(pendientes))

        try:
            ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/'
                                       + 'Altas_' + str(hoy.year)
                                       + str(hoy.month).zfill(2)
                                       + str(hoy.day).zfill(2) + '.zip',
                                       mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/tmp/' + 'Altas_' + str(hoy.year)
                      + str(hoy.month).zfill(2) + str(hoy.day).zfill(2) + '.zip')
            ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/'
                                       + 'Altas_' + str(hoy.year)
                                       + str(hoy.month).zfill(2)
                                       + str(hoy.day).zfill(2) + '.zip',
                                       mode='x', compression=zipfile.ZIP_DEFLATED)

        ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/'
                       + 'Altas_' + str(hoy.year) + str(hoy.month).zfill(2)
                       + str(hoy.day).zfill(2) + '.txt',
                       os.path.basename(settings.MEDIA_ROOT + r'/tmp/'
                                        + 'Altas_' + str(hoy.year) + str(hoy.month).zfill(2)
                                        + str(hoy.day).zfill(2) + '.txt'))
        ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/'
                       + 'Pendientes_' + str(hoy.year) + str(hoy.month).zfill(2)
                       + str(hoy.day).zfill(2) + '.txt',
                       os.path.basename(settings.MEDIA_ROOT + r'/tmp/'
                                        + 'Pendientes_' + str(hoy.year) + str(hoy.month).zfill(2)
                                        + str(hoy.day).zfill(2) + '.txt'))
        ARCH_ZIP.close()

    except Exception as expt:
        print(log.append('Error al crear archivos finales: ' + repr(expt)))

    if log:
        with io.open(settings.MEDIA_ROOT + r'/tmp/'
                     + 'Log_altas_' + str(hoy.year) + str(hoy.month).zfill(2)
                     + str(hoy.day).zfill(2) + '.txt', 'wt', newline='\r\n') as archivo:
            archivo.write('\n'.join(log))
        return (settings.MEDIA_ROOT + r'/tmp/' + 'Log_altas_'
                + str(hoy.year) + str(hoy.month).zfill(2) + str(hoy.day).zfill(2) + '.txt')
    else:
        return (settings.MEDIA_ROOT + r'/tmp/' + 'Altas_'
                + str(hoy.year) + str(hoy.month).zfill(2) + str(hoy.day).zfill(2) + '.zip')
