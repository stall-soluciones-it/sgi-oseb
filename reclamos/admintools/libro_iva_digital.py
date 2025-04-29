import io
from decimal import Decimal
import os
import zipfile
import pandas as pd
import pymysql
import calendar
import datetime
import sgi.shpd_cnf as cnf
from django.conf import settings

LOG = []


def libro_iva_digital(periodo, vtas, vtasa, vtasb, compras, n_perc):
    """Procesa archivos y genera LID."""
    ANIO = str(periodo)[0:4]
    MES = str(periodo)[4:6]

    def dec(numero):
        """Formato de numero decimal redondeado a dos decimales."""
        num = Decimal(str(numero).replace(',', ''))
        dos_decimales = Decimal("0.01")
        return num.quantize(dos_decimales)

    NETO_GR = dec(0)

    def busco_fecha_pago(anio, mes):
        """Busco comprobantes en tablas de cobranzas cpd_pi######."""
        # Constantes y comprobaciones.
        try:
            anio = int(anio)
            mes = int(mes)
            if 2017 <= anio <= 2040:
                pass
            else:
                LOG.append('ERROR: El año "' + str(anio) + '" es incorrecto.')
            if 1 <= mes <= 12:
                pass
            else:
                LOG.append('ERROR: El mes "' + str(mes) + '" es incorrecto.')

            last_day = int(calendar.monthrange(anio, mes)[1])
            date_ref = datetime.date(2017, 1, 1)
            date = datetime.date(anio, mes, 1)
        except Exception as expt:
            LOG.append('Error en datos de fecha: ' + repr(expt))
        # z80cpd_pi_#######:
        tab = int(n_perc)
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
                    rango_fechas = ("'" + str(anio) + "-" + str(mes).zfill(2) + "-" + "01'" +
                                    " AND '" + str(anio) + "-" + str(mes).zfill(2) + "-" +
                                    str(last_day) + "'")
                    query = ("SELECT unidad, tpo_com, pre_com, num_com, fec_cob" +
                             " FROM z80cpd_pi_" + tabla +
                             " WHERE (cod_ser NOT IN ('IRBC', 'I10', 'I21', 'I27'))" +
                             " AND (estado = 'C')" +
                             " AND (fec_cob BETWEEN " + rango_fechas + ");")
                    cursor.execute(query)
                    datos_cpd = cursor.fetchall()
                    cursor.close()
                    connection.close()
                    date_ref = datos_cpd[0]['fec_cob']
                    tab += 1
                except Exception as expt:
                    cuenta_iter.append('Tabla para fecha solicitada no encontrada: ' + str(expt))
                    if sum('exist' in string for string in cuenta_iter) >= 50:
                        LOG.append('NO SE ENCONTRÓ TABLA PARA LA FECHA SOLICITADA.')
                        break
                    else:
                        tab += 1
                        continue
        except Exception as expt2:
            LOG.append('Error al consultar la DB: ' + repr(expt2))
        return datos_cpd

    def num_elect():
        """Extraigo números de FC electrónica."""
        # Constantes y comprobaciones.
        try:
            connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                         user=cnf.DB_SISA_USR,
                                         password=cnf.DB_SISA_PASS,
                                         db='osebal_produccion',
                                         charset='utf8mb4',
                                         cursorclass=pymysql.cursors.DictCursor)
            cursor = pymysql.cursors.DictCursor(connection)
            query = ("SELECT z80unidad.unidad, z80facturas_elec.pre_com, " +
                     "z80facturas_elec.num_com, z80facturas_elec.pre_com_elec, " +
                     "z80facturas_elec.num_com_elec " +
                     "FROM z80facturas_elec " +
                     "INNER JOIN z80unidad " +
                     "ON z80unidad.usuario = z80facturas_elec.usuario;")
            cursor.execute(query)
            num_elec = cursor.fetchall()
            cursor.close()
            connection.close()
        except Exception as expt:
            LOG.append(str(expt))
        return num_elec

    n_elec = {}
    for dic in num_elect():
        u_p_n = str(int(dic['unidad'])) + str(int(dic['pre_com'])) + '-' + str(int(dic['num_com']))
        n_elec[u_p_n] = [str(int(dic['pre_com_elec'])).zfill(5), str(int(dic['num_com_elec'])).zfill(20)]

    vtos = {}
    for dic in busco_fecha_pago(ANIO, MES):
        u_p_n = str(int(dic['unidad'])) + str(int(dic['pre_com'])) + '-' + str(int(dic['num_com']))
        vtos[u_p_n] = str(dic['fec_cob'].year) + str(dic['fec_cob'].month).zfill(2) + str(dic['fec_cob'].day).zfill(2)

    df_iva_vtas = pd.read_excel(vtas,
                                usecols='B,C,D,E,F,H,I,J,K,L,M,N,O,P,Q')
    df_iva_vtas.columns = ['cond', 'unidad', 'fecha', 'tipo', 'numero', 'nombre', 'tipo_doc', 'doc',
                           'total', 'iibb', 'gravado', 'alicuota', 'imp_liq', 'no_g', 'no_gravado']

    df_iva_vtas.dropna(inplace=True)
    df_iva_vtas.drop(df_iva_vtas[df_iva_vtas.nombre == '* * ANULADO * *'].index, inplace=True)
    pd.set_option('display.max_columns', 500)

    final_cbte = []
    final_alic = []
    # comprobantes = {}

    # FACTURAS A
    for index, row in df_iva_vtas.iterrows():
        numero = row['numero']

        unidad_pre_num = (str(int(row['unidad'])) + str(int(numero[:numero.find('-')])) + '-' +
                          str(int(numero[numero.find('-') + 1:])))

        try:
            pre = n_elec[unidad_pre_num][0]
            num = n_elec[unidad_pre_num][1]
            num_hasta = num
        except KeyError:
            pre = str(int(numero[:numero.find('-')])).zfill(5)
            num = str(int(numero[numero.find('-') + 1:])).zfill(20)
            num_hasta = num

        fecha = (str(row['fecha'].year) + str(row['fecha'].month).zfill(2) +
                 str(row['fecha'].day).zfill(2))

        pre_tipo = str(row['tipo'])
        if pre_tipo == 'CP':
            tipo = str(90).zfill(3)
        elif pre_tipo == 'DR':
            if row['cond'] == 'RESPONSABLE INSCRIPTO':
                tipo = str(39).zfill(3)
            else:
                tipo = str(40).zfill(3)
        elif pre_tipo in ['FC', 'ND']:
            if row['cond'] == 'RESPONSABLE INSCRIPTO':
                tipo = str(17).zfill(3)
            else:
                tipo = str(18).zfill(3)
        elif pre_tipo == 'MG':
            if row['cond'] == 'RESPONSABLE INSCRIPTO':
                tipo = str(17).zfill(3)
            else:
                tipo = str(18).zfill(3)
        elif pre_tipo == 'MP':
            if row['cond'] == 'RESPONSABLE INSCRIPTO':
                tipo = str(39).zfill(3)
            else:
                tipo = str(40).zfill(3)
        elif pre_tipo in ['NC', 'NG', 'NP']:
            if row['cond'] == 'RESPONSABLE INSCRIPTO':
                tipo = str(3).zfill(3)
            else:
                tipo = str(8).zfill(3)
        elif pre_tipo == 'PP':
            if row['cond'] == 'RESPONSABLE INSCRIPTO':
                tipo = str(39).zfill(3)
            else:
                tipo = str(40).zfill(3)
        elif pre_tipo == 'NX':
            tipo = str().zfill(3)
        else:
            LOG.append('Código no encontrado: ' + str(row['tipo']))

        # Tipo documento
        if str(row['tipo_doc']) == 'PSP':
            doc = ''.zfill(20)
        else:
            pre_doc = str(int(row['doc']))
            doc = pre_doc.zfill(20)

        if doc == '00000000000000000000':
            tipo_doc = str(99)
        else:
            if str(row['tipo_doc']) == 'CID':
                tipo_doc = '01'
            if str(row['tipo_doc']) == 'CUIT':
                if len(str(pre_doc)) < 11:
                    tipo_doc = '99'
                    doc = '00000000000000000000'
                else:
                    tipo_doc = '80'
            if str(row['tipo_doc']) == 'DNC':
                tipo_doc = '99'
                doc = '00000000000000000000'
            if str(row['tipo_doc']) == 'DNI':
                tipo_doc = '96'
            if str(row['tipo_doc']) == 'LCI':
                tipo_doc = '90'
            if str(row['tipo_doc']) == 'LEN':
                tipo_doc = '89'
            if str(row['tipo_doc']) == 'PSP':
                tipo_doc = '99'

        nombre = str(row['nombre'])[:30].ljust(30)

        # Total
        if dec(row['no_gravado']) == dec(0):
            total = str(dec(row['total'])).replace('.', '').replace('-', '').zfill(15)
        else:
            total = str(dec(row['total']) - dec(row['no_gravado'])).replace('.', '').replace('-', '').zfill(15)

        gravado = str(dec(row['gravado'])).replace('.', '').replace('-', '').zfill(15)
        NETO_GR += dec(row['gravado'])
        no_gravado = ''.zfill(15)  # str(dec(row['no_gravado']) + dec(row['no_g'])).replace('.', '').replace('-', '').zfill(15)

        iibb = str(dec(row['iibb'])).replace('.', '').replace('-', '').zfill(15)

        # alicuota
        if dec(row['alicuota']) < dec(22.5):
            alicuota = '5'.zfill(4)
        elif dec(row['alicuota']) >= dec(22.5):
            alicuota = '6'.zfill(4)

        # Corrijo tipo y Nº de doc de acuerdo a alicuota
        if alicuota == '0006' and tipo_doc == '99':
            tipo_doc = '80'
            doc = '20222222223'.zfill(20)

        imp_liq = str(dec(row['imp_liq'])).replace('.', '').replace('-', '').zfill(15)

        no_corresponde = '000000000000000'

        moneda = 'PES'

        tc = '0000000000'

        cant_alic = '1'

        cod_oper = '0'

        # fecha vto
        if tipo == str(38).zfill(3):
            fecha_vto = '00000000'
        else:
            try:
                fecha_vto = vtos[unidad_pre_num]
                fecha_vto = max(fecha_vto, fecha)
            except KeyError:
                fecha_vto = fecha

        linea_cbte = (fecha + tipo + pre + num + num_hasta + tipo_doc + doc + nombre + total + no_gravado +
                      no_corresponde + no_corresponde + no_corresponde + iibb + no_corresponde +
                      no_corresponde + moneda + tc + cant_alic + cod_oper + no_corresponde + fecha_vto)

        linea_alic = (tipo + pre + num + gravado + alicuota + imp_liq)

        if dec(row['no_gravado']) - dec(row['total']) != dec(0):
            final_cbte.append(linea_cbte)
            final_alic.append(linea_alic)

    # FACTURAS B
    df_iva_vtas_b = pd.read_excel(vtasb,
                                  usecols='A,B,C,D,F,G,H')

    df_iva_vtas_b.columns = ['tipo', 'pto_vta', 'comp', 'fecha', 'neto_gr', 'iva', 'total']

    comprobantes_b = []
    for index, row in df_iva_vtas_b.iterrows():
        if str(row['pto_vta']) != 'nan':
            comprobantes_b.append({'tipo': str(row['tipo']),
                                   'pto_vta': int(row['pto_vta']),
                                   'comp': int(row['comp']),
                                   'fecha': str(row['fecha'])[:10].replace('-', ''),
                                   'neto_gr': dec(row['neto_gr']),
                                   'iva': dec(row['iva']),
                                   'total': dec(row['total'])})

    for dic in comprobantes_b:
        fecha = dic['fecha']

        # tipo
        if dic['tipo'] == 'Factura B':
            tipo = '006'
        elif dic['tipo'] == 'NC B':
            tipo = '008'
        else:
            LOG.append('ERROR EN TIPO DE COMPROBANTE B')

        pre = str(dic['pto_vta']).zfill(5)

        num = str(dic['comp']).zfill(20)

        num_hasta = num

        tipo_doc = '80'

        doc = '30999007739'.zfill(20)

        nombre = 'MUNICIPALIDAD DE BALCARCE'.ljust(30)

        total = str(dic['total']).replace('.', '').replace('-', '').zfill(15)

        no_gravado = ''.zfill(15)

        gravado = str(dic['neto_gr']).replace('.', '').replace('-', '').zfill(15)
        NETO_GR += dec(dic['neto_gr'])
        no_corresponde = '000000000000000'

        moneda = 'PES'

        tc = '0000000000'

        cant_alic = '1'

        cod_oper = '0'

        fecha_vto = dic['fecha']

        alicuota = '5'.zfill(4)

        imp_liq = str(dic['iva']).replace('.', '').replace('-', '').zfill(15)

        linea_cbte = (fecha + tipo + pre + num + num_hasta + tipo_doc + doc + nombre + total + no_gravado +
                      no_corresponde + no_corresponde + no_corresponde + no_corresponde + no_corresponde +
                      no_corresponde + moneda + tc + cant_alic + cod_oper + no_corresponde + fecha_vto)

        linea_alic = (tipo + pre + num + gravado + alicuota + imp_liq)

        final_cbte.append(linea_cbte)
        final_alic.append(linea_alic)

    # FACTURAS A
    df_iva_vtas_b = pd.read_excel(vtasa,
                                  usecols='A,B,C,D,F,G,H')

    df_iva_vtas_b.columns = ['tipo', 'pto_vta', 'comp', 'fecha', 'neto_gr', 'iva', 'total']

    comprobantes_b = []
    for index, row in df_iva_vtas_b.iterrows():
        if str(row['pto_vta']) != 'nan':
            comprobantes_b.append({'tipo': str(row['tipo']),
                                   'pto_vta': int(row['pto_vta']),
                                   'comp': int(row['comp']),
                                   'fecha': str(row['fecha'])[:10].replace('-', ''),
                                   'neto_gr': dec(row['neto_gr']),
                                   'iva': dec(row['iva']),
                                   'total': dec(row['total'])})

    for dic in comprobantes_b:
        fecha = dic['fecha']

        # tipo
        if dic['tipo'] == 'Factura A':
            tipo = '001'
        elif dic['tipo'] == 'NC A':
            tipo = '003'
        elif dic['tipo'] == 'ND A':
            tipo = '002'
        else:
            LOG.append('ERROR EN TIPO DE COMPROBANTE A')

        pre = str(dic['pto_vta']).zfill(5)

        num = str(dic['comp']).zfill(20)

        num_hasta = num

        tipo_doc = '80'

        doc = '30677286314'.zfill(20)

        nombre = 'AGUAS DE BALCARCE S.A.'.ljust(30)

        total = str(dic['total']).replace('.', '').replace('-', '').zfill(15)

        no_gravado = ''.zfill(15)

        gravado = str(dic['neto_gr']).replace('.', '').replace('-', '').zfill(15)
        NETO_GR += dec(dic['neto_gr'])
        no_corresponde = '000000000000000'

        moneda = 'PES'

        tc = '0000000000'

        cant_alic = '1'

        cod_oper = '0'

        fecha_vto = dic['fecha']

        alicuota = '5'.zfill(4)

        imp_liq = str(dic['iva']).replace('.', '').replace('-', '').zfill(15)

        linea_cbte = (fecha + tipo + pre + num + num_hasta + tipo_doc + doc + nombre + total + no_gravado +
                      no_corresponde + no_corresponde + no_corresponde + no_corresponde + no_corresponde +
                      no_corresponde + moneda + tc + cant_alic + cod_oper + no_corresponde + fecha_vto)

        linea_alic = (tipo + pre + num + gravado + alicuota + imp_liq)

        final_cbte.append(linea_cbte)
        final_alic.append(linea_alic)
    final_cbte_vtas = list(final_cbte)
    final_alic_vtas = list(final_alic)

    # COMPRAS
    final_cbte = []
    final_alic = []

    df_iva_compras = pd.read_excel(compras,
                                   usecols='A,B,C,D,E,F,G,H,I,J,K,L,M,N')
    df_iva_compras.columns = ['fec_emi', 'razon', 'cuit', 'tipo_iva', 'tipo_comp',
                              'n_comp', 'neto_gr', 'neto_no_gr', 'iva_insc',
                              'reca_no_insc', 'iva_perc', 'iva_no_computable',
                              'otros_impuestos', 'total']

    for index, row in df_iva_compras.iterrows():
        # Fecha comprobante
        pre_fec_comp = str(row['fec_emi'])
        fec_comp = pre_fec_comp[0:4] + pre_fec_comp[5:7] + pre_fec_comp[8:10]

        # Tipo comprobante
        tipos = {'FCPA': '001', 'NCPA': '003', 'NDPA': '002', 'RCPA': '004',
                 'FCPC': '011', 'NCPC': '013', 'NDPC': '012', 'RCPC': '015',
                 'FCPM': '051', 'NCPM': '053', 'NDPM': '052', 'DBGR': '099'}
        pre_tpo_comp = str(row['tipo_comp'])
        tpo_com = tipos[pre_tpo_comp]

        # Punto de venta
        pto_vta = str(row['n_comp'])[:str(row['n_comp']).find('-')].zfill(5)

        # Nº de comprobante
        n_comp = str(row['n_comp'])[str(row['n_comp']).find('-') + 1:].zfill(20)

        # Nº identificación vendedor
        n_id = str(row['cuit']).replace('-', '').zfill(20)

        # Razón
        razon = str(row['razon'])[:20].ljust(30, ' ')

        # Total
        total = str(dec(row['total'])).replace('.', '').replace('-', '').zfill(15)

        # Total != neto gravado
        if row['tipo_iva'] == 'Exento':
            tot_no_gr = '0'.zfill(15)
        else:
            tot_no_gr = str(dec(row['neto_no_gr'])).replace('.', '').replace('-', '').zfill(15)

        # Exento
        if row['tipo_iva'] == 'Exento':
            exento = str(dec(row['neto_no_gr'])).replace('.', '').replace('-', '').zfill(15)
        else:
            exento = '0'.zfill(15)

        # Percepción IVA
        perc_iva = str(dec(row['iva_perc'])).replace('.', '').replace('-', '').zfill(15)

        # Percepción IIBB
        perc_iibb = str(dec(row['otros_impuestos'])).replace('.', '').replace('-', '').zfill(15)

        # Crédito fiscal computable
        iva = str(dec(row['iva_insc'])).replace('.', '').replace('-', '').zfill(15)

        # Neto gravado
        neto_gr = str(dec(row['neto_gr'])).replace('.', '').replace('-', '').zfill(15)

        # Alícuota
        try:
            pre_alic = (dec(row['iva_insc']) / dec(row['neto_gr'])) * dec(100)
        except Exception:
            pre_alic = 0
        if pre_alic >= 2 and pre_alic <= 3:
            alicuota = '0009'
        elif pre_alic >= 4.5 and pre_alic <= 5.5:
            alicuota = '0008'
        elif pre_alic >= 10 and pre_alic <= 11:
            alicuota = '0004'
        elif pre_alic >= 20.5 and pre_alic <= 21.5:
            alicuota = '0005'
        elif pre_alic >= 26.5 and pre_alic <= 27.5:
            alicuota = '0006'
        elif pre_alic == 0:
            alicuota = '0003'

        # Código de operación
        if alicuota == '0003' and row['tipo_iva'] == 'Exento':
            cod_oper = 'E'
        elif alicuota == '0003' and row['tipo_iva'] != 'Exento':
            cod_oper = 'A'
        else:
            cod_oper = '0'

        # Cantidad de alicuotas IVA
        if alicuota == '0003':
            cant_alic = '0'
        else:
            cant_alic = '1'

        linea_cbte = (fec_comp + tpo_com + pto_vta + n_comp + ''.ljust(16, ' ') +
                      '80' + n_id + razon + total + tot_no_gr + exento + perc_iva +
                      '0'.zfill(15) + perc_iibb + '0'.zfill(15) + '0'.zfill(15) +
                      'PES' + '0'.zfill(10) + cant_alic + cod_oper + iva + '0'.zfill(15) +
                      '0'.zfill(11) + ''.ljust(30, ' ') + '0'.zfill(15))

        linea_alic = (tpo_com + pto_vta + n_comp + '80' + n_id + neto_gr + alicuota +
                      iva)

        final_cbte.append(linea_cbte)
        if row['tipo_iva'] not in ['Monotributo', 'Exento']:
            if ((row['tipo_iva'] == 'Iva Responsable Inscripto.') and (int(row['neto_gr']) == 0)):
                pass
            else:
                final_alic.append(linea_alic)

    try:
        ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/LID' + str(periodo) + '.zip',
                                   mode='x', compression=zipfile.ZIP_DEFLATED)
    except FileExistsError:
        os.remove(settings.MEDIA_ROOT + r'/tmp/LID' + str(periodo) + '.zip')
        ARCH_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/LID' + str(periodo) + '.zip',
                                   mode='x', compression=zipfile.ZIP_DEFLATED)

    with io.open(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.txt', 'wt', newline='\r\n', encoding='cp1252') as arch_final:
        arch_final.write('\n'.join(final_cbte_vtas))
    try:
        VTAS_CBTE_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
    except FileExistsError:
        os.remove(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.zip')
        VTAS_CBTE_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
    VTAS_CBTE_ZIP.write(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.txt'))
    VTAS_CBTE_ZIP.close()

    with io.open(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.txt', 'wt', newline='\r\n', encoding='cp1252') as arch_final2:
        arch_final2.write('\n'.join(final_alic_vtas))
    try:
        VTAS_ALIC_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
    except FileExistsError:
        os.remove(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.zip')
        VTAS_ALIC_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
    VTAS_ALIC_ZIP.write(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.txt'))
    VTAS_ALIC_ZIP.close()

    with io.open(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.txt', 'wt', newline='\r\n', encoding='cp1252') as arch_final:
        arch_final.write('\n'.join(final_cbte))
    try:
        COMP_CBTE_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
    except FileExistsError:
        os.remove(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.zip')
        COMP_CBTE_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
    COMP_CBTE_ZIP.write(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.txt'))
    COMP_CBTE_ZIP.close()

    with io.open(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.txt', 'wt', newline='\r\n', encoding='cp1252') as arch_final2:
        arch_final2.write('\n'.join(final_alic))
    try:
        COMP_ALIC_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
    except FileExistsError:
        os.remove(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.zip')
        COMP_ALIC_ZIP = zipfile.ZipFile(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                                        mode='x', compression=zipfile.ZIP_DEFLATED)
    COMP_ALIC_ZIP.write(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.txt',
                        os.path.basename(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.txt'))
    COMP_ALIC_ZIP.close()

    ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                   os.path.basename(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.zip'))
    ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                   os.path.basename(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_VENTAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.zip'))
    ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                   os.path.basename(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_CBTE_' + str(ANIO) + str(MES).zfill(2) + '.zip'))
    ARCH_ZIP.write(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.zip',
                   os.path.basename(settings.MEDIA_ROOT + r'/tmp/LIBRO_IVA_DIGITAL_COMPRAS_ALICUOTAS_' + str(ANIO) + str(MES).zfill(2) + '.zip'))
    ARCH_ZIP.close()

    if LOG:
        with io.open(settings.MEDIA_ROOT + r'/tmp/Log_LID' + str(ANIO) + str(MES).zfill(2) + '.txt',
                     'wt', newline='\r\n', encoding='cp1252') as log_arch:
            log_arch.write('\n'.join(LOG))

        return settings.MEDIA_ROOT + r'/tmp/Log_LID' + str(ANIO) + str(MES).zfill(2) + '.txt'
    else:
        return settings.MEDIA_ROOT + r'/tmp/LID' + str(periodo) + '.zip'
