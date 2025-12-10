# Plan de Dockerización - SGI ADBSA

## Decisión de arquitectura: ¿Dónde deployar?

### RECOMENDACIÓN: Mantener SGI en Server Ubuntu separado (dockerizado)

**Contexto:**
- Tienes Proxmox con 2 VMs: Server Docker (con múltiples servicios, carga moderada) y Server Ubuntu (SGI actual)
- SGI es crítico en horario laboral (7-18hs)
- Eres experto en Docker (gestionar múltiples hosts no es problema)
- Ambos servidores tienen recursos similares

**Justificación:**
1. **Aislamiento de recursos:** SGI hace queries pesadas a SISA (actualización cache 5-10min cada hora 7-15hs). El server Docker ya tiene carga moderada → riesgo de contención en horario crítico.
2. **Sin desventaja de complejidad:** Eres experto, dos hosts Docker no son problema.
3. **Flexibilidad Proxmox:** Snapshot antes de dockerizar = rollback fácil. Recursos dedicados sin afectar otros servicios.
4. **Troubleshooting aislado:** Problemas con SISA, cron, o queries no afectan otros servicios.
5. **Migración futura fácil:** Si después quieres consolidar, Docker lo facilita.

**Estrategia de implementación:**
1. Clonar VM Ubuntu en Proxmox (backup)
2. Dockerizar en la misma VM
3. Testing paralelo (app actual + Docker en diferentes puertos)
4. Switch en horario no laboral (viernes noche)
5. Si todo va bien, eliminar app legacy después de 1-2 semanas

---

## Respuesta a tu pregunta: ¿Dónde va Gunicorn?

**GUNICORN VA DENTRO DEL CONTENEDOR DJANGO**, no en un contenedor separado.

### Arquitectura de 3 contenedores:

```
┌─────────────┐      ┌──────────────────────────┐      ┌─────────────┐
│   NGINX     │─────▶│   DJANGO + GUNICORN      │─────▶│  POSTGRES   │
│ (puerto 80) │      │   (puerto 8000)          │      │ (puerto 5432)│
└─────────────┘      └──────────────────────────┘      └─────────────┘
                               │
                               │ (conexión pymysql)
                               ▼
                     ┌──────────────────────┐
                     │  MYSQL EXTERNAS      │
                     │  (SISA/SHPD/OSEBAL)  │
                     │  NO dockerizadas     │
                     └──────────────────────┘
```

**Justificación:**
- Gunicorn es el servidor WSGI que ejecuta la aplicación Django (como `runserver` pero para producción)
- Nginx actúa como reverse proxy: recibe peticiones del navegador → las reenvía a Gunicorn → sirve archivos estáticos directamente
- PostgreSQL es la base de datos principal (la actual en localhost)
- Las bases MySQL externas (SISA, SHPD, OSEBAL) NO se dockerizan porque son sistemas legacy compartidos

---

## Archivos a crear

### 1. Estructura de directorios Docker

```
/mnt/q/DJANGO/sgi_adbsa/
├── docker/
│   ├── django/
│   │   ├── Dockerfile                 # Imagen Python + Django + Gunicorn
│   │   ├── entrypoint.sh              # Script de inicialización (migrate, collectstatic, cron)
│   │   └── gunicorn_config.py         # Configuración de Gunicorn
│   ├── nginx/
│   │   ├── Dockerfile                 # Imagen Nginx
│   │   └── nginx.conf                 # Config reverse proxy + static files
│   └── postgres/
│       └── init-db.sh                 # (opcional) Inicialización DB
├── docker-compose.yml                 # Orquestación de servicios
├── docker-compose.prod.yml            # Override para producción
├── .dockerignore                      # Excluir archivos innecesarios
├── .env.example                       # Template de variables de entorno
└── scripts/
    ├── export_credentials.py          # Migrar shpd_cnf.py → .env
    └── docker-helpers.sh              # Scripts de utilidad
```

### 2. Nuevos archivos de configuración

**`sgi/settings_docker.py`** - Settings que leen de variables de entorno:
- Reemplaza el sistema `shpd_cnf.py` + `sec.stall` + `dcyt.py` por variables de entorno
- Lee `DB_SISA_HOST`, `DB_SISA_USR`, etc. desde `os.getenv()`
- Mantiene compatibilidad con settings_base.py

**`sgi/urls.py`** - Agregar endpoint healthcheck:
- `path('healthz/', healthz)` → Para healthchecks de Docker

