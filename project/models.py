from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


def limite_de_vencimiento():
    """Un préstamo está vencido si su fecha límite es anterior a este momento (ya con tolerancia)."""
    return timezone.now() - timedelta(minutes=settings.TOLERANCIA_MINUTOS)


class Rol(models.Model):
    SOLICITANTE = 'solicitante'
    ENCARGADO = 'encargado'
    ADMINISTRADOR = 'administrador'

    nombre = models.CharField(max_length=30, unique=True)

    class Meta:
        db_table = 'roles'
        verbose_name = 'rol'
        verbose_name_plural = 'roles'

    def __str__(self):
        return self.nombre.capitalize()


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, correo, nombre, password=None, rol=Rol.SOLICITANTE, **extra):
        if not correo:
            raise ValueError('El correo es obligatorio')
        rol_obj, _ = Rol.objects.get_or_create(nombre=rol)
        usuario = self.model(correo=self.normalize_email(correo), nombre=nombre, rol=rol_obj, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, correo, nombre, password=None, **extra):
        extra.setdefault('is_superuser', True)
        extra.setdefault('num_empleado', 'ADMIN')
        return self.create_user(correo, nombre, password, rol=Rol.ADMINISTRADOR, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    nombre = models.CharField(max_length=120)
    correo = models.EmailField(unique=True)
    # Solo uno de los dos aplica según el rol; se usan para iniciar sesión.
    matricula = models.CharField(max_length=20, unique=True, null=True, blank=True)
    num_empleado = models.CharField(max_length=20, unique=True, null=True, blank=True)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name='usuarios')
    is_active = models.BooleanField('activo', default=True, db_column='activo')

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.identificador})'

    @property
    def identificador(self):
        return self.matricula or self.num_empleado or self.correo

    @property
    def es_solicitante(self):
        return self.rol.nombre == Rol.SOLICITANTE

    @property
    def es_administrador(self):
        return self.rol.nombre == Rol.ADMINISTRADOR

    @property
    def es_encargado(self):
        # El administrador hereda todo lo del encargado (diagrama de casos de uso).
        return self.rol.nombre in (Rol.ENCARGADO, Rol.ADMINISTRADOR)

    @property
    def is_staff(self):
        return self.es_administrador

    # El rol Administrador tiene todos los permisos en el sitio de administración,
    # sin tener que asignarlos modelo por modelo.
    def has_perm(self, perm, obj=None):
        if self.is_active and self.es_administrador:
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if self.is_active and self.es_administrador:
            return True
        return super().has_module_perms(app_label)

    # --- Adeudos -------------------------------------------------------
    # Un adeudo es un préstamo vencido sin devolver, o un daño/pérdida de un equipo que
    # tuvo prestado y que todavía no ha repuesto ni pagado. Reparar o dar de baja el equipo
    # NO salda el adeudo: solo lo salda la reposición o el pago (ver Incidencia.adeudo_saldado).

    def prestamos_vencidos(self):
        return self.prestamos_solicitados.filter(
            estado=Prestamo.ACTIVO, fecha_limite__lt=limite_de_vencimiento()
        )

    def incidencias_pendientes(self):
        return Incidencia.objects.con_adeudo_pendiente().filter(prestamo__solicitante=self)

    @property
    def tiene_adeudos(self):
        return self.prestamos_vencidos().exists() or self.incidencias_pendientes().exists()


class Categoria(models.Model):
    POR_DIAS = 'dias'
    POR_HORAS = 'horas'
    MODALIDADES = [
        (POR_DIAS, 'Por días'),
        (POR_HORAS, 'Por horas (mismo día)'),
    ]

    nombre = models.CharField(max_length=60, unique=True)
    # Los equipos por horas se prestan dentro del horario de servicio y se devuelven el mismo día.
    modalidad = models.CharField(max_length=10, choices=MODALIDADES, default=POR_DIAS)

    class Meta:
        db_table = 'categorias'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def por_horas(self):
        return self.modalidad == self.POR_HORAS


