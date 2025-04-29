from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from .gral import Operarios


OPCIONES_COND_IVA = [('-------', '-------'), ('Monotributo', 'Monotributo'),
                     ('Resp. Inscripto', 'Resp. Inscripto')]
OPCIONES_DESTINO_STOCK = [('-------', '-------'), ('Conexiones', 'Conexiones'), ('Pérdidas', 'Pérdidas'),
                          ('Conexiones / Pérdidas', 'Conexiones / Pérdidas'), ('Extensiones', 'Extensiones'),
                          ('Otro', 'Otro')]
OPCIONES_CATEG_MATERIALES = [('-------', '-------'), ('Agua', 'Agua'), ('Cloacas', 'Cloacas'),
                             ('Herramienta', 'Herramienta'), ('Indumentaria', 'Indumentaria'),
                             ('Elemento seguridad', 'Elemento seguridad'), ('Repuesto', 'Repuesto')]


class Proveedores(models.Model):
    """Altas Proveedores."""

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_new_proveedor')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_new_proveedor')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    cuit = models.BigIntegerField()
    razon = models.CharField(max_length=200, null=False)
    domicilio = models.CharField(max_length=200, null=True)
    cond_iva = models.CharField(max_length=50, choices=OPCIONES_COND_IVA, default='-------')
    mail_1 = models.CharField(max_length=130, null=True, blank=True)
    mail_2 = models.CharField(max_length=130, null=True, blank=True)
    tel_1 = models.CharField(max_length=130, null=True, blank=True)
    tel_2 = models.CharField(max_length=130, null=True, blank=True)
    contacto = models.CharField(max_length=130, null=True, blank=True)
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
        id_alta = (str(self.cuit) + ' | ' + str(self.razon))
        return id_alta


class Materiales(models.Model):
    """Altas Materiales."""

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_new_material')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_new_material')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    descripcion = models.CharField(max_length=200, null=False)
    unidad_medida = models.CharField(max_length=50, null=False)
    categoria = models.CharField(max_length=50, null=False)
    destino = models.CharField(max_length=50, choices=OPCIONES_DESTINO_STOCK, default='-------')
    stock_minimo = models.IntegerField(blank=True, null=True)
    stock_correcto = models.IntegerField(blank=True, null=True)
    proveedores = models.ManyToManyField(Proveedores, blank=True, limit_choices_to={'eliminado': 'Activo'})
    imagen = models.ImageField(blank=True, null=True,
                               upload_to='pat_pics/%Y-%m-%d/')
    eliminado = models.CharField(max_length=50, default='Activo')

    @property
    def semaforo(self):
        try:
            existencia = int(MovimientoMateriales.objects.filter(material=self.pk)
                             .aggregate(stock=Sum('cantidad'))['stock'])
        except TypeError:
            return '<span>Error</span>'
        try:
            mini = int(self.stock_minimo)
            corr = int(self.stock_correcto)
            existencia = int(existencia)
        except TypeError:
            return '<span>Error</span>'
        if existencia < mini:
            sem = '<span style="color: red; font-size:25px;">&#9873;</span>'
        elif mini <= existencia < corr:
            sem = '<span style="color: yellow; font-size:25px;">&#9873;</span>'
        elif existencia >= corr:
            sem = '<span style="color: green; font-size:25px;">&#9873;</span>'
        return sem

    def guardar(self):
        """Guarda nueva alta."""
        self.save()

    def eliminar(self):
        """Elimina alta."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_rec como str."""
        id_alta = (str(self.id) + ' | ' + str(self.descripcion)) + ' | ' + str(self.categoria)
        return id_alta


class Solicitante(models.Model):
    """Altas solicitante de compra."""

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_new_solicitante')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_new_solicitante')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    solicitante = models.CharField(max_length=200, null=False)
    eliminado = models.CharField(max_length=50, default='Activo')

    def guardar(self):
        """Guarda nuevo solicitante."""
        self.save()

    def eliminar(self):
        """Elimina solicitante."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_sol como str."""
        id_solicitante = (str(self.solicitante))
        return id_solicitante


