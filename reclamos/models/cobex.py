from django.conf import settings
from django.db import models


class Fava(models.Model):
    """Altas débito automático FAVA."""
    n_de_alta = models.AutoField(primary_key=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_fava')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_fava')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    cuenta_osebal = models.IntegerField(null=False)
    tarjeta_fava = models.BigIntegerField(null=False)
    mail = models.CharField(max_length=50, blank=True, null=True)
    telefono = models.CharField(max_length=50, null=False)
    eliminado = models.CharField(max_length=50, default='Activo')
    archivo = models.FileField(blank=True, null=True,
                               upload_to='%Y-%m-%d/')

    def guardar(self):
        """Guarda nueva alta."""
        self.save()

    def eliminar(self):
        """Elimina alta."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_rec como str."""
        id_alta = (str(self.n_de_alta) + ' / ' + str(self.cuenta_osebal))
        return id_alta


class DebDirect(models.Model):
    """Altas débito automático debito directo."""
    n_de_alta = models.AutoField(primary_key=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='author_debdirect')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='editor_debdirect')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    cuenta_osebal = models.IntegerField(null=False)
    cbu = models.CharField(max_length=22, null=False)
    mail = models.CharField(max_length=50, blank=True, null=True)
    telefono = models.CharField(max_length=50, null=False)
    eliminado = models.CharField(max_length=50, default='Activo')
    archivo = models.FileField(blank=True, null=True,
                               upload_to='%Y-%m-%d/')

    def guardar(self):
        """Guarda nueva alta."""
        self.save()

    def eliminar(self):
        """Elimina alta."""
        self.eliminado = 'Eliminado'
        self.save()

    def __str__(self):
        """Devuelve id_rec como str."""
        id_alta = (str(self.n_de_alta) + ' / ' + str(self.cuenta_osebal))
        return id_alta
