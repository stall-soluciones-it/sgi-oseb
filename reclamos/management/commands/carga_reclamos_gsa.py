# Libs python
import datetime
import re
import pandas as pd
# De Django
from reclamos.models import Reclamo
from django.contrib.auth.models import User
from reclamos.models import Tipos
from reclamos.models import Estados


def str_date_to_date(string):
    
    barras = [m.start() for m in re.finditer('/', string)]
    puntos = [m.start() for m in re.finditer(':', string)]
    
    dia = int(string[:barras[0]])
    mes = int(string[barras[0] + 1:barras[1]])
    anio = int(string[barras[1] + 1:string.find(' ')])
    hora = int(string[string.find(' '):puntos[0]])
    minutos = int(string[puntos[0] + 1:puntos[1]])
    segundos = int(string[puntos[1] + 1:])
    
    return datetime(day=dia, month=mes, year=anio, hour=hora, minute=minutos, second=segundos)


def carga_reclamos_gsa():
    
    reclamos = Reclamo.objects.all()

    # Estados
    pendiente = Estados.objects.get(estado='Pendiente')

    # Tipos
    agua = Tipos.objects.get(tipo='Agua')
    vereda = Tipos.objects.get(tipo='Vereda')
    facturacion = Tipos.objects.get(tipo='Facturación')
    deuda = Tipos.objects.get(tipo='Consulta Deuda')
    conexion = Tipos.objects.get(tipo='Consulta Conexión')
    calidad = Tipos.objects.get(tipo='Calidad')
    cloacas = Tipos.objects.get(tipo='Cloacas')
    marco_tapa = Tipos.objects.get(tipo='Marco y tapa')
    pavimento = Tipos.objects.get(tipo='Pavimento')
    
    # Genero listado de id_gsa cargados para comparar.
    id_gsa_cargados = []
    for reclamo in reclamos:
        id_gsa_cargados.append(reclamo.n_reclamo_gsa)


    # Traigo df de GSA.
    def preparo_df():
        sheet_id = '1yN6S6j0XaCByOnHlKjFGwYPPGtONPl2V4DfSvWjXUlM'
        sheet_name = "'Respuestas'"
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
        df = pd.read_csv(url)
        df.rename(columns={'Marca temporal': 'HORA',
                           'TELEFONO (2266 - 5421763)': 'TELEFONO',
                           'CANAL DE COMUNICACION': 'CANAL',
                           'MOTIVO DEL LLAMADO': 'MOTIVO',
                           'DETALLE RS': 'DETALLE1',
                           'DETALLE RA': 'DETALLE2',
                           'DETALLE RC': 'DETALLE3',
                           'DETALLE com': 'DETALLE4',
                           'Comentario (nota)': 'COMENTARIO',
                           'Nro de Reclamo (dia mes ultimos 4 dni) ( 27049992)': 'N_RECLAMO',
                           'Operador': 'OPERADOR',
                           'NUMERO DE CUENTA/UNIDAD': 'CUENTA',
                           'Entre calles': 'ENTRE',
                           'Vereda (par o impar)': 'VEREDA_PAR_IMPAR'},
                           inplace=True)
        df.drop('Unnamed: 27', axis=1, inplace=True)
        df.drop('Unnamed: 26', axis=1, inplace=True)
        df.drop('Unnamed: 25', axis=1, inplace=True)
        df.drop('Unnamed: 24', axis=1, inplace=True)
        df.drop('Unnamed: 23', axis=1, inplace=True)
        df.drop('Unnamed: 22', axis=1, inplace=True)
        df = df.reset_index()
        return df
    
    DF = preparo_df()
    
    # Comparo y cargo los no cargados.
    for index, row in DF.iterrows():
        id_gsa = (str(dict(row)['HORA'] + dict(row)['OPERADOR']).replace(' ', '').replace(r'/', '').replace(':', ''))
        
        if id_gsa not in id_gsa_cargados:
            # pre_n_de_reclamo = ''
            pre_author = 17  # 17 es el id del usuario carga_gsa.
            pre_editor = 17  # 17 es el id del usuario carga_gsa.
            # pre_created_date = ''
            # pre_updated_date = ''
            pre_fecha = str_date_to_date(str(row['HORA']))
            pre_tipo_de_reclamo = ''
            pre_apellido = str(row['APELLIDO']) + ' ' + str(row['NOMBRE'])
            pre_calle = str(row['CALLE']) + ' ' + str(row['ALTURA']) + (str(' Piso: ' + str(row['PISO'])) if str(row['PISO']) != 'nan' else '') + (str(' Dto: ' + str(row['DPTO'])) if str(row['DPTO']) != 'nan' else '')
            pre_altura = int(row['ALTURA'])
            pre_telefono = ''
            pre_detalle = ''
            pre_estado = pendiente
            pre_partida = ''
            pre_deuda = ''
            pre_fecha_resolucion = ''
            pre_tarea_realizada = ''
            pre_operario_s = ''
            pre_notificacion = ''
            pre_comentario = ''
            pre_a_reporte = ''
            pre_eliminado = ''
            pre_borrador = ''
            pre_n_reclamo_gsa = id_gsa

            rec = Reclamo.objects.create(author = pre_author,
                                         editor = pre_editor,
                                         fecha = pre_fecha,
                                         tipo_de_reclamo = pre_tipo_de_reclamo,
                                         apellido = pre_apellido,
                                         calle = pre_calle,
                                         altura = pre_altura,
                                         telefono = pre_telefono,
                                         detalle = pre_detalle,
                                         estado = pre_estado,
                                         partida = pre_partida,
                                         deuda = pre_deuda,
                                         fecha_resolucion = pre_fecha_resolucion,
                                         tarea_realizada = pre_tarea_realizada,
                                         operario_s = pre_operario_s,
                                         notificacion = pre_notificacion,
                                         comentario = pre_comentario,
                                         a_reporte = pre_a_reporte,
                                         eliminado = pre_eliminado,
                                         borrador = pre_borrador,
                                         n_reclamo_gsa = pre_n_reclamo_gsa)
            rec.guardar()