---

## Archivos a modificar

### Cambio crítico: Reemplazar imports de `shpd_cnf`

**28 archivos** que actualmente hacen `import sgi.shpd_cnf as cnf` deben cambiar a usar `settings`:

```python
# ANTES:
import sgi.shpd_cnf as cnf
password = cnf.DB_SISA_PASS

# DESPUÉS:
from django.conf import settings
password = settings.DB_SISA_PASS
```

**Archivos afectados:**
- `reclamos/views/reclamos.py`
- `reclamos/views/admintools.py`
- `reclamos/management/commands/actualizar_cache_unidades.py`
- Todos los archivos en `reclamos/admintools/*.py`
- etc. (lista completa en exploración previa)

**Estrategia:** Usar buscar/reemplazar global con cuidado en cada archivo.

---

## Configuración de servicios

### Service 1: PostgreSQL

**Dockerfile:** Usa imagen oficial `postgres:15-alpine`

**Configuración:**
- Base de datos: `sgi_db`
- Puerto interno: 5432 (NO expuesto al host por seguridad)
- Volumen persistente: `postgres_data` (named volume)
- Healthcheck: `pg_isready`

### Service 2: Django + Gunicorn

**Dockerfile:** Multi-stage build (builder + runtime)
- **Stage 1 (builder):** Compila dependencias con gcc, libpq-dev, etc.
- **Stage 2 (runtime):** Copia solo ejecutables, sin build tools (imagen más liviana)

**Características:**
- Usuario no-root: `django` (UID 1000) para seguridad
- Instala `cron` para django-crontab
- Expone puerto 8000
- Comando: `gunicorn sgi.wsgi:application -c gunicorn_config.py`

**Entrypoint (`entrypoint.sh`):**
1. Espera a que PostgreSQL esté listo (`nc -z`)
2. Ejecuta `migrate --noinput`
3. Ejecuta `collectstatic --noinput`
4. Configura cron: `python manage.py crontab add`
5. Inicia daemon cron en background
6. Ejecuta comando principal (Gunicorn)

**Gunicorn config:**
- Workers: auto-calculado (`cpu_count * 2 + 1`)
- Timeout: 120s (para queries lentas a SISA)
- Max requests: 1000 (reciclar workers para prevenir leaks)
- Logs a stdout/stderr

**Volúmenes:**
- `./uploads:/app/uploads` (bind mount - persistente)
- `./cuadrillas:/app/cuadrillas` (bind mount - persistente)
- `static_volume:/app/static` (named volume - regenerable)

### Service 3: Nginx

**Dockerfile:** Usa imagen oficial `nginx:1.25-alpine`

**Configuración (`nginx.conf`):**
- **Upstream:** `django:8000` (nombre del servicio en docker-compose)
- **Location `/`:** Proxy a Gunicorn
- **Location `/static/`:** Servir directamente desde volumen (cache 30 días)
- **Location `/uploads/`:** Servir directamente (cache 7 días)
- **Location `/cuadrillas/`:** Servir directamente (cache 1 día)
- **Rate limiting:** Login endpoint (5 req/min)
- **Gzip:** Compresión de respuestas
- **Security headers:** X-Frame-Options, X-Content-Type-Options, etc.

**Volúmenes (read-only):**
- `static_volume:/app/static:ro`
- `./uploads:/app/uploads:ro`
- `./cuadrillas:/app/cuadrillas:ro`

**Puertos:**
- `80:80` (HTTP - expuesto al host)
- Opcional: `443:443` (HTTPS)

---

## Variables de entorno (.env)

**Archivo `.env.example`** con todas las variables necesarias:

```bash
# Django
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=172.16.29.129,plataforma.as

# PostgreSQL (principal)
DB_NAME=sgi_db
DB_USER=sgi_user
DB_PASSWORD=...
DB_HOST=postgres
DB_PORT=5432

# MySQL externas (SISA/SHPD/OSEBAL)
DB_SISA_HOST=172.16.29.xxx
DB_SISA_USR=...
DB_SISA_PASS=...
DB_SHPD_HOST=...
DB_SHPD_USR=...
DB_SHPD_PASS=...
DB_OSEBAL_HOST=...

# Gunicorn
GUNICORN_WORKERS=4
GUNICORN_LOG_LEVEL=info

# Cron
ENABLE_CRON=true

# Inicialización
CREATE_SUPERUSER=false
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=...
```

