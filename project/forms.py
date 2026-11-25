from django import forms

from . import services
from .models import Equipo, Prestamo


class SolicitudPrestamoForm(forms.Form):
    equipos = forms.ModelMultipleChoiceField(
        queryset=Equipo.objects.none(),
        error_messages={'required': 'Elige al menos un equipo.'},
    )
    fecha_limite = forms.DateTimeField(
        label='Fecha y hora de devolución',
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'step': 900}, format='%Y-%m-%dT%H:%M'),
    )
    motivo_tipo = forms.ChoiceField(
        label='Motivo de la solicitud', choices=Prestamo.MOTIVOS,
        widget=forms.RadioSelect,
        error_messages={'required': 'Elige el motivo de la solicitud.'},
    )
    motivo = forms.CharField(
        label='Detalles (opcional)', required=False, max_length=500,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ej. Práctica de la materia de Redes'}),
    )

    def __init__(self, *args, solicitante, **kwargs):
        super().__init__(*args, **kwargs)
        self.solicitante = solicitante
        self.fields['equipos'].queryset = Equipo.objects.filter(
            estado=Equipo.DISPONIBLE).select_related('categoria')

    def clean(self):
        datos = super().clean()
        equipos = datos.get('equipos')
        limite = datos.get('fecha_limite')
        motivo_tipo = datos.get('motivo_tipo')
        try:
            if equipos and limite and motivo_tipo:
                datos['fecha_limite'] = services.validar_solicitud(
                    self.solicitante, equipos, limite, motivo_tipo, datos.get('motivo', ''))
            elif self.solicitante.tiene_adeudos:
                raise services.ErrorOperacion('Tienes adeudos pendientes y no puedes solicitar equipos.')
        except services.ErrorOperacion as error:
            if error.campo:
                self.add_error(error.campo, str(error))
            else:
                raise forms.ValidationError(str(error))
        return datos

    def guardar(self):
        datos = self.cleaned_data
        return services.solicitar_prestamo(
            self.solicitante, datos['equipos'], datos['fecha_limite'], datos['motivo_tipo'], datos['motivo'])
