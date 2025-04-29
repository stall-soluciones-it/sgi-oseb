# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 11:15:02 2020.

@author: Daniel
"""
import io
import calendar
from decimal import Decimal as dc
from pymysql import connect, cursors
import pandas as pd
import sgi.shpd_cnf as cnf
from django.conf import settings


def dec(numero):
    """Formato de numero decimal redondeado a dos decimales."""
    num = dc(numero)
    dos_decimales = dc("0.01")
    return num.quantize(dos_decimales)


def process_listado_b_c(tipo1, anio, mes):
    """Procesa listados carenciados o bomberos."""
    log = []
    try:
        anio = int(anio)
        mes = int(mes)
        tipo1 = str(tipo1)
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
        log.append('Error en datos de fecha: ' + repr(expt))
    if tipo1 == 'carenciados':
        tipo = "'DCAA', 'DCAB', 'DCAC', 'DCAT', 'DXMA', 'DXMB', 'DXMC', 'DCB5', 'DCA5'"
    elif tipo1 == 'bomberos':
        tipo = "'DBMA', 'DBMB', 'DBMC', 'DBOA', 'DBOB', 'DBOC'"
    elif tipo1 == 'municipales':
        tipo = "'MMB', 'NMBI', 'NMBM', 'NMAM', 'NMCM'"
    
    desde = str(anio) + "-" + str(mes).zfill(2) + "-01"
    hasta = str(anio) + "-" + str(mes).zfill(2) + "-" + str(last_day)
    # Conecto a DB y extraigo tarifa x unidad.
    try:
        connection = connect(host=cnf.DB_OSEBAL_HOST,
                             user=cnf.DB_SISA_USR,
                             password=cnf.DB_SISA_PASS,
                             db='osebal_produccion',
                             charset='utf8mb4',
                             cursorclass=cursors.DictCursor)
        cursor = cursors.DictCursor(connection)
        if tipo1 == 'municipales':
            query = (
                f"""SELECT 
                    unidad, 
                    ROUND(SUM(CAST(imp_iva AS DECIMAL(10, 2))), 2) AS tarifa
                FROM z80facturado
                WHERE (unidad, num_com) IN (
                    SELECT unidad, num_com
                    FROM z80facturado
                    WHERE cod_ser IN ({tipo})
                    AND tpo_com = 'FC'
                    AND fecha BETWEEN '{desde}' AND '{hasta}'
                )
                AND tpo_com = 'FC'
                AND fecha BETWEEN '{desde}' AND '{hasta}'
                GROUP BY unidad, num_com;"""
            )
        elif tipo1 == 'carenciados' or tipo1 == 'bomberos':
            query = (
                f"""SELECT unidad, tarifa
                FROM z80facturado
                WHERE cod_ser IN ({tipo})
                AND tpo_com IN ('FC')
                AND fecha BETWEEN '{desde}' AND '{hasta}';"""
                )
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as expt:
        log.append('Error en conexión a DB z80facturado: ' + repr(expt))
    # Creo final "unidad: tarifa"
    try:
        final = {}
        monto_total = dec(0)
        cantidad = 0
        for dic in datos:  # noqa
            if tipo1 == 'municipales':
                final[str(dic['unidad'])] = [str(dec(str(dic['tarifa'])))]
                monto_total += dec(str(dic['tarifa']))
                cantidad += 1
            elif tipo1 == 'carenciados' or tipo1 == 'bomberos':
                final[str(dic['unidad'])] = [str(dec(dec(str(dic['tarifa'])) * dec(1.21)))]
                monto_total += dec(dec(str(dic['tarifa'])) * dec(1.21))
                cantidad += 1
    except Exception as expt:
        log.append('Error al crear dic final: ' + repr(expt))
    # Conecto a DB y extraigo domicilio, razon y partida.
    try:
        connection = connect(host=cnf.DB_OSEBAL_HOST,
                             user=cnf.DB_SISA_USR,
                             password=cnf.DB_SISA_PASS,
                             db='osebal_produccion',
                             charset='utf8mb4',
                             cursorclass=cursors.DictCursor)
        cursor = cursors.DictCursor(connection)
        query = ("SELECT unidad, unidad_alt, razon, calle, numero" +
                 " FROM z80unidad;")

        cursor.execute(query)
        unidades = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as expt:
        log.append('Error en conexión a DB z80unidad: ' + repr(expt))
    # Creo listado de datos:
    try:
        unidad = {}
        for dic in unidades:  # noqa
            unidad[str(dic['unidad'])] = [str(dic['unidad_alt']), str(dic['razon']),
                                          str(dic['calle']), str(dic['numero'])]
        # Completo listado final
        for key, value in list(final.items()):  # noqa
            value += unidad[key]
        if tipo1 == 'municipales':
            encabezado = ['PARTIDA', 'RAZON', 'DOMICILIO', 'IMPORTE']
        else:
            encabezado = ['PARTIDA', 'RAZON', 'DOMICILIO', 'DESCUENTO']
        listado_final = []
        for value in final.values():
            listado_final.append([value[1], value[2], value[3] + ' N° ' + value[4],
                                  str(value[0]).replace('.', ',')])
        listado_final.append(['', '', 'TOTAL:', ('%.2f' % monto_total).replace('.', ',')])  # noqa
        listado_final.append(['Cantidad de partidas: ' + str(cantidad), '', '', ''])  # noqa
        df = pd.DataFrame.from_records(listado_final, columns=encabezado)
        df.to_csv(settings.MEDIA_ROOT + r'/list_c_b/' + tipo1 + '_' + str(anio) + '-' +
                  str(mes).zfill(2) + '.csv', index=False, sep=';',
                  columns=encabezado, encoding="cp1252")
    except Exception as expt:
        log.append('Error al crear dic, df y csv final: ' + repr(expt))

    if log:
        with io.open(settings.MEDIA_ROOT + r'/list_c_b/' + 'Log_' + tipo1 + '_' +
                     str(anio) + '-' + str(mes) + '.txt', 'wt', newline='\r\n') as logarch:
            logarch.write('\n'.join(log))
        return (settings.MEDIA_ROOT + r'/list_c_b/' + 'Log_' + tipo1 + '_' +
                str(anio) + '-' + str(mes) + '.txt')
    else:
        return (settings.MEDIA_ROOT + r'/list_c_b/' + tipo1 + '_' + str(anio) +
                '-' + str(mes).zfill(2) + '.csv')
