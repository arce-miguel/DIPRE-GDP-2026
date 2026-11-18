"""Reglas de negocio del encargado: cada función es una transición de estado completa.

Las vistas solo validan la petición y llaman aquí; así las reglas viven en un solo lugar,
corren dentro de una transacción y dejan rastro en la bitácora.
"""
from django.db import transaction
from django.utils import timezone

from .models import (
    Bitacora, DetallePrestamo, Equipo, Incidencia, Prestamo, Rol, Usuario, limite_de_vencimiento,
)


class ErrorOperacion(Exception):
    """La operación no se puede realizar; el mensaje se muestra tal cual al encargado."""


def registrar(usuario, accion, entidad='', id_registro=None, detalle='', tipo=Bitacora.OPERACION):
    Bitacora.objects.create(
        tipo=tipo, usuario=usuario, accion=accion, entidad=entidad,
        id_registro=id_registro, detalle=detalle,
    )


# --- Solicitantes -----------------------------------------------------------

def buscar_solicitante(identificador):
    """Solicitante activo por matrícula o correo; None si no existe."""
    identificador = (identificador or '').strip()
    if not identificador:
        return None
    return (Usuario.objects.filter(rol__nombre=Rol.SOLICITANTE, is_active=True)
            .filter(matricula__iexact=identificador).first())


# --- Préstamos --------------------------------------------------------------

def crear_prestamo_directo(encargado, solicitante, equipo_id, fecha_limite, observaciones=''):
    """Préstamo en ventanilla: se aprueba y se entrega en el mismo momento."""
    if solicitante is None:
        raise ErrorOperacion('Matrícula no encontrada.')
    if solicitante.tiene_adeudos:
        raise ErrorOperacion(f'{solicitante.nombre} tiene adeudos pendientes y no puede recibir equipo.')
    ahora = timezone.now()
    if fecha_limite <= ahora:
        raise ErrorOperacion('La fecha límite de devolución debe ser posterior a este momento.')

    with transaction.atomic():
        equipo = Equipo.objects.select_for_update().filter(pk=equipo_id).first()
        if equipo is None or equipo.estado != Equipo.DISPONIBLE:
            raise ErrorOperacion('El equipo elegido ya no está disponible.')
        prestamo = Prestamo.objects.create(
            solicitante=solicitante, usuario_registro=encargado, fecha_entrega=ahora,
            fecha_limite=fecha_limite, estado=Prestamo.ACTIVO,
            motivo='Préstamo registrado en ventanilla', observaciones=observaciones.strip(),
        )
        DetallePrestamo.objects.create(prestamo=prestamo, equipo=equipo)
        equipo.estado = Equipo.PRESTADO
        equipo.save(update_fields=['estado'])
        registrar(encargado, 'Préstamo registrado', 'prestamo', prestamo.pk,
                  f'{equipo.nombre} · {equipo.codigo_inventario} → {solicitante.nombre}')
    return prestamo


def aprobar_prestamo(encargado, prestamo_id):
    """Pendiente → activo: entrega los equipos solicitados."""
    with transaction.atomic():
        prestamo = (Prestamo.objects.select_for_update()
                    .select_related('solicitante').filter(pk=prestamo_id).first())
        if prestamo is None:
            raise ErrorOperacion('La solicitud no existe.')
        if prestamo.estado != Prestamo.PENDIENTE:
            raise ErrorOperacion('Esta solicitud ya fue atendida.')
        if prestamo.solicitante.tiene_adeudos:
            raise ErrorOperacion(
                f'{prestamo.solicitante.nombre} tiene adeudos pendientes; rechaza la solicitud.')
        ahora = timezone.now()
        if prestamo.fecha_limite <= ahora:
            raise ErrorOperacion('La fecha límite de la solicitud ya pasó; recházala por fecha no válida.')

        equipos = list(Equipo.objects.select_for_update().filter(detalles__prestamo=prestamo))
        no_disponibles = [e.codigo_inventario for e in equipos if e.estado != Equipo.DISPONIBLE]
        if no_disponibles:
            raise ErrorOperacion(
                'No se puede entregar: no está disponible ' + ', '.join(no_disponibles)
                + '. Rechaza la solicitud o espera a que se libere.')

        for equipo in equipos:
            equipo.estado = Equipo.PRESTADO
            equipo.save(update_fields=['estado'])
        prestamo.estado = Prestamo.ACTIVO
        prestamo.usuario_registro = encargado
        prestamo.fecha_entrega = ahora
        prestamo.save(update_fields=['estado', 'usuario_registro', 'fecha_entrega'])
        registrar(encargado, 'Solicitud aprobada y entregada', 'prestamo', prestamo.pk,
                  f'{", ".join(e.codigo_inventario for e in equipos)} → {prestamo.solicitante.nombre}')
    return prestamo


