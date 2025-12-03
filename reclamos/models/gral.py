from django.db import models

YEARS = list(range(2017, 2028))
UNIDADES = [('Un.', 'Un.'), ('Mts.', 'Mts.')]


class Customperms(models.Model):
    """Permisos personalizados."""

    tipo = models.CharField(max_length=255)

    class Meta:
        """Meta data para el modelo."""

        permissions = [
            ('ver_reclamo', 'ver_reclamo'),
            ('editar_reclamo', 'editar_reclamo'),
            ('admin_tools_1', 'admin_tools_1'),
            ('admin_tools_2', 'admin_tools_2'),
            ('admin_tools_3', 'admin_tools_3'),
            ('stock', 'stock'),
            ('gsa', 'gsa'),
            ('sarasa', 'sarasa'),
            ('simulador', 'simulador'),
            ('rrhh', 'rrhh'),
            ('medidos', 'medidos')
        ]


class Operarios(models.Model):
    """Listado de operarios."""

    operario = models.CharField(max_length=255)

    def __str__(self):
        """Devuelve str operario."""
        return str(self.operario)


class CacheUnidadSISA(models.Model):
    """Cache completo de la tabla z80unidad de SISA."""

    # Campos clave
    unidad = models.DecimalField(max_digits=10, decimal_places=0, primary_key=True)
    unidad_alt = models.CharField(max_length=20, db_index=True, blank=True, null=True)

    # Identificación
    razon = models.CharField(max_length=50, db_index=True, blank=True, null=True)
    usuario = models.DecimalField(max_digits=10, decimal_places=0, db_index=True, blank=True, null=True)
    tpo_doc = models.CharField(max_length=4, blank=True, null=True)
    num_doc = models.DecimalField(max_digits=11, decimal_places=0, blank=True, null=True)
    tpo_iva = models.CharField(max_length=2, blank=True, null=True)
    propietario = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True)

    # Domicilio
    calle = models.CharField(max_length=40, blank=True, null=True)
    zona = models.CharField(max_length=8, db_index=True, blank=True, null=True)
    locali = models.CharField(max_length=8, blank=True, null=True)
    numero = models.DecimalField(max_digits=8, decimal_places=0, blank=True, null=True)
    piso = models.CharField(max_length=2, blank=True, null=True)
    depto = models.CharField(max_length=4, blank=True, null=True)
    dat_complem = models.CharField(max_length=40, blank=True, null=True)
    cod_pos = models.DecimalField(max_digits=5, decimal_places=0, blank=True, null=True)
    seccion = models.CharField(max_length=8, blank=True, null=True)
    manzana = models.CharField(max_length=8, blank=True, null=True)
    parcela = models.CharField(max_length=8, blank=True, null=True)
    subparcela = models.CharField(max_length=4, blank=True, null=True)

    # Contacto
    telefono = models.CharField(max_length=25, blank=True, null=True)
    telefono_cel = models.CharField(max_length=25, blank=True, null=True)
    fax = models.CharField(max_length=25, blank=True, null=True)
    tel_laboral = models.CharField(max_length=25, blank=True, null=True)
    e_mail = models.CharField(max_length=60, blank=True, null=True)
    e_mail_alternativo = models.CharField(max_length=60, blank=True, null=True)

    # Fechas
    fec_sit = models.DateField(blank=True, null=True)
    fec_ini_mot_cor = models.DateField(blank=True, null=True)
    fec_rev_mot_cor = models.DateField(blank=True, null=True)
    fec_ini_mot_gd = models.DateField(blank=True, null=True)
    fec_rev_mot_gd = models.DateField(blank=True, null=True)
    fec_ini_mot_gj = models.DateField(blank=True, null=True)
    fec_rev_mot_gj = models.DateField(blank=True, null=True)
    fec_ini_mot_ges = models.DateField(blank=True, null=True)
    fec_rev_mot_ges = models.DateField(blank=True, null=True)
    ult_act = models.DateField(blank=True, null=True)
    ult_ver_e_mail = models.DateField(blank=True, null=True)
    fec_aviso_fin_vig_cond_imp = models.DateField(blank=True, null=True)

    # Flags y estados
    cortable = models.CharField(max_length=1, blank=True, null=True)
    gestionable = models.CharField(max_length=1, blank=True, null=True)
    lec_obl = models.CharField(max_length=1, blank=True, null=True)
    rep_obl = models.CharField(max_length=1, blank=True, null=True)
    gestion_gd = models.CharField(max_length=1, blank=True, null=True)
    gestion_gj = models.CharField(max_length=1, blank=True, null=True)
    adh_fac_dig = models.CharField(max_length=1, blank=True, null=True)

    # Motivos
    mot_cortable = models.CharField(max_length=3, blank=True, null=True)
    mot_gd = models.CharField(max_length=3, blank=True, null=True)
    mot_gestionable = models.CharField(max_length=3, blank=True, null=True)
    mot_gj = models.CharField(max_length=3, blank=True, null=True)
    motivo_e_mail = models.CharField(max_length=2, blank=True, null=True)
    motivo_telefono = models.CharField(max_length=2, blank=True, null=True)

    # Configuración
    situacion = models.CharField(max_length=4, db_index=True, blank=True, null=True)
    rel_cli_uni = models.CharField(max_length=2, db_index=True, blank=True, null=True)
    uni_fun = models.CharField(max_length=3, blank=True, null=True)

    # Relaciones
    dir_cob = models.IntegerField(blank=True, null=True)
    dir_env = models.IntegerField(blank=True, null=True)
    nro_calle = models.IntegerField(db_index=True, blank=True, null=True)

    # Distribución
    reparto = models.CharField(max_length=4, blank=True, null=True)
    ruta_dis = models.CharField(max_length=30, blank=True, null=True)
    cod_edi = models.CharField(max_length=2, blank=True, null=True)
    nom_edi = models.CharField(max_length=40, blank=True, null=True)

    # Auditoría
    usu_act = models.CharField(max_length=8, blank=True, null=True)
    usu_sit = models.CharField(max_length=8, blank=True, null=True)
    usu_of_vir = models.CharField(max_length=60, blank=True, null=True)

    # Varios
    cuenta = models.CharField(max_length=16, blank=True, null=True)
    ite_agr = models.CharField(max_length=16, blank=True, null=True)
    por_gra = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True)

    # Atributos dinámicos (30 campos)
    val_atr_0 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_1 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_2 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_3 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_4 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_5 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_6 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_7 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_8 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_9 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_10 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_11 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_12 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_13 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_14 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_15 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_16 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_17 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_18 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_19 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_20 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_21 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_22 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_23 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_24 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_25 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_26 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_27 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_28 = models.CharField(max_length=50, blank=True, null=True)
    val_atr_29 = models.CharField(max_length=50, blank=True, null=True)

    # Control del cache
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cache_unidad_sisa'
        verbose_name = 'Cache Unidad SISA'
        verbose_name_plural = 'Cache Unidades SISA'

    def __str__(self):
        return f"Unidad {self.unidad} - {self.razon or 'Sin razón'}"
