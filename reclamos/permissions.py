"""
Módulo de permisos para el sistema de reclamos.

Proporciona funciones helper y decoradores para validar permisos server-side,
reemplazando la lógica anterior basada en nombres de usuario.

Lógica de permisos:
- CREATE: editar_reclamo OR gsa
- VIEW: ver_reclamo OR gsa
- EDIT/DELETE: editar_reclamo (cualquier reclamo) OR gsa + author en grupo GSA
"""

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group


def user_can_view_reclamos(user):
    """
    Verifica si el usuario puede ver reclamos.

    Returns:
        bool: True si el usuario tiene permiso ver_reclamo o gsa
    """
    return user.has_perm('reclamos.ver_reclamo') or user.has_perm('reclamos.gsa')


def user_can_create_reclamo(user):
    """
    Verifica si el usuario puede crear reclamos.

    Returns:
        bool: True si el usuario tiene permiso editar_reclamo o gsa
    """
    return user.has_perm('reclamos.editar_reclamo') or user.has_perm('reclamos.gsa')


def user_can_edit_reclamo(user, reclamo):
    """
    Verifica si el usuario puede editar un reclamo específico.

    Lógica:
    - Si tiene editar_reclamo: puede editar cualquier reclamo
    - Si tiene gsa: solo puede editar reclamos donde el author está en grupo GSA

    Args:
        user: Usuario Django
        reclamo: Instancia de modelo Reclamo

    Returns:
        bool: True si el usuario puede editar el reclamo
    """
    # Usuarios con editar_reclamo pueden editar cualquier reclamo
    if user.has_perm('reclamos.editar_reclamo'):
        return True

    # Usuarios con gsa solo pueden editar reclamos de autores en grupo GSA
    if user.has_perm('reclamos.gsa'):
        return reclamo.author.groups.filter(name='GSA').exists()

    return False


def user_can_delete_reclamo(user, reclamo):
    """
    Verifica si el usuario puede eliminar un reclamo específico.

    Usa la misma lógica que edición:
    - Si tiene editar_reclamo: puede eliminar cualquier reclamo
    - Si tiene gsa: solo puede eliminar reclamos donde el author está en grupo GSA

    Args:
        user: Usuario Django
        reclamo: Instancia de modelo Reclamo

    Returns:
        bool: True si el usuario puede eliminar el reclamo
    """
    # La lógica de eliminación es idéntica a la de edición
    return user_can_edit_reclamo(user, reclamo)


def require_view_permission(view_func):
    """
    Decorador que requiere permiso ver_reclamo O gsa para acceder a la vista.

    Usage:
        @login_required
        @require_view_permission
        def mi_vista(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not user_can_view_reclamos(request.user):
            raise PermissionDenied("No tienes permiso para ver reclamos.")
        return view_func(request, *args, **kwargs)
    return wrapper


def require_create_permission(view_func):
    """
    Decorador que requiere permiso editar_reclamo O gsa para crear reclamos.

    Usage:
        @login_required
        @require_create_permission
        def nuevo_reclamo(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not user_can_create_reclamo(request.user):
            raise PermissionDenied("No tienes permiso para crear reclamos.")
        return view_func(request, *args, **kwargs)
    return wrapper


def require_reclamo_edit_permission(view_func):
    """
    Decorador que verifica permisos de edición para un reclamo específico.

    La vista debe recibir 'pk' como parámetro (ID del reclamo).

    Usage:
        @login_required
        @require_reclamo_edit_permission
        def editar_reclamo(request, pk):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from reclamos.models import Reclamo

        # Obtener el reclamo desde el parámetro pk
        pk = kwargs.get('pk')
        if not pk:
            raise PermissionDenied("No se especificó el reclamo a editar.")

        reclamo = get_object_or_404(Reclamo, pk=pk, eliminado='Activo')

        # Verificar permisos
        if not user_can_edit_reclamo(request.user, reclamo):
            raise PermissionDenied(
                "No tienes permiso para editar este reclamo. "
                "Los usuarios GSA solo pueden editar reclamos creados por otros usuarios GSA."
            )

        return view_func(request, *args, **kwargs)
    return wrapper


def require_reclamo_delete_permission(view_func):
    """
    Decorador que verifica permisos de eliminación para un reclamo específico.

    La vista debe recibir 'pk' como parámetro (ID del reclamo).

    Usage:
        @login_required
        @require_reclamo_delete_permission
        def eliminar_reclamo(request, pk):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from reclamos.models import Reclamo

        # Obtener el reclamo desde el parámetro pk
        pk = kwargs.get('pk')
        if not pk:
            raise PermissionDenied("No se especificó el reclamo a eliminar.")

        reclamo = get_object_or_404(Reclamo, pk=pk, eliminado='Activo')

        # Verificar permisos
        if not user_can_delete_reclamo(request.user, reclamo):
            raise PermissionDenied(
                "No tienes permiso para eliminar este reclamo. "
                "Los usuarios GSA solo pueden eliminar reclamos creados por otros usuarios GSA."
            )

        return view_func(request, *args, **kwargs)
    return wrapper
