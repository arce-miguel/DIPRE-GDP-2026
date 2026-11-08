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
});
