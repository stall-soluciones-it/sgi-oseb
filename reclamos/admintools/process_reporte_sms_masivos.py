# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 11:25:06 2020.

@author: Daniel
"""
import datetime
import pymysql
import sgi.shpd_cnf as cnf
import pandas as pd
from django.conf import settings


def process_reporte_sms_masivos(listado, anio, mes, dia):
    """Reporta a partir de listado de un. o part. y fecha a partir de la cual ve si hay pagos."""
    log = []
    try:
        anio = int(anio)
        mes = int(mes)
        dia = int(dia)
        fecha = datetime.date(anio, mes, dia)
    except (ValueError, NameError) as expt:
        log.append('Error en valores de año, mes o día, deben ser números enteros: ' + repr(expt))

    # CARGO ARCHIVO Y CREO LISTA PARTIDAS, LISTA DE UNIDADES Y QUERY DE UNIDADES:
    # Cargo archivo y creo listado partidas:
    try:
        partidas = []
        unidades = []
        with open(listado, 'r') as arch_partidas:
            for line in arch_partidas:
                try:
                    partida = int(line.replace('\n', ''))
                    partidas.append(str(partida))
                except TypeError:
                    pass
        total_partidas = len(partidas)
        # Creo query con partidas:
        query_partidas = ''
        for partida in partidas:
            query_partidas += str("'" + partida + "'" + ', ')
        query_partidas = query_partidas[:-2]
        # Consulto DB para crear listado unidades a partir de partidas:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT unidad, unidad_alt" +
                 " FROM z80unidad" +
                 " WHERE unidad_alt IN (" + query_partidas + ");")
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        for dic in datos:
            unidades.append(str(dic['unidad']))
        # Creo query con unidades:
        query_unidades = ''
        for unidad in unidades:
            query_unidades += str(unidad + ', ')
        query_unidades = query_unidades[:-2]

    except (ValueError, NameError) as expt:
        log.append('Error al crear listados o query de unidades: ' + repr(expt))

    # BUSCO TABLAS DE PAGOS A ANALIZAR:
    try:
        tablas = 300

        def tabla_ok(tabla):
            """Funcion para buscar tablas a procesar."""
            try:
                connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                             user=cnf.DB_SISA_USR,
                                             password=cnf.DB_SISA_PASS,
                                             db='osebal_produccion',
                                             charset='utf8mb4',
                                             cursorclass=pymysql.cursors.DictCursor)
                cursor = pymysql.cursors.DictCursor(connection)
                query = ("SELECT fec_cob FROM z80cpd_pi_" + str(tabla).zfill(7)
                         + " WHERE estado = 'C'"
                         + " AND cod_ser <> 'IRBC'"
                         + " LIMIT 1;")
                cursor.execute(query)
                datos = cursor.fetchall()
                fechat = datos[0]['fec_cob']
                cursor.close()
                connection.close()
            except:
                fechat = ''
            return(fechat)

        # Busco tablas a procesar
        tablas_ok = []
        while tablas > 0:
            fechatt = tabla_ok(tablas)
            if fechatt != '':
                if fechatt.year >= fecha.year and fechatt.month >= fecha.month:
                    tablas_ok.append(str(tablas))
                else:
                    break
            tablas -= 1

        # Ingresó pago:
        df_list1 = []
        for tabla in tablas_ok:
            connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                         user=cnf.DB_SISA_USR,
                                         password=cnf.DB_SISA_PASS,
                                         db='osebal_produccion',
                                         charset='utf8mb4',
                                         cursorclass=pymysql.cursors.DictCursor)
            cursor = pymysql.cursors.DictCursor(connection)

            query = ("SELECT z80unidad.unidad_alt, fec_cob, importe_cob" +
                     " FROM z80cpd_pi_" + str(tabla).zfill(7) +
                     " JOIN z80unidad" +
                     " ON z80cpd_pi_" + str(tabla).zfill(7) + ".unidad = z80unidad.unidad" +
                     " WHERE z80cpd_pi_" + str(tabla).zfill(7) + ".unidad IN (" + query_unidades + ")" +
                     " AND estado = 'C'" +
                     " AND cod_ser <> 'IRBC';")
            cursor.execute(query)
            datos = cursor.fetchall()
            cursor.close()
            connection.close()
            df_list1.extend(datos)
        df_dic1 = {}
        for dic in df_list1:
            if dic['fec_cob'] >= fecha:
                if dic['unidad_alt'] not in df_dic1:
                    df_dic1[dic['unidad_alt']] = dic['importe_cob']
                else:
                    df_dic1[dic['unidad_alt']] += dic['importe_cob']
        df_list2 = []
        for key, value in df_dic1.items():
            df_list2.append({'partida': key, 'monto': value})
        df_list2 = [item for item in df_list2 if item['monto'] > 0]
    except Exception as expt:
        log.append('Error al analizar tablas de pagos o crear dict y lists finales: ' + repr(expt))

    pagaron_partidas = len(df_list2)

    df_resumen = pd.DataFrame([{'Total partidas': total_partidas, 'Pagaron': pagaron_partidas}])

    # CREO DATAFRAME:
    df_pagos = pd.DataFrame(df_list2)
    # CREO EL ARCHIVO FINAL
    # Set destination directory to save excel.
    xlsFilepath = (settings.MEDIA_ROOT + r'/tmp/Reporte_sms_masivos.xlsx')
    writer = pd.ExcelWriter(xlsFilepath, engine='xlsxwriter')
    # Write excel to file using pandas to_excel
    df_resumen.to_excel(writer, startrow=0, sheet_name='Resumen', index=False)
    df_pagos.to_excel(writer, startrow=0, sheet_name='Detalle pagaron', index=False)
    # FORMATEO EL LIBRO:
    # Indicate workbook and worksheet for formatting
    workbook = writer.book
    worksheet = writer.sheets['Resumen']
    # Iterate through each column and set the width == the max length in that column.
    # A padding length of 2 is also added.
    for i, col in enumerate(df_resumen.columns):
        # find length of column i
        column_len = df_resumen[col].astype(str).str.len().max()
        # Setting the length if the column header is larger
        # than the max column value length
        column_len = max(column_len, len(col)) + 2
        # set the column length
        worksheet.set_column(i, i, column_len)
    worksheet = writer.sheets['Detalle pagaron']
    # Iterate through each column and set the width == the max length in that column.
    # A padding length of 2 is also added.
    for i, col in enumerate(df_pagos.columns):
        # find length of column i
        column_len = df_pagos[col].astype(str).str.len().max()
        # Setting the length if the column header is larger
        # than the max column value length
        column_len = max(column_len, len(col)) + 2
        # set the column length
        worksheet.set_column(i, i, column_len)

    writer.save()

    return(settings.MEDIA_ROOT + r'/tmp/Reporte_sms_masivos.xlsx')