class Equipo(models.Model):
    DISPONIBLE = 'disponible'
    PRESTADO = 'prestado'
    MANTENIMIENTO = 'mantenimiento'
    EXTRAVIADO = 'extraviado'
    BAJA = 'baja'
    ESTADOS = [
        (DISPONIBLE, 'Disponible'),
        (PRESTADO, 'Prestado'),
        (MANTENIMIENTO, 'En mantenimiento'),
        (EXTRAVIADO, 'Extraviado'),
        (BAJA, 'Dado de baja'),
    ]

    # La baja es definitiva y siempre lleva una razón específica
    RAZON_PERDIDO = 'perdido'
    RAZON_IRREPARABLE = 'irreparable'
    RAZON_REPOSICION = 'reposicion'
    RAZON_OBSOLETO = 'obsoleto'
    RAZONES_BAJA = [
        (RAZON_PERDIDO, 'Pérdida confirmada'),
        (RAZON_IRREPARABLE, 'Dañado sin reparación'),
        (RAZON_REPOSICION, 'Repuesto por el solicitante'),
        (RAZON_OBSOLETO, 'Obsoleto o fuera de uso'),
    ]

    codigo_inventario = models.CharField(max_length=40, unique=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='equipos')
    marca = models.CharField(max_length=60)
    modelo = models.CharField(max_length=60)
    numero_serie = models.CharField(max_length=60, unique=True, null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default=DISPONIBLE)
    razon_baja = models.CharField(max_length=15, choices=RAZONES_BAJA, blank=True)
    fecha_baja = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'equipos'
        ordering = ['categoria__nombre', 'marca', 'modelo']

    def __str__(self):
        return f'{self.marca} {self.modelo} ({self.codigo_inventario})'

    def clean(self):
        super().clean()
        if self.estado == self.BAJA and not self.razon_baja:
            raise ValidationError({'razon_baja': 'Para dar de baja un equipo indica la razón.'})
        if self.estado != self.BAJA and self.razon_baja:
            raise ValidationError({'razon_baja': 'Solo un equipo dado de baja lleva razón de baja.'})

    def save(self, *args, **kwargs):
        # La fecha de baja se mantiene coherente aunque el estado se cambie desde el admin
        if self.estado == self.BAJA and self.fecha_baja is None:
            self.fecha_baja = timezone.now()
        elif self.estado != self.BAJA:
            self.fecha_baja = None
        super().save(*args, **kwargs)

    def dar_de_baja(self, razon):
        self.estado = self.BAJA
        self.razon_baja = razon
        self.fecha_baja = timezone.now()

    def poner_en_servicio(self):
        """Vuelve a disponible (por ejemplo, un equipo reparado o recuperado)."""
        self.estado = self.DISPONIBLE
        self.razon_baja = ''
        self.fecha_baja = None

    @property
    def nombre(self):
        return f'{self.marca} {self.modelo}'

    @property
    def disponible(self):
        return self.estado == self.DISPONIBLE

    @property
    def por_horas(self):
        return self.categoria.por_horas


