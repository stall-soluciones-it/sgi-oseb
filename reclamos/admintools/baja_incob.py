# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 16:25:42 2020.

@author: Daniel
"""
import datetime
import io
import pymysql
import psycopg2
import pandas as pd
import sgi.shpd_cnf as cnf
from django.conf import settings

log = []


def change_postresql(query):
    """Aplico cambios a DB Postgre."""
    try:
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
    except Exception as expt:
        log.append('Error al modificar DB: ' + repr(expt))


def process_baja_incob(data_input):
    """Procesa el archivo deuda de SISA y Excel con listado de unidades que no pagaron nunca."""
    pagaron = []
    # Ingresó pago (lista guardada en DB):
    try:
        query = "SELECT unidad FROM baja_incob;"
        connection = psycopg2.connect(user=cnf.DB_SHPD_USR,
                                      password=cnf.DB_SHPD_PASS,
                                      host=cnf.DB_SHPD_HOST,
                                      port="5432",
                                      database="external_data")
        cursor = connection.cursor()
        cursor.execute(query)
        datos = cursor.fetchall()
        if connection:
            cursor.close()
            connection.close()
    except Exception as expt:
        log.append('Error al consultar DB baja_incob: ' + repr(expt))

    try:
        for tup in datos:
            pagaron.append(int(tup[0]))
    except Exception as expt:
        log.append('Error al ingresar datos de DB baja_incob a listado "pagaron": ' + repr(expt))

    # Consulto en DB última tabla guardada en listado:
    try:
        query = "SELECT last_table FROM baja_incob_last_table;"
        connection = psycopg2.connect(user=cnf.DB_SHPD_USR,
                                      password=cnf.DB_SHPD_PASS,
                                      host=cnf.DB_SHPD_HOST,
                                      port="5432",
                                      database="external_data")
        cursor = connection.cursor()
        cursor.execute(query)
        datos = cursor.fetchall()
        if connection:
            cursor.close()
            connection.close()
    except Exception as expt:
        log.append('Error al consultar DB baja_incob: ' + repr(expt))
    try:
        last_table = int(datos[0][0])
    except Exception as expt:
        log.append('Error al extraer dato last_table de DB: ' + repr(expt))

    try:
        new_db = list(pagaron)
        tablas = 200
        tabla_mas_nueva = 0
        tabla_mas_nueva_ok = 0
        first_loop = True
    except Exception as expt:
        log.append('Error al crear constantes para consultar tablas de pagos: ' + repr(expt))
    try:
        while tablas != last_table:
            try:
                connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                             user=cnf.DB_SISA_USR,
                                             password=cnf.DB_SISA_PASS,
                                             db='osebal_produccion',
                                             charset='utf8mb4',
                                             cursorclass=pymysql.cursors.DictCursor)
                cursor = pymysql.cursors.DictCursor(connection)
                query = ("SELECT unidad FROM z80cpd_pi_" + str(tablas).zfill(7)
                         + " WHERE estado = 'C'"
                         + " AND cod_ser <> 'IRBC';")
                cursor.execute(query)
                datos = cursor.fetchall()
                cursor.close()
                connection.close()
                for dic in datos:
                    if int(dic['unidad']) not in pagaron:
                        pagaron.append(int(dic['unidad']))
                if tabla_mas_nueva > 1:
                    if int(dic['unidad']) not in new_db:
                        new_db.append(int(dic['unidad']))
                    if first_loop is True:
                        tabla_mas_nueva_ok = tablas
                        first_loop = False
                tabla_mas_nueva += 1
                tablas -= 1
            except:
                tablas -= 1
                continue
    except Exception as expt:
        log.append('Error al traer tablas z80cpd_pi_### y crear listado final3:' + repr(expt))

    # Renuevo DB del sistema si es necesario:
    if tabla_mas_nueva_ok == 0:
        pass
    else:
        try:
            change_postresql("DROP TABLE baja_incob_last_table;")
            change_postresql("CREATE TABLE baja_incob_last_table (last_table varchar NOT NULL);")
            change_postresql("INSERT INTO baja_incob_last_table(last_table) VALUES ('"
                             + str(tabla_mas_nueva_ok) + "');")
            query_fin = ''
            for item in new_db:
                query_fin += '(' + str(item) + '), '
            query_fin += 'ult'
            query_fin = query_fin.replace('), ult', ');')
            change_postresql("DROP TABLE baja_incob;")
            change_postresql("CREATE TABLE baja_incob (unidad int NOT NULL);")
            change_postresql("INSERT INTO baja_incob(unidad) VALUES " + query_fin)
        except Exception as expt:
            log.append('Error al actualizar DB sistema: ' + repr(expt))
    # Con servicio:
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT unidad, cod_ser FROM z80servi WHERE fec_vig_h IS NULL;")
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        con_ser = []
        cod_ser = {}
        for dic in datos:
            try:
                con_ser.append(int(dic['unidad']))
                cod_ser[int(dic['unidad'])] = str(dic['cod_ser'])
            except TypeError:
                pass
    except Exception as expt:
        log.append('Error al consultar DB z80servi y crear listado final: ' + repr(expt))

    # Filtro escuelas y municipales:
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = ("SELECT unidad FROM osebal_produccion.z80servi"
                 + " WHERE (cod_ser IN ('MEA', 'MEB', 'MEPC', 'NEAA', 'NEAB', 'NEAD', 'NEAI',"
                 + " 'NEAM', 'NEBA', 'NEBB', 'NEBD', 'NEBI', 'NEBM', 'NECA', 'NECB', 'NECD',"
                 + " 'NECI', 'NECM', 'NEPC', 'ZEAI', 'ZEBI', 'ZECI', 'MMA', 'MMB', 'MMPC',"
                 + " 'NMAA', 'NMAB', 'NMAD', 'NMAI', 'NMAM', 'NMBA', 'NMBB', 'NMBD', 'NMBI',"
                 + " 'NMBM', 'NMCA', 'NMCB', 'NMCD', 'NMCI', 'NMCM', 'NMPC', 'ZMAI', 'ZMBI',"
                 + " 'ZMCI'));")
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as expt:
        log.append('Error al conectar con DB z80servi: ' + repr(expt))
    try:
        escuelas_muni = []
        for dic in data:
            try:
                escuelas_muni.append(int(dic['unidad']))
            except TypeError:
                pass
    except Exception as expt:
        log.append('Error al crear listado de escuelas: ' + repr(expt))

    # Listado Alberghini:
    try:
        connection = pymysql.connect(host=cnf.DB_OSEBAL_HOST,
                                     user=cnf.DB_SISA_USR,
                                     password=cnf.DB_SISA_PASS,
                                     db='osebal_produccion',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        cursor = pymysql.cursors.DictCursor(connection)
        query = "SELECT unidad FROM z80unidad WHERE val_atr_8 = '4';"
        cursor.execute(query)
        datos = cursor.fetchall()
        cursor.close()
        connection.close()
        alberghini = []
        for dic in datos:
            alberghini.append(int(dic['unidad']))
    except Exception as expt:
        log.append('Error al consultar DB de Alberghini y crear listado: ' + repr(expt))

    # Traigo el archivo de deuda y lo trabajo:
    try:
        df_deuda = pd.read_excel(data_input, skiprows=[0, 1, 2, 3, 4, 5, 6, 7, 9])
        del df_deuda['Tipo de Error']
        del df_deuda['Teléfono']
        df_deuda = df_deuda[~df_deuda.Unidad.isin(pagaron)]
        df_deuda = df_deuda[df_deuda.Unidad.isin(con_ser)]
        df_deuda = df_deuda[~df_deuda.Unidad.isin(escuelas_muni)]
        df_deuda["Código Servicio"] = df_deuda.apply(lambda x: cod_ser[x["Unidad"]], axis=1)
        df_deuda["Est. Alberghini"] = df_deuda.apply(lambda x: 'Sí' if x['Unidad'] in alberghini
                                                     else '', axis=1)
        df_deuda = df_deuda[df_deuda['Cant.'] >= 12]
    except Exception as expt:
        log.append('Error al trabajar con archivo excel o DF: ' + repr(expt))

    hoy = str(datetime.date.today())

    if log:
        with io.open(settings.MEDIA_ROOT + r'/tmp/Log_' + hoy + '.txt',
                     'wt', newline='\r\n') as log_arch:
            log_arch.write('\n'.join(log))
        return settings.MEDIA_ROOT + r'/tmp/Log_' + hoy + '.txt'
    else:
        try:
            # Set destination directory to save excel.
            xlsFilepath = settings.MEDIA_ROOT + r'/tmp/Nuevos_incobrables_' + hoy + '.xlsx'
            writer = pd.ExcelWriter(xlsFilepath, engine='xlsxwriter')
            # Write excel to file using pandas to_excel
            df_deuda.to_excel(writer, startrow=0, sheet_name='Sheet1', index=False)
            # Indicate workbook and worksheet for formatting
            # workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            # Iterate through each column and set the width == the max length in that column.
            # A padding length of 2 is also added.
            for i, col in enumerate(df_deuda.columns):
                # find length of column i
                column_len = df_deuda[col].astype(str).str.len().max()
                # Setting the length if the column header is larger
                # than the max column value length
                column_len = max(column_len, len(col)) + 2
                # set the column length
                worksheet.set_column(i, i, column_len)
            writer.save()
            return settings.MEDIA_ROOT + r'/tmp/Nuevos_incobrables_' + hoy + '.xlsx'
        except Exception as expt:
            log.append('Error al crear archivo final: ' + repr(expt))
            with io.open(settings.MEDIA_ROOT + r'/tmp/Log_' + hoy + '.txt',
                         'wt', newline='\r\n') as log_arch:
                log_arch.write('\n'.join(log))
            return settings.MEDIA_ROOT + r'/tmp/Log_' + hoy + '.txt'
