from datetime import datetime, timedelta
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import services
from .forms import SolicitudPrestamoForm
from .models import (
    Bitacora, Categoria, DetallePrestamo, Equipo, Incidencia, Prestamo, Rol, Usuario,
)


def crear_equipo(codigo, categoria=None):
    categoria = categoria or Categoria.objects.get_or_create(nombre='Laptop')[0]
    return Equipo.objects.create(codigo_inventario=codigo, categoria=categoria, marca='Dell', modelo='Latitude')


class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alumno = Usuario.objects.create_user('ana@x.mx', 'Ana Pérez', password='clave123', matricula='A01234')
        cls.otro = Usuario.objects.create_user('luis@x.mx', 'Luis Ramírez', password='clave123', matricula='A01877')
        cls.encargado = Usuario.objects.create_user(
            'enc@x.mx', 'Enc Uno', password='clave123', rol=Rol.ENCARGADO, num_empleado='E001')
        cls.admin = Usuario.objects.create_user(
            'adm@x.mx', 'Admin Uno', password='clave123', rol=Rol.ADMINISTRADOR, num_empleado='AD01')

    def entrar(self, usuario):
        self.client.force_login(usuario)


class LoginTests(BaseTest):
    def test_alumno_entra_con_matricula(self):
        r = self.client.post(reverse('login') + '?tipo=estudiante', {'username': 'A01234', 'password': 'clave123'})
        self.assertRedirects(r, reverse('panel_solicitante'))
        self.assertTrue(Bitacora.objects.filter(tipo=Bitacora.ACCESO, usuario=self.alumno).exists())

    def test_encargado_entra_con_numero_de_empleado(self):
        r = self.client.post(reverse('login') + '?tipo=encargado', {'username': 'E001', 'password': 'clave123'})
        self.assertRedirects(r, reverse('enc-dash'))

    def test_contrasena_incorrecta(self):
        r = self.client.post(reverse('login'), {'username': 'A01234', 'password': 'mala'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'incorrectos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_alumno_no_entra_por_el_modulo_del_encargado(self):
        r = self.client.post(reverse('login') + '?tipo=encargado', {'username': 'A01234', 'password': 'clave123'})
        self.assertContains(r, 'no tiene acceso')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_no_redirige_a_sitios_externos(self):
        r = self.client.post(reverse('login') + '?next=https://malo.example/',
                             {'username': 'A01234', 'password': 'clave123'})
        self.assertRedirects(r, reverse('panel_solicitante'))

    def test_logout(self):
        self.entrar(self.alumno)
        self.client.get(reverse('logout'))
        self.assertEqual(self.client.get(reverse('panel_solicitante')).status_code, 302)


class AccesoEncargadoTests(BaseTest):
    def test_anonimo_va_al_login_del_encargado(self):
        r = self.client.get(reverse('enc-dash'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('tipo=encargado', r['Location'])

    def test_alumno_no_ve_el_panel_del_encargado(self):
        self.entrar(self.alumno)
        self.assertRedirects(self.client.get(reverse('enc-pres')), reverse('index'))

    def test_las_cuatro_paginas_cargan(self):
        crear_equipo('LAP-1')
        self.entrar(self.encargado)
        for nombre in ('enc-dash', 'enc-pres', 'enc-dev', 'enc-inci'):
            with self.subTest(nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)

    def test_el_administrador_hereda_el_acceso(self):
        self.entrar(self.admin)
        self.assertEqual(self.client.get(reverse('enc-dash')).status_code, 200)

    def test_acciones_exigen_post(self):
        self.entrar(self.encargado)
        self.assertEqual(self.client.get(reverse('enc-devolver')).status_code, 405)


class PrestamosTests(BaseTest):
    def setUp(self):
        self.equipo = crear_equipo('LAP-1')
        self.entrar(self.encargado)

    def solicitud(self, solicitante=None, dias=2):
        p = Prestamo.objects.create(
            solicitante=solicitante or self.alumno, fecha_limite=timezone.now() + timedelta(days=dias))
        DetallePrestamo.objects.create(prestamo=p, equipo=self.equipo)
        return p

    def test_aprobar_entrega_el_equipo(self):
        p = self.solicitud()
        self.client.post(reverse('enc-prestamo-aprobar', args=[p.pk]))
        p.refresh_from_db()
        self.equipo.refresh_from_db()
        self.assertEqual(p.estado, Prestamo.ACTIVO)
        self.assertEqual(p.usuario_registro, self.encargado)
        self.assertEqual(self.equipo.estado, Equipo.PRESTADO)
        self.assertTrue(Bitacora.objects.filter(accion='Solicitud aprobada y entregada').exists())

    def test_no_aprueba_si_el_equipo_ya_esta_prestado(self):
        p = self.solicitud()
        self.equipo.estado = Equipo.PRESTADO
        self.equipo.save()
        self.client.post(reverse('enc-prestamo-aprobar', args=[p.pk]))
        p.refresh_from_db()
        self.assertEqual(p.estado, Prestamo.PENDIENTE)

    def test_no_aprueba_a_quien_tiene_adeudos(self):
        otro = crear_equipo('LAP-2')
        vencido = Prestamo.objects.create(
            solicitante=self.alumno, estado=Prestamo.ACTIVO, fecha_limite=timezone.now() - timedelta(days=3))
        DetallePrestamo.objects.create(prestamo=vencido, equipo=otro)
        p = self.solicitud()
        self.client.post(reverse('enc-prestamo-aprobar', args=[p.pk]))
        p.refresh_from_db()
        self.assertEqual(p.estado, Prestamo.PENDIENTE)

    def test_rechazar_guarda_el_motivo(self):
        p = self.solicitud()
        self.client.post(reverse('enc-prestamo-rechazar', args=[p.pk]), {'motivo': 'fuera_horario'})
        p.refresh_from_db()
        self.assertEqual(p.estado, Prestamo.RECHAZADO)
        self.assertIn('horario', p.observaciones)

    def test_no_se_atiende_dos_veces(self):
        p = self.solicitud()
        self.client.post(reverse('enc-prestamo-rechazar', args=[p.pk]), {'motivo': 'otro'})
        self.client.post(reverse('enc-prestamo-aprobar', args=[p.pk]))
        p.refresh_from_db()
        self.assertEqual(p.estado, Prestamo.RECHAZADO)

    def datos_nuevo(self, **extra):
        limite = (timezone.localtime() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        return {'matricula': 'A01234', 'equipo': self.equipo.pk, 'fecha_limite': limite,
                'observaciones': 'Con cargador', **extra}

    def test_prestamo_directo(self):
        self.client.post(reverse('enc-prestamo-nuevo'), self.datos_nuevo())
        p = Prestamo.objects.get()
        self.equipo.refresh_from_db()
        self.assertEqual((p.estado, p.solicitante, p.usuario_registro), (Prestamo.ACTIVO, self.alumno, self.encargado))
        self.assertEqual(p.observaciones, 'Con cargador')
        self.assertEqual(self.equipo.estado, Equipo.PRESTADO)

    def test_prestamo_directo_con_matricula_inexistente(self):
        self.client.post(reverse('enc-prestamo-nuevo'), self.datos_nuevo(matricula='NOEXISTE'))
        self.assertFalse(Prestamo.objects.exists())

    def test_prestamo_directo_con_fecha_pasada(self):
        self.client.post(reverse('enc-prestamo-nuevo'), self.datos_nuevo(fecha_limite='2020-01-01T10:00'))
        self.assertFalse(Prestamo.objects.exists())

    def test_verificar_matricula(self):
        r = self.client.get(reverse('enc-verificar'), {'matricula': 'A01234'}).json()
        self.assertEqual((r['encontrado'], r['puede']), (True, True))
        self.assertFalse(self.client.get(reverse('enc-verificar'), {'matricula': 'X'}).json()['encontrado'])

    def test_verificar_detecta_adeudos(self):
        vencido = Prestamo.objects.create(
            solicitante=self.alumno, estado=Prestamo.ACTIVO, fecha_limite=timezone.now() - timedelta(days=3))
        DetallePrestamo.objects.create(prestamo=vencido, equipo=self.equipo)
        r = self.client.get(reverse('enc-verificar'), {'matricula': 'A01234'}).json()
        self.assertFalse(r['puede'])

    def test_listado_muestra_estados_calculados(self):
        p = self.solicitud()
        self.client.post(reverse('enc-prestamo-aprobar', args=[p.pk]))
        Prestamo.objects.filter(pk=p.pk).update(fecha_limite=timezone.now() - timedelta(days=1))
        r = self.client.get(reverse('enc-pres'))
        self.assertContains(r, 'data-estado="vencido"')
        self.assertContains(r, 'Ana Pérez')


class DevolucionTests(BaseTest):
    def setUp(self):
        self.entrar(self.encargado)
        self.laptop = crear_equipo('LAP-1')
        self.otra = crear_equipo('LAP-2')
        self.prestamo = Prestamo.objects.create(
            solicitante=self.alumno, estado=Prestamo.ACTIVO, fecha_limite=timezone.now() + timedelta(days=1))
        self.d1 = DetallePrestamo.objects.create(prestamo=self.prestamo, equipo=self.laptop)
        self.d2 = DetallePrestamo.objects.create(prestamo=self.prestamo, equipo=self.otra)
        Equipo.objects.update(estado=Equipo.PRESTADO)

    def test_devolucion_en_buen_estado(self):
        self.client.post(reverse('enc-devolver'), {'detalle': self.d1.pk})
        self.laptop.refresh_from_db()
        self.prestamo.refresh_from_db()
        self.assertEqual(self.laptop.estado, Equipo.DISPONIBLE)
        self.assertEqual(self.prestamo.estado, Prestamo.ACTIVO)  # falta el otro equipo
        self.assertFalse(Incidencia.objects.exists())

    def test_el_prestamo_se_cierra_con_el_ultimo_equipo(self):
        self.client.post(reverse('enc-devolver'), {'detalle': self.d1.pk})
        self.client.post(reverse('enc-devolver'), {'detalle': self.d2.pk})
        self.prestamo.refresh_from_db()
        self.assertEqual(self.prestamo.estado, Prestamo.DEVUELTO)

    def test_devolucion_danada_abre_incidente_y_adeudo(self):
        self.client.post(reverse('enc-devolver'), {
            'detalle': self.d1.pk, 'incidente': 'on', 'estado_devolucion': 'danado', 'descripcion': 'Pantalla rota'})
        self.laptop.refresh_from_db()
        incidencia = Incidencia.objects.get()
        self.assertEqual(self.laptop.estado, Equipo.MANTENIMIENTO)
        self.assertEqual((incidencia.tipo, incidencia.prestamo), (Incidencia.DANO, self.prestamo))
        self.assertTrue(self.alumno.tiene_adeudos)

    def test_incidente_exige_descripcion(self):
        self.client.post(reverse('enc-devolver'), {
            'detalle': self.d1.pk, 'incidente': 'on', 'estado_devolucion': 'danado', 'descripcion': ' '})
        self.d1.refresh_from_db()
        self.assertFalse(self.d1.devuelto)

    def test_no_se_devuelve_dos_veces(self):
        self.client.post(reverse('enc-devolver'), {'detalle': self.d1.pk})
        self.client.post(reverse('enc-devolver'), {'detalle': self.d1.pk})
        self.assertEqual(Bitacora.objects.filter(accion='Devolución registrada').count(), 1)

    def test_pagina_de_devoluciones_lista_los_equipos(self):
        r = self.client.get(reverse('enc-dev'))
        self.assertContains(r, 'LAP-1')
        self.assertContains(r, 'LAP-2')


class IncidenteTests(BaseTest):
    def setUp(self):
        self.entrar(self.encargado)
        self.equipo = crear_equipo('LAP-1')

    def test_registrar_incidente_vincula_al_ultimo_solicitante(self):
        p = Prestamo.objects.create(
            solicitante=self.alumno, estado=Prestamo.DEVUELTO, fecha_limite=timezone.now())
        DetallePrestamo.objects.create(prestamo=p, equipo=self.equipo)
        self.client.post(reverse('enc-incidente-nuevo'), {
            'equipo': self.equipo.pk, 'tipo': Incidencia.DANO, 'descripcion': 'Teclado roto'})
        incidencia = Incidencia.objects.get()
        self.equipo.refresh_from_db()
        self.assertEqual(incidencia.prestamo, p)
        self.assertEqual(self.equipo.estado, Equipo.MANTENIMIENTO)
        self.assertTrue(self.alumno.tiene_adeudos)

    def test_resolver_repara_el_equipo_y_saldar_cierra_el_adeudo(self):
        p = Prestamo.objects.create(
            solicitante=self.alumno, estado=Prestamo.DEVUELTO, fecha_limite=timezone.now())
        DetallePrestamo.objects.create(prestamo=p, equipo=self.equipo)
        self.client.post(reverse('enc-incidente-nuevo'), {
            'equipo': self.equipo.pk, 'tipo': Incidencia.DANO, 'descripcion': 'Teclado roto'})
        incidencia = Incidencia.objects.get()

        self.client.post(reverse('enc-incidente-resolver', args=[incidencia.pk]), {'resolucion': Incidencia.REPARADO})
        self.equipo.refresh_from_db()
        incidencia.refresh_from_db()
        self.assertEqual(self.equipo.estado, Equipo.DISPONIBLE)
        self.assertTrue(incidencia.resuelta)
        self.assertTrue(self.alumno.tiene_adeudos)  # reparar el equipo no salda el adeudo

        self.client.post(reverse('enc-incidente-resolver', args=[incidencia.pk]), {'forma_saldo': Incidencia.PAGO})
        self.assertFalse(self.alumno.tiene_adeudos)

    def test_baja_definitiva(self):
        self.client.post(reverse('enc-incidente-nuevo'), {
            'equipo': self.equipo.pk, 'tipo': Incidencia.PERDIDA, 'descripcion': 'No aparece'})
        incidencia = Incidencia.objects.get()
        self.client.post(reverse('enc-incidente-resolver', args=[incidencia.pk]), {'resolucion': Incidencia.BAJA_PERDIDA})
        self.equipo.refresh_from_db()
        self.assertEqual((self.equipo.estado, self.equipo.razon_baja), (Equipo.BAJA, Equipo.RAZON_PERDIDO))

    def test_resolucion_que_no_corresponde_al_tipo(self):
        self.client.post(reverse('enc-incidente-nuevo'), {
            'equipo': self.equipo.pk, 'tipo': Incidencia.PERDIDA, 'descripcion': 'No aparece'})
        incidencia = Incidencia.objects.get()
        self.client.post(reverse('enc-incidente-resolver', args=[incidencia.pk]), {'resolucion': Incidencia.REPARADO})
        incidencia.refresh_from_db()
        self.assertFalse(incidencia.resuelta)

    def test_pagina_de_incidentes_incluye_los_datos(self):
        self.client.post(reverse('enc-incidente-nuevo'), {
            'equipo': self.equipo.pk, 'tipo': Incidencia.DANO, 'descripcion': 'Rayadura'})
        r = self.client.get(reverse('enc-inci'))
        self.assertContains(r, 'datos-incidentes')
        self.assertContains(r, 'Rayadura')


class MenuSolicitanteTests(BaseTest):
    PAGINAS = ('panel_solicitante', 'solicitar_equipo', 'mis_prestamos', 'catalogo',
               'mis_adeudos', 'reglas', 'mi_cuenta')

    def test_todas_las_pestanas_cargan_con_la_barra_lateral(self):
        crear_equipo('LAP-1')
        self.entrar(self.alumno)
        for nombre in self.PAGINAS:
            with self.subTest(nombre):
                r = self.client.get(reverse(nombre))
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, 'id="menu-lateral"')
                self.assertContains(r, 'styles-sidebar.css')
                self.assertContains(r, 'styles-solicitante.css')
                self.assertNotContains(r, 'styles-encargado.css')

    def test_la_pestana_activa_se_marca(self):
        self.entrar(self.alumno)
        html = self.client.get(reverse('catalogo')).content.decode()
        self.assertEqual(html.count('aside-nav-select'), 1)
        self.assertIn(f'href="{reverse("catalogo")}" class="aside-nav-select"', html)

    def test_las_pestanas_exigen_sesion_y_rol(self):
        for nombre in self.PAGINAS:
            with self.subTest(nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 302)  # anónimo
        self.entrar(self.encargado)
        for nombre in self.PAGINAS:
            with self.subTest(nombre):
                self.assertRedirects(self.client.get(reverse(nombre)), reverse('index'))

    def test_el_encargado_usa_su_css_y_la_misma_barra(self):
        self.entrar(self.encargado)
        r = self.client.get(reverse('enc-dash'))
        self.assertContains(r, 'styles-sidebar.css')
        self.assertContains(r, 'styles-encargado.css')
        self.assertNotContains(r, 'styles-solicitante.css')

    def test_aviso_de_adeudos_en_el_menu(self):
        equipo = crear_equipo('LAP-1')
        self.entrar(self.alumno)
        self.assertNotContains(self.client.get(reverse('reglas')), 'aside-aviso')
        vencido = Prestamo.objects.create(
            solicitante=self.alumno, estado=Prestamo.ACTIVO, fecha_limite=timezone.now() - timedelta(days=2))
        DetallePrestamo.objects.create(prestamo=vencido, equipo=equipo)
        self.assertContains(self.client.get(reverse('reglas')), 'aside-aviso')

    def test_mis_prestamos_filtra_por_estado(self):
        e1, e2 = crear_equipo('LAP-1'), crear_equipo('LAP-2')
        pendiente = Prestamo.objects.create(solicitante=self.alumno, fecha_limite=timezone.now() + timedelta(days=1))
        DetallePrestamo.objects.create(prestamo=pendiente, equipo=e1)
        devuelto = Prestamo.objects.create(
            solicitante=self.alumno, estado=Prestamo.DEVUELTO, fecha_limite=timezone.now())
        DetallePrestamo.objects.create(prestamo=devuelto, equipo=e2)
        ajeno = Prestamo.objects.create(solicitante=self.otro, fecha_limite=timezone.now() + timedelta(days=1))
        DetallePrestamo.objects.create(prestamo=ajeno, equipo=e1)

        self.entrar(self.alumno)
        todos = self.client.get(reverse('mis_prestamos'))
        self.assertEqual(len(todos.context['prestamos']), 2)  # no incluye préstamos de otros
        solo = self.client.get(reverse('mis_prestamos'), {'estado': 'devuelto'})
        self.assertEqual([p.pk for p in solo.context['prestamos']], [devuelto.pk])
        raro = self.client.get(reverse('mis_prestamos'), {'estado': 'inventado'})
        self.assertEqual(raro.context['filtro'], 'todos')

    def test_catalogo_cuenta_disponibles(self):
        crear_equipo('LAP-1')
        ocupado = crear_equipo('LAP-2')
        ocupado.estado = Equipo.PRESTADO
        ocupado.save()
        crear_equipo('LAP-3')
        self.entrar(self.alumno)
        categoria = self.client.get(reverse('catalogo')).context['categorias'][0]
        self.assertEqual((categoria.disponibles, len(categoria.lista)), (2, 3))

    def test_cambiar_contrasena(self):
        self.entrar(self.alumno)
        r = self.client.post(reverse('mi_cuenta'), {
            'old_password': 'clave123', 'new_password1': 'Nueva-clave-987', 'new_password2': 'Nueva-clave-987'})
        self.assertRedirects(r, reverse('mi_cuenta'))
        self.alumno.refresh_from_db()
        self.assertTrue(self.alumno.check_password('Nueva-clave-987'))
        self.assertEqual(self.client.get(reverse('reglas')).status_code, 200)  # la sesión sigue abierta

    def test_contrasena_actual_incorrecta(self):
        self.entrar(self.alumno)
        self.client.post(reverse('mi_cuenta'), {
            'old_password': 'mala', 'new_password1': 'Nueva-clave-987', 'new_password2': 'Nueva-clave-987'})
        self.alumno.refresh_from_db()
        self.assertTrue(self.alumno.check_password('clave123'))


class BitacoraDeAccesosTests(BaseTest):
    def test_intento_fallido_queda_en_la_bitacora_sin_la_contrasena(self):
        self.client.post(reverse('login'), {'username': 'A01234', 'password': 'secreta-mala'})
        registro = Bitacora.objects.get(tipo=Bitacora.ACCESO, accion='Intento de acceso fallido')
        self.assertIn('A01234', registro.detalle)
        self.assertNotIn('secreta-mala', registro.detalle)

    def test_rol_incorrecto_queda_en_la_bitacora(self):
        self.client.post(reverse('login') + '?tipo=encargado', {'username': 'A01234', 'password': 'clave123'})
        self.assertTrue(Bitacora.objects.filter(
            tipo=Bitacora.ACCESO, usuario=self.alumno, accion__startswith='Acceso denegado').exists())

    def test_cierre_de_sesion_queda_en_la_bitacora(self):
        self.entrar(self.alumno)
        self.client.get(reverse('logout'))
        self.assertTrue(Bitacora.objects.filter(
            tipo=Bitacora.ACCESO, usuario=self.alumno, accion='Cierre de sesión').exists())


class AdeudosEncargadoTests(BaseTest):
    def setUp(self):
        self.entrar(self.encargado)

    def prestamo_vencido(self, equipo, minutos):
        p = Prestamo.objects.create(
            solicitante=self.alumno, estado=Prestamo.ACTIVO, fecha_limite=timezone.now() - timedelta(minutes=minutos))
        return p, DetallePrestamo.objects.create(prestamo=p, equipo=equipo)

    def test_lista_prestamos_vencidos_y_danos_sin_saldar(self):
        self.prestamo_vencido(crear_equipo('LAP-1'), 120)
        equipo = crear_equipo('LAP-2')
        prestamo = Prestamo.objects.create(
            solicitante=self.otro, estado=Prestamo.DEVUELTO, fecha_limite=timezone.now())
        incidencia = Incidencia.objects.create(
            equipo=equipo, prestamo=prestamo, usuario_registro=self.encargado,
            tipo=Incidencia.DANO, descripcion='Pantalla rota')
        r = self.client.get(reverse('enc-adeu'))
        self.assertEqual(r.context['total_adeudos'], 2)
        self.assertEqual(r.context['solicitantes_con_adeudo'], 2)
        self.assertContains(r, 'Pantalla rota')
        self.assertContains(r, reverse('enc-incidente-resolver', args=[incidencia.pk]))

    def test_saldar_desde_adeudos_vuelve_a_adeudos(self):
        equipo = crear_equipo('LAP-1')
        prestamo = Prestamo.objects.create(
            solicitante=self.alumno, estado=Prestamo.DEVUELTO, fecha_limite=timezone.now())
        incidencia = Incidencia.objects.create(
            equipo=equipo, prestamo=prestamo, usuario_registro=self.encargado,
            tipo=Incidencia.PERDIDA, descripcion='No apareció')
        r = self.client.post(reverse('enc-incidente-resolver', args=[incidencia.pk]),
                             {'forma_saldo': Incidencia.PAGO, 'next': reverse('enc-adeu')})
        self.assertRedirects(r, reverse('enc-adeu'))
        incidencia.refresh_from_db()
        self.assertTrue(incidencia.adeudo_saldado)
        self.assertEqual(self.client.get(reverse('enc-adeu')).context['total_adeudos'], 0)

    def test_vencidos_respeta_la_tolerancia(self):
        self.prestamo_vencido(crear_equipo('LAP-1'), 5)  # dentro de los 10 minutos de tolerancia
        self.prestamo_vencido(crear_equipo('LAP-2'), 60)
        r = self.client.get(reverse('enc-ven'))
        self.assertEqual(r.context['total_vencidos'], 1)

    def test_nuevas_pestanas_cargan_y_exigen_encargado(self):
        for nombre in ('enc-ven', 'enc-inven', 'enc-adeu', 'enc-historial'):
            with self.subTest(nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)
        self.client.logout()
        for nombre in ('enc-ven', 'enc-inven', 'enc-adeu', 'enc-historial'):
            with self.subTest(anonimo=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 302)
        self.entrar(self.alumno)
        for nombre in ('enc-ven', 'enc-inven', 'enc-adeu', 'enc-historial'):
            with self.subTest(alumno=nombre):
                self.assertRedirects(self.client.get(reverse(nombre)), reverse('index'))


class InventarioEncargadoTests(BaseTest):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre='Laptop')
        self.entrar(self.encargado)

    def test_agrega_un_equipo(self):
        r = self.client.post(reverse('enc-inven'), {
            'nombre': 'Dell Latitude', 'codigo_inventario': 'LAP-9', 'categoria': self.categoria.pk}, follow=True)
        equipo = Equipo.objects.get(codigo_inventario='LAP-9')
        self.assertEqual((equipo.marca, equipo.modelo), ('Dell', 'Latitude'))
        self.assertContains(r, 'Equipo agregado')

    def test_codigo_repetido_avisa(self):
        crear_equipo('LAP-9', self.categoria)
        r = self.client.post(reverse('enc-inven'), {
            'nombre': 'HP Probook', 'codigo_inventario': 'LAP-9', 'categoria': self.categoria.pk}, follow=True)
        self.assertContains(r, 'Ya existe un equipo')
        self.assertEqual(Equipo.objects.count(), 1)

    def test_el_alumno_no_puede_agregar_equipos(self):
        self.entrar(self.alumno)
        self.client.post(reverse('enc-inven'), {
            'nombre': 'Dell Latitude', 'codigo_inventario': 'LAP-9', 'categoria': self.categoria.pk})
        self.assertFalse(Equipo.objects.exists())


class AdministradorTests(BaseTest):
    def test_panel_y_bitacora_solo_para_el_administrador(self):
        for nombre in ('adm-panel', 'adm-bitacora'):
            with self.subTest(nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 302)  # anónimo
                self.entrar(self.encargado)
                self.assertRedirects(self.client.get(reverse(nombre)), reverse('index'))
                self.entrar(self.admin)
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)
                self.client.logout()

    def test_el_login_de_admin_lleva_al_panel(self):
        r = self.client.post(reverse('login') + '?tipo=ADMIN', {'username': 'AD01', 'password': 'clave123'})
        self.assertRedirects(r, reverse('adm-panel'))

    def test_bitacora_filtra_y_pagina_de_50_en_50(self):
        for n in range(60):
            Bitacora.objects.create(tipo=Bitacora.OPERACION, usuario=self.encargado, accion=f'Operación {n}')
        Bitacora.objects.create(tipo=Bitacora.ACCESO, usuario=self.alumno, accion='Inicio de sesión')
        self.entrar(self.admin)
        r = self.client.get(reverse('adm-bitacora'))
        self.assertEqual(len(r.context['pagina']), 50)
        self.assertEqual(r.context['pagina'].paginator.num_pages, 2)
        accesos = self.client.get(reverse('adm-bitacora'), {'tipo': 'acceso'})
        self.assertEqual([x.accion for x in accesos.context['pagina']], ['Inicio de sesión'])
        por_usuario = self.client.get(reverse('adm-bitacora'), {'usuario': 'A01234'})
        self.assertEqual(por_usuario.context['pagina'].paginator.count, 1)
        por_accion = self.client.get(reverse('adm-bitacora'), {'accion': 'Operación 59'})
        self.assertEqual(por_accion.context['pagina'].paginator.count, 1)

    def test_el_historial_del_encargado_no_muestra_accesos(self):
        Bitacora.objects.create(tipo=Bitacora.ACCESO, usuario=self.alumno, accion='Inicio de sesión')
        Bitacora.objects.create(tipo=Bitacora.OPERACION, usuario=self.encargado, accion='Devolución registrada')
        self.entrar(self.encargado)
        r = self.client.get(reverse('enc-historial'), {'tipo': 'acceso'})  # el filtro de tipo no se respeta
        self.assertEqual([x.accion for x in r.context['pagina']], ['Devolución registrada'])


class SolicitudReglasTests(BaseTest):
    """Las reglas de horario se prueban con la hora fijada: 24/11/2026, 10:00 (zona del proyecto)."""

    def setUp(self):
        self.ahora = timezone.make_aware(datetime(2026, 11, 24, 10, 0))
        self.laptop = crear_equipo('LAP-1')  # categoría por días
        horas = Categoria.objects.create(nombre='Proyector', modalidad=Categoria.POR_HORAS)
        self.proyector = crear_equipo('PRO-1', horas)

    def validar(self, equipo, limite, ahora=None, **extra):
        with mock.patch('project.services.ahora', return_value=ahora or self.ahora):
            return services.validar_solicitud(
                self.alumno, [equipo], limite, extra.pop('motivo_tipo', 'practica'), **extra)

    def error(self, equipo, limite, **kwargs):
        with self.assertRaises(services.ErrorOperacion) as ctx:
            self.validar(equipo, limite, **kwargs)
        return ctx.exception

    def en(self, dia, hora, minuto=0):
        return timezone.make_aware(datetime(2026, 11, dia, hora, minuto))

    def test_por_horas_acepta_hoy_en_pasos_de_15_minutos(self):
        self.assertEqual(self.validar(self.proyector, self.en(24, 11, 45)), self.en(24, 11, 45))

    def test_por_horas_rechaza_mas_de_dos_horas(self):
        self.assertIn('2 horas', str(self.error(self.proyector, self.en(24, 12, 15))))

    def test_por_horas_rechaza_minutos_fuera_del_paso(self):
        self.assertIn('15 minutos', str(self.error(self.proyector, self.en(24, 11, 10))))

    def test_por_horas_rechaza_otro_dia(self):
        self.assertIn('mismo día', str(self.error(self.proyector, self.en(25, 9, 0))))

    def test_por_horas_rechaza_fuera_de_horario(self):
        tarde = self.en(24, 19, 0)
        self.assertIn('horario', str(self.error(self.proyector, self.en(24, 21, 0), ahora=tarde)))
        madrugada = self.en(24, 6, 0)
        self.assertIn('horario', str(self.error(self.proyector, self.en(24, 7, 30), ahora=madrugada)))

    def test_por_dias_se_devuelve_al_cierre_del_dia_elegido(self):
        self.assertEqual(self.validar(self.laptop, self.en(25, 9, 30)), self.en(25, 20, 0))

    def test_por_dias_no_acepta_hoy_ni_mas_de_siete_dias(self):
        self.assertIn('mañana', str(self.error(self.laptop, self.en(24, 15, 0))))
        self.assertIn('7 días', str(self.error(self.laptop, self.ahora + timedelta(days=8))))
        self.assertEqual(self.validar(self.laptop, self.ahora + timedelta(days=7)).hour, 20)

    def test_una_solicitud_es_de_un_solo_equipo(self):
        self.assertEqual(settings.SOLICITUD_MAX_EQUIPOS, 1)
        otro = crear_equipo('LAP-2')
        error = self.error_con_equipos([self.laptop, otro], self.en(25, 9))
        self.assertEqual(error.campo, 'equipos')
        self.assertIn('un equipo', str(error))

    @override_settings(SOLICITUD_MAX_EQUIPOS=3)
    def test_si_se_permiten_varios_no_mezcla_modalidades_ni_pasa_del_maximo(self):
        self.assertIn('combinar', str(self.error_con_equipos([self.laptop, self.proyector], self.en(25, 9))))
        extras = [crear_equipo(f'X-{n}') for n in range(4)]
        self.assertIn('hasta 3', str(self.error_con_equipos(extras, self.en(25, 9))))

    def error_con_equipos(self, equipos, limite):
        with mock.patch('project.services.ahora', return_value=self.ahora):
            with self.assertRaises(services.ErrorOperacion) as ctx:
                services.validar_solicitud(self.alumno, equipos, limite, 'practica')
        return ctx.exception

    def test_la_pagina_limita_la_seleccion_a_un_equipo(self):
        self.entrar(self.alumno)
        r = self.client.get(reverse('solicitar_equipo'))
        self.assertContains(r, 'data-max="1"')
        self.assertContains(r, 'Elige un equipo disponible')

    def test_con_adeudos_no_puede_solicitar(self):
        vencido = Prestamo.objects.create(
            solicitante=self.alumno, estado=Prestamo.ACTIVO, fecha_limite=timezone.now() - timedelta(days=2))
        DetallePrestamo.objects.create(prestamo=vencido, equipo=crear_equipo('LAP-9'))
        self.assertIn('adeudos', str(self.error(self.laptop, self.en(25, 9))))

    def test_motivo_otro_exige_detalle(self):
        error = self.error(self.laptop, self.en(25, 9), motivo_tipo=Prestamo.MOTIVO_OTRO, motivo=' ')
        self.assertEqual(error.campo, 'motivo')

    def test_solicitar_crea_pendiente_con_bitacora(self):
        with mock.patch('project.services.ahora', return_value=self.ahora):
            prestamo = services.solicitar_prestamo(self.alumno, [self.laptop], self.en(26, 9), 'tarea')
        self.assertEqual(prestamo.estado, Prestamo.PENDIENTE)
        self.assertEqual(prestamo.fecha_limite, self.en(26, 20, 0))
        self.assertEqual(list(prestamo.equipos.all()), [self.laptop])
        self.assertTrue(Bitacora.objects.filter(accion='Solicitud de préstamo', id_registro=prestamo.pk).exists())

    def test_equipo_no_disponible_se_rechaza(self):
        self.laptop.estado = Equipo.PRESTADO
        self.laptop.save()
        with mock.patch('project.services.ahora', return_value=self.ahora):
            with self.assertRaises(services.ErrorOperacion):
                services.solicitar_prestamo(self.alumno, [self.laptop], self.en(26, 9), 'tarea')

    def test_el_formulario_muestra_el_error_en_el_campo(self):
        with mock.patch('project.services.ahora', return_value=self.ahora):
            form = SolicitudPrestamoForm(
                {'equipos': [self.proyector.pk], 'fecha_limite': '2026-11-24T14:00', 'motivo_tipo': 'tarea'},
                solicitante=self.alumno)
            self.assertFalse(form.is_valid())
        self.assertIn('fecha_limite', form.errors)
