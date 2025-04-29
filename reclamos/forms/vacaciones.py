"""Formularios."""
# pylint: disable=too-few-public-methods
from django import forms
from reclamos.models import (Empleado, Novedades_vacaciones)


class EmpleadoVacacionesForm(forms.ModelForm):
    """Form nuevo empleado vacaciones."""

    class Meta:
        """"Campos de form."""
        model = Empleado
        fields = ('n_legajo', 'nombre', 'cuil', 'fecha_ingreso', 'fecha_egreso')
        widgets = {'fecha_ingreso': forms.SelectDateWidget(years=range(1980, 2041)),
                   'fecha_egreso': forms.SelectDateWidget(years=range(2000, 2041))}


class NovedadesForm(forms.ModelForm):
    """Form nuevo novedad vacaciones."""

    licencia_completa = forms.ChoiceField(choices=[('SI', 'SI'), ('NO', 'NO')])

    class Meta:
        """"Campos de form."""
        model = Novedades_vacaciones
        fields = ('fecha_solicitud', 'periodo', 'desde', 'hasta', 'reincorpora',
                  'dias', 'licencia_completa', 'observaciones')
        widgets = {'fecha_solicitud': forms.SelectDateWidget(years=range(1980, 2030)),
                   'desde': forms.SelectDateWidget(years=range(1980, 2030)),
                   'hasta': forms.SelectDateWidget(years=range(1980, 2030)),
                   'reincorpora': forms.SelectDateWidget(years=range(1980, 2030))}
