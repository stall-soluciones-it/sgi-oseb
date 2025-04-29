# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 11:15:02 2020.

@author: Daniel
"""
import io
import calendar
import pymysql
import pandas as pd
import numpy as np
import sgi.shpd_cnf as cnf
from django.conf import settings


def process_dto_int_canon(anio, mes):
    """Dto. int canon."""
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

    try:
        # Diccionario comprobante = partida:
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
        datos = cursor.fetchall()
        cursor.close()
        connection.close()

        lista_unidades = []
        for dic in datos:
            lista_unidades.append(int(dic['unidad']))

        dic_partidas = {}
        for dic in datos:
            try:
                dic_partidas[int(dic['unidad'])] = int(dic['unidad_alt'])
            except ValueError:
                pass

        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT auxiliar, cod_mov, num_mov, descripcion, fecha, imp_bas"
                 + " FROM mov_ren"
                 + " WHERE (fecha BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()

        unidades = {}
        for dic in datos:
            try:
                auxiliar = int(dic['auxiliar'])
                if auxiliar in lista_unidades:
                    try:
                        if auxiliar > unidades[str(int(dic['cod_mov'])) + '-'
                                               + str(int(dic['num_mov']))]:
                            pass
                        else:
                            unidades[str(int(dic['cod_mov'])) + '-' + str(int(dic['num_mov']))] \
                                = int(dic['auxiliar'])
                    except KeyError:
                        unidades[str(int(dic['cod_mov'])) + '-' + str(int(dic['num_mov']))] \
                            = int(dic['auxiliar'])
            except (TypeError, ValueError):
                pass

        partidas = {}
        for key, value in unidades.items():
            try:
                partidas[key] = dic_partidas[value]
            except KeyError:
                pass
    except Exception as expt:
        log.append('Error al crear dict. de comprobantes = partida: ' + repr(expt))

    # Conecto a DB y extraigo datos 1 (41120).
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT cod_mov, num_mov, descripcion, fecha, imp_bas"
                 + " FROM mov_ren"
                 + " WHERE (cuenta IN ('41120'))"
                 + " AND descripcion IN ('Movimientos de Servicios')"
                 + " AND (fecha BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        list_41120 = []
        if datos != ():
            for dic in datos:
                try:
                    list_41120.append({'Fecha': dic['fecha'],
                                       'Partida': partidas[str(int(dic['cod_mov']))
                                                           + '-' + str(int(dic['num_mov']))],
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
                except KeyError:
                    list_41120.append({'Fecha': dic['fecha'],
                                       'Partida': '-',
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
    
            df_41120 = pd.DataFrame(list_41120)
            df_41120['Debe'] = df_41120.apply(lambda row: float(row['Importe']) if
                                              row['Importe'] > 0 else '', axis=1)
            df_41120['Haber'] = df_41120.apply(lambda row: float(row['Importe']) if
                                               row['Importe'] < 0 else '', axis=1)
            df_41120.replace(r'^\s*$', np.nan, regex=True, inplace=True)
            df_41120.loc[:, 'sumafila'] = df_41120.loc[:, ['Debe', 'Haber']].sum(axis=1, min_count=1)
            df_41120['Total'] = df_41120['sumafila'].cumsum()
            df_41120['Haber'] = df_41120.apply(lambda row: float(row['Haber'] * -1), axis=1)
            df_41120 = df_41120[['Fecha', 'Partida', 'Cod_mov', 'Num_mov', 'Descripción',
                                 'Debe', 'Haber', 'Total']]
        else:
            df_41120 = pd.DataFrame([])
    except Exception as expt:
        log.append('Error en conexión a DB (41120): ' + repr(expt))

    # Conecto a DB y extraigo datos 2 (41109).
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT cod_mov, num_mov, descripcion, fecha, imp_bas"
                 + " FROM mov_ren"
                 + " WHERE (cuenta IN ('41109'))"
                 + " AND (fecha BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        list_41109 = []
        if datos != ():
            for dic in datos:
                try:
                    list_41109.append({'Fecha': dic['fecha'],
                                       'Partida': partidas[str(int(dic['cod_mov']))
                                                           + '-' + str(int(dic['num_mov']))],
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
                except KeyError:
                    list_41109.append({'Fecha': dic['fecha'],
                                       'Partida': '-',
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
                    
            df_41109 = pd.DataFrame(list_41109)
            df_41109['Debe'] = df_41109.apply(lambda row: float(row['Importe']) if
                                              row['Importe'] > 0 else '', axis=1)
            df_41109['Haber'] = df_41109.apply(lambda row: float(row['Importe']) if
                                               row['Importe'] < 0 else '', axis=1)
            df_41109.replace(r'^\s*$', np.nan, regex=True, inplace=True)
            df_41109.loc[:, 'sumafila'] = df_41109.loc[:, ['Debe', 'Haber']].sum(axis=1, min_count=1)
            df_41109['Total'] = df_41109['sumafila'].cumsum()
            df_41109['Haber'] = df_41109.apply(lambda row: float(row['Haber'] * -1), axis=1)
            df_41109 = df_41109[['Fecha', 'Partida', 'Cod_mov', 'Num_mov', 'Descripción',
                                 'Debe', 'Haber', 'Total']]
        else:
            df_41109 = pd.DataFrame([])
    except Exception as expt:
        log.append('Error en conexión a DB (41109): ' + repr(expt))

    # Conecto a DB y extraigo datos 3 (41203).
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT cod_mov, num_mov, descripcion, fecha, imp_bas"
                 + " FROM mov_ren"
                 + " WHERE (cuenta IN ('41203'))"
                 + " AND descripcion IN ('Movimientos de Servicios')"
                 + " AND (fecha BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        if datos != ():
            list_41203 = []
            for dic in datos:
                try:
                    list_41203.append({'Fecha': dic['fecha'],
                                       'Partida': partidas[str(int(dic['cod_mov']))
                                                           + '-' + str(int(dic['num_mov']))],
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
                except KeyError:
                    list_41203.append({'Fecha': dic['fecha'],
                                       'Partida': '-',
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
    
            df_41203 = pd.DataFrame(list_41203)
            df_41203['Debe'] = df_41203.apply(lambda row: float(row['Importe']) if
                                              row['Importe'] > 0 else '', axis=1)
            df_41203['Haber'] = df_41203.apply(lambda row: float(row['Importe']) if
                                               row['Importe'] < 0 else '', axis=1)
            df_41203.replace(r'^\s*$', np.nan, regex=True, inplace=True)
            df_41203.loc[:, 'sumafila'] = df_41203.loc[:, ['Debe', 'Haber']].sum(axis=1, min_count=1)
            df_41203['Total'] = df_41203['sumafila'].cumsum()
            df_41203['Haber'] = df_41203.apply(lambda row: float(row['Haber'] * -1), axis=1)
            df_41203 = df_41203[['Fecha', 'Partida', 'Cod_mov', 'Num_mov', 'Descripción',
                                 'Debe', 'Haber', 'Total']]
        else:
            df_41203 = pd.DataFrame([])
    except Exception as expt:
        log.append('Error en conexión a DB (41203): ' + repr(expt))

    # Conecto a DB y extraigo datos 4 (41111).
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT cod_mov, num_mov, descripcion, fecha, imp_bas"
                 + " FROM mov_ren"
                 + " WHERE (cuenta IN ('41111'))"
                 + " AND (fecha BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        if datos != ():
            list_41111 = []
            for dic in datos:
                try:
                    list_41111.append({'Fecha': dic['fecha'],
                                       'Partida': partidas[str(int(dic['cod_mov']))
                                                           + '-' + str(int(dic['num_mov']))],
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
                except KeyError:
                    list_41111.append({'Fecha': dic['fecha'],
                                       'Partida': '-',
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
    
            df_41111 = pd.DataFrame(list_41111)
            df_41111['Debe'] = df_41111.apply(lambda row: float(row['Importe']) if
                                              row['Importe'] > 0 else '', axis=1)
            df_41111['Haber'] = df_41111.apply(lambda row: float(row['Importe']) if
                                               row['Importe'] < 0 else '', axis=1)
            df_41111.replace(r'^\s*$', np.nan, regex=True, inplace=True)
            df_41111.loc[:, 'sumafila'] = df_41111.loc[:, ['Debe', 'Haber']].sum(axis=1, min_count=1)
            df_41111['Total'] = df_41111['sumafila'].cumsum()
            df_41111['Haber'] = df_41111.apply(lambda row: float(row['Haber'] * -1), axis=1)
            df_41111 = df_41111[['Fecha', 'Partida', 'Cod_mov', 'Num_mov', 'Descripción',
                                 'Debe', 'Haber', 'Total']]
        else:
            df_41111 = pd.DataFrame([])
    except Exception as expt:
        log.append('Error en conexión a DB (41111): ' + repr(expt))

    # Conecto a DB y extraigo datos 5 (41112).
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT cod_mov, num_mov, descripcion, fecha, imp_bas"
                 + " FROM mov_ren"
                 + " WHERE (cuenta IN ('41112'))"
                 + " AND (fecha BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        if datos != ():
            list_41112 = []
            for dic in datos:
                try:
                    list_41112.append({'Fecha': dic['fecha'],
                                       'Partida': partidas[str(int(dic['cod_mov']))
                                                           + '-' + str(int(dic['num_mov']))],
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
                except KeyError:
                    list_41112.append({'Fecha': dic['fecha'],
                                       'Partida': '-',
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
    
            df_41112 = pd.DataFrame(list_41112)
            df_41112['Debe'] = df_41112.apply(lambda row: float(row['Importe']) if
                                              row['Importe'] > 0 else '', axis=1)
            df_41112['Haber'] = df_41112.apply(lambda row: float(row['Importe']) if
                                               row['Importe'] < 0 else '', axis=1)
            df_41112.replace(r'^\s*$', np.nan, regex=True, inplace=True)
            df_41112.loc[:, 'sumafila'] = df_41112.loc[:, ['Debe', 'Haber']].sum(axis=1, min_count=1)
            df_41112['Total'] = df_41112['sumafila'].cumsum()
            df_41112['Haber'] = df_41112.apply(lambda row: float(row['Haber'] * -1), axis=1)
            df_41112 = df_41112[['Fecha', 'Partida', 'Cod_mov', 'Num_mov', 'Descripción',
                                 'Debe', 'Haber', 'Total']]
        else:
            df_41112 = pd.DataFrame([])
    except Exception as expt:
        log.append('Error en conexión a DB (41112): ' + repr(expt))

    # Conecto a DB y extraigo datos 6 (41208).
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT cod_mov, num_mov, descripcion, fecha, imp_bas"
                 + " FROM mov_ren"
                 + " WHERE (cuenta IN ('41208'))"
                 + " AND (fecha BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        if datos != ():
            list_41208 = []
            for dic in datos:
                try:
                    list_41208.append({'Fecha': dic['fecha'],
                                       'Partida': partidas[str(int(dic['cod_mov']))
                                                           + '-' + str(int(dic['num_mov']))],
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
                except KeyError:
                    list_41208.append({'Fecha': dic['fecha'],
                                       'Partida': '-',
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
    
            df_41208 = pd.DataFrame(list_41208)
            df_41208['Debe'] = df_41208.apply(lambda row: float(row['Importe']) if
                                              row['Importe'] > 0 else '', axis=1)
            df_41208['Haber'] = df_41208.apply(lambda row: float(row['Importe']) if
                                               row['Importe'] < 0 else '', axis=1)
            df_41208.replace(r'^\s*$', np.nan, regex=True, inplace=True)
            df_41208.loc[:, 'sumafila'] = df_41208.loc[:, ['Debe', 'Haber']].sum(axis=1, min_count=1)
            df_41208['Total'] = df_41208['sumafila'].cumsum()
            df_41208['Haber'] = df_41208.apply(lambda row: float(row['Haber'] * -1), axis=1)
            df_41208 = df_41208[['Fecha', 'Partida', 'Cod_mov', 'Num_mov', 'Descripción',
                                 'Debe', 'Haber', 'Total']]
        else:
            df_41208 = pd.DataFrame([])
    except Exception as expt:
        log.append('Error en conexión a DB (41208): ' + repr(expt))

    # Conecto a DB y extraigo datos 7 (41212).
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT cod_mov, num_mov, descripcion, fecha, imp_bas"
                 + " FROM mov_ren"
                 + " WHERE (cuenta IN ('41212'))"
                 + " AND (fecha BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        if datos != ():
            list_41212 = []
            for dic in datos:
                try:
                    list_41212.append({'Fecha': dic['fecha'],
                                       'Partida': partidas[str(int(dic['cod_mov']))
                                                           + '-' + str(int(dic['num_mov']))],
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
                except KeyError:
                    list_41212.append({'Fecha': dic['fecha'],
                                       'Partida': '-',
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
    
            df_41212 = pd.DataFrame(list_41212)
            df_41212['Debe'] = df_41212.apply(lambda row: float(row['Importe']) if
                                              row['Importe'] > 0 else '', axis=1)
            df_41212['Haber'] = df_41212.apply(lambda row: float(row['Importe']) if
                                               row['Importe'] < 0 else '', axis=1)
            df_41212.replace(r'^\s*$', np.nan, regex=True, inplace=True)
            df_41212.loc[:, 'sumafila'] = df_41212.loc[:, ['Debe', 'Haber']].sum(axis=1, min_count=1)
            df_41212['Total'] = df_41212['sumafila'].cumsum()
            df_41212['Haber'] = df_41212.apply(lambda row: float(row['Haber'] * -1), axis=1)
            df_41212 = df_41212[['Fecha', 'Partida', 'Cod_mov', 'Num_mov', 'Descripción',
                                 'Debe', 'Haber', 'Total']]
        else:
            df_41212 = pd.DataFrame([])
    except Exception as expt:
        log.append('Error en conexión a DB (41212): ' + repr(expt))

    # Conecto a DB y extraigo datos 8 (41211).
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT cod_mov, num_mov, descripcion, fecha, imp_bas"
                 + " FROM mov_ren"
                 + " WHERE (cuenta IN ('41211'))"
                 + " AND (fecha BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        if datos != ():
            list_41211 = []
            for dic in datos:
                try:
                    list_41211.append({'Fecha': dic['fecha'],
                                       'Partida': partidas[str(int(dic['cod_mov']))
                                                           + '-' + str(int(dic['num_mov']))],
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
                except KeyError:
                    list_41211.append({'Fecha': dic['fecha'],
                                       'Partida': '-',
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})

            df_41211 = pd.DataFrame(list_41211)
            df_41211['Debe'] = df_41211.apply(lambda row: float(row['Importe']) if
            row['Importe'] > 0 else '', axis=1)
            df_41211['Haber'] = df_41211.apply(lambda row: float(row['Importe']) if
            row['Importe'] < 0 else '', axis=1)
            df_41211.replace(r'^\s*$', np.nan, regex=True, inplace=True)
            df_41211.loc[:, 'sumafila'] = df_41211.loc[:, ['Debe', 'Haber']].sum(axis=1, min_count=1)
            df_41211['Total'] = df_41211['sumafila'].cumsum()
            df_41211['Haber'] = df_41211.apply(lambda row: float(row['Haber'] * -1), axis=1)
            df_41211 = df_41211[['Fecha', 'Partida', 'Cod_mov', 'Num_mov', 'Descripción',
                                 'Debe', 'Haber', 'Total']]
        else:
            df_41211 = pd.DataFrame([])
    except Exception as expt:
        log.append('Error en conexión a DB (41211): ' + repr(expt))

    # Conecto a DB y extraigo datos 9 (41207).
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT cod_mov, num_mov, descripcion, fecha, imp_bas"
                 + " FROM mov_ren"
                 + " WHERE (cuenta IN ('41207'))"
                 + " AND (fecha BETWEEN '" + str(anio) + "-" + str(mes).zfill(2)
                 + "-01' AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                 + str(last_day) + "');")

        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        if datos != ():
            list_41207 = []
            for dic in datos:
                try:
                    list_41207.append({'Fecha': dic['fecha'],
                                       'Partida': partidas[str(int(dic['cod_mov']))
                                                           + '-' + str(int(dic['num_mov']))],
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})
                except KeyError:
                    list_41207.append({'Fecha': dic['fecha'],
                                       'Partida': '-',
                                       'Cod_mov': dic['cod_mov'],
                                       'Num_mov': dic['num_mov'],
                                       'Descripción': dic['descripcion'],
                                       'Importe': dic['imp_bas']})

            df_41207 = pd.DataFrame(list_41207)
            df_41207['Debe'] = df_41207.apply(lambda row: float(row['Importe']) if
            row['Importe'] > 0 else '', axis=1)
            df_41207['Haber'] = df_41207.apply(lambda row: float(row['Importe']) if
            row['Importe'] < 0 else '', axis=1)
            df_41207.replace(r'^\s*$', np.nan, regex=True, inplace=True)
            df_41207.loc[:, 'sumafila'] = df_41207.loc[:, ['Debe', 'Haber']].sum(axis=1, min_count=1)
            df_41207['Total'] = df_41207['sumafila'].cumsum()
            df_41207['Haber'] = df_41207.apply(lambda row: float(row['Haber'] * -1), axis=1)
            df_41207 = df_41207[['Fecha', 'Partida', 'Cod_mov', 'Num_mov', 'Descripción',
                                 'Debe', 'Haber', 'Total']]
        else:
            df_41207 = pd.DataFrame([])
    except Exception as expt:
        log.append('Error en conexión a DB (41207): ' + repr(expt))

    try:
        # Set destination directory to save excel.
        xlsFilepath = (settings.MEDIA_ROOT + r'/tmp/' + 'Intereses_discriminados'
                       + str(anio) + str(mes).zfill(2) + '.xlsx')
        writer = pd.ExcelWriter(xlsFilepath, engine='xlsxwriter')
        # Write excel to file using pandas to_excel
        df_41120.to_excel(writer, startrow=0, sheet_name='41120', index=False)
        df_41109.to_excel(writer, startrow=0, sheet_name='41109', index=False)
        df_41203.to_excel(writer, startrow=0, sheet_name='41203', index=False)
        df_41111.to_excel(writer, startrow=0, sheet_name='41111', index=False)
        df_41112.to_excel(writer, startrow=0, sheet_name='41112', index=False)
        df_41208.to_excel(writer, startrow=0, sheet_name='41208', index=False)
        df_41212.to_excel(writer, startrow=0, sheet_name='41212', index=False)
        df_41211.to_excel(writer, startrow=0, sheet_name='41211', index=False)
        df_41207.to_excel(writer, startrow=0, sheet_name='41207', index=False)
        # Indicate workbook and worksheet for formatting
        sheets = ['41120', '41109', '41203', '41111', '41112', '41208', '41212', '41211', '41207']

        for sheet in sheets:
            workbook = writer.book
            worksheet = writer.sheets[sheet]
            # Iterate through each column and set the width == the max length in that column.
            # A padding length of 2 is also added.
            for i, col in enumerate(df_41120.columns):
                # find length of column i
                column_len = df_41120[col].astype(str).str.len().max()
                # Setting the length if the column header is larger
                # than the max column value length
                column_len = max(column_len, len(col)) + 2
                # set the column length
                worksheet.set_column(i, i, column_len)
            format1 = workbook.add_format({'num_format': '#0.00'})
            worksheet.set_column('F:F', None, format1)
            worksheet.set_column('G:G', None, format1)
        writer.save()
    except Exception as expt:
        log.append('Error al generar archivo excel: ' + repr(expt))

    if log:
        with io.open(settings.MEDIA_ROOT + r'/tmp/' + 'Log_' + str(anio)
                     + '-' + str(mes).zfill(2) + '.txt', 'wt', newline='\r\n') as logarch:
            logarch.write('\n'.join(log))
        return (settings.MEDIA_ROOT + r'/tmp/' + 'Log_' + str(anio)
                + '-' + str(mes).zfill(2) + '.txt')
    else:
        return (settings.MEDIA_ROOT + r'/tmp/' + 'Intereses_discriminados'
                + str(anio) + str(mes).zfill(2) + '.xlsx')
