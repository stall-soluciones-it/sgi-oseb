# Plan: Refactorización del Sistema de Permisos GSA

## Objetivo

Migrar el sistema GSA de verificación basada en nombres de usuario (`'gsa-' in username`) a un sistema basado en permisos Django y grupos, eliminando lógica redundante y mejorando la seguridad.

## Requisitos del Usuario

1. **Eliminar lógica de nombres de usuario**: Remover todos los checks de `'gsa-' in user` o `author__username__startswith='gsa-'`
2. **Usar solo permisos Django**: Basarse en el permiso custom `reclamos.gsa` y el grupo Django "GSA"
3. **Capacidades del permiso GSA**:
   - CREATE: Puede crear nuevos reclamos
   - VIEW: Puede ver TODOS los reclamos (sin filtrado)
   - EDIT: Solo puede editar reclamos donde el autor pertenece al grupo GSA
   - DELETE: Solo puede eliminar reclamos donde el autor pertenece al grupo GSA
4. **Permisos independientes**: `ver_reclamo` y `editar_reclamo` mantienen su lógica actual
5. **Eliminar campo `n_reclamo_gsa`**: Ya no es necesario, GSA usará `n_de_reclamo` como todos
6. **Eliminar menú separado**: Quitar sección "Trabajos GSA", usar el menú general "Trabajos"

## Problema de Seguridad Crítico Identificado

**ESTADO ACTUAL**: Todas las validaciones de permisos están SOLO en templates. Las vistas solo tienen `@login_required`.

**RIESGO**: Los usuarios pueden eludir los permisos accediendo directamente a las URLs.

**SOLUCIÓN**: Agregar validación server-side en todas las vistas.

## Lógica de Permisos Implementada

| Operación | Permiso requerido |
|-----------|-------------------|
| **Crear** | `editar_reclamo` OR `gsa` |
| **Ver** | `ver_reclamo` OR `gsa` |
| **Editar** | `editar_reclamo` (cualquier reclamo) OR `gsa` + author en grupo GSA |
| **Eliminar** | Misma lógica que Editar |

## Orden de Implementación

### Fase 1: Migración de Base de Datos
1. Eliminar campo `n_reclamo_gsa` del modelo Reclamo
2. Crear migración: `python manage.py makemigrations reclamos -n remove_n_reclamo_gsa`
3. Aplicar migración: `python manage.py migrate`

### Fase 2: Crear Módulo de Permisos Helper
**Archivo nuevo**: `/mnt/q/DJANGO/sgi_adbsa/reclamos/permissions.py`

Crear funciones helper centralizadas:
- `user_can_edit_reclamo(user, reclamo)` - Verifica si user puede editar
- `user_can_delete_reclamo(user, reclamo)` - Verifica si user puede eliminar
- `@require_create_permission` - Decorador para vistas de creación
- `@require_reclamo_edit_permission` - Decorador para vistas de edición
- `@require_reclamo_delete_permission` - Decorador para vistas de eliminación
- `@require_view_permission` - Decorador para vistas de visualización

**Lógica de `user_can_edit_reclamo`**:
```python
if user.has_perm('reclamos.editar_reclamo'):
    return True
if user.has_perm('reclamos.gsa'):
    return reclamo.author.groups.filter(name='GSA').exists()
return False
```

### Fase 3: Actualizar Modelo Reclamo
**Archivo**: `/mnt/q/DJANGO/sgi_adbsa/reclamos/models/reclamos.py`

1. **Eliminar** línea 73: `n_reclamo_gsa = models.CharField(max_length=100)`
2. **Agregar** métodos helper (después del método `eliminar()`):
   - `is_author_gsa()` - Verifica si author está en grupo GSA
   - `user_can_edit(user)` - Verifica si user puede editar este reclamo

### Fase 4: Actualizar Vistas
**Archivo**: `/mnt/q/DJANGO/sgi_adbsa/reclamos/views/reclamos.py`

#### 4.1 Agregar imports
```python
from reclamos.permissions import (
    require_create_permission,
    require_reclamo_edit_permission,
    require_reclamo_delete_permission,
    require_view_permission,
    user_can_edit_reclamo,
)
```

#### 4.2 Vistas de Lista - Remover filtrado por username (5 funciones)
**Funciones a modificar**:
- `lista_reclamos()` (líneas 99-134)
- `lista_reclamos_pendientes()` (líneas 167-211)
- `lista_reclamos_finalizados()` (líneas 214-237)
- `lista_reclamos_seguimiento()` (líneas 258-299)
- `lista_reclamos_ajax()` (líneas 350-446)

**Cambios**:
1. **Eliminar** todo el bloque `if 'gsa-' in user:`
2. **Agregar** decorador `@require_view_permission` (que acepta `ver_reclamo` OR `gsa`)
3. Todos los usuarios ven TODOS los reclamos activos (sin filtro por author)

#### 4.3 Vistas de Creación - Agregar decorador (2 funciones)
- `nuevo_reclamo()` (línea 534) → Agregar `@require_create_permission`
- `nuevo_reclamo_r()` (línea 553) → Agregar `@require_create_permission`

#### 4.4 Vistas de Edición - Agregar decorador (3 funciones)
- `editar_reclamo()` (línea 574) → Agregar `@require_reclamo_edit_permission`
- `grabar_reclamo()` (línea 592) → Agregar `@require_reclamo_edit_permission`
- `carga_archivos()` (línea 1216) → Agregar `@require_reclamo_edit_permission`

#### 4.5 Vistas de Eliminación - Agregar decorador (2 funciones)
- `eliminar_reclamo()` (línea 599) → Agregar `@require_reclamo_delete_permission`
- `eliminar_archivo()` (línea 1240) → Agregar check manual `user_can_edit_reclamo()`

