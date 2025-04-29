"""Formularios."""
# pylint: disable=too-few-public-methods
from django import forms
from reclamos.models import (Reclamo, Archivos, DatosCuadrilla, Reclamos_correo,
                             FiltroInformePendFin, FiltroInformeTiemResol,
                             FiltroListadosTrabajos1, OPCIONES_ANIO,
                             FiltroListadosTrabajos2, OPCIONES_TIPO, Fava, DebDirect,
                             YEARS)


class ReclamoForm(forms.ModelForm):
    """Form de Reclamo."""

    class Meta:
        """Campos de form Reclamo."""

        model = Reclamo
        fields = ('fecha', 'tipo_de_reclamo', 'apellido', 'calle', 'altura', 'telefono',
                  'detalle', 'estado', 'a_reporte', 'partida', 'fecha_resolucion',
                  'operario_s', 'tarea_realizada', 'notificacion', 'comentario')
        widgets = {'fecha': forms.SelectDateWidget(years=YEARS),
                   'fecha_resolucion': forms.SelectDateWidget(years=YEARS)}


class FavaForm(forms.ModelForm):
    """Form de alta FAVA."""

    class Meta:
        """Campos de form FAVA."""

        model = Fava
        fields = ('cuenta_osebal', 'tarjeta_fava', 'mail', 'telefono', 'archivo')


class DebForm(forms.ModelForm):
    """Form de alta debito directo."""

    class Meta:
        """Campos de form debito directo."""
        model = DebDirect
        fields = ('cuenta_osebal', 'cbu', 'mail', 'telefono', 'archivo')

    def clean_cbu(self):
        cbu = self.cleaned_data.get('cbu')
        if not cbu.isdigit() or len(cbu) != 22:
            raise forms.ValidationError("El CBU debe contener exactamente 22 dígitos numéricos.")
        return cbu


class ArchivoForm(forms.ModelForm):
    """Form de Archivo."""

    class Meta:
        """Campos de form Archivo."""

        model = Archivos
        fields = ('archivo', 'descripcion')


class CuadrillaAgua(forms.ModelForm):
    """Form de Archivo."""

    class Meta:
        """Campos de form Archivo."""

        model = DatosCuadrilla
        fields = ('fecha', 'operarios_agua')
        widgets = {'fecha': forms.SelectDateWidget(years=YEARS)}


class CuadrillaCloaca(forms.ModelForm):
    """Form de Archivo."""

    class Meta:
        """Campos de form Archivo."""

        model = DatosCuadrilla
        fields = ('fecha', 'operarios_cloacas')
        widgets = {'fecha': forms.SelectDateWidget(years=YEARS)}


class CuadrillaNivPozos(forms.ModelForm):
    """Form de Archivo."""

    class Meta:
        """Campos de form Archivo."""

        model = DatosCuadrilla
        fields = ('fecha', 'operarios_pozos')
        widgets = {'fecha': forms.SelectDateWidget(years=YEARS)}


class CuadrillaMcoTapa(forms.ModelForm):
    """Form de Archivo."""

    class Meta:
        """Campos de form Archivo."""

        model = DatosCuadrilla
        fields = ('fecha', 'operarios_marco_tapa')
        widgets = {'fecha': forms.SelectDateWidget(years=YEARS)}


class CuadrillaMantCloacal(forms.ModelForm):
    """Form de Archivo."""

    class Meta:
        """Campos de form Archivo."""

        model = DatosCuadrilla
        fields = ('fecha', 'operarios_mant_red_cloacal')
        widgets = {'fecha': forms.SelectDateWidget(years=YEARS)}


class CuadrillaVerifFact(forms.ModelForm):
    """Form de Archivo."""

    class Meta:
        """Campos de form Archivo."""

        model = DatosCuadrilla
        fields = ('fecha', 'operarios_verif_por_fact')
        widgets = {'fecha': forms.SelectDateWidget(years=YEARS)}


class CuadrillaServMed(forms.ModelForm):
    """Form de Archivo."""

    class Meta:
        """Campos de form Archivo."""

        model = DatosCuadrilla
        fields = ('fecha', 'operarios_serv_med')
        widgets = {'fecha': forms.SelectDateWidget(years=YEARS)}


class FiltroInformePendFinForm(forms.ModelForm):
    """Form para filtro de reporte."""

    class Meta:
        """Campos de form para reporte."""

        model = FiltroInformePendFin
        fields = ('fecha_inicio', 'fecha_fin', 'tipo')
        widgets = {'fecha_inicio': forms.SelectDateWidget(years=YEARS),
                   'fecha_fin': forms.SelectDateWidget(years=YEARS)}


class FiltroInformeTiemResolForm(forms.ModelForm):
    """Form para filtro de reporte."""

    class Meta:
        """Campos de form para reporte."""

        model = FiltroInformeTiemResol
        fields = ('fecha_inicio', 'fecha_fin', 'tipo')
        widgets = {'fecha_inicio': forms.SelectDateWidget(years=YEARS),
                   'fecha_fin': forms.SelectDateWidget(years=YEARS)}


class FiltroListadosTrabajosForm1(forms.ModelForm):
    """Form de filtro de anio en listados de trabajos (anio)."""

    anio = forms.ChoiceField(choices=OPCIONES_ANIO)

    class Meta:
        """Campos de form para filtro."""

        model = FiltroListadosTrabajos1
        fields = ('anio',)


class FiltroListadosTrabajosForm2(forms.ModelForm):
    """Form de filtro de anio en listados de trabajos (tipo)."""

    tipo = forms.ChoiceField(choices=OPCIONES_TIPO)

    class Meta:
        """Campos de form para filtro."""

        model = FiltroListadosTrabajos2
        fields = ('tipo',)


class CorreoForm(forms.ModelForm):
    """Form de reclamo correo."""

    class Meta:
        """Campos de form CorreoForm."""

        model = Reclamos_correo
        fields = ('cuenta', 'observaciones')
