# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Descripción del Proyecto

Este es el **SGI (Sistema de Gestión Interno)** - un sistema de gestión interno para ADBSA (empresa de agua y saneamiento). La aplicación está construida con Django y gestiona órdenes de trabajo (reclamos), stock/materiales, seguimiento de vacaciones de empleados y herramientas administrativas para facturación y reportes de servicios públicos.

## Entorno de Desarrollo

### Requisitos
- **Python 3.10+** (proyecto desarrollado en Python 3.10.12)
- Dependencias principales:
  - Django 5.1.3 (actualizado desde 4.0, django-autocomplete-light fue removido por incompatibilidad)
  - pymysql (conexión a bases de datos MySQL/MariaDB externas)
  - django-crontab (tareas programadas)
  - django-cleanup (limpieza automática de archivos)
  - django-filters (filtrado en vistas)
  - pandas (procesamiento de datos en comandos personalizados)
  - reportlab (generación de PDFs)
  - psycopg2 (conector PostgreSQL para producción, requiere libpq-dev en sistemas Debian)
  - gunicorn (servidor WSGI para producción)

### Instalación de Dependencias

```bash
# Instalar dependencias del sistema (Debian/Ubuntu)
sudo apt install libpq-dev

# Instalar dependencias de Python
pip install -r requirements.txt
```

**Nota importante sobre numpy**: El proyecto requiere numpy==1.26.4 específicamente porque versiones posteriores no son compatibles con pandas 1.3.5.

### Ejecutar la Aplicación

**Modo desarrollo** (usa SQLite):
```bash
python manage.py runserver
```

La configuración está preparada para usar `sgi.settings_development` por defecto (vía `sgi/settings.py`).

**Modo producción** utiliza PostgreSQL y configuraciones diferentes en `sgi/settings_production.py`.

### Gestión de Base de Datos

```bash
# Crear/aplicar migraciones
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Acceder al shell de Django
python manage.py shell
```

### Comandos Personalizados de Gestión

- `python manage.py carga_reclamos_gsa` - Carga reclamos desde el sistema externo GSA
- `python manage.py actualizar_cache_unidades` - Actualiza el cache local de la tabla z80unidad desde SISA (se ejecuta automáticamente cada hora entre las 7:00 y 15:00 hs)

## Arquitectura y Estructura del Código

### Configuración de Settings

El proyecto usa un **patrón de configuración multi-ambiente**:
- `sgi/settings_base.py` - Configuración común para todos los ambientes
- `sgi/settings_development.py` - Ambiente de desarrollo (SQLite, DEBUG=True)
- `sgi/settings_production.py` - Ambiente de producción (PostgreSQL, DEBUG=False)
- `sgi/settings.py` - Archivo de settings activo (importa desde development por defecto)

**Importante**: Los settings importan credenciales desde `sgi/shpd_cnf.py` (no está en el repo) que contiene:
- `DJANGO_SECRET_KEY`
- Detalles de conexión a bases de datos (SISA, SHPD, OSEBAL)

### Estructura de la App: `reclamos`

A pesar de su nombre, la app `reclamos` maneja toda la lógica de negocio, no solo órdenes de trabajo. Está organizada en submódulos:

#### Modelos (`reclamos/models/`)
- `reclamos.py` - Órdenes de trabajo (Reclamo), archivos adjuntos, tipos de trabajo, estados
- `stock.py` - Materiales, proveedores, movimientos de inventario (MovimientoMateriales)
- `gral.py` - Modelos generales como Operarios, CacheUnidadSISA (cache local de z80unidad)
- `cobex.py` - Modelos de débito automático (Fava, DebDirect)
- `admintools.py` - Empleado, seguimiento de vacaciones (Novedades_vacaciones), reclamos por correo (Reclamos_correo)

Los modelos se exponen vía `reclamos/models/__init__.py` usando imports con asterisco.

