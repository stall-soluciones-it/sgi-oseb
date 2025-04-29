# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 09:07:43 2020.

@author: Daniel
"""
import os
import re
import io
import hashlib
import datetime
from decimal import Decimal as Dc
import zipfile
from pymysql import cursors, connect
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


def process_pres_cuat_arba_osebal(anio, cuatrimestre):
    """Genera archivo para presentar a arba cuatrimestralmente."""
    # Entradas
    min_imp = False
    try:
        anio = int(anio)
        cuatrimestre = int(cuatrimestre)
        if anio < 2023:
            min_imp = 2000
        else:
            min_imp = 4000
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

    per_desde = False
    per_hasta = False
    mes1 = False
    mes2 = False
    mes3 = False
    mes4 = False
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
    unidad = {}
    try:
        connection = connect(host=cnf.DB_OSEBAL_HOST,
                             user=cnf.DB_SISA_USR,
                             password=cnf.DB_SISA_PASS,
                             db='osebal_produccion',
                             charset='utf8mb4',
                             cursorclass=cursors.DictCursor)
        cursor = cursors.DictCursor(connection)
        query = ("SELECT unidad, num_doc, tpo_doc, razon, calle, numero"
                 + " FROM z80unidad;")
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
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
            num_doc = False
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
            razon1 = (str(dic['razon']).replace('Ñ', 'N').replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
                      .replace('Ó', 'O').replace('Ú', 'U'))
            razon = str(re.sub('[^qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890 ]', '', razon1)
                        )[0:50].ljust(50, ' ')

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

    cod_ser1 = {}
    cod_ser2 = {}
    cod_ser3 = {}
    cod_ser4 = {}
    try:
        connection = connect(host=cnf.DB_OSEBAL_HOST,
                             user=cnf.DB_SISA_USR,
                             password=cnf.DB_SISA_PASS,
                             db='osebal_produccion',
                             charset='utf8mb4',
                             cursorclass=cursors.DictCursor)
        cursor = cursors.DictCursor(connection)
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
    monto1 = {}
    monto2 = {}
    monto3 = {}
    monto4 = {}
    try:
        connection = connect(host=cnf.DB_OSEBAL_HOST,
                             user=cnf.DB_SISA_USR,
                             password=cnf.DB_SISA_PASS,
                             db='osebal_produccion',
                             charset='utf8mb4',
                             cursorclass=cursors.DictCursor)
        cursor = cursors.DictCursor(connection)
        query = ("SELECT usuario, fec_emi, cf_sin_subsidio"
                 + " FROM z80facturas_elec"
                 + " WHERE fec_emi BETWEEN '" + str(per_desde.year) + "-"
                 + str(per_desde.month).zfill(2) + "-" + str(per_desde.day).zfill(2) + "' AND '"
                 + str(per_hasta.year) + "-" + str(per_hasta.month).zfill(2) + "-"
                 + str(per_hasta.day).zfill(2) + "'"
                 + " AND pre_com_elec IN ('0003', '0004');")
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        for dic in datos:
            if dic['fec_emi'].month == mes1:
                if str(dic['usuario']) not in monto1.keys():
                    monto1[str(dic['usuario'])] = Dc(dic['cf_sin_subsidio'])
                else:
                    monto1[str(dic['usuario'])] += Dc(dic['cf_sin_subsidio'])
            if dic['fec_emi'].month == mes2:
                if str(dic['usuario']) not in monto2.keys():
                    monto2[str(dic['usuario'])] = Dc(dic['cf_sin_subsidio'])
                else:
                    monto2[str(dic['usuario'])] += Dc(dic['cf_sin_subsidio'])
            if dic['fec_emi'].month == mes3:
                if str(dic['usuario']) not in monto3.keys():
                    monto3[str(dic['usuario'])] = Dc(dic['cf_sin_subsidio'])
                else:
                    monto3[str(dic['usuario'])] += Dc(dic['cf_sin_subsidio'])
            if dic['fec_emi'].month == mes4:
                if str(dic['usuario']) not in monto4.keys():
                    monto4[str(dic['usuario'])] = Dc(dic['cf_sin_subsidio'])
                else:
                    monto4[str(dic['usuario'])] += Dc(dic['cf_sin_subsidio'])
    except Exception as expt:
        log.append('Error al consultar DB z80facturas_elec: ' + str(expt))

    # ARMO ARCHIVOS:
    lineas1 = False
    lineas2 = False
    lineas3 = False
    lineas4 = False
    try:
        # 1
        lineas1 = []
        for key, value in monto1.items():
            try:
                if (value < min_imp) and (cod_ser1[key] != '2'):
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
                if (value < min_imp) and (cod_ser2[key] != '2'):
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
                if (value < min_imp) and (cod_ser3[key] != '2'):
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
                if (value < min_imp) and (cod_ser4[key] != '2'):
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
        with io.open(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio) + str(cuatrimestre).zfill(2)
                     + '-01-02-lote1.txt',
                     'wt', newline='\r\n') as arch1:
            arch1.write('\n'.join(lineas1))
        with io.open(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio) + str(cuatrimestre).zfill(2)
                     + '-01-02-lote2.txt',
                     'wt', newline='\r\n') as arch2:
            arch2.write('\n'.join(lineas2))
        with io.open(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio) + str(cuatrimestre).zfill(2)
                     + '-01-02-lote3.txt',
                     'wt', newline='\r\n') as arch3:
            arch3.write('\n'.join(lineas3))
        with io.open(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio) + str(cuatrimestre).zfill(2)
                     + '-01-02-lote4.txt',
                     'wt', newline='\r\n') as arch4:
            arch4.write('\n'.join(lineas4))
    except Exception as expt:
        log.append('Error al escribir los TXT: ' + str(expt))

    try:
        try:  # 1
            arch_zip1 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote1.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                      + str(anio) + str(cuatrimestre).zfill(2)
                      + '-01-02-lote1.zip')
            arch_zip1 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote1.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        arch_zip1.write(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio)
                        + str(cuatrimestre).zfill(2) + '-01-02-lote1.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio)
                                         + str(cuatrimestre).zfill(2) + '-01-02-lote1.txt'))
        arch_zip1.close()

        try:  # 2
            arch_zip2 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote2.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                      + str(anio) + str(cuatrimestre).zfill(2)
                      + '-01-02-lote2.zip')
            arch_zip2 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote2.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        arch_zip2.write(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio)
                        + str(cuatrimestre).zfill(2) + '-01-02-lote2.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio)
                                         + str(cuatrimestre).zfill(2) + '-01-02-lote2.txt'))
        arch_zip2.close()

        try:  # 3
            arch_zip3 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote3.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                      + str(anio) + str(cuatrimestre).zfill(2)
                      + '-01-02-lote3.zip')
            arch_zip3 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote3.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        arch_zip3.write(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio)
                        + str(cuatrimestre).zfill(2) + '-01-02-lote3.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio)
                                         + str(cuatrimestre).zfill(2) + '-01-02-lote3.txt'))
        arch_zip3.close()

        try:  # 4
            arch_zip4 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote4.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                      + str(anio) + str(cuatrimestre).zfill(2)
                      + '-01-02-lote4.zip')
            arch_zip4 = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote4.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
        arch_zip4.write(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio)
                        + str(cuatrimestre).zfill(2) + '-01-02-lote4.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-' + str(anio)
                                         + str(cuatrimestre).zfill(2) + '-01-02-lote4.txt'))
        arch_zip4.close()

        try:  # FINAL
            arch_zip_final = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/Arba_cuat_' +
                                             str(anio) + str(cuatrimestre).zfill(2) + '.zip',
                                             mode='x', compression=zipfile.ZIP_DEFLATED)
        except FileExistsError:
            os.remove(settings.MEDIA_ROOT + r'/tmp/Arba_cuat_' + str(anio)
                      + str(cuatrimestre).zfill(2) + '.zip')
            arch_zip_final = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/Arba_cuat_' + str(anio)
                                             + str(cuatrimestre).zfill(2) + '.zip',
                                             mode='x', compression=zipfile.ZIP_DEFLATED)

        hash1 = md5(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote1.zip')
        hash2 = md5(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote2.zip')
        hash3 = md5(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote3.zip')
        hash4 = md5(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                        + str(anio) + str(cuatrimestre).zfill(2)
                                        + '-01-02-lote4.zip')
        os.rename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote1.zip',
                  settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote1_' + hash1 + '.zip')
        os.rename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote2.zip',
                  settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote2_' + hash2 + '.zip')
        os.rename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote3.zip',
                  settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote3_' + hash3 + '.zip')
        os.rename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote4.zip',
                  settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                      + str(anio) + str(cuatrimestre).zfill(2)
                                      + '-01-02-lote4_' + hash4 + '.zip')

        arch_zip_final.write(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                             + str(anio) + str(cuatrimestre).zfill(2)
                             + '-01-02-lote1_' + hash1 + '.zip',
                             os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                              + str(anio) + str(cuatrimestre).zfill(2)
                                              + '-01-02-lote1_' + hash1 + '.zip'))
        arch_zip_final.write(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                             + str(anio) + str(cuatrimestre).zfill(2)
                             + '-01-02-lote2_' + hash2 + '.zip',
                             os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                              + str(anio) + str(cuatrimestre).zfill(2)
                                              + '-01-02-lote2_' + hash2 + '.zip'))
        arch_zip_final.write(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                             + str(anio) + str(cuatrimestre).zfill(2)
                             + '-01-02-lote3_' + hash3 + '.zip',
                             os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                              + str(anio) + str(cuatrimestre).zfill(2)
                                              + '-01-02-lote3_' + hash3 + '.zip'))
        arch_zip_final.write(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                             + str(anio) + str(cuatrimestre).zfill(2)
                             + '-01-02-lote4_' + hash4 + '.zip',
                             os.path.basename(settings.MEDIA_ROOT + r'/tmp/AI-33717445509-'
                                              + str(anio) + str(cuatrimestre).zfill(2)
                                              + '-01-02-lote4_' + hash4 + '.zip'))
        arch_zip_final.close()

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
