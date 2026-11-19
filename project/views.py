from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import SolicitudPrestamoForm
from .models import Bitacora, Categoria, Equipo, Prestamo
from .services import registrar

# Cuántos préstamos se muestran en el inicio (el resto está en "Mis préstamos")
RECIENTES = 5

# Filtros de "Mis préstamos": la clave es el estado que se muestra
FILTROS_PRESTAMO = [
    ('todos', 'Todos'),
    ('pendiente', 'Pendientes'),
    ('activo', 'Activos'),
    ('vencido', 'Vencidos'),
    ('devuelto', 'Devueltos'),
    ('rechazado', 'Rechazados'),
]


def solicitante_required(vista):
    """Solo estudiantes con sesión iniciada; a cualquier otro rol lo manda al inicio."""
    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.es_solicitante:
            return redirect('index')
        return vista(request, *args, **kwargs)
    return envoltura


def index(request):
    return render(request, 'gestion/index.html')

# Cada módulo de acceso: título, subtítulo, quién puede entrar y adónde va después
MODULOS_LOGIN = {
    'estudiante': {
        'titulo': 'ESTUDIANTE',
        'subtitulo': 'Ingrese con sus credenciales de estudiante',
        'campo': 'Número de control',
        'permitido': lambda u: u.es_solicitante,
        'destino': 'panel_solicitante',
    },
    'encargado': {
        'titulo': 'ENCARGADO',
        'subtitulo': 'Ingrese datos de encargado',
        'campo': 'Número de empleado',
        'permitido': lambda u: u.es_encargado,
        'destino': 'enc-dash',
    },
    'ADMIN': {
        'titulo': 'ADMINISTRADOR',
        'subtitulo': 'Ingrese datos de administrador',
        'campo': 'Número de empleado',
        'permitido': lambda u: u.es_administrador,
        'destino': 'admin:index',
    },
}


