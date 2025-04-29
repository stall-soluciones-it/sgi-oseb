# -*- coding: utf-8 -*-
"""@Shepherd."""
import io
import pandas as pd
from django.conf import settings


def process_deuda_proveedores(archivo):
    """Filtra archivos deuda proveedores."""
    log = []
    # DF PROVEEDORES Y DEUDA DE ADBSA
    try:
        df_deuda_prov = pd.read_excel(archivo, skiprows=[0, 1, 2, 3, 4, 5, 6, 7, 8, 10],
                                      usecols='B,C,D,M')
        df_deuda_prov = df_deuda_prov[:-1]
        df_deuda_prov['PROVEEDOR'] = (df_deuda_prov.Auxiliar.apply(lambda x: int(x[3:x.find(' - ')])
                                                                   if 'PR.' in str(x)
                                                                   else float('NaN')))
        df_deuda_prov.loc[:, ['PROVEEDOR']] = df_deuda_prov.loc[:, ['PROVEEDOR']].ffill()
        df_deuda_prov.loc[:, ['Auxiliar']] = df_deuda_prov.loc[:, ['Auxiliar']].ffill()
        df_deuda_prov['Auxiliar'] = (df_deuda_prov.Auxiliar.apply(lambda x: x[x.find(' - ') + 3:] if
                                                                  'PR.' in x else x))
        df_deuda_prov.dropna(subset=['Saldo'], inplace=True)
        df_deuda_prov.columns = ['RAZÓN', 'COMPROBANTE', 'FECHA', 'SALDO', 'PROVEEDOR']
        df_deuda_prov['FECHA'] = (df_deuda_prov.FECHA.apply(lambda x: str(x)[0:10]))
        df_deuda_prov.replace({'NaT': 'TOTAL:'}, inplace=True)
        df_deuda_prov = df_deuda_prov[['PROVEEDOR', 'RAZÓN', 'COMPROBANTE', 'FECHA', 'SALDO']]
        df_deuda_prov['SALDO'] = df_deuda_prov.apply(lambda row: (row['SALDO'] * -1), axis=1)
        pre_partcdeuda_list = df_deuda_prov['PROVEEDOR'].tolist()
        partcdeuda_list = []
        for item in pre_partcdeuda_list:
            partcdeuda_list.append(str(int(item)))
    except Exception as expt:
        log.append(repr(expt))

    # PARTIDAS DE PROVEEDOR
    try:
        df_part_prov = pd.read_excel(settings.MEDIA_ROOT +
                                     r'/proveedores/partidas_x_proveedor.xlsx')
        dict_part_prov = df_part_prov.to_dict('list')
        for key, value in dict_part_prov.items():
            new_value = [x for x in value if str(x) != 'nan']
            new_value2 = []
            for item in new_value:
                try:
                    new_value2.append(int(item))
                except ValueError:
                    pass
            dict_part_prov[key] = new_value2
        dict_part_prov = {k: v for k, v in dict_part_prov.items() if v != []}
    except Exception as expt:
        log.append(repr(expt))

    # DEUDA DE PROVEEDOR CON ADBSA
    try:
        df_deuda_adbsa = pd.read_excel(settings.MEDIA_ROOT + r'/proveedores/deuda_masivo.xls',
                                       skiprows=[0, 1, 2, 3, 4, 5, 6, 7, 9],
                                       usecols='E,J')
        dict_deuda_adbsa = {}
        for _, row in df_deuda_adbsa.iterrows():
            if row['Total'] == float('NaN'):
                pass
            else:
                try:
                    dict_deuda_adbsa[int(row['Unidad Alt.'])] = row['Total']
                except ValueError:
                    pass
    except Exception as expt:
        log.append(repr(expt))

    # DIC {N° PROV: {PARTIDA: DEUDA, PARTIDA: DEUDA, ......}}
    try:
        dic_prov_part_deu = {}
        for key, value in dict_part_prov.items():
            for item in dict_part_prov[key]:
                if key not in dic_prov_part_deu:
                    try:
                        dic_prov_part_deu[int(key)] = {int(item): dict_deuda_adbsa[int(item)]}
                    except KeyError:
                        pass
                else:
                    try:
                        dic_prov_part_deu[int(key)][int(item)] = dict_deuda_adbsa[int(item)]
                    except KeyError:
                        pass

        # Creo dict de DFs para cada proveedor con detalle de partida: deuda
        dfs_prov = {}
        for n_prov, parts in dic_prov_part_deu.items():
            if str(n_prov) in partcdeuda_list:
                dfs_prov[n_prov] = pd.DataFrame.from_dict(parts, orient='index')
                dfs_prov[n_prov].reset_index(level=0, inplace=True)
                dfs_prov[n_prov].columns = ['Partida', 'Deuda']

        # DIC {N° PROV: DEUDA, .......}
        dict_prov_deu = {}
        for key, value in dic_prov_part_deu.items():
            dict_prov_deu[int(key)] = sum(value.values())
    except Exception as expt:
        log.append(repr(expt))

    # Agrego columna deuda partidas al DF:
    try:
        df_deuda_prov['DEBE'] = df_deuda_prov.PROVEEDOR.apply(lambda x: dict_prov_deu[x]
                                                              if x in dict_prov_deu.keys()
                                                              else float('NaN'))

        for index, row in df_deuda_prov.iterrows():
            if 'Total' in row['RAZÓN']:
                df_deuda_prov.at[index, 'PROVEEDOR'] = str(row['PROVEEDOR'])
            else:
                df_deuda_prov.at[index, 'DEBE'] = float('NaN')
        # CREO EL ARCHIVO FINAL
        # Set destination directory to save excel.
        xlsFilepath = (settings.MEDIA_ROOT + r'/proveedores/Reporte_proveedores.xlsx')
        writer = pd.ExcelWriter(xlsFilepath, engine='xlsxwriter')
        # Write excel to file using pandas to_excel
        df_deuda_prov.to_excel(writer, startrow=0, sheet_name='Deuda Proveedores', index=False)
        for n_prov, df in dfs_prov.items():
            df.to_excel(writer, startrow=0, sheet_name=str(n_prov), index=False)

        # Lista de filas con totales
        pre_filas_totales = list(df_deuda_prov.RAZÓN.values)
        filas_totales = []
        index = 0
        for item in pre_filas_totales:
            index += 1
            if 'Total' in item:
                filas_totales.append(index)

        # FORMATEO EL LIBRO:
        # Indicate workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Deuda Proveedores']

        f_moneda = workbook.add_format({'bold': True, 'num_format': '[$$-es-AR] #,##0.00'})
        f_fecha = workbook.add_format({'num_format': 'dd/mm/yy'})
        # f_totales = workbook.add_format({'num_format': '[$$-es-AR] #,##0.00', 'bold': True})
        f_proveedor = workbook.add_format({'bold': True, 'num_format': '0'})
        worksheet.set_column('A:A', None, f_proveedor)
        worksheet.set_column('E:E', None, f_moneda)
        worksheet.set_column('F:F', None, f_moneda)
        worksheet.set_column('D:D', None, f_fecha)

        # for row in filas_totales:
        #     worksheet.set_column('A:A', None, f_proveedor)
        #     worksheet.set_row(row, None, f_totales)

        # Iterate through each column and set the width == the max length in that column.
        # A padding length of 2 is also added.
        for i, col in enumerate(df_deuda_prov.columns):
            # find length of column i
            column_len = df_deuda_prov[col].astype(str).str.len().max()
            # Setting the length if the column header is larger
            # than the max column value length
            column_len = max(column_len, len(col)) + 2
            # set the column length
            worksheet.set_column(i, i, column_len)

        # AGREGAR FORMULA AL FINAL:
        # row_num = len(df_deuda_prov.index) + 1
        # worksheet.write(row_num, 0, '=SUM(A1:A' + str(row_num) + ')')

        # Escribo el libro:
        writer.save()
    except Exception as expt:
        log.append(repr(expt))

    if log:
        with io.open(settings.MEDIA_ROOT + r'/proveedores/Log_error.txt',
                     'wt', newline='\r\n') as log_arch:
            log_arch.write('\n'.join(log))
        return settings.MEDIA_ROOT + r'/proveedores/Log_error.txt'
    else:
        return settings.MEDIA_ROOT + r'/proveedores/Reporte_proveedores.xlsx'
