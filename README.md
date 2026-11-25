# DIPRE – Sistema de Control de Préstamos e Inventario

Sistema web para llevar el control de los préstamos de equipos electrónicos de un laboratorio o almacén escolar: quién tiene qué, hasta cuándo, y en qué estado regresa.

Es un proyecto para la materia de Gestión de proyectos de software. Esta es una versión borrador para ir viendo cómo queda.

## Integrantes del equipo

| Número de control | Nombre |
| --- | --- |
| 23211916 | Arce Benitez Miguel Angel |
| 23211071 | Sedano Herrera Alejandro |
| 23212722 | Velázquez Montiel José Alberto |

## Tecnologías utilizadas

| Tecnología | Para qué se usa |
| --- | --- |
| Django 5.2 | Framework web: rutas, vistas, plantillas, panel de administración y autenticación |
| MySQL | Base de datos principal |
| SQLite | Base de datos alternativa para probar sin instalar nada |
| mysqlclient | Conexión de Django con MySQL |
| Git y GitHub | Control de versiones del equipo |

## Lenguajes de programación

- **Python 3** (lógica del sistema, con Django)
- **JavaScript** (interacción en el navegador: menús, filtros, modales)
- **HTML** (plantillas de Django)
- **CSS** (estilos propios de cada rol y un tema compartido)
- **SQL** (esquema y consultas de MySQL, generados por las migraciones de Django)

## Qué hace

Hay tres tipos de usuario:

- **Solicitante** (alumno o docente): ve los equipos disponibles, pide uno prestado, revisa su historial y sabe si tiene adeudos.
- **Encargado**: aprueba o rechaza solicitudes, entrega y recibe equipos, registra incidencias (daño, pérdida o mantenimiento) y salda adeudos.
- **Administrador**: todo lo del encargado, más un panel con estadísticas, la bitácora y la gestión de usuarios, equipos y categorías.

Algunas reglas que ya funcionan:

- Cada solicitud es de **un solo equipo**.
- Hay equipos que se prestan **por días** y otros **por horas**; se define por categoría.
  - Por días: la devolución va de mañana a 7 días, y el equipo se entrega al cierre (20:00) del día elegido.
  - Por horas: solo se piden hoy, de 7:00 a 20:00, por 2 horas como máximo y en pasos de 15 minutos.
- Pasada la hora límite más **10 minutos de tolerancia**, el préstamo queda como vencido y el solicitante no puede pedir otro equipo hasta devolverlo.
- Un equipo no se presta dos veces: se valida su disponibilidad al aprobar.
- Si un equipo regresa dañado o perdido, se abre una incidencia y el equipo sale de circulación hasta resolverla. Resolver el equipo (repararlo o darlo de baja) no salda el adeudo del solicitante: solo lo salda la reposición o el pago.
- La bitácora guarda por separado los accesos (inicios y cierres de sesión, intentos fallidos) y las operaciones (solicitudes, préstamos, rechazos, devoluciones).

Los horarios, la duración y la tolerancia se cambian en `config/settings.py`.

## Instrucciones de instalación

### Requisitos

- Python 3.10 o superior (se probó con Python 3.14).
- Git.
- MySQL 8, solo si vas a usar MySQL. Con SQLite no necesitas instalar nada más.

### Pasos

```bash
# 1. Descargar el proyecto
git clone https://github.com/arce-miguel/DIPRE-GDP-2026.git
cd DIPRE-GDP-2026

# 2. Entorno virtual y dependencias
python -m venv venv
venv\Scripts\activate        # en Mac o Linux: source venv/bin/activate
pip install -r requirements.txt

# 3. Configuración
copy .env.example .env       # en Mac o Linux: cp .env.example .env
# abre .env y llena tus datos de MySQL (o usa SQLite, ver más abajo)

# 4. Base de datos
python manage.py migrate
python manage.py seed        # datos de ejemplo y cuentas de prueba (opcional, recomendado)
```

### Si solo quieres probarlo rápido (SQLite)

Sin MySQL. Pon esto en tu `.env` y sigue desde el paso 4:

```
DB_ENGINE=sqlite
```

Se crea el archivo `db.sqlite3` en la raíz del proyecto.

### MySQL

Crea la base antes de migrar, con un usuario que tenga permisos sobre ella:

```sql
CREATE DATABASE dipre_borrador CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON dipre_borrador.* TO 'admin_user'@'localhost';
```

Los nombres de la base y del usuario son los de `.env.example`; cámbialos si usas otros. Después llena `DB_PASSWORD` en el `.env` con la contraseña de ese usuario.

## Instrucciones para ejecutar el sistema

Con el entorno virtual activado:

```bash
python manage.py runserver
```

Abre http://localhost:8000. La pantalla de inicio tiene un acceso para cada rol:

| Rol | Dirección de acceso |
| --- | --- |
| Estudiante (solicitante) | http://localhost:8000/login/?tipo=estudiante |
| Encargado | http://localhost:8000/login/?tipo=encargado |
| Administrador | http://localhost:8000/login/?tipo=ADMIN |

Una cuenta solo entra por el acceso de su rol. Para iniciar sesión se escribe la matrícula o el número de empleado (también sirve el correo).

### Pruebas automáticas

```bash
python manage.py test
```

Con MySQL, el usuario de la base necesita permiso para crear la base de pruebas (`test_` + nombre de la base). Si no lo tiene, usa SQLite: pon `DB_ENGINE=sqlite` en el `.env` y vuelve a correr el comando.

## Credenciales de prueba

Con `python manage.py seed` se crean (o se actualizan) estas cuentas. **Todas usan la contraseña `dipre123`:**

| Rol | Usuario (matrícula o número de empleado) |
| --- | --- |
| Solicitante | `s01`, `s02`, `s03` |
| Solicitante (alumnos de prueba) | `23210001` a `23210009` |
| Encargado | `e01`, `e02` |
| Encargado (empleados de prueba) | `2101`, `2102`, `2103` |
| Administrador | `admin` |

Son solo para desarrollo local; el comando `seed` no funciona con `DEBUG=False`. En una base vacía, `s01` trae un préstamo vencido (sirve para ver cómo se bloquean las solicitudes) y `s02` una solicitud pendiente.

## Gestión de datos

Usuarios, equipos y categorías se administran desde el panel de Django en `/admin/` (solo para administradores). El panel del administrador del sistema (`/administrador/panel`) muestra estadísticas y la bitácora de accesos y operaciones.

## Estructura del proyecto

```
config/                    Configuración de Django (settings.py lee el .env)
project/
  models.py                Roles, usuarios, categorías, equipos, préstamos, incidencias y bitácora
  services.py              Reglas de negocio (cada una dentro de una transacción)
  views.py                 Acceso y panel del solicitante
  views_encargado.py       Panel del encargado
  views_admin.py           Panel del administrador, bitácora e historial
  forms.py                 Formulario de solicitud de equipo
  tests.py                 Pruebas automáticas
  management/commands/     Comando seed (datos de ejemplo)
  templates/ y static/     Plantillas HTML, estilos y scripts
```

## Pendiente

Cosas que se dejaron fuera a propósito de esta primera versión: varias sedes, avisos por correo, reservas con anticipación, cobro de multas, aplicación móvil y lectura de QR.
