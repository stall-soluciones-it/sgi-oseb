# -*- coding: utf-8 -*-
"""
Created on Wed Jan 18 12:40:05 2023

@author: Daniel
"""
import pymysql
from decimal import Decimal
import pandas as pd
import sgi.shpd_cnf as cnf
from django.conf import settings

def dec(numero):
    """Formato de numero decimal redondeado a dos decimales."""
    num = Decimal(numero)
    dos_decimales = Decimal("0.01")
    return num.quantize(dos_decimales)


def arch_cons_ctas(cuenta, desde, hasta):

    cuenta = str(cuenta)
    d_anio = str(desde)[0:4]
    d_mes = str(desde)[4:6]
    d_dia = str(desde)[6:8]
    h_anio = str(hasta)[0:4]
    h_mes = str(hasta)[4:6]
    h_dia = str(hasta)[6:8]

    query = ("SELECT * FROM mov_ren " +
             f"WHERE cuenta = '{cuenta}' " +
             f"AND fecha BETWEEN '{d_anio}-{d_mes}-{d_dia}' AND '{h_anio}-{h_mes}-{h_dia}';")

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
    
    cta_name = str(cuenta)

    df.to_excel(settings.MEDIA_ROOT + r'/tmp/Cuenta_' + cta_name + "_" + str(desde) + '_a_' + str(hasta) + '.xlsx', index = False)
    return settings.MEDIA_ROOT + r'/tmp/Cuenta_' + cta_name + "_" + str(desde) + '_a_' + str(hasta) + '.xlsx'
