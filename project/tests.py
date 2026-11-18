from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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
