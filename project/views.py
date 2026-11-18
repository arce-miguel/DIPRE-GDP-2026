from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import SolicitudPrestamoForm
from .models import Bitacora, Equipo, Prestamo
from .services import registrar

# Create your views here.
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


@login_required
def panel_solicitante(request):
    usuario = request.user
    if not usuario.es_solicitante:
        return redirect('index')

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
        'prestamos': prestamos,
        'resumen': resumen,
        'tiene_adeudos': bool(incidencias) or resumen['vencidos'] > 0,
        'incidencias_pendientes': incidencias,
    })


@login_required
def solicitar_equipo(request):
    usuario = request.user
    if not usuario.es_solicitante:
        return redirect('index')

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


@login_required
def detalle_prestamo(request, pk):
    usuario = request.user
    if not usuario.es_solicitante:
        return redirect('index')
    prestamo = get_object_or_404(
        usuario.prestamos_solicitados.prefetch_related('detalles__equipo__categoria'), pk=pk)
    return render(request, 'gestion/detalle_prestamo.html', {'prestamo': prestamo})


@login_required
def mis_adeudos(request):
    usuario = request.user
    if not usuario.es_solicitante:
        return redirect('index')
    return render(request, 'gestion/mis_adeudos.html', {
        'vencidos': usuario.prestamos_vencidos().prefetch_related('detalles__equipo'),
        'incidencias': usuario.incidencias_pendientes().select_related('equipo', 'prestamo'),
    })
