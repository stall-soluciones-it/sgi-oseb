# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 16:25:42 2020.

@author: Daniel
"""
import datetime
import os
import io
import calendar
from decimal import Decimal as dc
import zipfile
import pymysql
import pandas as pd
import sgi.shpd_cnf as cnf
from django.conf import settings


def procesa_rbc(data_input):
    """Procesa el archivo TXT y devuelve ZIP con el CSV final y un log en TXT."""
    # Constantes:
    error = False
    salida = []
    date = ((str(datetime.datetime.now())[0:19]).replace(' ', '_')).replace(':', '-')
    linea1 = str('unidad|cod_ser|cod_con|fecha|medicion|fec_med|consumo|a_facturar|'
                 'pendiente|coeficiente|tpo_med|num_med|estado|tpo_aux|num_aux|numero|'
                 'transaccion|usu_act|fec_act|tpo_com|pre_com|num_com|sub_gpo_fac|per_has|')
    log = []
    monto_aguastxt = dc(0)
    monto_facturados = dc(0)
    log.append('Procesando archivo RBC.......')
    # MYQSL:
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ('SELECT unidad, unidad_alt FROM osebal_produccion.z80unidad;')
        cursor.execute(query)
        df = pd.DataFrame(cursor.fetchall())
        cursor.close()
        connection.close()
    except Exception as expt:
        log.append('Error en conexióna a DB de SISA: ' + repr(expt))
        error = True
    try:
        part_un = {}
        for _, row in df.iterrows():
            part_un[str(row['unidad_alt'])] = str(int(row['unidad']))
    except Exception as expt:
        log.append('Error al crear dic part_un: ' + repr(expt))
        error = True
    # CREA LINEAS DEL ARCHIVO FINAL A PARTIR DEL TXT ENVIADO POR MUNICIPALIDAD DEJANDO
    # SOLO LAS PARTIDAS CONTENIDAS EN LISTA UN_FACT.
    print(part_un)
    try:
        lines = []
        try:
            with open(data_input, 'rt') as in_file:
                for line in in_file:
                    if line != '\n':
                        lines.append(line.replace('\n', ''))
        except UnicodeDecodeError:
            lines = []
            with open(data_input, 'rt', encoding='ISO8859-1') as in_file:
                for line in in_file:
                    if line != '\n':
                        lines.append(line.replace('\n', ''))
        for linea in lines:
            partida = str(int(linea[14:31]))
            unidad = part_un[partida]
            if str(int(linea[31:45]) / 100)[-2] == '.':  # EXTRAE EL MONTO DEL TXT.
                monto = str(int(linea[31:45]) / 100) + '0'
            else:
                monto = str(int(linea[31:45]) / 100)
            monto_aguastxt = monto_aguastxt + dc(monto)
            hoy = str(datetime.date.today())  # CALCULO DE FECHAS (HOY Y FIN DE MES)
            year = int(hoy[0:4])
            month = int(hoy[5:7])
            monthstr = str(hoy[5:7])
            fin_mes = hoy[0:8] + str(calendar.monthrange(year, month)[1])
            linea = str(unidad + '|' + 'IRBC' + '|' + 'II' + '|' + fin_mes + '||||' + str(monto) +
                        '||' + '1' + '|||' + 'P' + '|||' + '0' + '|' + 'MIGRA' + '|' + 'MIGRA' +
                        '|' + hoy + '||||||')
        # FILTRO:
            salida.append(linea)
            monto_facturados = monto_facturados + dc(monto)
        log.append('-> Lineas del archivo original AGUAS.TXT modificadas.')
        salida = [linea1] + salida
    except Exception as expt:
        log.append('Error al procesar el archivo original: ' + repr(expt))
        error = True
    # ------------------------------------------------------------------------------
    # ESCRIBE EL ARCHIVO FINAL A PARTIR DE "salida".
    try:
        meses = {'01': 'ENE', '02': 'FEB', '03': 'MAR', '04': 'ABR', '05': 'MAY', '06': 'JUN',
                 '07': 'JUL', '08': 'AGO', '09': 'SEP', '10': 'OCT', '11': 'NOV', '12': 'DIC'}
        with io.open(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' + meses[monthstr] + str(year) +
                     '.csv', 'wt', newline='\r\n') as final:
            for item in salida:
                final.write("%s\n" % item)
            final.close()
        log.append('-> Archivo RBC ' + meses[monthstr] + str(year) + '.csv generado correctamente.')
        log.append('Monto total: $ ' + str(format(monto_aguastxt, '.2f')))
        log.append('Cantidad de partidas: ' + str(len(lines)))
        if dc(format(monto_aguastxt, '.2f')) == dc(format((monto_facturados), '.2f')):
            log.append('Montos verificados exitosamente!')
        else:
            log.append('ERROR en montos.......')
    except Exception as expt:
        log.append('Error al crear el archivo final: ' + repr(expt))
        error = True

    try:
        try:
            zip_rbc = zipfile.ZipFile(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' +
                                      meses[str(datetime.date.today())[5:7]] +
                                      str(datetime.date.today())[0:4] + '.zip',
                                      mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' +
                      meses[str(datetime.date.today())[5:7]] +
                      str(datetime.date.today())[0:4] + '.zip')
            zip_rbc = zipfile.ZipFile(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' +
                                      meses[str(datetime.date.today())[5:7]] +
                                      str(datetime.date.today())[0:4] + '.zip',
                                      mode='x', compression=zipfile.ZIP_DEFLATED)

        with io.open(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' + 'Log_' + date + '.txt',
                     'wt', newline='\r\n') as log_arch:
            for item in log:
                log_arch.write("%s\n" % item)
            log_arch.close()

        zip_rbc.write(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' +
                      meses[str(datetime.date.today())[5:7]] +
                      str(datetime.date.today())[0:4] + '.csv',
                      os.path.basename(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' +
                                       meses[monthstr] + str(year) + '.csv'))
        zip_rbc.write(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' + 'Log_' + date + '.txt',
                      os.path.basename(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' + 'Log_' +
                                       date + '.txt'))
        zip_rbc.close()
        os.remove(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' + meses[monthstr] +
                  str(year) + '.csv')
        os.remove(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' + 'Log_' + date + '.txt')
    except Exception as expt:
        log.append('Error al crear archivos finales: ' + repr(expt))
        error = True

    if error is False:
        return settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' + meses[monthstr] + str(year) + '.zip'
    else:
        with io.open(settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' + 'Log_' + date + '.txt',
                     'wt', newline='\r\n') as log_arch:
            for item in log:
                log_arch.write("%s\n" % item)
            log_arch.close()
        return settings.MEDIA_ROOT + r'/conversor_rbc/RBC ' + 'Log_' + date + '.txt'