def rechazar_prestamo(encargado, prestamo_id, clave_motivo):
    motivos = dict(Prestamo.MOTIVOS_RECHAZO)
    if clave_motivo not in motivos:
        raise ErrorOperacion('Elige el motivo del rechazo.')
    with transaction.atomic():
        prestamo = (Prestamo.objects.select_for_update()
                    .select_related('solicitante').filter(pk=prestamo_id).first())
        if prestamo is None:
            raise ErrorOperacion('La solicitud no existe.')
        if prestamo.estado != Prestamo.PENDIENTE:
            raise ErrorOperacion('Esta solicitud ya fue atendida.')
        prestamo.estado = Prestamo.RECHAZADO
        prestamo.usuario_registro = encargado
        prestamo.observaciones = motivos[clave_motivo]
        prestamo.save(update_fields=['estado', 'usuario_registro', 'observaciones'])
        registrar(encargado, 'Solicitud rechazada', 'prestamo', prestamo.pk,
                  f'{prestamo.solicitante.nombre}: {motivos[clave_motivo]}')
    return prestamo


# --- Devoluciones -----------------------------------------------------------

# Qué pasa con el equipo según cómo se devuelve
_ESTADO_EQUIPO_AL_DEVOLVER = {
    DetallePrestamo.BUEN_ESTADO: Equipo.DISPONIBLE,
    DetallePrestamo.DANADO: Equipo.MANTENIMIENTO,
    DetallePrestamo.PERDIDO: Equipo.EXTRAVIADO,
}
_INCIDENCIA_AL_DEVOLVER = {
    DetallePrestamo.DANADO: Incidencia.DANO,
    DetallePrestamo.PERDIDO: Incidencia.PERDIDA,
}


def devolver_equipo(encargado, detalle_id, estado_devolucion=DetallePrestamo.BUEN_ESTADO, descripcion=''):
    if estado_devolucion not in _ESTADO_EQUIPO_AL_DEVOLVER:
        raise ErrorOperacion('Estado de devolución no válido.')
    descripcion = (descripcion or '').strip()
    if estado_devolucion != DetallePrestamo.BUEN_ESTADO and not descripcion:
        raise ErrorOperacion('Describe el incidente del equipo.')

    with transaction.atomic():
        detalle = (DetallePrestamo.objects.select_for_update()
                   .select_related('prestamo__solicitante', 'equipo').filter(pk=detalle_id).first())
        if detalle is None:
            raise ErrorOperacion('El préstamo no existe.')
        prestamo = detalle.prestamo
        if prestamo.estado != Prestamo.ACTIVO or detalle.devuelto:
            raise ErrorOperacion('Este equipo ya fue devuelto o el préstamo no está activo.')

        detalle.fecha_devolucion = timezone.now()
        detalle.estado_devolucion = estado_devolucion
        detalle.usuario_devolucion = encargado
        detalle.save(update_fields=['fecha_devolucion', 'estado_devolucion', 'usuario_devolucion'])

        equipo = detalle.equipo
        equipo.estado = _ESTADO_EQUIPO_AL_DEVOLVER[estado_devolucion]
        equipo.save(update_fields=['estado'])

        if estado_devolucion in _INCIDENCIA_AL_DEVOLVER:
            Incidencia.objects.create(
                equipo=equipo, prestamo=prestamo, usuario_registro=encargado,
                tipo=_INCIDENCIA_AL_DEVOLVER[estado_devolucion], descripcion=descripcion)

        if not prestamo.detalles.filter(fecha_devolucion__isnull=True).exists():
            prestamo.estado = Prestamo.DEVUELTO
            prestamo.save(update_fields=['estado'])

        registrar(encargado, 'Devolución registrada', 'prestamo', prestamo.pk,
                  f'{equipo.nombre} · {equipo.codigo_inventario} ({detalle.get_estado_devolucion_display()})'
                  f' de {prestamo.solicitante.nombre}')
    return detalle


