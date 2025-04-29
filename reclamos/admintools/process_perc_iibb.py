# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 12:42:19 2020.

@author: Daniel
"""
import datetime
import io
import os
import zipfile
import hashlib
import calendar
from decimal import Decimal as dc
import pymysql
import sgi.shpd_cnf as cnf
from django.conf import settings


def md5(fname):
    """Genero hash."""
    hash_md5 = hashlib.md5()
    with open(fname, 'rb') as fff:
        for chunk in iter(lambda: fff.read(4096), b''):
            hash_md5.update(chunk)
    return str(hash_md5.hexdigest()).upper()


def process_perc_iibb(anio, mes, quincena):
    """Procesa presentación perc. IIBB."""
    # Constantes y comprobaciones.
    log = []
    try:
        anio = int(anio)
        mes = int(mes)
        quincena = int(quincena)
        if 2017 <= anio <= 2040:
            pass
        else:
            log.append('ERROR: El año "' + str(anio) + '" es incorrecto.')
        if 1 <= mes <= 12:
            pass
        else:
            log.append('ERROR: El mes "' + str(mes) + '" es incorrecto.')
        if 1 <= quincena <= 2:
            pass
        else:
            log.append('ERROR: La quincena "' + str(quincena) + '" es incorrecta.')

        last_day = int(calendar.monthrange(anio, mes)[1])
        date_ref = datetime.date(2017, 1, 1)
        date = datetime.date(anio, mes, 1)
    except Exception as expt:
        log.append('Error en datos de fecha: ' + repr(expt))
    # z80cpd_pi_#######:
    tab = 35
    cuenta_iter = []
    try:
        while (date.year != date_ref.year) or (date.month != date_ref.month):
            tabla = str(tab).zfill(7)
            try:
                connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                             user=cnf.DB_SISA_USR,
                                             password=cnf.DB_SISA_PASS,
                                             db='osebal_produccion',
                                             charset='utf8mb4',
                                             cursorclass=pymysql.cursors.DictCursor)
                cursor = pymysql.cursors.DictCursor(connection)
                if quincena == 1:
                    rango_fechas = ("'" + str(anio) + "-" + str(mes).zfill(2) + "-" + "01'"
                                    + " AND '" + str(anio) + "-" + str(mes).zfill(2) + "-15'")
                elif quincena == 2:
                    rango_fechas = ("'" + str(anio) + "-" + str(mes).zfill(2) + "-" + "15'"
                                    + " AND '" + str(anio) + "-" + str(mes).zfill(2) + "-"
                                    + str(last_day) + "'")
                query = ("SELECT unidad, cod_ser, tpo_com, pre_com, num_com,"
                         + " cod_mov, num_mov, importe_cob, fec_cob"
                         + " FROM z80cpd_pi_" + tabla
                         + " WHERE (cod_ser NOT IN ('IRBC', 'I10', 'I21', 'I27'))"
                         + " AND (estado = 'C')"
                         + " AND (tpo_com IN ('FC', 'NC', 'NCPP', 'FCPP', 'DR'))"
                         + " AND (fec_cob BETWEEN " + rango_fechas + ");")
                cursor.execute(query)
                datos_cpd = cursor.fetchall()
                cursor.close()
                connection.close()
                date_ref = datos_cpd[0]['fec_cob']
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
    # Creo diccinario "comprobante: unidad, gravado, fecha, imp".
    try:
        dic_cpd = {}
        for dic in datos_cpd:
            comprobante = (str(dic['cod_mov']) + str(dic['num_mov'])
                           + '-' + str(dic['tpo_com']) + str(dic['pre_com'])
                           + str(dic['num_com']))
            unidad = str(dic['unidad'])
            gravado = str(dic['importe_cob'])
            fecha = str(dic['fec_cob'])
            imp = str(dic['importe_cob'])

            if dic['cod_ser'] != 'PIB' and dc(imp) != dc(0):
                if comprobante not in dic_cpd:
                    dic_cpd[comprobante] = [unidad, gravado, fecha, str(0)]
                elif (dic_cpd[comprobante][0] == unidad and dic_cpd[comprobante][2] == fecha):
                    dic_cpd[comprobante] = [unidad, str(dc(dic_cpd[comprobante][1])
                                                        + dc(gravado)), fecha,
                                            dic_cpd[comprobante][3]]
                else:
                    log.append('Error en armado de diccionario CPD, revisar...' + comprobante)
            elif dic['cod_ser'] == 'PIB' and dc(imp) != dc(0):
                if comprobante not in dic_cpd:
                    dic_cpd[comprobante] = [unidad, str(0), fecha, imp]
                elif (dic_cpd[comprobante][0] == unidad and dic_cpd[comprobante][2] == fecha):
                    dic_cpd[comprobante] = [unidad, dic_cpd[comprobante][1], fecha,
                                            str(dc(dic_cpd[comprobante][3]) + dc(imp))]
                else:
                    log.append('Error en armado de diccionario CPD, revisar...' + comprobante)
    except Exception as expt:
        log.append('Error al armar diccionario CPD: ' + repr(expt))
    # Creo dic final y filtro PIB == 0:
    try:
        dic_cpd_fin = {}
        for key, value in list(dic_cpd.items()):
            if value[3] != '0':
                dic_cpd_fin[key[key.find('-') + 1:]] = value
    except Exception as expt:
        log.append('Error al crear dic cpd_fin: ' + repr(expt))

    # z80facturas_elec:
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT tpo_doc_tit_ser, num_doc_tit_ser, id_imp_tit_ser,"
                 + " tpo_com, pre_com, num_com, pre_com_elec, num_com_elec"
                 + " FROM z80facturas_elec"
                 + " WHERE tpo_com IN ('FC', 'NC', 'NCPP', 'FCPP', 'DR')"
                 + " AND num_doc_tit_ser != '0';")
        cursor.execute(query)
        fact_elect = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as expt:
        log.append('Error al conectar DB z80facturas_elec: ' + repr(expt))

    # Creo dic "comprobante: cuit, tipo_comp, letra_comp, pto_vta, numero"
    try:
        facturas = {}
        for dic in fact_elect:
            comprobante = (str(dic['tpo_com']) + str(dic['pre_com'])
                           + str(dic['num_com']))
            if comprobante in dic_cpd_fin.keys():
                cuit = str(dic['num_doc_tit_ser'])
                tipo_comp = str(dic['tpo_com'])
                letra_comp = str(dic['id_imp_tit_ser'])
                pto_vta = str(dic['pre_com_elec'])
                numero = str(dic['num_com_elec'])

                if tipo_comp == 'FC':
                    tipo_comp = 'F'
                elif tipo_comp == 'NC':
                    tipo_comp = 'C'
                elif tipo_comp == 'NCPP':
                    tipo_comp = 'C'
                elif tipo_comp == 'FCPP':
                    tipo_comp = 'F'
                elif tipo_comp == 'DR':
                    tipo_comp = 'D'

                if letra_comp == '06':
                    letra_comp = 'B'
                elif letra_comp == '01':
                    letra_comp = 'A'
                if len(cuit) == 11:
                    facturas[comprobante] = [cuit, tipo_comp, letra_comp, pto_vta, numero]
                else:
                    pass
            else:
                pass
    except Exception as expt:
        log.append('Error al cread dic facturas: ' + repr(expt))

    # Z80unidad:
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT unidad, num_doc, tpo_iva"
                 + " FROM z80unidad;")
        cursor.execute(query)
        unidades = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as expt:
        log.append('Error al conectar DB z80unidad: ' + repr(expt))
    # Creo diccionario "unidad: cuit, tpo_iva".
    try:
        cuits = {}
        for dic in unidades:
            cuits[str(dic['unidad'])] = [str(dic['num_doc']), str(dic['tpo_iva'])]
    except Exception as expt:
        log.append('Error al crear dic unidades: ' + repr(expt))

    # Creo lineas del archivo final:
    try:
        final = []
        for key, value in dic_cpd_fin.items():
            if key in facturas.keys():
                line = ''
                line += ((facturas[key][0])[0:2] + '-' + (facturas[key][0])[2:10] + '-'
                         + (facturas[key][0])[10])
                line += (value[2][8:10] + r'/' + value[2][5:7] + r'/'
                         + value[2][0:4])
                line += (facturas[key][1])
                line += (facturas[key][2])
                line += facturas[key][3].zfill(4)
                line += facturas[key][4].zfill(8)
                if facturas[key][1] == 'C':
                    line += '-' + (value[1]).replace('-', '').zfill(11)
                else:
                    line += (value[1]).zfill(12)
                if facturas[key][1] == 'C':
                    line += '-' + (value[3]).replace('-', '').zfill(10)
                else:
                    line += (value[3]).zfill(11)
                line += (value[2][8:10] + r'/' + value[2][5:7] + r'/'
                         + value[2][0:4])
                line += ('A')
                final.append(line)
            else:
                if len(cuits[value[0]][0]) == 11:
                    line = ''
                    line += (cuits[value[0]][0][0:2] + '-' + cuits[value[0]][0][2:10]
                             + '-' + cuits[value[0]][0][10])
                    line += (value[2][8:10] + r'/' + value[2][5:7] + r'/' + value[2][0:4])
                    if ''.join(x for x in key if x.isalpha()) == 'FC':
                        line += 'F'
                    elif ''.join(x for x in key if x.isalpha()) == 'NC':
                        line += 'C'
                    elif ''.join(x for x in key if x.isalpha()) == 'NCPP':
                        line += 'C'
                    elif ''.join(x for x in key if x.isalpha()) == 'FCPP':
                        line += 'F'
                    elif ''.join(x for x in key if x.isalpha()) == 'DR':
                        line += 'D'
                    if cuits[value[0]][1] == 'RI':
                        line += 'A'
                    elif cuits[value[0]][1] == 'MO':
                        line += 'B'
                    line += (''.join(x for x in key if x.isdigit()))[0:4].zfill(4)
                    line += (''.join(x for x in key if x.isdigit()))[4:].zfill(8)
                    if ''.join(x for x in key if x.isalpha()) == 'NC':
                        line += '-' + (value[1]).replace('-', '').zfill(11)
                    else:
                        line += (value[1]).zfill(12)
                    if ''.join(x for x in key if x.isalpha()) == 'NC':
                        line += '-' + (value[3]).replace('-', '').zfill(10)
                    else:
                        line += (value[3]).zfill(11)
                    line += (value[2][8:10] + r'/' + value[2][5:7] + r'/' + value[2][0:4])
                    line += ('A')
                    final.append(line)
                else:
                    pass
    except Exception as expt:
        log.append('Error al crear lineas finales: ' + repr(expt))

    NAME = 'AR-30677286314-' + str(anio) + str(mes).zfill(2) + str(quincena) + '-7-LOTE1'
    try:
        with io.open(settings.MEDIA_ROOT + r'/tmp/'
                     + NAME + '.txt', 'wt', newline='\r\n') as archivo:
            archivo.write('\n'.join(final))
    except Exception as expt:
        log.append('Error al crear archivo final: ' + repr(expt))

    try:
        try:
            ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/perc_iibb/' + NAME + '.zip',
                                       mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/perc_iibb/' + NAME + '.zip')
            ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/perc_iibb/' + NAME + '.zip',
                                       mode='x', compression=zipfile.ZIP_DEFLATED)
        ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/' + NAME + '.txt',
                       os.path.basename(settings.MEDIA_ROOT + r'/tmp/' + NAME + '.txt'))
        ARCH_ZIP.close()
    except Exception as expt:
        log.append('Error al zipear archivo: ' + repr(expt))
    try:
        md5str = str(md5(settings.MEDIA_ROOT + r'/perc_iibb/' + NAME + '.zip'))
        os.rename(settings.MEDIA_ROOT + r'/perc_iibb/' + NAME + '.zip',
                  settings.MEDIA_ROOT + r'/perc_iibb/' + NAME + '_' + md5str + '.zip')
        os.remove(settings.MEDIA_ROOT + r'/tmp/' + NAME + '.txt')
    except Exception as expt:
        log.append('Error al generar hash, renombrar y eliminar txt: ' + repr(expt))

    if log:
        with io.open(settings.MEDIA_ROOT + r'/perc_iibb/' + 'Log_' + NAME
                     + '.txt', 'wt', newline='\r\n') as logarch:
            logarch.write('\n'.join(log))
        return settings.MEDIA_ROOT + r'/perc_iibb/' + 'Log_' + NAME + '.txt'
    else:
        return settings.MEDIA_ROOT + r'/perc_iibb/' + NAME + '_' + md5str + '.zip'