def login_todos(request):
    tipo = request.GET.get('tipo', 'estudiante')
    modulo = MODULOS_LOGIN.get(tipo, MODULOS_LOGIN['estudiante'])
    error = None

    if request.method == 'POST':
        usuario = authenticate(
            request, username=request.POST.get('username', ''), password=request.POST.get('password', ''))
        if usuario is None:
            error = 'Número de control o contraseña incorrectos.'
        elif not modulo['permitido'](usuario):
            error = 'Esta cuenta no tiene acceso a este módulo.'
        else:
            login(request, usuario)
            registrar(usuario, 'Inicio de sesión', 'usuario', usuario.pk, tipo=Bitacora.ACCESO)
            siguiente = request.GET.get('next', '')
            if siguiente and url_has_allowed_host_and_scheme(
                    siguiente, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(siguiente)
            return redirect(modulo['destino'])

    return render(request, 'gestion/login.html', {
        'titulo_login': modulo['titulo'],
        'subtitulo': modulo['subtitulo'],
        'campo_usuario': modulo['campo'],
        'tipo': tipo,
        'error': error,
    })


def cerrar_sesion(request):
    logout(request)
    return redirect('index')


@solicitante_required
def panel_solicitante(request):
    usuario = request.user
    prestamos = list(
        usuario.prestamos_solicitados
        .prefetch_related('detalles__equipo__categoria')
        .order_by('-fecha_solicitud')
    )
    resumen = {
        'activos': sum(1 for p in prestamos if p.estado == Prestamo.ACTIVO),
        'vencidos': sum(1 for p in prestamos if p.vencido),
        'pendientes': sum(1 for p in prestamos if p.estado == Prestamo.PENDIENTE),
    }
    incidencias = list(usuario.incidencias_pendientes().select_related('equipo__categoria'))
    return render(request, 'gestion/panel_solicitante.html', {
        'prestamos': prestamos[:RECIENTES],
        'hay_mas': len(prestamos) > RECIENTES,
        'resumen': resumen,
        'tiene_adeudos': bool(incidencias) or resumen['vencidos'] > 0,
        'incidencias_pendientes': incidencias,
    })


@solicitante_required
def solicitar_equipo(request):
    usuario = request.user
    tiene_adeudos = usuario.tiene_adeudos
    form = SolicitudPrestamoForm(request.POST or None, solicitante=usuario)
    if request.method == 'POST' and form.is_valid():
        form.guardar()
        messages.success(request, 'Tu solicitud fue enviada. Espera la aprobación del encargado.')
        return redirect('panel_solicitante')

    equipos = (Equipo.objects.filter(estado__in=[Equipo.DISPONIBLE, Equipo.PRESTADO])
               .select_related('categoria'))
    seleccionados = {int(pk) for pk in request.POST.getlist('equipos') if pk.isdigit()}
    return render(request, 'gestion/solicitar_equipo.html', {
        'form': form,
        'equipos': equipos,
        'categorias': sorted({e.categoria for e in equipos}, key=lambda c: c.nombre),
        'seleccionados': seleccionados,
        'tiene_adeudos': tiene_adeudos,
        'max_equipos': settings.SOLICITUD_MAX_EQUIPOS,
        'max_horas': settings.SOLICITUD_MAX_HORAS,
        'max_dias': settings.SOLICITUD_MAX_DIAS,
    })


@solicitante_required
def mis_prestamos(request):
    """Todos mis préstamos, con filtro por estado (el estado 'vencido' se calcula, no se guarda)."""
    filtro = request.GET.get('estado', 'todos')
    if filtro not in dict(FILTROS_PRESTAMO):
        filtro = 'todos'

    prestamos = list(
        request.user.prestamos_solicitados
        .prefetch_related('detalles__equipo__categoria').order_by('-fecha_solicitud'))
    conteos = {clave: 0 for clave, _ in FILTROS_PRESTAMO}
    for p in prestamos:
        conteos['todos'] += 1
        conteos[p.estado_visible] += 1

    visibles = prestamos if filtro == 'todos' else [p for p in prestamos if p.estado_visible == filtro]
    return render(request, 'gestion/mis_prestamos.html', {
        'prestamos': visibles,
        'filtro': filtro,
        'filtros': [(clave, texto, conteos[clave]) for clave, texto in FILTROS_PRESTAMO],
    })


@solicitante_required
def detalle_prestamo(request, pk):
    prestamo = get_object_or_404(
        request.user.prestamos_solicitados.prefetch_related('detalles__equipo__categoria'), pk=pk)
    return render(request, 'gestion/detalle_prestamo.html', {'prestamo': prestamo})


@solicitante_required
def mis_adeudos(request):
    usuario = request.user
    return render(request, 'gestion/mis_adeudos.html', {
        'vencidos': usuario.prestamos_vencidos().prefetch_related('detalles__equipo'),
        'incidencias': usuario.incidencias_pendientes().select_related('equipo', 'prestamo'),
    })


@solicitante_required
def catalogo(request):
    """Equipo que existe en el inventario y cuántos hay disponibles ahora, por categoría."""
    visibles = [Equipo.DISPONIBLE, Equipo.PRESTADO, Equipo.MANTENIMIENTO]
    categorias = []
    for categoria in Categoria.objects.all():
        equipos = list(categoria.equipos.filter(estado__in=visibles))
        if not equipos:
            continue
        categoria.lista = equipos
        categoria.disponibles = sum(1 for e in equipos if e.disponible)
        categorias.append(categoria)
    return render(request, 'gestion/catalogo.html', {
        'categorias': categorias,
        'tiene_adeudos': request.user.tiene_adeudos,
        'max_horas': settings.SOLICITUD_MAX_HORAS,
        'max_dias': settings.SOLICITUD_MAX_DIAS,
        'apertura': settings.HORARIO_SERVICIO[0],
        'cierre': settings.HORARIO_SERVICIO[1],
    })


@solicitante_required
def reglas(request):
    return render(request, 'gestion/reglas.html', {
        'max_equipos': settings.SOLICITUD_MAX_EQUIPOS,
        'max_horas': settings.SOLICITUD_MAX_HORAS,
        'max_dias': settings.SOLICITUD_MAX_DIAS,
        'apertura': settings.HORARIO_SERVICIO[0],
        'cierre': settings.HORARIO_SERVICIO[1],
        'tolerancia': settings.TOLERANCIA_MINUTOS,
    })


@solicitante_required
def mi_cuenta(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        update_session_auth_hash(request, usuario)  # la sesión actual sigue abierta
        registrar(usuario, 'Contraseña cambiada', 'usuario', usuario.pk, tipo=Bitacora.ACCESO)
        messages.success(request, 'Tu contraseña se actualizó.')
        return redirect('mi_cuenta')
    return render(request, 'gestion/mi_cuenta.html', {'form': form})
