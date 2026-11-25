document.addEventListener('DOMContentLoaded', () => {
    const buscador = document.getElementById('buscar-equipo');
    const filtros = document.querySelectorAll('.filtro-categoria');
    const tarjetas = document.querySelectorAll('.equipo-card');
    const vacio = document.getElementById('sin-resultados');
    let categoria = 'todos';

    function aplicar() {
        const texto = buscador.value.trim().toLowerCase();
        let visibles = 0;
        tarjetas.forEach((t) => {
            const coincide = (categoria === 'todos' || t.dataset.categoria === categoria)
                && t.dataset.busqueda.includes(texto);
            t.hidden = !coincide;
            if (coincide) visibles += 1;
        });
        vacio.hidden = visibles > 0;
    }

    buscador.addEventListener('input', aplicar);
    filtros.forEach((f) => f.addEventListener('click', () => {
        categoria = f.dataset.categoria;
        filtros.forEach((x) => x.classList.toggle('activo', x === f));
        aplicar();
    }));

    /* Límite de equipos por solicitud: al llegar al máximo, el resto ya no se puede marcar.
       El servidor vuelve a validarlo, esto solo evita que el alumno llegue a un error. */
    const lista = document.querySelector('.equipos-lista');
    const maximo = parseInt((lista && lista.dataset.max) || '0', 10);
    const contador = document.getElementById('contador-equipos');
    const cajas = Array.from(document.querySelectorAll('.equipo-card input[type="checkbox"]'));
    const noDisponibles = new Set(cajas.filter((c) => c.disabled));  // ya vienen bloqueadas del servidor

    function limitar() {
        const marcadas = cajas.filter((c) => c.checked).length;
        const lleno = maximo > 0 && marcadas >= maximo;
        cajas.forEach((c) => {
            if (noDisponibles.has(c)) return;
            c.disabled = lleno && !c.checked;
            c.closest('.equipo-card').classList.toggle('equipo-limite', c.disabled);
        });
        if (contador && maximo > 0) {
            const plural = maximo === 1 ? 'equipo' : 'equipos';
            contador.textContent = lleno
                ? `Elegiste ${marcadas} de ${maximo} ${plural}. Desmárcalo si quieres elegir otro.`
                : `Puedes elegir ${maximo} ${plural}.`;
            contador.classList.toggle('contador-lleno', lleno);
        }
    }

    cajas.forEach((c) => c.addEventListener('change', limitar));
    limitar();
});