class TrabRealizStock(models.Model):
    """Trabajos realizados STOCK."""

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_trabrealiz')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_trabrealiz')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    trabajo = models.CharField(max_length=200, null=False)
    eliminado = models.CharField(max_length=50, default='Activo')

    def guardar(self):
        """Guarda trabajo realizado."""
        self.save()

    def eliminar(self):
        """Elimina solicitante."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_sol como str."""
        id_trabajo = (str(self.trabajo))
        return id_trabajo


class Egreso(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_nuevo_egreso')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_nuevo_egreso')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    fecha = models.DateField(default=timezone.now)
    trabajo_realizado = models.ForeignKey(TrabRealizStock, on_delete=models.CASCADE, limit_choices_to={'eliminado': 'Activo'}, null=True)  # models.CharField(max_length=150, choices=OPCIONES_TRABAJO_REALIZADO_STOCK, default='-------')
    personal = models.ManyToManyField(Operarios, blank=True)
    observaciones_egr = models.CharField(max_length=3000, blank=True, null=True)
    eliminado = models.CharField(max_length=50, default='Activo')

    def guardar(self):
        """Guarda egreso."""
        self.save()

    def eliminar(self):
        """Elimina egreso."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_egr como str."""
        id_egr = (str(self.trabajo_realizado) + ' | ' + str(self.fecha))
        return id_egr


class Ingreso(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_nuevo_ingreso')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_nuevo_ingreso')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    fecha = models.DateField(default=timezone.now)
    proveedor = models.ForeignKey(Proveedores, on_delete=models.CASCADE, limit_choices_to={'eliminado': 'Activo'}, null=True)
    n_orden_de_compra = models.CharField(max_length=100, blank=True, null=True)
    n_presupuesto = models.CharField(max_length=100, blank=True, null=True)
    n_factura = models.CharField(max_length=100, blank=True, null=True)
    n_remito = models.CharField(max_length=100, blank=True, null=True)
    cond_pago = models.CharField(max_length=200, blank=True, null=True)
    solicitante = models.ManyToManyField(Solicitante, related_name='solicitante_stock')
    observaciones_ing = models.CharField(max_length=3000, blank=True, null=True)
    eliminado = models.CharField(max_length=50, default='Activo')

    def guardar(self):
        """Guarda ingreso."""
        self.save()

    def eliminar(self):
        """Elimina ingreso."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_ing como str."""
        id_ing = (str(self.proveedor) + ' | ' + str(self.fecha))
        return id_ing


class MovimientoMateriales(models.Model):
    """Movimiento de materiales."""
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_movimiento_materiales')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_movimiento_materiales')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    tipo = models.CharField(max_length=50)
    material = models.ForeignKey(Materiales, on_delete=models.CASCADE, limit_choices_to={'eliminado': 'Activo'}, null=False)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    eliminado = models.CharField(max_length=50, default='Activo')
    ing_asoc = models.ForeignKey(Ingreso, on_delete=models.CASCADE, limit_choices_to={'eliminado': 'Activo'}, null=True, related_name='articulos_ing')
    egr_asoc = models.ForeignKey(Egreso, on_delete=models.CASCADE, limit_choices_to={'eliminado': 'Activo'}, null=True, related_name='articulos_egr')

    def guardar(self):
        """Guarda movimiento."""
        self.save()

    def eliminar(self):
        """Elimina movimiento."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_mov como str."""
        id_mov = (str(self.material) + ' | ' + str(self.cantidad))
        return id_mov


class PrecioMateriales(models.Model):
    """Precios de materiales."""
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_precio_materiales')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_precio_materiales')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    fecha = models.DateField(default=timezone.now)
    proveedor = models.ForeignKey(Proveedores, on_delete=models.CASCADE, limit_choices_to={'eliminado': 'Activo'}, null=False)
    material = models.ForeignKey(Materiales, on_delete=models.CASCADE, limit_choices_to={'eliminado': 'Activo'}, null=False)
    precio = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    eliminado = models.CharField(max_length=50, default='Activo')

    def guardar(self):
        """Guarda precio."""
        self.save()

    def eliminar(self):
        """Elimina precio."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_mov como str."""
        id_precio = (str(self.fecha + ' | ' + self.proveedor) + ' | ' + str(self.material))
        return id_precio
