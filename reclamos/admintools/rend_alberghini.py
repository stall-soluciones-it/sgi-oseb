# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 16:09:56 2020.

@author: Daniel
"""
import datetime
import io
from decimal import Decimal
import pymysql
import pandas as pd
import sgi.shpd_cnf as cnf
from django.conf import settings


# Func. para trabajar en sistema decimal:
def dec(numero):
    """Formato de numero decimal redondeado a dos decimales."""
    num = Decimal(numero)
    dos_decimales = Decimal("0.01")
    return num.quantize(dos_decimales)


def process_alberghini(anio, mes):
    """Genera el archivo con la rendición del Estudio Alberghini."""
    log = []
    try:
        anio = int(anio)
        mes = int(mes)
    except (ValueError, NameError) as expt:
        log.append('Error en valores de año o mes, deben ser números enteros: ' + repr(expt))

    def df_alberghini():
        """Consulto tabla de unidades y genero DF de UN asignadas a Alberghini."""
        try:
            connection = pymysql.connect(host=cnf.DB_SISA_HOST,
                                         user=cnf.DB_SISA_USR,
                                         password=cnf.DB_SISA_PASS,
                                         db='osebal_produccion',
                                         charset='utf8mb4',
                                         cursorclass=pymysql.cursors.DictCursor)
            cursor = pymysql.cursors.DictCursor(connection)
            query = ("SELECT unidad, unidad_alt, razon FROM z80unidad WHERE val_atr_8 = '4';")
            cursor.execute(query)
            datos = cursor.fetchall()
            cursor.close()
            connection.close()
            final = []
            for dic in datos:
                final.append([str(dic['unidad']), str(dic['unidad_alt']), str(dic['razon'])])
            df = pd.DataFrame.from_records(final, columns=['Unidad', 'Partida', 'Razón'])
            df['Importe'] = ''
            return df
        except Exception as expt:
            log.append('Error al consultar DB de SISA y crear DF: ' + repr(expt))

    def cuotas_pp_pagas(mes, anio):
        """Consulto tablas de pagos y busco la que corresponde al periodo."""
        try:
            date_ref = datetime.date(2017, 1, 1)
            date = datetime.date(anio, mes, 1)
            tab = 35
        except Exception as expt:
            log.append('Error en valores de año o mes, deben ser números enteros: ' + repr(expt))
        cuenta_iter = []
        try:
            while (date.year != date_ref.year) or (date.month != date_ref.month):
                tabla = str(tab).zfill(7)
                try:
                    connection = pymysql.connect(host=cnf.DB_SISA_HOST,
                                                 user=cnf.DB_SISA_USR,
                                                 password=cnf.DB_SISA_PASS,
                                                 db='osebal_produccion',
                                                 charset='utf8mb4',
                                                 cursorclass=pymysql.cursors.DictCursor)
                    cursor = pymysql.cursors.DictCursor(connection)
                    query = ("SELECT unidad, tpo_com, fec_cob, importe_cob"
                             + " FROM z80cpd_pi_" + tabla
                             + " WHERE tpo_com = 'FCPP' OR tpo_com = 'NCPP';")
                    cursor.execute(query)
                    datos = cursor.fetchall()
                    cursor.close()
                    connection.close()
                    date_ref = datos[0]['fec_cob']
                    tab += 1
                except Exception as expt:
                    cuenta_iter.append('Tabla para fecha solicitada no encontrada: ' + str(expt))
                    if sum('exist' in string for string in cuenta_iter) >= 50:
                        log.append('NO SE ENCONTRÓ TABLA PARA LA FECHA SOLICITADA.')
                        break
                    else:
                        tab += 1
                        continue
        except Exception as expt2:
            log.append('Error al consultar la DB: ' + repr(expt2))
        try:
            dic_final = {}
            for dic in datos:
                if str(dic['unidad']) not in dic_final:
                    dic_final[str(dic['unidad'])] = dic['importe_cob']
                else:
                    dic_final[str(dic['unidad'])] = (dic_final[str(dic['unidad'])]
                                                     + dic['importe_cob'])
            return dic_final
        except Exception as expt:
            log.append('Error al crear diccionario final: ' + repr(expt))
    try:
        DF = df_alberghini()
        IMPORTES = cuotas_pp_pagas(mes, anio)
        for key, value in IMPORTES.items():
            DF.loc[DF['Unidad'] == key, ['Importe']] = value
        DF = DF[DF['Importe'] != '']
        DF['Comisión'] = (DF.Importe / (dec(1) + (dec(0.25) * dec(1.21)))) * dec(0.25)
        DF['Unidad'] = DF['Unidad'].apply(lambda x: int(x))
        DF['Partida'] = DF['Partida'].apply(lambda x: int(x))
        DF['Comisión'] = DF['Comisión'].apply(lambda x: float(x))
        DF['Importe'] = DF['Importe'].apply(lambda x: float(x))
        total = dec(0)
        for index, row in DF.iterrows():
            total += dec(row['Comisión'])
        DF = DF.append({'Comisión': float(total)}, ignore_index=True)

        # Set destination directory to save excel.
        xlsFilepath = (settings.MEDIA_ROOT + r'/rend_alberghini/' + 'Alberghini_' + str(anio)
                       + '-' + str(mes).zfill(2) + '.xlsx')
        writer = pd.ExcelWriter(xlsFilepath, engine='xlsxwriter')
        # Write excel to file using pandas to_excel
        DF.to_excel(writer, startrow=0, sheet_name='Sheet1', index=False)
        # Indicate workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        # Iterate through each column and set the width == the max length in that column.
        # A padding length of 2 is also added.
        for i, col in enumerate(DF.columns):
            # find length of column i
            column_len = DF[col].astype(str).str.len().max()
            # Setting the length if the column header is larger
            # than the max column value length
            column_len = max(column_len, len(col)) + 2
            # set the column length
            worksheet.set_column(i, i, column_len)
        format1 = workbook.add_format({'num_format': '#0.00'})
        format2 = workbook.add_format({'num_format': '#0'})
        worksheet.set_column('D:D', None, format1)
        worksheet.set_column('E:E', None, format1)
        worksheet.set_column('A:A', None, format2)
        worksheet.set_column('B:B', None, format2)
        writer.save()
    except Exception as expt:
        log.append('Error al crear DF final: ' + repr(expt))

    if log:
        with io.open(settings.MEDIA_ROOT + r'/rend_alberghini/Log_' + str(anio)
                     + '-' + str(mes) + '.txt',
                     'wt', newline='\r\n') as log_arch:
            for item in log:
                log_arch.write("%s\n" % item)
            log_arch.close()
        return (settings.MEDIA_ROOT + r'/rend_alberghini/Log_' + str(anio)
                + '-' + str(mes) + '.txt')
    else:
        return (settings.MEDIA_ROOT + r'/rend_alberghini/' + 'Alberghini_' + str(anio)
                + '-' + str(mes).zfill(2) + '.xlsx')
