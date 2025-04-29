# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 11:15:02 2020.

@author: Daniel
"""
import os
import io
import calendar
import pymysql
import pandas as pd
import zipfile
import sgi.shpd_cnf as cnf
from django.conf import settings

"""IIBB de AdBSA"""


def process_liq_iibb(anio, mes):
    """Procesa listados carenciados o bomberos."""
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

    # Conecto a DB y extraigo datos.
    try:
        connection = pymysql.connect(host=cnf.DB_SISA_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT tpo_com, pre_com, num_com, unidad, cod_ser, cod_con, fecha,"
                 + " importe, tar_iva, imp_iva"
                 + " FROM z80facturado"
                 + " WHERE (cod_ser NOT IN ('P80', 'P81', 'P84', 'IRBC', 'I10', 'I21',"
                 + " 'I27', 'PIB', 'ZI21', 'ZI27', 'ZRBC'))"
                 + " AND (tpo_aux NOT IN ('MG'))"
                 + " AND (fecha BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as expt:
        log.append('Error en conexión a DB z80facturado: ' + repr(expt))
    # Consulto facturas_elec
    try:
        connection = pymysql.connect(host=cnf.DB_SISA_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT tpo_com, pre_com, num_com, pre_com_elec, num_com_elec"
                 + " FROM z80facturas_elec"
                 + " WHERE (fec_emi BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")
        cursor.execute(query)
        fac_elec = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as expt:
        log.append('Error al conectar DB z80facturas_elec: ' + repr(expt))
    try:
        f_elec = {}
        for dic in fac_elec:
            f_elec[str(dic['tpo_com'])
                   + str(dic['pre_com'])
                   + str(dic['num_com'])] = [dic['pre_com_elec'],
                                             dic['num_com_elec']]
    except Exception as expt:
        log.append('Error al crear dic f_elec: ' + repr(expt))

    # Condicion ante IVA
    try:
        connection = pymysql.connect(host=cnf.DB_SISA_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT unidad, tpo_iva"
                 + " FROM z80unidad;")
        cursor.execute(query)
        cond_iva = cursor.fetchall()
        cursor.close()
        connection.close()
        cond_iva2 = {}
        for dic in cond_iva:
            cond_iva2[int(dic['unidad'])] = str(dic['tpo_iva'])
    except Exception as expt:
        log.append('Error al conectar DB z80unidad: ' + repr(expt))

    try:
        df1 = pd.DataFrame(datos)
        df1['pre_com_elec'] = ''
        df1['num_com_elec'] = ''
        for i, row in df1.iterrows():
            try:
                df1.at[i, 'pre_com_elec'] = f_elec[str(row['tpo_com'])
                                                   + str(row['pre_com'])
                                                   + str(row['num_com'])][0]
                df1.at[i, 'num_com_elec'] = f_elec[str(row['tpo_com'])
                                                   + str(row['pre_com'])
                                                   + str(row['num_com'])][1]
            except KeyError:
                pass
        df2 = df1.copy()

        df1['cond_iva'] = df1.unidad.apply(lambda x: cond_iva2[int(x)])

        df1.to_excel(settings.MEDIA_ROOT + r'/liq_iibb/' + 'LiqIIBB_'
                     + str(anio) + str(mes).zfill(2) + ' (completo).xlsx', index=False)
        df4 = df1.groupby(by=["cond_iva"])["importe"].sum()
        del df2['cod_ser']
        df2 = df2.groupby(['tpo_com', 'pre_com', 'num_com', 'unidad', 'cod_con',
                           'fecha', 'pre_com_elec',
                           'num_com_elec']).agg({'importe': 'sum',
                                                 'tar_iva': 'sum',
                                                 'imp_iva': 'sum'}).reset_index()
        df2.to_excel(settings.MEDIA_ROOT + r'/liq_iibb/' + 'LiqIIBB_'
                     + str(anio) + str(mes).zfill(2) + ' (agrupado).xlsx', index=False)
        df4.to_excel(settings.MEDIA_ROOT + r'/liq_iibb/' + 'Totales_cond_iva_'
                     + str(anio) + str(mes).zfill(2) + '.xlsx')
    except Exception as expt:
        log.append('Error al crear dataframes: ' + repr(expt))

    try:
        try:
            ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/liq_iibb/' + 'LiqIIBB_AdBSA_'
                                       + str(anio) + str(mes).zfill(2) + '.zip',
                                       mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/liq_iibb/' + 'LiqIIBB_AdBSA_'
                      + str(anio) + str(mes).zfill(2) + '.zip')
            ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/liq_iibb/' + 'LiqIIBB_AdBSA_'
                                       + str(anio) + str(mes).zfill(2) + '.zip',
                                       mode='x', compression=zipfile.ZIP_DEFLATED)
        ARCH_ZIP.write(settings.MEDIA_ROOT + r'/liq_iibb/' + 'LiqIIBB_'
                       + str(anio) + str(mes).zfill(2) + ' (completo).xlsx',
                       os.path.basename(settings.MEDIA_ROOT + r'/liq_iibb/'
                                        + 'LiqIIBB_' + str(anio) + str(mes).zfill(2)
                                        + ' (completo).xlsx'))
        ARCH_ZIP.write(settings.MEDIA_ROOT + r'/liq_iibb/' + 'LiqIIBB_'
                       + str(anio) + str(mes).zfill(2) + ' (agrupado).xlsx',
                       os.path.basename(settings.MEDIA_ROOT + r'/liq_iibb/'
                                        + 'LiqIIBB_' + str(anio) + str(mes).zfill(2)
                                        + ' (agrupado).xlsx'))
        ARCH_ZIP.write(settings.MEDIA_ROOT + r'/liq_iibb/' + 'Totales_cond_iva_'
                       + str(anio) + str(mes).zfill(2) + '.xlsx',
                       os.path.basename(settings.MEDIA_ROOT + r'/liq_iibb/'
                                        + 'Totales_cond_iva_' + str(anio) + str(mes).zfill(2)
                                        + '.xlsx'))
        ARCH_ZIP.close()
    except Exception as expt:
        log.append('Error al crear zipear archivos: ' + repr(expt))

    if log:
        with io.open(settings.MEDIA_ROOT + r'/liq_iibb/' + 'Log_AdBSA_' + str(anio)
                     + '-' + str(mes).zfill(2) + '.txt', 'wt', newline='\r\n') as logarch:
            logarch.write('\n'.join(log))
        return (settings.MEDIA_ROOT + r'/liq_iibb/' + 'Log_AdBSA_' + str(anio)
                + '-' + str(mes).zfill(2) + '.txt')
    else:
        return (settings.MEDIA_ROOT + r'/liq_iibb/' + 'LiqIIBB_AdBSA_'
                + str(anio) + str(mes).zfill(2) + '.zip')
