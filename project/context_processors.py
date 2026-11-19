def menu_solicitante(request):
    """Variables del menú lateral del solicitante; solo se consultan si la plantilla las usa."""
    usuario = getattr(request, 'user', None)
    if usuario is None or not usuario.is_authenticated or not usuario.es_solicitante:
        return {}
    # Se pasa una función: Django la llama solo cuando el menú pregunta por el valor
    return {'tiene_adeudos_menu': lambda: usuario.tiene_adeudos}
