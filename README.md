# DIPRE

Sistema web para llevar el control de los préstamos de equipos electrónicos de un laboratorio o almacén escolar: quién tiene qué, hasta cuándo, y en qué estado regresa.

Es un proyecto para la materia de Gestión de proyectos de software. Esta es una versión borrador para ir viendo cómo queda.

## Qué hace

Hay tres tipos de usuario:

- **Solicitante** (alumno o docente): ve los equipos disponibles, pide uno prestado, revisa su historial y sabe si tiene adeudos.
- **Encargado**: aprueba o rechaza solicitudes, entrega y recibe equipos, y registra incidencias (daño, pérdida o mantenimiento).
- **Administrador**: todo lo del encargado, más reportes, bitácora y la gestión de usuarios, equipos y categorías.

Algunas reglas que ya funcionan:

- Hay equipos que se prestan **por días** y otros **por horas** (el mismo día, de 7:00 a 20:00, máximo 2 horas). Se define por categoría.
- Pasada la hora límite más **10 minutos de tolerancia**, el préstamo queda como vencido y el solicitante no puede pedir otro equipo hasta devolverlo.
- Un equipo no se presta dos veces: se valida su disponibilidad al aprobar.
- Si un equipo regresa dañado o perdido, se abre una incidencia y el equipo sale de circulación hasta resolverla.
- La bitácora guarda por separado los accesos (inicios y cierres de sesión) y las operaciones (préstamos, rechazos, devoluciones).

Los horarios, la duración y la tolerancia se cambian en `config/settings.py`.

## Tecnologías

- Python 3 y Django 5.2
- MySQL (o SQLite para probar sin instalar nada)
- HTML, CSS y JavaScript

## Cómo correrlo

Necesitas Python 3 y, si vas a usar MySQL, tener el servidor corriendo.

```bash
# 1. Entorno virtual y dependencias
python -m venv venv
venv\Scripts\activate        # en Mac o Linux: source venv/bin/activate
pip install -r requirements.txt

# 2. Configuración
copy .env.example .env       # en Mac o Linux: cp .env.example .env
# abre .env y llena tus datos de MySQL

# 3. Base de datos
python manage.py migrate
python manage.py seed_demo   # datos de ejemplo (opcional)

# 4. Servidor
python manage.py runserver
```

Abre http://localhost:8000.

### Si solo quieres probarlo rápido

Sin MySQL, usando SQLite. Pon esto en tu `.env`:

```
DB_ENGINE=sqlite
```

y sigue desde el paso 3.

### MySQL

Crea la base antes de migrar, con un usuario que tenga permisos sobre ella:

```sql
CREATE DATABASE dipre_borrador CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON dipre_borrador.* TO 'admin_user'@'localhost';
```

Los nombres de la base y del usuario son los de `.env.example`; cámbialos si usas otros.

## Cuentas de ejemplo

Con `seed_demo` se crean estas cuentas. Para entrar por tipo de acceso:

| Tipo | Usuario | Correo |
| --- | --- | --- |
| Estudiante | `20210001` (Ana), `20210002` (Luis), `20210003` (Marta) | `ana@dipre.local`, `luis@dipre.local`, `marta@dipre.local` |
| Encargado | `E001` | `encargado@dipre.local` |
| Administrador | `A001` | `admin@dipre.local` |

La contraseña de las cuentas de ejemplo está en `project/management/commands/seed_demo.py`. Son solo para desarrollo local.

Luis ya trae un préstamo vencido, así que sirve para ver cómo se bloquean las solicitudes.

## Gestión de datos

Usuarios, equipos y categorías se administran desde el panel de Django en `/admin/` (solo para administradores). Se abre en otra pestaña y tiene un enlace para volver al sistema.

## Pendiente

Cosas que se dejaron fuera a propósito de esta primera versión: varias sedes, avisos por correo, reservas con anticipación, cobro de multas, aplicación móvil y lectura de QR.
