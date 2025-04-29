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
