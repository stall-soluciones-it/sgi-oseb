# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 11:15:02 2020.

@author: Daniel
"""
import io
import calendar
import pymysql
import pandas as pd
import sgi.shpd_cnf as cnf
from django.conf import settings


def process_rd_generados(anio, mes):
    """Procesa reporte con RDs generados (mensual)."""
    log = []
    try:
        anio = int(anio)
        mes = int(mes)
        if 2017 <= anio <= 2040:
            pass
        else:
            log.append('ERROR: El año "' + str(anio) + '" es incorrecto.')
        if 1 <= mes <= 12:
            pass
        else:
            log.append('ERROR: El mes "' + str(mes) + '" es incorrecto.')
        last_day = calendar.monthrange(anio, mes)[1]
    except Exception as expt:
        log.append('Error, los datos ingresados son incorrectos: ' + repr(expt))

    # Conecto z80unidad.
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT unidad, unidad_alt"
                 + " FROM z80unidad;")

        cursor.execute(query)
        unidades = cursor.fetchall()
        cursor.close()
        connection.close()
        partidas = {}
        for dic in unidades:
            try:
                partidas[int(dic['unidad'])] = int(dic['unidad_alt'])
            except ValueError:
                pass
    except Exception as expt:
        log.append('Error en conexión a DB z80unidad: ' + repr(expt))

    # Conecto z80resumen.
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT unidad, pre_com, num_com, fec_emi, fec_vto1, sit_com_moroso"
                 + " FROM z80resumen"
                 + " WHERE (tpo_com IN ('RD'))"
                 + " AND (fec_emi BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as expt:
        log.append('Error en conexión a DB z80resumen: ' + repr(expt))

    # Consulto comprobantes asociados
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT pre_com, num_com, importe, recargo, iva_recargo"
                 + " FROM z80resumen_det"
                 + " WHERE (tpo_com IN ('RD'));")
        cursor.execute(query)
        det_rd = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as expt:
        log.append('Error al conectar DB z80resumen_det: ' + repr(expt))
    try:
        totales = {}
        for dic in det_rd:
            indice = str(dic['pre_com']) + str(dic['num_com'])
            valor = dic['importe'] + dic['recargo'] + dic['iva_recargo']
            if indice not in totales.keys():
                totales[indice] = valor
            else:
                totales[indice] = totales[indice] + valor
    except Exception as expt:
        log.append('Error al crear dic totales: ' + repr(expt))

    try:
        df = pd.DataFrame(datos)
        df = df.astype({"num_com": str})
        df['comprobante'] = df['pre_com'] + df['num_com']
        df['monto'] = df.comprobante.apply(lambda x: float(totales[str(x)]))
        df['partida'] = df.unidad.apply(lambda x: partidas[int(x)])
        del df['comprobante']
        df.columns = ['Unidad', 'Pre_num.', 'Número', 'Emisión', 'Vencimiento', 'Estado',
                      'Monto', 'Partida']
        df = df[['Partida', 'Pre_num.', 'Número', 'Emisión', 'Vencimiento', 'Monto', 'Estado']]

        # Set destination directory to save excel.
        xlsFilepath = (settings.MEDIA_ROOT + r'/tmp/' + 'Comp_RD_generados_'
                       + str(anio) + '-' + str(mes).zfill(2) + '.xlsx')
        writer = pd.ExcelWriter(xlsFilepath, engine='xlsxwriter')
        # Write excel to file using pandas to_excel
        df.to_excel(writer, startrow=0, sheet_name='Sheet1', index=False)
        # Indicate workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        format1 = workbook.add_format({'num_format': '$ #,##0.00'})
        worksheet.set_column('F:F', None, format1)
        # Iterate through each column and set the width == the max length in that column.
        # A padding length of 2 is also added.
        for i, col in enumerate(df.columns):
            # find length of column i
            column_len = df[col].astype(str).str.len().max()
            # Setting the length if the column header is larger
            # than the max column value length
            column_len = max(column_len, len(col)) + 2
            # set the column length
            worksheet.set_column(i, i, column_len)
        writer.save()

    except Exception as expt:
        log.append('Error al crear dataframes: ' + repr(expt))

    if log:
        with io.open(settings.MEDIA_ROOT + r'/tmp/' + 'Log_RD_' + str(anio)
                     + '-' + str(mes).zfill(2) + '.txt', 'wt', newline='\r\n') as logarch:
            logarch.write('\n'.join(log))
        return (settings.MEDIA_ROOT + r'/tmp/' + 'Log_RD_' + str(anio)
                + '-' + str(mes).zfill(2) + '.txt')
    else:
        return (settings.MEDIA_ROOT + r'/tmp/' + 'Comp_RD_generados_'
                + str(anio) + '-' + str(mes).zfill(2) + '.xlsx')
