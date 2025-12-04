# -*- coding: utf-8 -*-
"""Vista AJAX para toggle de a_reporte en reclamos."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from reclamos.models import Reclamo


@login_required
@require_POST
def toggle_a_reporte(request):
    """
    Toggle del campo a_reporte entre 'Si' y 'No'.

    POST parameters:
    - reclamo_id: ID del reclamo a modificar

    Returns:
    - JSON con éxito/error y nuevo estado
    """
    try:
        reclamo_id = request.POST.get('reclamo_id')

        if not reclamo_id:
            return JsonResponse({
                'success': False,
                'error': 'ID de reclamo no proporcionado'
            }, status=400)

        reclamo = get_object_or_404(Reclamo, n_de_reclamo=reclamo_id)

        # Toggle: Si -> No, No -> Si
        nuevo_estado = 'No' if reclamo.a_reporte == 'Si' else 'Si'
        reclamo.a_reporte = nuevo_estado
        reclamo.save(update_fields=['a_reporte'])

        return JsonResponse({
            'success': True,
            'nuevo_estado': nuevo_estado,
            'reclamo_id': reclamo_id
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
