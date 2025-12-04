# -*- coding: utf-8 -*-
"""Vista AJAX para búsqueda de partidas."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from reclamos.models import CacheUnidadSISA, Reclamo


@login_required
def buscar_partidas_ajax(request):
    """
    Búsqueda AJAX de partidas en cache local de SISA.

    Query parameters:
    - q: término de búsqueda (mínimo 3 caracteres)

    Returns:
    - JSON con resultados, máximo 100 registros
    """
    query = request.GET.get('q', '').strip()

    # Validación: mínimo 3 caracteres
    if len(query) < 3:
        return JsonResponse({
            'success': False,
            'message': 'Ingrese al menos 3 caracteres para buscar',
            'resultados': [],
            'total': 0
        })

    # Construir filtros con Q objects
    filtros = Q()

    # Detectar si es búsqueda combinada "calle numero" (ej: "Chacabuco 401")
    partes = query.split()
    busqueda_combinada = False

    if len(partes) >= 2 and partes[-1].isdigit():
        # Última parte es numérica, asumir búsqueda de calle + número
        numero = partes[-1]
        calle = ' '.join(partes[:-1])  # Todo excepto el último elemento

        # Búsqueda con AND: calle Y número
        filtros_combinados = Q(calle__icontains=calle) & Q(numero__icontains=numero)

        # Probar si hay resultados con búsqueda combinada
        count_combinada = CacheUnidadSISA.objects.filter(filtros_combinados).count()

        if count_combinada > 0:
            filtros = filtros_combinados
            busqueda_combinada = True

    # Si no es búsqueda combinada o no dio resultados, usar lógica estándar
    if not busqueda_combinada:
        if query.isdigit():
            # Si es numérico, buscar en: unidad, número de calle, y partida
            filtros |= Q(unidad__icontains=query)
            filtros |= Q(numero__icontains=query)
            filtros |= Q(unidad_alt__icontains=query)
        else:
            # Si es texto, buscar en calle y razón social
            filtros |= Q(calle__icontains=query)
            filtros |= Q(razon__icontains=query)
            # También buscar en partida alternativa
            filtros |= Q(unidad_alt__icontains=query)

    # Ejecutar consulta con límite de 100 resultados
    unidades = CacheUnidadSISA.objects.filter(filtros).values(
        'unidad', 'unidad_alt', 'razon', 'calle', 'numero', 'piso', 'depto'
    )[:100]

    # Obtener partidas con trabajos activos (para marcar en rojo)
    partidas_con_trabajos = set(
        Reclamo.objects.filter(eliminado='Activo', partida__isnull=False)
        .values_list('partida', flat=True)
        .distinct()
    )

    # Construir lista de resultados
    resultados = []
    for unidad in unidades:
        partida_str = str(unidad['unidad_alt']) if unidad['unidad_alt'] else ''
        tiene_trabajos = int(unidad['unidad_alt']) in partidas_con_trabajos if partida_str.isdigit() else False

        resultados.append({
            'unidad': int(unidad['unidad']) if unidad['unidad'] else 0,
            'partida': partida_str,
            'razon': unidad['razon'] or '',
            'calle': unidad['calle'] or '',
            'numero': int(unidad['numero']) if unidad['numero'] else '',
            'piso': unidad['piso'] or '',
            'depto': unidad['depto'] or '',
            'tiene_trabajos': tiene_trabajos
        })

    total_encontrados = len(resultados)
    mensaje = f"Se encontraron {total_encontrados} resultados"
    if total_encontrados == 100:
        mensaje += " (máximo). Refine su búsqueda para mejores resultados."

    return JsonResponse({
        'success': True,
        'message': mensaje,
        'resultados': resultados,
        'total': total_encontrados
    })
