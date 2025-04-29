from django.conf import settings
from django.db import models
from django.utils import timezone


class Empleado(models.Model):
    """Alta legajo empleado-vacaciones."""
    n_de_alta = models.AutoField(primary_key=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_vacaciones')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_vacaciones')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    n_legajo = models.IntegerField(null=False)
    cuil = models.BigIntegerField(null=False)
    nombre = models.CharField(max_length=100, null=False)
    fecha_ingreso = models.DateField()
    fecha_egreso = models.DateField(null=True, blank=True)
    eliminado = models.CharField(max_length=50, default='Activo')

    def guardar(self):
        """Guarda nueva alta."""
        self.save()

    def eliminar(self):
        """Elimina alta."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_rec como str."""
        id_alta = (str(self.n_de_alta) + ' / ' + str(self.nombre))
        return id_alta


class Novedades_vacaciones(models.Model):
    """Alta novedad-vacaciones."""
    n_novedad = models.AutoField(primary_key=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_vacaciones_novedad')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_vacaciones_novedad')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha_solicitud = models.DateField(null=False, default=timezone.now)
    periodo = models.IntegerField(null=False)
    desde = models.DateField(null=False, default=timezone.now)
    hasta = models.DateField(null=False, default=timezone.now)
    reincorpora = models.DateField(null=False, default=timezone.now)
    dias = models.DecimalField(null=False, max_digits=5, decimal_places=2)
    licencia_completa = models.CharField(max_length=2, null=False)
    observaciones = models.CharField(max_length=2000, null=True, blank=True)
    eliminado = models.CharField(max_length=50, default='Activo')

    def guardar(self):
        """Guarda nueva alta."""
        self.save()

    def eliminar(self):
        """Elimina alta."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_rec como str."""
        id_alta = (str(self.n_novedad) + ' / ' + str(self.empleado))
        return id_alta


class Reclamos_correo(models.Model):
    """Reclamos correo."""
    n_rec_correo = models.AutoField(primary_key=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_correo_novedad')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_correo_novedad')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    cuenta = models.IntegerField(null=False)
    calle = models.CharField(max_length=200, null=True, blank=True)
    altura = models.IntegerField(null=False)
    observaciones = models.CharField(max_length=2000, null=True, blank=True)
    eliminado = models.CharField(max_length=50, default='Activo')
    imprime = models.CharField(max_length=20, null=True, blank=True)

    def guardar(self):
        """Guarda nuevo rec-correo."""
        self.save()

    def eliminar(self):
        """Elimina rec-correo."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_rec como str."""
        id_rec_correo = (str(self.n_rec_correo) + ' / ' + str(self.cuenta))
        return id_rec_correo
