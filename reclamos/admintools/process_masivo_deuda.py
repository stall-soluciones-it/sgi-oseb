# -*- coding: utf-8 -*-
"""@Shepherd."""
import io
import pandas as pd
import psycopg2
import sgi.shpd_cnf as cnf
from django.conf import settings


def change_postresql(query):
    """Aplico cambios a DB Postgre."""
    connection = psycopg2.connect(user=cnf.DB_SHPD_USR,
                                  password=cnf.DB_SHPD_PASS,
                                  host=cnf.DB_SHPD_HOST,
                                  port="5432",
                                  database="external_data")
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    if(connection):
        cursor.close()
        connection.close()


def process_masivo_deuda(archivo, fecha):
    """Creo DF Masivo Deuda."""
    log = []

    # DEUDA DE PROVEEDOR CON ADBSA
    try:
        df_deuda_adbsa = pd.read_excel(archivo, skiprows=[0, 1, 2, 3, 4, 5, 6, 7, 9],
                                       usecols='E,J')
        dict_deuda_adbsa = {}
        for _, row in df_deuda_adbsa.iterrows():
            if row['Total'] == float('NaN'):
                pass
            else:
                try:
                    dict_deuda_adbsa[int(row['Unidad Alt.'])] = row['Total']
                except ValueError:
                    pass
    except Exception as expt:
        log.append(repr(expt))






















    with io.open(settings.MEDIA_ROOT + r'/proveedores/Log_error.txt',
                 'wt', newline='\r\n') as log_arch:
        log_arch.write('\n'.join(log))
    return settings.MEDIA_ROOT + r'/proveedores/Log_error.txt'
