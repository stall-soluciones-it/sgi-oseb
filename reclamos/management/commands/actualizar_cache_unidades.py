"""Management command para actualizar el cache de z80unidad desde SISA."""
import pymysql
from django.core.management.base import BaseCommand
from django.db import transaction
import sgi.shpd_cnf as cnf
from reclamos.models import CacheUnidadSISA


class Command(BaseCommand):
    help = 'Actualiza el cache de z80unidad desde la base de datos SISA'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando actualización del cache de unidades...')

        registros_procesados = 0
        registros_creados = 0
        registros_actualizados = 0
        errores = []

        try:
            # Conectar a SISA
            self.stdout.write('Conectando a base de datos SISA...')
            connection = pymysql.connect(
                host=cnf.DB_OSEBAL_HOST,
                user=cnf.DB_SISA_USR,
                password=cnf.DB_SISA_PASS,
                db='osebal_produccion',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )

            cursor = connection.cursor()

            # Obtener todas las unidades de SISA
            self.stdout.write('Consultando z80unidad...')
            query = "SELECT * FROM z80unidad;"
            cursor.execute(query)

            # Procesar en lotes para eficiencia de memoria
            self.stdout.write('Procesando registros...')
            batch_size = 1000
            batch = []

            with transaction.atomic():
                while True:
                    row = cursor.fetchone()
                    if not row:
                        break

                    registros_procesados += 1

                    try:
                        # Preparar datos para Django
                        datos = {
                            'unidad': row['unidad'],
                            'unidad_alt': row.get('unidad_alt'),
                            'razon': row.get('razon'),
                            'usuario': row.get('usuario'),
                            'tpo_doc': row.get('tpo_doc'),
                            'num_doc': row.get('num_doc'),
                            'tpo_iva': row.get('tpo_iva'),
                            'propietario': row.get('propietario'),
                            'calle': row.get('calle'),
                            'zona': row.get('zona'),
                            'locali': row.get('locali'),
                            'numero': row.get('numero'),
                            'piso': row.get('piso'),
                            'depto': row.get('depto'),
                            'dat_complem': row.get('dat_complem'),
                            'cod_pos': row.get('cod_pos'),
                            'seccion': row.get('seccion'),
                            'manzana': row.get('manzana'),
                            'parcela': row.get('parcela'),
                            'subparcela': row.get('subparcela'),
                            'telefono': row.get('telefono'),
                            'telefono_cel': row.get('telefono_cel'),
                            'fax': row.get('fax'),
                            'tel_laboral': row.get('tel_laboral'),
                            'e_mail': row.get('e_mail'),
                            'e_mail_alternativo': row.get('e_mail_alternativo'),
                            'fec_sit': row.get('fec_sit'),
                            'fec_ini_mot_cor': row.get('fec_ini_mot_cor'),
                            'fec_rev_mot_cor': row.get('fec_rev_mot_cor'),
                            'fec_ini_mot_gd': row.get('fec_ini_mot_gd'),
                            'fec_rev_mot_gd': row.get('fec_rev_mot_gd'),
                            'fec_ini_mot_gj': row.get('fec_ini_mot_gj'),
                            'fec_rev_mot_gj': row.get('fec_rev_mot_gj'),
                            'fec_ini_mot_ges': row.get('fec_ini_mot_ges'),
                            'fec_rev_mot_ges': row.get('fec_rev_mot_ges'),
                            'ult_act': row.get('ult_act'),
                            'ult_ver_e_mail': row.get('ult_ver_e_mail'),
                            'fec_aviso_fin_vig_cond_imp': row.get('fec_aviso_fin_vig_cond_imp'),
                            'cortable': row.get('cortable'),
                            'gestionable': row.get('gestionable'),
                            'lec_obl': row.get('lec_obl'),
                            'rep_obl': row.get('rep_obl'),
                            'gestion_gd': row.get('gestion_gd'),
                            'gestion_gj': row.get('gestion_gj'),
                            'adh_fac_dig': row.get('adh_fac_dig'),
                            'mot_cortable': row.get('mot_cortable'),
                            'mot_gd': row.get('mot_gd'),
                            'mot_gestionable': row.get('mot_gestionable'),
                            'mot_gj': row.get('mot_gj'),
                            'motivo_e_mail': row.get('motivo_e_mail'),
                            'motivo_telefono': row.get('motivo_telefono'),
                            'situacion': row.get('situacion'),
                            'rel_cli_uni': row.get('rel_cli_uni'),
                            'uni_fun': row.get('uni_fun'),
                            'dir_cob': row.get('dir_cob'),
                            'dir_env': row.get('dir_env'),
                            'nro_calle': row.get('nro_calle'),
                            'reparto': row.get('reparto'),
                            'ruta_dis': row.get('ruta_dis'),
                            'cod_edi': row.get('cod_edi'),
                            'nom_edi': row.get('nom_edi'),
                            'usu_act': row.get('usu_act'),
                            'usu_sit': row.get('usu_sit'),
                            'usu_of_vir': row.get('usu_of_vir'),
                            'cuenta': row.get('cuenta'),
                            'ite_agr': row.get('ite_agr'),
                            'por_gra': row.get('por_gra'),
                            'val_atr_0': row.get('val_atr_0'),
                            'val_atr_1': row.get('val_atr_1'),
                            'val_atr_2': row.get('val_atr_2'),
                            'val_atr_3': row.get('val_atr_3'),
                            'val_atr_4': row.get('val_atr_4'),
                            'val_atr_5': row.get('val_atr_5'),
                            'val_atr_6': row.get('val_atr_6'),
                            'val_atr_7': row.get('val_atr_7'),
                            'val_atr_8': row.get('val_atr_8'),
                            'val_atr_9': row.get('val_atr_9'),
                            'val_atr_10': row.get('val_atr_10'),
                            'val_atr_11': row.get('val_atr_11'),
                            'val_atr_12': row.get('val_atr_12'),
                            'val_atr_13': row.get('val_atr_13'),
                            'val_atr_14': row.get('val_atr_14'),
                            'val_atr_15': row.get('val_atr_15'),
                            'val_atr_16': row.get('val_atr_16'),
                            'val_atr_17': row.get('val_atr_17'),
                            'val_atr_18': row.get('val_atr_18'),
                            'val_atr_19': row.get('val_atr_19'),
                            'val_atr_20': row.get('val_atr_20'),
                            'val_atr_21': row.get('val_atr_21'),
                            'val_atr_22': row.get('val_atr_22'),
                            'val_atr_23': row.get('val_atr_23'),
                            'val_atr_24': row.get('val_atr_24'),
                            'val_atr_25': row.get('val_atr_25'),
                            'val_atr_26': row.get('val_atr_26'),
                            'val_atr_27': row.get('val_atr_27'),
                            'val_atr_28': row.get('val_atr_28'),
                            'val_atr_29': row.get('val_atr_29'),
                        }

                        # Actualizar o crear registro
                        obj, created = CacheUnidadSISA.objects.update_or_create(
                            unidad=datos['unidad'],
                            defaults=datos
                        )

                        if created:
                            registros_creados += 1
                        else:
                            registros_actualizados += 1

                        # Mostrar progreso cada 1000 registros
                        if registros_procesados % 1000 == 0:
                            self.stdout.write(f'Procesados: {registros_procesados}...')

                    except Exception as e:
                        errores.append(f"Error en unidad {row.get('unidad')}: {str(e)}")
                        continue

            cursor.close()
            connection.close()

            # Resumen
            self.stdout.write(self.style.SUCCESS(f'\n=== RESUMEN ==='))
            self.stdout.write(self.style.SUCCESS(f'Registros procesados: {registros_procesados}'))
            self.stdout.write(self.style.SUCCESS(f'Registros creados: {registros_creados}'))
            self.stdout.write(self.style.SUCCESS(f'Registros actualizados: {registros_actualizados}'))

            if errores:
                self.stdout.write(self.style.WARNING(f'\nErrores encontrados: {len(errores)}'))
                for error in errores[:10]:  # Mostrar solo los primeros 10
                    self.stdout.write(self.style.WARNING(f'  - {error}'))

            self.stdout.write(self.style.SUCCESS('\nActualización completada exitosamente!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nError fatal: {str(e)}'))
            raise