class Prestamo(models.Model):
    PENDIENTE = 'pendiente'
    ACTIVO = 'activo'
    DEVUELTO = 'devuelto'
    RECHAZADO = 'rechazado'
    ESTADOS = [
        (PENDIENTE, 'Pendiente'),
        (ACTIVO, 'Activo'),
        (DEVUELTO, 'Devuelto'),
        (RECHAZADO, 'Rechazado'),
    ]

    MOTIVO_OTRO = 'otro'
    MOTIVOS = [
        ('practica', 'Práctica de laboratorio'),
        ('tarea', 'Tarea o proyecto de clase'),
        ('exposicion', 'Exposición o presentación'),
        ('estudio', 'Trabajo de estudio'),
        ('actividad', 'Actividad estudiantil'),
        (MOTIVO_OTRO, 'Otro'),
    ]

    # Motivos de rechazo que el encargado elige de una lista (no se escriben).
    MOTIVOS_RECHAZO = [
        ('no_disponible', 'El equipo ya no está disponible'),
        ('adeudos', 'El solicitante tiene adeudos pendientes'),
        ('fuera_horario', 'Fuera del horario de servicio'),
        ('fecha_invalida', 'Fecha u hora de devolución no válida'),
        ('motivo_insuficiente', 'El motivo de la solicitud no es suficiente'),
        ('otro', 'Otro motivo (consultar con el encargado)'),
    ]

    solicitante = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='prestamos_solicitados')
    # El encargado que aprueba y entrega; vacío mientras la solicitud está pendiente.
    usuario_registro = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name='prestamos_registrados', null=True, blank=True
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    # Fecha y hora límite de devolución (por días: el cierre del día elegido).
    fecha_limite = models.DateTimeField()
    estado = models.CharField(max_length=15, choices=ESTADOS, default=PENDIENTE)
    motivo_tipo = models.CharField(max_length=20, choices=MOTIVOS, default=MOTIVO_OTRO)
    motivo = models.TextField(blank=True)  # detalle adicional del motivo
    observaciones = models.TextField(blank=True)  # motivo de rechazo u observaciones del encargado

    equipos = models.ManyToManyField(Equipo, through='DetallePrestamo', related_name='prestamos')

    class Meta:
        db_table = 'prestamos'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f'Préstamo #{self.pk} - {self.solicitante.nombre}'

    @property
    def vencido(self):
        return self.estado == self.ACTIVO and self.fecha_limite < limite_de_vencimiento()

    @property
    def motivo_completo(self):
        etiqueta = self.get_motivo_tipo_display()
        return f'{etiqueta}: {self.motivo}' if self.motivo else etiqueta

    @property
    def estado_visible(self):
        """Estado para mostrar: 'vencido' no se guarda, se calcula con la fecha límite."""
        return 'vencido' if self.vencido else self.estado

    @property
    def resumen_equipos(self):
        return ', '.join(d.equipo.nombre for d in self.detalles.all())


class DetallePrestamo(models.Model):
    BUEN_ESTADO = 'buen_estado'
    DANADO = 'danado'
    PERDIDO = 'perdido'
    ESTADOS_DEVOLUCION = [
        (BUEN_ESTADO, 'Buen estado'),
        (DANADO, 'Dañado'),
        (PERDIDO, 'Perdido'),
    ]

    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name='detalles')
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name='detalles')
    fecha_devolucion = models.DateTimeField(null=True, blank=True)
    estado_devolucion = models.CharField(max_length=15, choices=ESTADOS_DEVOLUCION, blank=True)
    usuario_devolucion = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name='devoluciones_registradas', null=True, blank=True
    )

    class Meta:
        db_table = 'detalle_prestamo'
        constraints = [
            models.UniqueConstraint(fields=['prestamo', 'equipo'], name='uniq_prestamo_equipo'),
        ]

    def __str__(self):
        return f'{self.prestamo_id} - {self.equipo}'

    @property
    def devuelto(self):
        return self.fecha_devolucion is not None


class IncidenciaQuerySet(models.QuerySet):
    def con_adeudo_pendiente(self):
        """Daños y pérdidas de un préstamo cuyo solicitante aún no repone ni paga."""
        return self.filter(
            prestamo__isnull=False, adeudo_saldado=False,
            tipo__in=[Incidencia.DANO, Incidencia.PERDIDA],
        )

    def abiertas(self):
        """Falta resolver el equipo, o falta que el solicitante salde su adeudo."""
        return self.filter(Q(resuelta=False) | Q(
            prestamo__isnull=False, adeudo_saldado=False, tipo__in=[Incidencia.DANO, Incidencia.PERDIDA]))

    def cerradas(self):
        return self.exclude(pk__in=self.abiertas().values('pk'))