#### 4.6 Vista de Detalle - Pasar contexto
`detalle_reclamo()` (línea 607):
- Agregar decorador `@require_view_permission`
- Pasar `user_can_edit` en el contexto para el template

### Fase 5: Actualizar Templates

#### 5.1 Eliminar Menú GSA
**Archivo**: `/mnt/q/DJANGO/sgi_adbsa/reclamos/templates/reclamos/base/nav_menu.html`

**Eliminar** líneas 12-20 (sección "Trabajos GSA"):
```html
{% if perms.reclamos.gsa %}
    <div class="dropdown">
        <button class="dropbtn">Trabajos GSA ...
    </div>
{% endif %}
```

**Modificar** líneas 1 y 6 (menú principal "Trabajos"):
- Línea 1: `{% if perms.reclamos.ver_reclamo %}` → `{% if perms.reclamos.ver_reclamo or perms.reclamos.gsa %}`
- Línea 6: `{% if perms.reclamos.editar_reclamo %}` → `{% if perms.reclamos.editar_reclamo or perms.reclamos.gsa %}`

#### 5.2 Actualizar Template de Detalle
**Archivo**: `/mnt/q/DJANGO/sgi_adbsa/reclamos/templates/reclamos/detalle_reclamo.html`

**Cambiar** líneas 7 y 59:
- Antes: `{% if perms.reclamos.editar_reclamo or perms.reclamos.gsa %}`
- Después: `{% if user_can_edit %}`

Esto usa la variable de contexto pasada desde la vista, que ya contiene la lógica correcta.

#### 5.3 Otros Templates
Los siguientes templates mantienen sus checks actuales (validación está en decoradores):
- `nuevo_reclamo.html` - OK como está
- `nuevo_reclamo_r.html` - OK como está
- `editar_reclamo.html` - OK como está
- `carga_archivos.html` - OK como está

### Fase 6: Manejar Comando GSA
**Archivo**: `/mnt/q/DJANGO/sgi_adbsa/reclamos/management/commands/carga_reclamos_gsa.py`

**Opción A (Recomendada)**: Eliminar el comando completo
- El setting `CARGA_GSA = 'NO'` en todos los ambientes
- La funcionalidad parece estar deshabilitada

**Opción B**: Actualizar el comando
- Eliminar uso de `n_reclamo_gsa` (líneas 46-48, 111, 133)
- Usar `comentario` u otro campo para rastrear ID externo si es necesario

## Archivos Modificados

### Nuevos (1)
- `reclamos/permissions.py` - Módulo helper de permisos

### Modificados (5)
1. `reclamos/models/reclamos.py` - Eliminar campo, agregar métodos
2. `reclamos/views/reclamos.py` - 11+ funciones (quitar filtros, agregar decoradores)
3. `reclamos/templates/reclamos/base/nav_menu.html` - Eliminar menú GSA, ajustar permisos
4. `reclamos/templates/reclamos/detalle_reclamo.html` - Usar variable contexto
5. `reclamos/management/commands/carga_reclamos_gsa.py` - Actualizar o eliminar

### Migraciones (1)
- `reclamos/migrations/XXXX_remove_n_reclamo_gsa.py` - Auto-generada

## Pasos Post-Implementación

### 1. Verificar/Crear Grupo GSA
```python
python manage.py shell
from django.contrib.auth.models import Group
gsa_group, created = Group.objects.get_or_create(name='GSA')
```

### 2. Asignar Usuarios al Grupo
```python
from django.contrib.auth.models import User
# Usuarios con nombres que empiezan con 'gsa-'
gsa_users = User.objects.filter(username__startswith='gsa-')
for user in gsa_users:
    user.groups.add(gsa_group)
```

### 3. Verificar Permisos
Asegurar que usuarios GSA tienen el permiso `reclamos.gsa` asignado.

## Testing Manual

### Usuario GSA (username cualquiera, en grupo GSA, permiso reclamos.gsa)
- ✓ Ve menú "Trabajos" (NO menú separado "Trabajos GSA")
- ✓ Puede crear reclamos
- ✓ Ve TODOS los reclamos en los listados
- ✓ Puede editar reclamos creados por usuarios del grupo GSA
- ✗ NO puede editar reclamos creados por usuarios fuera del grupo GSA (403)
- ✓ Puede eliminar reclamos creados por usuarios del grupo GSA
- ✗ NO puede eliminar reclamos creados por usuarios fuera del grupo GSA (403)

### Usuario Administrador (permisos ver_reclamo + editar_reclamo)
- ✓ Puede crear, ver, editar y eliminar CUALQUIER reclamo
- ✓ Sin restricciones de grupo

### Usuario Regular (sin permisos especiales)
- ✗ NO ve menú "Trabajos"
- ✗ NO puede acceder a URLs de reclamos (403)

### Tests de Seguridad
- Intentar acceso directo a `/trabajos/editar/<pk>/` donde author no está en GSA
- Verificar respuesta 403 PermissionDenied
- Verificar que mensaje de error no filtra información sensible

## Notas Adicionales

### Performance
- La verificación `reclamo.author.groups.filter(name='GSA').exists()` agrega 1 query por check
- Puede optimizarse con `select_related`/`prefetch_related` si es necesario
- El impacto es mínimo (solo en edición/eliminación, no en listados)

### Compatibilidad
- Los usuarios con nombres `'gsa-*'` seguirán funcionando (el nombre no importa)
- Solo necesitan estar en el grupo GSA
- Nuevos usuarios GSA pueden tener cualquier nombre de usuario

### Convención de Nombres
- Ya NO es necesario que usuarios GSA tengan nombres que empiecen con `'gsa-'`
- La membresía al grupo GSA es el único requisito
