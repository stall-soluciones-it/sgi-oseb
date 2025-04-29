# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 09:07:43 2020.

@author: Daniel
"""
import os
import io
import hashlib
import datetime
from decimal import Decimal as dc
import zipfile
import pymysql
import sgi.shpd_cnf as cnf
from django.conf import settings


log = []


def md5(fname):
    """Genero hash."""
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return str(hash_md5.hexdigest()).upper()


def process_pres_cuat_arba(anio, cuatrimestre):
    """Genera archivo para presentar a arba cuatrimestralmente."""
    # Entradas
    try:
        anio = int(anio)
        cuatrimestre = int(cuatrimestre)
        if 2017 <= anio <= 2040:
            pass
        else:
            log.append('ERROR: El año "' + str(anio) + '" es incorrecto.')
        if cuatrimestre in [1, 2, 3]:
            pass
        else:
            log.append('ERROR: El cuatrimestre "' + str(cuatrimestre) + '" es incorrecto.')
    except Exception as expt:
        log.append('Error en datos de fecha: ' + repr(expt))

    if cuatrimestre == 1:
        per_desde = datetime.date(anio, 1, 1)
        per_hasta = datetime.date(anio, 4, 30)
        mes1 = 1
        mes2 = 2
        mes3 = 3
        mes4 = 4
    elif cuatrimestre == 2:
        per_desde = datetime.date(anio, 4, 1)
        per_hasta = datetime.date(anio, 8, 31)
        mes1 = 5
        mes2 = 6
        mes3 = 7
        mes4 = 8
    if cuatrimestre == 3:
        per_desde = datetime.date(anio, 9, 1)
        per_hasta = datetime.date(anio, 12, 31)
        mes1 = 9
        mes2 = 10
        mes3 = 11
        mes4 = 12

    # Datos unidades (z80unidad):
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT unidad, num_doc, tpo_doc, razon, calle, numero"
                 + " FROM z80unidad;")
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        unidad = {}
        for dic in datos:
            # Unidad:
            uni = str(dic['unidad'])

            # Tipo documento:
            if str(dic['tpo_doc']) == 'CUIT':
                tpo_doc = '0'
            else:
                tpo_doc = '1'

            # Cuit:
            if tpo_doc == '0':
                if len(str(dic['num_doc'])) == 11:
                    cuit = str(dic['num_doc'])
                else:
                    cuit = '00000000000'
                    tpo_doc = '1'
            else:
                cuit = '00000000000'

            # Documento:
            if tpo_doc == '1':
                if str(dic['num_doc']) == '0':
                    num_doc = '99999999'
                else:
                    if len(str(dic['num_doc'])) < 8:
                        num_doc = str(dic['num_doc']).zfill(8)
                    elif len(str(dic['num_doc'])) == 8:
                        num_doc = str(dic['num_doc'])
                    elif len(str(dic['num_doc'])) > 8:
                        num_doc = str(dic['num_doc'])[2:10]
            else:
                if (str(dic['num_doc'])[0] == '2') and (len(str(dic['num_doc'])) == 11):
                    num_doc = str(dic['num_doc'])[2:10]
                    tpo_doc = '1'
                else:
                    tpo_doc = '0'
                    num_doc = '00000000'

            # Razon:
            if len(str(dic['razon'])) > 50:
                razon = str(dic['razon'])[0:50].replace('Ñ', 'N').replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
            else:
                razon = str(dic['razon']).ljust(50, ' ').replace('Ñ', 'N').replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')

            # Calle:
            if len(str(dic['calle'])) > 30:
                calle = '10000000000' + str(dic['calle'])[0:30]
            else:
                calle = '10000000000' + str(dic['calle']).ljust(30, ' ')

            # Numero:
            if int(dic['numero']) == 0:
                numero = '00000' + '1     7620Balcarce                      '
            else:
                if len(str(dic['numero'])) > 5:
                    numero = str(dic['numero'])[0:5] + '0     7620Balcarce                      '
                else:
                    numero = (str(dic['numero']).zfill(5)
                              + '0     7620Balcarce                      ')

            # Fin:
            fin = '0000000000' + '0000000000000000000000000000@0000000.com' + 'A'

            unidad[uni] = [cuit + tpo_doc + num_doc + razon, calle + numero + fin]

    except Exception as expt:
        log.append('Error al consultar DB z80unidad: ' + str(expt))

    # Tipo de prestación (z80facturado):
    terreno = ['ACER', 'ACPC', 'ATA', 'ATB', 'ATC', 'ATPC', 'BCER', 'CCER']
    comercial = ['ATMO', 'MCA', 'MCB', 'MCPC', 'NCAA', 'NCAB', 'NCAD', 'NCAI', 'NCAM', 'NCBA',
                 'NCBB', 'NCBD', 'NCBI', 'NCBM', 'NCCA', 'NCCB', 'NCCD', 'NCCI', 'NCCM', 'NCPC']
    residencial = ['MRA', 'MRB', 'MRPC', 'NDAI', 'NDBI', 'NDPC', 'NRAA', 'NRAB', 'NRAD', 'NRAI',
                   'NRAM', 'NRBA', 'NRBB', 'NRBD', 'NRBI', 'NRBM', 'NRCA', 'NRCB', 'NRCD', 'NRCI',
                   'NRCM', 'NRPC']
    codigos = terreno + comercial + residencial
    codigos_str = '('
    for item in codigos:
        codigos_str += "'" + item + "', "
    codigos_str += 'ult'
    codigos_str = codigos_str.replace(', ult', ')')
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT unidad, cod_ser, fecha"
                 + " FROM z80facturado"
                 + " WHERE fecha BETWEEN '" + str(per_desde.year) + "-"
                 + str(per_desde.month).zfill(2) + "-" + str(per_desde.day).zfill(2) + "' AND '"
                 + str(per_hasta.year) + "-" + str(per_hasta.month).zfill(2) + "-"
                 + str(per_hasta.day).zfill(2) + "'"
                 + " AND cod_ser IN " + codigos_str + ";")
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        cod_ser1 = {}
        cod_ser2 = {}
        cod_ser3 = {}
        cod_ser4 = {}
        for dic in datos:
            if dic['fecha'].month == mes1:
                if str(dic['cod_ser']) in terreno:
                    cod_ser1[str(dic['unidad'])] = '4'
                elif str(dic['cod_ser']) in comercial:
                    cod_ser1[str(dic['unidad'])] = '2'
                elif str(dic['cod_ser']) in residencial:
                    cod_ser1[str(dic['unidad'])] = '1'
            elif dic['fecha'].month == mes2:
                if str(dic['cod_ser']) in terreno:
                    cod_ser2[str(dic['unidad'])] = '4'
                elif str(dic['cod_ser']) in comercial:
                    cod_ser2[str(dic['unidad'])] = '2'
                elif str(dic['cod_ser']) in residencial:
                    cod_ser2[str(dic['unidad'])] = '1'
            elif dic['fecha'].month == mes3:
                if str(dic['cod_ser']) in terreno:
                    cod_ser3[str(dic['unidad'])] = '4'
                elif str(dic['cod_ser']) in comercial:
                    cod_ser3[str(dic['unidad'])] = '2'
                elif str(dic['cod_ser']) in residencial:
                    cod_ser3[str(dic['unidad'])] = '1'
            elif dic['fecha'].month == mes4:
                if str(dic['cod_ser']) in terreno:
                    cod_ser4[str(dic['unidad'])] = '4'
                elif str(dic['cod_ser']) in comercial:
                    cod_ser4[str(dic['unidad'])] = '2'
                elif str(dic['cod_ser']) in residencial:
                    cod_ser4[str(dic['unidad'])] = '1'
    except Exception as expt:
        log.append('Error al consultar DB z80facturado: ' + str(expt))

    # Montos (z80facturas_elec):
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT usuario, fec_emi, cf_sin_subsidio"
                 + " FROM z80facturas_elec"
                 + " WHERE fec_emi BETWEEN '" + str(per_desde.year) + "-"
                 + str(per_desde.month).zfill(2) + "-" + str(per_desde.day).zfill(2) + "' AND '"
                 + str(per_hasta.year) + "-" + str(per_hasta.month).zfill(2) + "-"
                 + str(per_hasta.day).zfill(2) + "'"
                 + " AND pre_com_elec IN ('0100');")
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        monto1 = {}
        monto2 = {}
        monto3 = {}
        monto4 = {}
        for dic in datos:
            if dic['fec_emi'].month == mes1:
                if str(dic['usuario']) not in monto1.keys():
                    monto1[str(dic['usuario'])] = dc(dic['cf_sin_subsidio'])
                else:
                    monto1[str(dic['usuario'])] += dc(dic['cf_sin_subsidio'])
            if dic['fec_emi'].month == mes2:
                if str(dic['usuario']) not in monto2.keys():
                    monto2[str(dic['usuario'])] = dc(dic['cf_sin_subsidio'])
                else:
                    monto2[str(dic['usuario'])] += dc(dic['cf_sin_subsidio'])
            if dic['fec_emi'].month == mes3:
                if str(dic['usuario']) not in monto3.keys():
                    monto3[str(dic['usuario'])] = dc(dic['cf_sin_subsidio'])
                else:
                    monto3[str(dic['usuario'])] += dc(dic['cf_sin_subsidio'])
            if dic['fec_emi'].month == mes4:
                if str(dic['usuario']) not in monto4.keys():
                    monto4[str(dic['usuario'])] = dc(dic['cf_sin_subsidio'])
                else:
                    monto4[str(dic['usuario'])] += dc(dic['cf_sin_subsidio'])
    except Exception as expt:
        log.append('Error al consultar DB z80facturas_elec: ' + str(expt))

    # ARMO ARCHIVOS:
    try:
        # 1
        lineas1 = []
        for key, value in monto1.items():
            try:
                if (value < 2000) and (cod_ser1[key] != '2'):
                    pass
                else:
                    linea = (unidad[key][0]
                             + cod_ser1[key]
                             + str(value).replace('.', ',').zfill(13)
                             + unidad[key][1])
                    lineas1.append(linea)
            except KeyError:
                pass

        # 2
        lineas2 = []
        for key, value in monto2.items():
            try:
                if (value < 2000) and (cod_ser2[key] != '2'):
                    pass
                else:
                    linea = (unidad[key][0]
                             + cod_ser2[key]
                             + str(value).replace('.', ',').zfill(13)
                             + unidad[key][1])
                    lineas2.append(linea)
            except KeyError:
                pass
        # 3
        lineas3 = []
        for key, value in monto3.items():
            try:
                if (value < 2000) and (cod_ser3[key] != '2'):
                    pass
                else:
                    linea = (unidad[key][0]
                             + cod_ser3[key]
                             + str(value).replace('.', ',').zfill(13)
                             + unidad[key][1])
                    lineas3.append(linea)
            except KeyError:
                pass
        # 4
        lineas4 = []
        for key, value in monto4.items():
            try:
                if (value < 2000) and (cod_ser4[key] != '2'):
                    pass
                else:
                    linea = (unidad[key][0]
                             + cod_ser4[key]
                             + str(value).replace('.', ',').zfill(13)
                             + unidad[key][1])
                    lineas4.append(linea)
            except KeyError:
                pass
    except Exception as expt:
        log.append('Error al armar archivo 1: ' + str(expt))

    try:
        with io.open(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio) + str(cuatrimestre).zfill(2)
                     + '-01-02-lote1.txt',
                     'wt', newline='\r\n') as arch1:
            arch1.write('\n'.join(lineas1))
        with io.open(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio) + str(cuatrimestre).zfill(2)
                     + '-01-02-lote2.txt',
                     'wt', newline='\r\n') as arch2:
            arch2.write('\n'.join(lineas2))
        with io.open(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio) + str(cuatrimestre).zfill(2)
                     + '-01-02-lote3.txt',
                     'wt', newline='\r\n') as arch3:
            arch3.write('\n'.join(lineas3))
        with io.open(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio) + str(cuatrimestre).zfill(2)
                     + '-01-02-lote4.txt',
                     'wt', newline='\r\n') as arch4:
            arch4.write('\n'.join(lineas4))
    except Exception as expt:
        log.append('Error al escribir los TXT: ' + str(expt))

    try:
        try:  # 1
            ARCH_ZIP1 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote1.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                      + str(anio) + str(cuatrimestre).zfill(2)
                      + '-01-02-lote1.zip')
            ARCH_ZIP1 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote1.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        ARCH_ZIP1.write(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio)
                        + str(cuatrimestre).zfill(2) + '-01-02-lote1.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio)
                                         + str(cuatrimestre).zfill(2) + '-01-02-lote1.txt'))
        ARCH_ZIP1.close()

        try:  # 2
            ARCH_ZIP2 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote2.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                      + str(anio) + str(cuatrimestre).zfill(2)
                      + '-01-02-lote2.zip')
            ARCH_ZIP2 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote2.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        ARCH_ZIP2.write(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio)
                        + str(cuatrimestre).zfill(2) + '-01-02-lote2.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio)
                                         + str(cuatrimestre).zfill(2) + '-01-02-lote2.txt'))
        ARCH_ZIP2.close()

        try:  # 3
            ARCH_ZIP3 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote3.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                      + str(anio) + str(cuatrimestre).zfill(2)
                      + '-01-02-lote3.zip')
            ARCH_ZIP3 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote3.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        ARCH_ZIP3.write(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio)
                        + str(cuatrimestre).zfill(2) + '-01-02-lote3.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio)
                                         + str(cuatrimestre).zfill(2) + '-01-02-lote3.txt'))
        ARCH_ZIP3.close()

        try:  # 4
            ARCH_ZIP4 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote4.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                      + str(anio) + str(cuatrimestre).zfill(2)
                      + '-01-02-lote4.zip')
            ARCH_ZIP4 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote4.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        ARCH_ZIP4.write(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio)
                        + str(cuatrimestre).zfill(2) + '-01-02-lote4.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-' + str(anio)
                                         + str(cuatrimestre).zfill(2) + '-01-02-lote4.txt'))
        ARCH_ZIP4.close()

        try:  # FINAL
            ARCH_ZIP_FINAL = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/Arba_cuat_' + str(anio) + str(cuatrimestre).zfill(2) + '.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/tmp/Arba_cuat_' + str(anio)
                      + str(cuatrimestre).zfill(2) + '.zip')
            ARCH_ZIP_FINAL = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/Arba_cuat_' + str(anio)
                                             + str(cuatrimestre).zfill(2) + '.zip',
                                             mode='x', compression=zipfile.ZIP_DEFLATED)

        HASH1 = md5(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote1.zip')
        HASH2 = md5(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote2.zip')
        HASH3 = md5(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote3.zip')
        HASH4 = md5(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote4.zip')
        os.rename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote1.zip',
                                      settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote1_' + HASH1 + '.zip')
        os.rename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote2.zip',
                                      settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote2_' + HASH2 + '.zip')
        os.rename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote3.zip',
                                      settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote3_' + HASH3 + '.zip')
        os.rename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote4.zip',
                                      settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote4_' + HASH4 + '.zip')

        ARCH_ZIP_FINAL.write(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                             + str(anio) + str(cuatrimestre).zfill(2)
                             + '-01-02-lote1_' + HASH1 + '.zip',
                             os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                              + str(anio) + str(cuatrimestre).zfill(2)
                                              + '-01-02-lote1_' + HASH1 + '.zip'))
        ARCH_ZIP_FINAL.write(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                             + str(anio) + str(cuatrimestre).zfill(2)
                             + '-01-02-lote2_' + HASH2 + '.zip',
                             os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                              + str(anio) + str(cuatrimestre).zfill(2)
                                              + '-01-02-lote2_' + HASH2 + '.zip'))
        ARCH_ZIP_FINAL.write(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                             + str(anio) + str(cuatrimestre).zfill(2)
                             + '-01-02-lote3_' + HASH3 + '.zip',
                             os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                              + str(anio) + str(cuatrimestre).zfill(2)
                                              + '-01-02-lote3_' + HASH3 + '.zip'))
        ARCH_ZIP_FINAL.write(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                             + str(anio) + str(cuatrimestre).zfill(2)
                             + '-01-02-lote4_' + HASH4 + '.zip',
                             os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-30677286314-'
                                              + str(anio) + str(cuatrimestre).zfill(2)
                                              + '-01-02-lote4_' + HASH4 + '.zip'))
        ARCH_ZIP_FINAL.close()

    except Exception as expt:
        log.append('Error al crear archivo zip: ' + repr(expt))

    if log:
        with io.open(settings.MEDIA_ROOT + r'/tmp/Log_cuat_arba_'
                     + str(anio) + str(cuatrimestre).zfill(2) + '.txt',
                     'wt', newline='\r\n') as log_arch:
            log_arch.write('\n'.join(log))
        return settings.MEDIA_ROOT + r'/tmp/Log_cuat_arba_' + str(anio) + str(cuatrimestre).zfill(2) + '.txt'
    else:
        return settings.MEDIA_ROOT + r'/tmp/Arba_cuat_' + str(anio) + str(cuatrimestre).zfill(2) + '.zip'
