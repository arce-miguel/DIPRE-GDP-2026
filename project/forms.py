from datetime import timedelta

from django import forms
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import DetallePrestamo, Equipo, Prestamo


class SolicitudPrestamoForm(forms.Form):
    equipos = forms.ModelMultipleChoiceField(
        queryset=Equipo.objects.none(),
        error_messages={'required': 'Elige al menos un equipo.'},
    )
    fecha_limite = forms.DateTimeField(
        label='Fecha y hora de devolución',
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
    )
    motivo_tipo = forms.ChoiceField(label='Motivo', choices=Prestamo.MOTIVOS)
    motivo = forms.CharField(
        label='Detalle del motivo', required=False, max_length=500,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, solicitante, **kwargs):
        super().__init__(*args, **kwargs)
        self.solicitante = solicitante
        self.fields['equipos'].queryset = Equipo.objects.filter(
            estado=Equipo.DISPONIBLE).select_related('categoria')

    def clean_equipos(self):
        equipos = self.cleaned_data['equipos']
        if len(equipos) > settings.SOLICITUD_MAX_EQUIPOS:
            raise forms.ValidationError(
                f'Puedes solicitar hasta {settings.SOLICITUD_MAX_EQUIPOS} equipos a la vez.')
        if len({e.por_horas for e in equipos}) > 1:
            raise forms.ValidationError(
                'No puedes combinar equipos por horas con equipos por días en la misma solicitud.')
        return equipos

    def clean(self):
        datos = super().clean()
        if self.solicitante.tiene_adeudos:
            raise forms.ValidationError('Tienes adeudos pendientes y no puedes solicitar equipos.')

        equipos = datos.get('equipos')
        limite = datos.get('fecha_limite')
        if equipos and limite:
            ahora = timezone.localtime()
            limite = timezone.localtime(limite)
            if limite <= ahora:
                self.add_error('fecha_limite', 'La fecha de devolución debe ser futura.')
            elif equipos[0].por_horas:
                apertura, cierre = settings.HORARIO_SERVICIO
                if limite.date() != ahora.date():
                    self.add_error('fecha_limite', 'Los equipos por horas se devuelven el mismo día.')
                elif not apertura <= limite.hour < cierre:
                    self.add_error(
                        'fecha_limite', f'Fuera del horario de servicio ({apertura}:00 a {cierre}:00).')
            elif limite > ahora + timedelta(days=settings.SOLICITUD_MAX_DIAS):
                self.add_error(
                    'fecha_limite', f'El préstamo no puede exceder {settings.SOLICITUD_MAX_DIAS} días.')

        if datos.get('motivo_tipo') == Prestamo.MOTIVO_OTRO and not datos.get('motivo', '').strip():
            self.add_error('motivo', 'Describe el motivo de la solicitud.')
        return datos

    def guardar(self):
        datos = self.cleaned_data
        with transaction.atomic():
            prestamo = Prestamo.objects.create(
                solicitante=self.solicitante,
                fecha_limite=datos['fecha_limite'],
                motivo_tipo=datos['motivo_tipo'],
                motivo=datos['motivo'].strip(),
            )
            DetallePrestamo.objects.bulk_create(
                DetallePrestamo(prestamo=prestamo, equipo=e) for e in datos['equipos'])
        return prestamo