# --- Incidencias ------------------------------------------------------------

def ultimo_prestamo_de(equipo):
    """El último préstamo entregado que incluyó al equipo (quién lo tuvo por última vez)."""
    detalle = (DetallePrestamo.objects
               .filter(equipo=equipo, prestamo__estado__in=[Prestamo.ACTIVO, Prestamo.DEVUELTO])
               .select_related('prestamo__solicitante')
               .order_by('-prestamo__fecha_solicitud').first())
    return detalle.prestamo if detalle else None


def registrar_incidencia(encargado, equipo_id, tipo, descripcion):
    if tipo not in dict(Incidencia.TIPOS):
        raise ErrorOperacion('Tipo de incidente no válido.')
    descripcion = (descripcion or '').strip()
    if not descripcion:
        raise ErrorOperacion('Describe el incidente.')

    with transaction.atomic():
        equipo = Equipo.objects.select_for_update().filter(pk=equipo_id).first()
        if equipo is None:
            raise ErrorOperacion('El equipo no existe.')
        incidencia = Incidencia.objects.create(
            equipo=equipo, prestamo=ultimo_prestamo_de(equipo), usuario_registro=encargado,
            tipo=tipo, descripcion=descripcion)
        # Un equipo prestado o dado de baja no cambia de estado hasta que se atienda la incidencia
        if equipo.estado not in (Equipo.PRESTADO, Equipo.BAJA):
            equipo.estado = Equipo.EXTRAVIADO if tipo == Incidencia.PERDIDA else Equipo.MANTENIMIENTO
            equipo.save(update_fields=['estado'])
        registrar(encargado, 'Incidente registrado', 'incidencia', incidencia.pk,
                  f'{incidencia.get_tipo_display()}: {equipo.nombre} · {equipo.codigo_inventario}')
    return incidencia


def resolver_incidencia(encargado, incidencia_id, resolucion='', forma_saldo=''):
    """Atiende al equipo (resolución) y/o salda el adeudo del solicitante (reposición o pago)."""
    if not resolucion and not forma_saldo:
        raise ErrorOperacion('Elige cómo se resolvió o cómo se saldó el adeudo.')

    with transaction.atomic():
        incidencia = (Incidencia.objects.select_for_update()
                      .select_related('equipo').filter(pk=incidencia_id).first())
        if incidencia is None:
            raise ErrorOperacion('El incidente no existe.')
        ahora = timezone.now()

        if resolucion:
            if incidencia.resuelta:
                raise ErrorOperacion('El equipo de este incidente ya fue atendido.')
            if resolucion not in Incidencia.RESOLUCIONES_POR_TIPO[incidencia.tipo]:
                raise ErrorOperacion('Esa resolución no corresponde al tipo de incidente.')
            equipo = incidencia.equipo
            if resolucion in Incidencia.RAZON_DE_BAJA:
                equipo.dar_de_baja(Incidencia.RAZON_DE_BAJA[resolucion])
                equipo.save()
            elif equipo.estado in (Equipo.MANTENIMIENTO, Equipo.EXTRAVIADO):
                equipo.poner_en_servicio()
                equipo.save()
            incidencia.resuelta = True
            incidencia.resolucion = resolucion
            incidencia.fecha_resolucion = ahora
            incidencia.usuario_resolucion = encargado

        if forma_saldo:
            if forma_saldo not in dict(Incidencia.FORMAS_SALDO):
                raise ErrorOperacion('Forma de saldo no válida.')
            if not incidencia.genera_adeudo:
                raise ErrorOperacion('Este incidente no genera adeudo.')
            if incidencia.adeudo_saldado:
                raise ErrorOperacion('El adeudo ya estaba saldado.')
            incidencia.adeudo_saldado = True
            incidencia.forma_saldo = forma_saldo
            incidencia.fecha_saldo = ahora
            incidencia.usuario_saldo = encargado

        incidencia.save()
        registrar(encargado, 'Incidente actualizado', 'incidencia', incidencia.pk,
                  f'{incidencia.get_tipo_display()}: {incidencia.equipo.nombre} · '
                  f'{incidencia.equipo.codigo_inventario}')
    return incidencia


# --- Consultas de apoyo -----------------------------------------------------

def prestamos_vencidos():
    return Prestamo.objects.filter(estado=Prestamo.ACTIVO, fecha_limite__lt=limite_de_vencimiento())
