# Estado: Refactorización Sistema de Permisos GSA

**Fecha inicio**: 10 Diciembre 2025
**Estado**: EN PROGRESO - Fase 1 completada parcialmente

---

## Resumen Ejecutivo

Se está migrando el sistema GSA de verificación basada en nombres de usuario (`'gsa-' in username`) a un sistema basado en permisos Django y el grupo "GSA".

## Documentación Completa

- **Plan detallado**: `/home/cthlh/.claude/plans/cached-tinkering-harp.md`
- **CLAUDE.md actualizado**: Sección "Trabajo en Progreso" agregada (líneas 253-286)
- **TODO list activo**: 13 tareas (1 completada, 12 pendientes)

---

## Cambios Realizados

### ✅ Completado

1. **Modelo Reclamo modificado** (`reclamos/models/reclamos.py`)
   - Línea 73: Campo `n_reclamo_gsa` **ELIMINADO**
   - Estado: Listo para migración

### 📝 Cambios detectados en git

```bash
$ git status
Changes not staged for commit:
  modified:   reclamos/models/reclamos.py
  modified:   reclamos/templates/reclamos/base/nav_menu.html  # (limpieza automática de comentarios)
```

---

## Acción Requerida (Usuario)

**ANTES DE CONTINUAR**, ejecutar:

```bash
# Crear migración
python manage.py makemigrations reclamos -n remove_n_reclamo_gsa

# Aplicar migración
python manage.py migrate
```

⚠️ **IMPORTANTE**: La migración eliminará la columna `n_reclamo_gsa` de la tabla `reclamos_reclamo` en la base de datos.

---

## Próximas Fases (Pendientes)

### Fase 2: Crear Módulo de Permisos
**Archivo nuevo**: `reclamos/permissions.py`

Funciones a crear:
- `user_can_edit_reclamo(user, reclamo)` → bool
- `user_can_delete_reclamo(user, reclamo)` → bool
- `@require_create_permission` → decorador
- `@require_reclamo_edit_permission` → decorador
- `@require_reclamo_delete_permission` → decorador
- `@require_view_permission` → decorador

### Fase 3: Actualizar Modelo Reclamo
**Archivo**: `reclamos/models/reclamos.py`

Agregar métodos (después de `eliminar()`, línea ~83):
```python
def is_author_gsa(self):
    """Verifica si el author está en grupo GSA."""
    return self.author.groups.filter(name='GSA').exists()

def user_can_edit(self, user):
    """Verifica si el user puede editar este reclamo."""
    from reclamos.permissions import user_can_edit_reclamo
    return user_can_edit_reclamo(user, self)
```

### Fase 4: Actualizar Vistas (11+ funciones)
**Archivo**: `reclamos/views/reclamos.py`

**4.1 Agregar imports** (línea ~3):
```python
from reclamos.permissions import (
    require_create_permission,
    require_reclamo_edit_permission,
    require_reclamo_delete_permission,
    require_view_permission,
    user_can_edit_reclamo,
)
```

**4.2 Vistas de Lista** - Remover filtros GSA (5 funciones):
- `lista_reclamos()` (línea 99)
- `lista_reclamos_pendientes()` (línea 167)
- `lista_reclamos_finalizados()` (línea 214)
- `lista_reclamos_seguimiento()` (línea 258)
- `lista_reclamos_ajax()` (línea 350)

Cambios:
1. Eliminar bloque completo: `if 'gsa-' in user:`
2. Agregar decorador: `@require_view_permission`
3. Todos ven TODOS los reclamos activos

**4.3 Vistas de Creación** (2 funciones):
- `nuevo_reclamo()` (línea 534) → `@require_create_permission`
- `nuevo_reclamo_r()` (línea 553) → `@require_create_permission`

**4.4 Vistas de Edición** (3 funciones):
- `editar_reclamo()` (línea 574) → `@require_reclamo_edit_permission`
- `grabar_reclamo()` (línea 592) → `@require_reclamo_edit_permission`
- `carga_archivos()` (línea 1216) → `@require_reclamo_edit_permission`