**Migrar credenciales actuales:**

```bash
# Script que lee shpd_cnf.py y genera variables de entorno
python scripts/export_credentials.py >> .env
```

---

## Tareas cron en Docker

**Estrategia recomendada:** Cron dentro del contenedor Django

**Justificación:**
- Simplicidad (un solo contenedor)
- django-crontab ya está configurado
- Necesita acceso al ORM de Django

**Implementación:**
1. Dockerfile instala `cron` package
2. Entrypoint ejecuta `python manage.py crontab add`
3. Entrypoint inicia daemon: `sudo cron` (en background)
4. Gunicorn se ejecuta como proceso principal

**Tareas configuradas:**
- `actualizar_cache_unidades` - Cron: `'0 7-15 * * *'` (cada hora de 7-15hs)

---

## Volúmenes y persistencia

| Volumen | Tipo | Contenido | Crítico | Backup |
|---------|------|-----------|---------|--------|
| `postgres_data` | Named | Datos PostgreSQL | SÍ | `pg_dump` diario |
| `./uploads` | Bind mount | Archivos subidos | SÍ | `tar.gz` semanal |
| `./cuadrillas` | Bind mount | PDFs generados | SÍ | `tar.gz` semanal |
| `static_volume` | Named | collectstatic | NO | Regenerable |

**Comandos de backup:**

```bash
# PostgreSQL
docker exec sgi_postgres pg_dump -U sgi_user sgi_db > backup_$(date +%Y%m%d).sql

# Archivos
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/
tar -czf cuadrillas_backup_$(date +%Y%m%d).tar.gz cuadrillas/
```

---

## Networking

**Red interna:** `sgi_network` (bridge)

**Comunicación:**
- Cliente → `nginx:80` (expuesto)
- Nginx → `django:8000` (interno)
- Django → `postgres:5432` (interno)
- Django → MySQL externas (por IP pública)

**Puertos expuestos al host:**
- Solo `80` (HTTP) desde Nginx
- PostgreSQL NO expuesto por seguridad

---

## Consideraciones específicas para Proxmox

### Antes de empezar la dockerización:

1. **Crear snapshot de la VM Ubuntu actual:**
   ```bash
   # En Proxmox host
   qm snapshot <VMID> predocker-backup --description "Backup antes de dockerizar SGI"
   ```

2. **Verificar recursos asignados a la VM:**
   ```bash
   # Verificar CPU, RAM disponibles
   qm config <VMID>
   ```

   **Recomendación mínima para SGI dockerizado:**
   - CPU: 2-4 cores
   - RAM: 4-8 GB (PostgreSQL + Django + Nginx + Cron)
   - Disco: 50-100 GB (dependiendo del crecimiento de uploads/cuadrillas)

3. **Opcional: Clonar VM para testing sin riesgo:**
   ```bash
   # Crear VM de testing completa
   qm clone <VMID> <NUEVO_VMID> --name sgi-docker-test --full

   # Asignar IP diferente y probar ahí primero
   ```

### Networking en Proxmox:

Si mantienes SGI en VM separada:
- **IP actual:** 172.16.29.129 (mantener la misma para no cambiar DNS/accesos)
- **Firewall Proxmox:** Verificar que puertos 80/443 estén abiertos
- **Acceso a MySQL externas:** La VM debe poder conectar a SISA/SHPD/OSEBAL

### Backup strategy en Proxmox:

```bash
# Backup automático de la VM completa (incluye todo)
vzdump <VMID> --storage <STORAGE> --mode snapshot --compress zstd

# Adicional: Backup específico de volúmenes Docker (dentro de la VM)
# Ver sección "Volúmenes y persistencia" más abajo
```

---

## Comandos de inicialización

### Primera vez (en VM Ubuntu de Proxmox):

```bash
cd /mnt/q/DJANGO/sgi_adbsa

# 1. Preparar variables de entorno
cp .env.example .env
python scripts/export_credentials.py >> .env
nano .env  # Editar contraseñas

# 2. Build de imágenes
docker-compose build

# 3. Iniciar servicios
docker-compose up -d

# 4. Verificar
docker-compose ps
docker-compose logs -f django

# 5. Crear superusuario (si no se hizo automáticamente)
docker-compose exec django python manage.py createsuperuser

# 6. Acceder: http://172.16.29.129 o http://plataforma.as
```

### Producción:

```bash
# En servidor de producción
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Comandos útiles:

```bash
# Logs
docker-compose logs -f [servicio]