#### Vistas (`reclamos/views/`)
Las vistas están organizadas por dominio de manera similar:
- `reclamos.py` - Gestión de órdenes de trabajo (listar, crear, editar, eliminar, asignaciones de cuadrillas)
- `stock/` subdirectorio - Materiales, proveedores, movimientos de inventario (egresos, ingresos)
- `admintools.py` - Herramientas administrativas (reportes, utilidades para impuestos/facturación)
- `cobex.py` - Gestión de débito automático
- `vacaciones.py` - Gestión de vacaciones de empleados
- `general.py` - Página de inicio y logout

Todas las vistas requieren el decorador `@login_required`.

#### Herramientas Administrativas (`reclamos/admintools/`)
Módulo separado con funciones de procesamiento para tareas fiscales y administrativas:
- `process_*.py` - Procesadores de datos fiscales (IIBB, ARBA, IVA digital, SICORE)
- `arch_*.py` - Generadores de archivos para sistemas externos (débito directo, FAVA, intermunicipal)
- `sicore.py` - Generación de archivos SICORE para retenciones/percepciones AFIP
- `libro_iva_digital.py` - Generación de libro IVA digital
- `vacaciones.py` - Lógica de cálculo de vacaciones de empleados
- Otros: Alta/baja de incobrables, descuentos percibidos, calculadoras fiscales

#### Formularios (`reclamos/forms/`)
- `forms.py` - Formularios principales para órdenes de trabajo
- `stock.py` - Formularios relacionados con stock
- `vacaciones.py` - Formularios relacionados con vacaciones

#### Enrutamiento de URLs
- `sgi/urls.py` - Configuración raíz de URLs (admin, auth, incluye URLs de reclamos)
- `reclamos/urls.py` - Patrones extensos de URLs organizados por funcionalidad:
  - Órdenes de trabajo (`/trabajos/`)
  - Vistas de cuadrillas (`/trabajos/cuadrillas/`)
  - Reportes (`/trabajos/reportes/`)
  - Gestión de stock (`/stock/`)
  - RRHH/vacaciones (`/rrhh/`)
  - Herramientas administrativas (`/herramientas/`)
  - Débito automático (`/fava/`, `/debdirect/`)

### Conceptos Clave del Dominio

**Órdenes de Trabajo (Reclamos)**:
- Modelo principal para rastrear solicitudes de servicio (agua, cloacas, pavimento, problemas de facturación, etc.)
- Estados: Pendiente, Finalizado, etc.
- Tipos: 20+ tipos incluyendo Agua, Cloacas, Verificación, Facturación, etc.
- Pueden asignarse a múltiples operarios
- Soporta archivos adjuntos
- Usa patrón de borrado lógico "eliminado" (no se borran físicamente)
- Sistema de borrador vía campo "borrador"

**Gestión de Stock**:
- Materiales rastreados con categorías (Agua, Cloacas, Herramienta, Indumentaria, etc.)
- Movimientos de inventario rastreados vía `MovimientoMateriales` (registros separados egreso/ingreso)
- Propiedad `semaforo` en materiales indica niveles de stock vs mínimos
- Los materiales pueden vincularse a múltiples proveedores

**Asignaciones de Cuadrillas**:
- Diferentes tipos de cuadrilla: agua, cloacas, niv_pozos, marco_tapa, mant_cloacal, verif_fact, serv_med
- Cada una tiene URLs de vista e impresión
- Órdenes de trabajo asignadas a cuadrillas vía modelo `DatosCuadrilla`

**Vacaciones de Empleados**:
- Modelo `Empleado` rastrea empleados con legajo, CUIL, fechas de ingreso/egreso
- `Novedades_vacaciones` rastrea períodos de vacaciones con cálculo de días
- Ambos usan patrón de borrado lógico

### Patrones Comunes

**Borrado Lógico**: Los modelos usan el campo `eliminado` con valores "Activo"/"Eliminado" en lugar de borrados físicos.

