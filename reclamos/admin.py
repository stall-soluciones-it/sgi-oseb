from django.contrib import admin

# Register your models here.
from .models import (Reclamo, Operarios, Archivos, Estados, Tipos, DatosCuadrilla,
                     FiltroInformePendFin, FiltroInformeTiemResol, FiltroListadosTrabajos1,
                     FiltroListadosTrabajos2, Fava, DebDirect, Materiales, Proveedores,
                     MovimientoMateriales, Solicitante, TrabRealizStock, Empleado,
                     Novedades_vacaciones, Reclamos_correo)


class ReclamosReadOnlyFields(admin.ModelAdmin):
    readonly_fields = ('created_date', 'updated_date')


admin.site.register(Reclamo, ReclamosReadOnlyFields)
admin.site.register(Operarios)
admin.site.register(Archivos)
admin.site.register(Estados)
admin.site.register(Tipos)
admin.site.register(DatosCuadrilla)
admin.site.register(FiltroInformePendFin)
admin.site.register(FiltroInformeTiemResol)
admin.site.register(FiltroListadosTrabajos1)
admin.site.register(FiltroListadosTrabajos2)
admin.site.register(Fava)
admin.site.register(DebDirect)
admin.site.register(Materiales)
admin.site.register(Proveedores)
admin.site.register(MovimientoMateriales)
admin.site.register(Solicitante)
admin.site.register(TrabRealizStock)
admin.site.register(Empleado)
admin.site.register(Novedades_vacaciones)
admin.site.register(Reclamos_correo)
