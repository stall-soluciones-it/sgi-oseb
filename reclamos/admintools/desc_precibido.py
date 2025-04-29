# -*- coding: utf-8 -*-
"""
Created on Wed Jan 18 12:40:05 2023

@author: Daniel
"""
import datetime
from decimal import Decimal
import pymysql
import pandas as pd
import sgi.shpd_cnf as cnf
from django.conf import settings


def proc_desc_percibido(percibido):

    ahora = str(datetime.datetime.now())[:19].replace(' ', '_').replace(':', '-')
    cpd_pi = str(percibido).zfill(7)

    query = f"SELECT * FROM osebal_produccion.z80cpd_pi_{cpd_pi};"

    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as expt:
        print('Error en conexión a DB: ' + repr(expt))

    df = pd.DataFrame(datos)
    df["num_com"] = df["tpo_com"].astype(str) + ' ' + df["pre_com"].astype(str) + '-' + df["num_com"].astype(str)
    df = df.drop(['tpo_com', 'pre_com'], axis=1)
    df = df.apply(pd.to_numeric, errors='ignore')
    df['periodo'] = pd.to_datetime(df['periodo'])
    df['periodo_trib'] = pd.to_datetime(df['periodo_trib'])

    df.to_csv(settings.MEDIA_ROOT + f'tmp/Percibido_{percibido}_{ahora}.csv', sep=';', index=False, decimal=",")

    return settings.MEDIA_ROOT + f'tmp/Percibido_{percibido}_{ahora}.csv'