**Rastreo de Autor/Editor**: La mayoría de modelos rastrean:
- `author` - Usuario que creó el registro
- `editor` - Usuario que modificó el registro por última vez
- Timestamps `created_date` y `updated_date`

**Integración con Sistema Externo**: El comando `carga_reclamos_gsa` puede sincronizar periódicamente órdenes de trabajo desde un sistema GSA externo (configurable vía setting `CARGA_GSA`).

**Gestión de Sesiones**: Las sesiones expiran después de 8 horas (28800 segundos) y expiran cuando se cierra el navegador.

## Testing

El código no tiene una suite de tests activa (`reclamos/tests.py` es mínimo). Al agregar tests, usar el framework de tests de Django:

```bash
python manage.py test reclamos
```

## Archivos Estáticos y Media

- Archivos estáticos: `STATIC_ROOT = static/`, servidos en `/static/`
- Uploads de usuarios: `MEDIA_ROOT = uploads/`, servidos en `/uploads/`
- Generación de PDFs: `PDF_ROOT = cuadrillas/`, servidos en `/cuadrillas/`

Recolectar archivos estáticos para producción:
```bash
python manage.py collectstatic
```

## Localización

- Idioma: Español (Argentina) - `LANGUAGE_CODE = 'es-ar'`
- Zona horaria: `America/Buenos_Aires`
- Usa el framework de localización de Django (USE_I18N, USE_L10N habilitados)

## Notas sobre Base de Datos

- Desarrollo usa SQLite (`db.sqlite3`)
- Producción usa PostgreSQL (nombre de base de datos: `sgi_db`)
- La aplicación se conecta a bases de datos externas (SISA, SHPD, OSEBAL) para integración de datos - credenciales en `shpd_cnf.py`
- Default AutoField: Usa el AutoField estándar de Django (configurado explícitamente)

### Sistema de Cache para z80unidad (SISA)

Para optimizar el rendimiento y reducir la carga en la base de datos externa SISA, se implementó un **sistema de cache local** de la tabla `z80unidad`:

#### Modelo de Cache
- **Modelo:** `CacheUnidadSISA` (en `reclamos/models/gral.py`)
- **Tabla:** `cache_unidad_sisa`
- **Campos:** 97 campos que replican exactamente la estructura de z80unidad en SISA
- **Primary Key:** `unidad` (número de cuenta OSEBAL)
- **Índices:** unidad_alt, razon, zona, situacion, rel_cli_uni, nro_calle
- **Timestamp:** `ultima_actualizacion` (auto_now=True)

#### Actualización Automática
```bash
# Comando manual
python manage.py actualizar_cache_unidades

# Actualización automática (crontab)
# Configurado en settings_base.py para ejecutarse cada hora entre las 7:00 y 15:00 hs
# Patrón cron: '0 7-15 * * *'
```

El comando `actualizar_cache_unidades`:
- Conecta a la base de datos SISA (osebal_produccion)
- Lee completamente la tabla z80unidad
- Actualiza o crea registros locales usando `update_or_create()`
- Procesa en lotes de 1000 registros para eficiencia
- Tarda aproximadamente 5-10 minutos en completarse

#### Vistas Optimizadas

Las siguientes vistas usan el cache local en lugar de consultas directas a SISA:

1. **`buscador_partidas()`** (`reclamos/views/reclamos.py:378`)
   - Antes: Query SQL completo a SISA (~2-3 segundos)
   - Ahora: Django ORM sobre cache local (<100ms)
   - Mejora: **20-30x más rápido**

2. **`detalle_partida()`** (`reclamos/views/reclamos.py:417`)
   - Datos principales desde cache local
   - Solo conecta a SISA para tabla `z80unidad_obs` (observaciones no cacheadas)
   - Respuesta casi instantánea

3. **`imprimir_comprobante_reclamo()`** (`reclamos/views/reclamos.py:1180`)
   - Usa cache para obtener número de cuenta OSEBAL

