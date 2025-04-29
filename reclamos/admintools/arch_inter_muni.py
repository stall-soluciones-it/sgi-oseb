# -*- coding: utf-8 -*-
"""
Created on Wed Jan 18 12:40:05 2023

@author: Daniel
"""
import io
from pymysql import cursors, connect
from decimal import Decimal
import pandas as pd
import sgi.shpd_cnf as cnf
from django.conf import settings


def dec(numero):
    """Formato de numero decimal redondeado a dos decimales."""
    num = Decimal(numero)
    dos_decimales = Decimal("0.01")
    return num.quantize(dos_decimales)


def arch_inter_muni(tipo, percibido, desde, hasta):
    datos = None
    tipo2 = None

    cpd_pi = str(percibido).zfill(7)
    d_anio = str(desde)[0:4]
    d_mes = str(desde)[4:6]
    d_dia = str(desde)[6:8]
    h_anio = str(hasta)[0:4]
    h_mes = str(hasta)[4:6]
    h_dia = str(hasta)[6:8]
    if tipo == 'FFI':
        tipo2 = str(tipo)
    elif (tipo == 'TSUM') or (tipo == 'TSUM2'):
        tipo2 = 'IRBC'

    query = (f"SELECT osebal_produccion.z80cpd_pi_{cpd_pi}.periodo,"
             f" osebal_produccion.z80cpd_pi_{cpd_pi}.importe_cob,"
             f" osebal_produccion.z80cpd_pi_{cpd_pi}.fec_cob,"
             " osebal_produccion.z80unidad.unidad_alt"
             f" FROM osebal_produccion.z80cpd_pi_{cpd_pi}"
             " LEFT JOIN osebal_produccion.z80unidad"
             f" ON osebal_produccion.z80cpd_pi_{cpd_pi}.unidad = osebal_produccion.z80unidad.unidad"
             f" WHERE osebal_produccion.z80cpd_pi_{cpd_pi}.estado = 'C'"
             f" AND osebal_produccion.z80cpd_pi_{cpd_pi}.ser_bas = '{tipo2}'"
             f" AND (osebal_produccion.z80cpd_pi_{cpd_pi}.fec_cob"
             f" BETWEEN '{d_anio}-{d_mes}-{d_dia}' AND '{h_anio}-{h_mes}-{h_dia}')"
             f" AND osebal_produccion.z80cpd_pi_{cpd_pi}.num_caja != 0;")

    try:
        connection = connect(host=cnf.DB_OSEBAL_HOST,
                             user=cnf.DB_SISA_USR,
                             password=cnf.DB_SISA_PASS,
                             db='osebal_produccion',
                             charset='utf8mb4',
                             cursorclass=cursors.DictCursor)
        cursor = cursors.DictCursor(connection)
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        if datos == ():
            datos = 'nodata'
    except Exception as expt:
        print('Error en conexión a DB: ' + repr(expt))

    if datos == 'nodata':
        return datos
    else:
        if (tipo == 'FFI') or (tipo == 'TSUM'):
            df = pd.DataFrame(datos)
            df.rename(columns={'periodo': 'PERIODO',
                               'importe_cob': 'IMPORTE',
                               'fec_cob': 'FEC_COB',
                               'unidad_alt': 'PARTIDA'},
                      inplace=True)
            df = df[['PARTIDA', 'PERIODO', 'FEC_COB', 'IMPORTE']]
            df['PERIODO'] = df['PERIODO'].apply(lambda x: str(x)[0:7])
            df['PARTIDA'] = df['PARTIDA'].apply(lambda x: int(x))
            df['IMPORTE'] = df['IMPORTE'].apply(lambda x: float(x))
            df = df.sort_values('PARTIDA')
            df = df.sort_values('FEC_COB')

            tipo_name = str(tipo)

            if (tipo_name == 'TSUM') or tipo_name == 'TSUM2':
                tipo_name = 'TSUM'

            # Set destination directory to save excel.
            xlsfilepath = settings.MEDIA_ROOT + f'/tmp/{tipo_name}_cobrado_{str(desde)}_a_{str(hasta)}.xlsx'
            writer = pd.ExcelWriter(xlsfilepath, engine='xlsxwriter')
            # Write excel to file using pandas to_excel
            df.to_excel(writer, startrow=0, sheet_name='Sheet1', index=False)
            # Indicate workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
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
            format1 = workbook.add_format({'num_format': '#0.00'})
            worksheet.set_column('D:D', None, format1)
            writer.close()

            # df.to_excel(tipo_name + '_cobrado_' + DESDE + '_a_' + HASTA + '.xlsx', index = False)
            return settings.MEDIA_ROOT + f'/tmp/{tipo_name}_cobrado_{str(desde)}_a_{str(hasta)}.xlsx'

        elif tipo == 'TSUM2':
            archivo_muni = []
            for dic in datos:

                fec_cob = (str(dic['fec_cob'].year) +
                           str(dic['fec_cob'].month).zfill(2) +
                           str(dic['fec_cob'].day).zfill(2))
                importe = str(dic['importe_cob']).replace('.', '').zfill(13)
                partida = str(int(dic['unidad_alt'])).zfill(18)
                periodo = str(dic['periodo'].year) + str(dic['periodo'].month).zfill(2)

                final = ("       00000000 " + fec_cob + "             " + importe + partida +
                         "                     " + importe + periodo +
                         "                          ")
                archivo_muni.append(final)

            with io.open(settings.MEDIA_ROOT + f'/tmp/TSUM_cobrado_{str(desde)}_a_{str(hasta)}.txt', 'wt',
                         newline='\r\n') as arch:
                arch.write('\n'.join(archivo_muni))
            return settings.MEDIA_ROOT + f'/tmp/TSUM_cobrado_{str(desde)}_a_{str(hasta)}.txt'
