from django.conf import settings
from django.db import models
from django.utils import timezone
from .gral import Operarios

OPCIONES_A_REPORTE = [('Si', 'Si'), ('No', 'No')]
OPCIONES_ANIO = [('Filtro', 'Filtro'), ('Todos', 'Todos'), ('2010', '2010'), ('2016', '2016'),
                 ('2017', '2017'), ('2018', '2018'), ('2019', '2019'), ('2020', '2020'),
                 ('2021', '2021'), ('2022', '2022'), ('2023', '2023'), ('2024', '2024'), ('2025', '2025')]
OPCIONES_TIPO = [('Filtro', 'Filtro'), ('Todos', 'Todos'), ('Agua', 'Agua'), ('Cloacas', 'Cloacas'),
                 ('Vereda', 'Vereda'), ('Calidad', 'Calidad'),
                 ('Facturación', 'Facturación'), ('Marco y tapa', 'Marco y tapa'),
                 ('Pavimento', 'Pavimento'),
                 ('Disminución', 'Disminución'), ('Verificación Redes', 'Verificación Redes'),
                 ('Nivelación / Pozos', 'Nivelación / Pozos'),
                 ('Mant. Red Cloacal', 'Mant. Red Cloacal'),
                 ('Verificación por nuevas conexiones', 'Verificación por nuevas conexiones'),
                 ('Verificación por facturación', 'Verificación por facturación'),
                 ('Verificación conexiones irregulares', 'Verificación conexiones irregulares'),
                 ('Baja Presión', 'Baja Presión'), ('Reclamo servicio medido', 'Reclamo servicio medido')]


class Tipos(models.Model):
    """Tipos de reclamo."""

    tipo = models.CharField(max_length=255)

    def __str__(self):
        """Devuelve str tipo."""
        return str(self.tipo)


class Estados(models.Model):
    """Estados de reclamo."""

    estado = models.CharField(max_length=255)

    def __str__(self):
        """Devuelve str estado."""
        return str(self.estado)


class Reclamo(models.Model):
    """Modelo de Reclamo completo con todos sus datos."""

    n_de_reclamo = models.AutoField(primary_key=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    fecha = models.DateField(default=timezone.now)
    tipo_de_reclamo = models.ForeignKey(Tipos, on_delete=models.CASCADE)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    calle = models.CharField(max_length=100)  # , blank=True, null=True)
    altura = models.IntegerField()  # blank=True, null=True)
    telefono = models.CharField(max_length=100, blank=True, null=True)
    detalle = models.TextField(blank=True, null=True)
    estado = models.ForeignKey(Estados, default='Pendiente', on_delete=models.CASCADE)
    partida = models.IntegerField(blank=True, null=True)
    # deuda = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    fecha_resolucion = models.DateField(blank=True, null=True)
    tarea_realizada = models.CharField(max_length=1000, blank=True, null=True)
    operario_s = models.ManyToManyField(Operarios, blank=True)
    notificacion = models.CharField(max_length=255, blank=True, null=True)
    comentario = models.TextField(blank=True, null=True)
    a_reporte = models.CharField(max_length=2,
                                 choices=OPCIONES_A_REPORTE,
                                 default='Si')
    eliminado = models.CharField(max_length=50, default='Activo')
    borrador = models.CharField(max_length=50, default='No')
    n_reclamo_gsa = models.CharField(max_length=100)

    def guardar(self):
        """Guarda nuevo Reclamo."""
        self.borrador = 'No'
        self.save()

    def eliminar(self):
        """Elimina reclamo."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_rec como str."""
        id_rec = (str(self.n_de_reclamo) + ' / ' + str(self.apellido) +
                  r' / ' + str(self.fecha)[0:10])
        return id_rec


class Archivos(models.Model):
    """Archivos asociados a reclamos."""
    reclamo = models.ForeignKey(Reclamo, on_delete=models.CASCADE,
                                related_name='archivos')
    archivo = models.FileField(blank=True, null=True,
                               upload_to='%Y-%m-%d/')
    descripcion = models.CharField(max_length=30)

    def __str__(self):
        """Devuelve id_arch como str."""
        id_arch = str(self.descripcion)
        return id_arch


class DatosCuadrilla(models.Model):
    """Operarios y fecha para planillas de cuadrilla."""
    fecha = models.DateField()
    datos = models.CharField(max_length=255, default='unico')
    operarios_agua = models.ManyToManyField(Operarios, related_name='operarios_agua')
    operarios_cloacas = models.ManyToManyField(Operarios, related_name='operarios_cloacas')
    operarios_dism = models.ManyToManyField(Operarios, related_name='operarios_dism')
    operarios_pozos = models.ManyToManyField(Operarios, related_name='operarios_pozos')
    operarios_marco_tapa = models.ManyToManyField(Operarios, related_name='operarios_marco_tapa')
    operarios_facturacion = models.ManyToManyField(Operarios, related_name='operarios_facturacion')
    operarios_mant_red_cloacal = models.ManyToManyField(Operarios, related_name='operarios_mant_red_cloacal')
    operarios_verif_por_fact = models.ManyToManyField(Operarios, related_name='operarios_verif_por_fact')
    operarios_serv_med = models.ManyToManyField(Operarios, related_name='operarios_serv_med')

    def __str__(self):
        """Devuelve str con fecha de datos p/ planillas."""
        datos_planillas = str(self.fecha)
        return datos_planillas


class FiltroInformePendFin(models.Model):
    """Filtro para informe de pendientes / finalizados."""

    single = models.CharField(max_length=255, default='unico')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    tipo = models.ForeignKey(Tipos, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        """Devuelve str unico."""
        uni = str(self.single)
        return uni


class FiltroInformeTiemResol(models.Model):
    """Filtro para informe tiempos de resolución."""

    single = models.CharField(max_length=255, default='unico')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    tipo = models.ForeignKey(Tipos, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        """Devuelve str unico."""
        uni = str(self.single)
        return uni


class FiltroListadosTrabajos1(models.Model):
    """Filtro para listados de trabajos (anio)."""

    single = models.CharField(max_length=255, default='unico')
    anio = models.CharField(max_length=255,
                            choices=OPCIONES_ANIO,
                            default='2023')

    def __str__(self):
        """Devuelve str unico."""
        uni = str(self.single)
        return uni


class FiltroListadosTrabajos2(models.Model):
    """Filtro para listados de trabajos (tipo)."""

    single = models.CharField(max_length=255, default='unico')
    tipo = models.CharField(max_length=255,
                            choices=OPCIONES_TIPO,
                            default='Todos')

    def __str__(self):
        """Devuelve str unico."""
        uni = str(self.single)
        return uni