**Nota:** Otros archivos en `reclamos/admintools/` aún usan consultas directas a SISA. Pueden ser optimizados en el futuro si es necesario.

#### Dependencias
- **pymysql:** Para conexión a base de datos MySQL/MariaDB de SISA
- **django-crontab:** Para programación de tareas automáticas (instalado en requirements)

## Trabajo en Progreso

### Diciembre 2025 - Refactorización Sistema de Permisos GSA (EN PROGRESO)

**Plan completo**: `/home/cthlh/.claude/plans/cached-tinkering-harp.md`

**Objetivo**: Migrar el sistema GSA de verificación basada en nombres de usuario a un sistema basado en permisos Django y grupos.

**Cambios completados**:
- ✅ Campo `n_reclamo_gsa` eliminado del modelo Reclamo (línea 73)

**Pendiente (usuario ejecutará)**:
- ⏸️ Crear y aplicar migración: `python manage.py makemigrations reclamos -n remove_n_reclamo_gsa && python manage.py migrate`

**Próximos pasos**:
- Fase 2: Crear módulo `reclamos/permissions.py` con decoradores de permisos
- Fase 3: Agregar métodos `is_author_gsa()` y `user_can_edit()` al modelo Reclamo
- Fase 4: Actualizar 11+ vistas en `reclamos/views/reclamos.py`:
  - Eliminar filtros basados en `'gsa-' in user`
  - Agregar decoradores de permisos server-side
  - Pasar contexto `user_can_edit` a templates
- Fase 5: Actualizar templates:
  - Eliminar sección "Trabajos GSA" de nav_menu.html
  - Usar variable contexto en detalle_reclamo.html
- Fase 6: Eliminar comando `carga_reclamos_gsa.py`

**Nueva lógica de permisos**:
- CREATE: `editar_reclamo` OR `gsa`
- VIEW: `ver_reclamo` OR `gsa` (ven TODOS los reclamos)
- EDIT/DELETE: `editar_reclamo` (cualquier reclamo) OR `gsa` + author en grupo GSA

**Problema de seguridad corregido**: Se agregará validación server-side (actualmente solo hay checks en templates).

---

## Actividad de Desarrollo Reciente

### Diciembre 2025 - Optimización de Rendimiento y Mejoras UI
- **Sistema de cache z80unidad:** Implementado cache local de tabla z80unidad para reducir latencia
  - Modelo `CacheUnidadSISA` con 97 campos
  - Actualización automática cada hora (7:00-15:00 hs) vía django-crontab
  - Optimización de `buscador_partidas()` y `detalle_partida()` (20-30x más rápido)
- **Comprobantes de reclamo:** Función para generar PDF de comprobantes con logo y datos de deuda
- **Configuración de umbral de deuda:** Setting `UMBRAL_DEUDA_COMPROBANTE = 50000` para alertas en comprobantes
- **Mejoras en generación de cuadrillas:**
  - Mejora de visualización del generador de impresión de cuadrillas
  - Sistema de toggle "imprimir sí/no" refactorizado para editarse desde página de generación de PDFs
  - Eliminación de columnas innecesarias en impresión de cuadrillas
  - Mejora de apariencia del buscador de partidas
- **Optimización de formularios:** Formulario de nuevo reclamo optimizado con buscador integrado (eliminado formulario antiguo "nuevo con buscador")
- **Estados de cuenta:** Implementado comentario automático "Se entrega Estado de Cuenta" en partes de trabajo basado en consulta de deuda

### Commits Anteriores
- Nombres de empleados se muestran en rojo cuando están en baja (`fecha_egreso` está configurada)
- Filtrado de empleados activos/en baja implementado
- Bug de cálculo de vacaciones corregido para empleados en baja en años posteriores
- Filtrado de semáforo corregido para excluir movimientos eliminados
- Generación de archivos SICORE mantiene saltos de línea apropiados