# Shell Django
docker-compose exec django python manage.py shell

# Ejecutar migrations
docker-compose exec django python manage.py migrate

# Actualizar cache manualmente
docker-compose exec django python manage.py actualizar_cache_unidades

# Reiniciar servicio
docker-compose restart django

# Rebuild completo
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Optimizaciones implementadas

1. **Multi-stage build:** Builder stage (con gcc, headers) + runtime stage (solo binarios) → Imagen final ~500MB vs ~1GB
2. **Cache de capas Docker:** requirements.txt en capa separada → rebuild rápido si solo cambia código
3. **Healthchecks:** Todos los servicios tienen healthcheck → `depends_on` garantiza orden correcto
4. **Usuario no-root:** Django corre como UID 1000 → Seguridad
5. **Nginx gzip:** Compresión de respuestas → Reduce bandwidth 70%
6. **Static files desde Nginx:** No pasan por Django → Más rápido
7. **Gunicorn worker recycling:** Max 1000 requests por worker → Previene memory leaks
8. **Connection timeouts:** 120s para queries lentas a SISA

---

## Migración desde deployment actual

### Plan de migración (4 fases):

**Fase 1: Preparación (2-3 horas)**
- Backup completo: BD actual, uploads/, cuadrillas/
- Crear archivos Docker en repositorio
- Modificar 28 archivos: `cnf.*` → `settings.*`
- Generar .env desde shpd_cnf.py

**Fase 2: Testing local (1-2 días)**
- Build y deploy en desarrollo
- Migrar SQLite → PostgreSQL con dumpdata/loaddata
- Probar funcionalidades críticas (login, reclamos, PDFs, cron)

**Fase 3: Staging (1 día)**
- Deploy en servidor staging
- Migrar datos de producción a staging
- Testing exhaustivo

**Fase 4: Producción (downtime 30min-1h)**
- Ventana de mantenimiento (horario nocturno)
- Backup final
- Deploy contenedores
- Migrar PostgreSQL local → Docker
- Verificar + monitorear 2-4h

---

## Archivos críticos para implementar

Prioridad para implementación:

1. **`docker-compose.yml`** - Orquestación de los 3 servicios
2. **`docker/django/Dockerfile`** - Imagen Django + Gunicorn + cron
3. **`docker/django/entrypoint.sh`** - Lógica de inicialización
4. **`sgi/settings_docker.py`** - Settings desde variables de entorno
5. **`docker/nginx/nginx.conf`** - Reverse proxy + static files
6. **`.env.example`** - Template de configuración
7. **`scripts/export_credentials.py`** - Migrar shpd_cnf.py → .env

---

## Troubleshooting común

| Problema | Causa | Solución |
|----------|-------|----------|
| "could not connect to server" | PostgreSQL no listo | Esperar healthcheck: `docker-compose logs postgres` |
| "No module named shpd_cnf" | .env incompleto | Ejecutar `export_credentials.py` |
| "Permission denied /app/uploads" | Permisos incorrectos | `sudo chown -R 1000:1000 uploads/` |
| "502 Bad Gateway" | Gunicorn no responde | `docker-compose logs django` |
| Cron no ejecuta | Daemon no inició | `docker-compose exec django ps aux \| grep cron` |
| MySQL externas fallan | Firewall/IP incorrecta | `docker-compose exec django nc -zv $DB_SISA_HOST 3306` |

---

## Resumen ejecutivo

**¿Cuántos contenedores?** → **3 contenedores**
- PostgreSQL (base de datos principal)
- Django + Gunicorn (aplicación + servidor WSGI)
- Nginx (reverse proxy + static files)

**¿Dónde va Gunicorn?** → **Dentro del contenedor Django**
- No es un servicio separado, es el proceso que ejecuta la app WSGI
- Nginx hace proxy a Gunicorn:8000

**Beneficios:**
- Portabilidad: deploy en cualquier servidor con Docker
- Aislamiento: cada servicio en su contenedor
- Escalabilidad: fácil escalar con `docker-compose scale`
- Reproducibilidad: mismo ambiente dev/staging/prod
- Seguridad: usuario no-root, DB no expuesta, rate limiting

**Esfuerzo de implementación:**
- Crear: 12 archivos nuevos
- Modificar: 28 archivos (cambiar cnf → settings)
- Tiempo estimado: 1-2 días desarrollo + 1-2 días testing
