from django import forms
from reclamos.models import (Materiales, Proveedores, MovimientoMateriales,
                             Egreso, Ingreso, PrecioMateriales,
                             OPCIONES_CATEG_MATERIALES, UNIDADES, YEARS,
                             OPCIONES_DESTINO_STOCK)


# GENERAL
class MaterialesForm(forms.ModelForm):
    """Form de Materiales."""
    categoria = forms.ChoiceField(choices=OPCIONES_CATEG_MATERIALES)
    unidad_medida = forms.ChoiceField(choices=UNIDADES)
    destino = forms.ChoiceField(choices=OPCIONES_DESTINO_STOCK)

    class Meta:
        """"Campos de form Materiales."""
        model = Materiales
        fields = ('descripcion', 'unidad_medida', 'categoria', 'stock_minimo',
                  'stock_correcto', 'destino', 'proveedores', 'imagen')


class ProveedoresForm(forms.ModelForm):
    """Form de proveedores."""

    class Meta:
        """"Campos de form."""
        model = Proveedores
        fields = ('cuit', 'cond_iva', 'razon', 'domicilio', 'mail_1', 'mail_2', 'tel_1', 'tel_2', 'contacto')


# EGRESOS
class EgresosForm(forms.ModelForm):
    """Form de egreso materiales."""

    class Meta:
        """"Campos de form."""
        model = Egreso
        fields = ('fecha', 'trabajo_realizado', 'personal', 'observaciones_egr')
        widgets = {'fecha': forms.SelectDateWidget(years=YEARS)}


class MovimientoEgrFormOUT(forms.ModelForm):
    """Form de salida de materiales relacionados a un Egreso."""

    class Meta:
        """"Campos de form."""
        model = MovimientoMateriales

        fields = ('material', 'cantidad')
        # widgets = {'material': autocomplete.ModelSelect2(url='material-autocomplete')}


# INGRESOS
class IngresosForm(forms.ModelForm):
    """Form de ingreso materiales."""

    class Meta:
        """"Campos de form."""
        model = Ingreso

        fields = ('fecha', 'proveedor', 'n_orden_de_compra', 'n_presupuesto',
                  'n_factura', 'n_remito', 'observaciones_ing', 'cond_pago', 'solicitante')
        widgets = {'fecha': forms.SelectDateWidget(years=YEARS)}


class MovimientoIngFormIN(forms.ModelForm):
    "Form de ingreso materiales."

    class Meta:
        "Campos de form."
        model = MovimientoMateriales

        fields = ('material', 'cantidad', 'precio')
        # widgets = {'material': autocomplete.ModelSelect2(url='material-autocomplete')}


# PRECIOS
class PreciosForm(forms.ModelForm):
    "Form de precios materiales."

    class Meta:
        "Campos de form."
        model = PrecioMateriales

        fields = ('fecha', 'proveedor', 'material', 'precio')
        # widgets = {'material': autocomplete.ModelSelect2(url='material-autocomplete')}