**4.5 Vistas de Eliminación** (2 funciones):
- `eliminar_reclamo()` (línea 599) → `@require_reclamo_delete_permission`
- `eliminar_archivo()` (línea 1240) → check manual con `user_can_edit_reclamo()`

**4.6 Vista de Detalle**:
- `detalle_reclamo()` (línea 607):
  - Agregar `@require_view_permission`
  - Pasar en contexto: `'user_can_edit': user_can_edit_reclamo(request.user, reclamo)`

### Fase 5: Actualizar Templates

**5.1 nav_menu.html**:
- **ELIMINAR** líneas 12-20 (sección "Trabajos GSA")
- **MODIFICAR** línea 1: `{% if perms.reclamos.ver_reclamo or perms.reclamos.gsa %}`
- **MODIFICAR** línea 6: `{% if perms.reclamos.editar_reclamo or perms.reclamos.gsa %}`

**5.2 detalle_reclamo.html**:
- **CAMBIAR** líneas 7 y 59:
  - De: `{% if perms.reclamos.editar_reclamo or perms.reclamos.gsa %}`
  - A: `{% if user_can_edit %}`

### Fase 6: Eliminar Comando GSA
**Archivo**: `reclamos/management/commands/carga_reclamos_gsa.py`

**ELIMINAR** el archivo completo (funcionalidad deshabilitada: `CARGA_GSA = 'NO'`)

---

## Nueva Lógica de Permisos

| Operación | Quién puede |
|-----------|-------------|
| **Crear** | Usuario con `editar_reclamo` OR `gsa` |
| **Ver** | Usuario con `ver_reclamo` OR `gsa` → Ve TODOS los reclamos |
| **Editar** | Usuario con `editar_reclamo` (cualquiera) OR usuario con `gsa` + reclamo creado por usuario del grupo GSA |
| **Eliminar** | Misma lógica que Editar |

---

## Archivos Afectados

### Modificados (3 confirmados)
1. ✅ `reclamos/models/reclamos.py` - Campo eliminado
2. 🔄 `reclamos/templates/reclamos/base/nav_menu.html` - Limpieza automática
3. ⏳ `reclamos/views/reclamos.py` - Pendiente (11+ funciones)

### Nuevos (1)
- ⏳ `reclamos/permissions.py` - Pendiente

### Eliminados (1)
- ⏳ `reclamos/management/commands/carga_reclamos_gsa.py` - Pendiente

### Migraciones (1)
- ⏳ `reclamos/migrations/XXXX_remove_n_reclamo_gsa.py` - Pendiente (usuario creará)

---

## Post-Implementación

Después de completar todas las fases:

1. **Crear grupo GSA**:
```python
python manage.py shell
from django.contrib.auth.models import Group
gsa_group, created = Group.objects.get_or_create(name='GSA')
```

2. **Asignar usuarios al grupo**:
```python
from django.contrib.auth.models import User
gsa_users = User.objects.filter(username__startswith='gsa-')
for user in gsa_users:
    user.groups.add(gsa_group)
```

3. **Verificar permisos**: Asegurar que usuarios GSA tienen el permiso `reclamos.gsa`

---

## Problema de Seguridad Corregido

**ANTES**: Solo validación en templates → usuarios pueden eludir permisos accediendo directamente a URLs
**DESPUÉS**: Validación server-side con decoradores → permisos aplicados en todas las vistas

---

## Para Continuar en Próxima Sesión

1. ✅ CLAUDE.md actualizado con sección "Trabajo en Progreso"
2. ✅ Plan detallado guardado en `/home/cthlh/.claude/plans/cached-tinkering-harp.md`
3. ✅ TODO list actualizado (13 tareas rastreadas)
4. ✅ Este documento de estado creado
5. ⏸️ **SIGUIENTE PASO**: Usuario ejecuta migración, luego continúa con Fase 2

---

**Última actualización**: 10 Diciembre 2025
**Progreso**: Fase 1/6 completada (parcial)