class Incidencia(models.Model):
    DANO = 'dano'
    PERDIDA = 'perdida'
    MANTENIMIENTO = 'mantenimiento'
    TIPOS = [
        (DANO, 'Daño'),
        (PERDIDA, 'Pérdida'),
        (MANTENIMIENTO, 'Mantenimiento'),
    ]

    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name='incidencias')
    # Préstamo en el que ocurrió; permite saber quién tenía el equipo.
    prestamo = models.ForeignKey(
        Prestamo, on_delete=models.PROTECT, related_name='incidencias', null=True, blank=True
    )
    usuario_registro = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='incidencias_registradas')
    tipo = models.CharField(max_length=15, choices=TIPOS)
    descripcion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    # --- Lado del equipo: qué pasó con el equipo (el encargado lo elige de una lista) ---
    REPARADO = 'reparado'
    SIN_FALLA = 'sin_falla'
    RECUPERADO = 'recuperado'
    BAJA_PERDIDA = 'baja_perdida'
    BAJA_IRREPARABLE = 'baja_irreparable'
    BAJA_REPOSICION = 'baja_reposicion'
    BAJA_OBSOLETO = 'baja_obsoleto'
    RESOLUCIONES = [
        (REPARADO, 'Reparado: el equipo vuelve a estar disponible'),
        (SIN_FALLA, 'Revisado sin falla: el equipo vuelve a estar disponible'),
        (RECUPERADO, 'Equipo recuperado: vuelve a estar disponible'),
        (BAJA_PERDIDA, 'Baja definitiva: pérdida confirmada'),
        (BAJA_IRREPARABLE, 'Baja definitiva: dañado sin reparación'),
        (BAJA_REPOSICION, 'Baja definitiva: el solicitante repuso el equipo'),
        (BAJA_OBSOLETO, 'Baja definitiva: obsoleto o fuera de uso'),
    ]
    # Qué resoluciones tienen sentido para cada tipo de incidencia
    RESOLUCIONES_POR_TIPO = {
        DANO: [REPARADO, BAJA_IRREPARABLE, BAJA_REPOSICION],
        MANTENIMIENTO: [REPARADO, SIN_FALLA, BAJA_IRREPARABLE, BAJA_OBSOLETO],
        PERDIDA: [RECUPERADO, BAJA_PERDIDA, BAJA_REPOSICION],
    }
    # Razón con la que queda registrada la baja del equipo
    RAZON_DE_BAJA = {
        BAJA_PERDIDA: Equipo.RAZON_PERDIDO,
        BAJA_IRREPARABLE: Equipo.RAZON_IRREPARABLE,
        BAJA_REPOSICION: Equipo.RAZON_REPOSICION,
        BAJA_OBSOLETO: Equipo.RAZON_OBSOLETO,
    }

    resuelta = models.BooleanField(default=False)  # el equipo ya se atendió (reparado, recuperado o de baja)
    resolucion = models.CharField(max_length=20, choices=RESOLUCIONES, blank=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    usuario_resolucion = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name='incidencias_resueltas', null=True, blank=True
    )

    # --- Lado del solicitante: el adeudo dura hasta que repone el equipo o paga ---
    REPOSICION = 'reposicion'
    PAGO = 'pago'
    FORMAS_SALDO = [
        (REPOSICION, 'El solicitante repuso el equipo'),
        (PAGO, 'El solicitante pagó el costo'),
    ]

    adeudo_saldado = models.BooleanField(default=False)
    forma_saldo = models.CharField(max_length=15, choices=FORMAS_SALDO, blank=True)
    fecha_saldo = models.DateTimeField(null=True, blank=True)
    usuario_saldo = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name='adeudos_saldados', null=True, blank=True
    )

    objects = IncidenciaQuerySet.as_manager()

    class Meta:
        db_table = 'incidencias'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.equipo}'

    @property
    def opciones_resolucion(self):
        etiquetas = dict(self.RESOLUCIONES)
        return [(clave, etiquetas[clave]) for clave in self.RESOLUCIONES_POR_TIPO[self.tipo]]

    @property
    def genera_adeudo(self):
        return self.prestamo_id is not None and self.tipo in (self.DANO, self.PERDIDA)

    @property
    def adeudo_pendiente(self):
        return self.genera_adeudo and not self.adeudo_saldado


class Bitacora(models.Model):
    ACCESO = 'acceso'
    OPERACION = 'operacion'
    TIPOS = [
        (ACCESO, 'Accesos'),
        (OPERACION, 'Operaciones'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPOS, default=OPERACION, db_index=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='bitacora')
    accion = models.CharField(max_length=80)
    entidad = models.CharField(max_length=40, blank=True)
    id_registro = models.PositiveIntegerField(null=True, blank=True)
    detalle = models.TextField(blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bitacora'
        ordering = ['-fecha_hora']
        verbose_name_plural = 'bitácora'

    def __str__(self):
        return f'{self.fecha_hora:%d/%m/%Y %H:%M} - {self.accion}'
