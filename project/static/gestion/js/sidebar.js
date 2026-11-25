/* Barra lateral de los paneles (encargado y solicitante).
   En escritorio se recuerda abierta/cerrada; en pantallas angostas empieza cerrada,
   se abre encima del contenido y se cierra con el fondo, con Escape o al elegir una opción. */

document.addEventListener('DOMContentLoaded', () => {
    const btnMenu = document.getElementById('btn-menu');
    const menuLateral = document.getElementById('menu-lateral');

    // Si la página no tiene el botón o el menú, salimos sin error
    if (!btnMenu || !menuLateral) return;

    // Seguro: si el archivo se cargara dos veces, no duplicar el clic
    if (btnMenu.dataset.listo) return;
    btnMenu.dataset.listo = '1';

    const movil = window.matchMedia('(max-width: 900px)');

    // Fondo oscuro que solo se muestra en pantallas angostas con el menú abierto
    const fondo = document.createElement('div');
    fondo.className = 'menu-fondo';
    fondo.hidden = true;
    document.body.appendChild(fondo);

    const guardado = (valor) => {
        try { return valor === undefined ? localStorage.getItem('estadoMenu') : localStorage.setItem('estadoMenu', valor); }
        catch (e) { return null; }  // sin almacenamiento (modo privado): el menú sigue funcionando
    };

    function actualizarFondo() {
        fondo.hidden = !(movil.matches && !menuLateral.classList.contains('closed'));
    }

    function cerrar() {
        menuLateral.classList.add('closed');
        if (!movil.matches) guardado('cerrado');
        actualizarFondo();
    }

    // 1. Desactivar animaciones por un instante
    const sinAnimacion = document.createElement('style');
    sinAnimacion.textContent = '*{transition:none !important}';
    document.head.appendChild(sinAnimacion);

    // 2. Estado inicial: en pantallas angostas siempre cerrado; en escritorio, el último guardado
    if (!movil.matches && guardado() === 'abierto') {
        menuLateral.classList.remove('closed');
    } else {
        menuLateral.classList.add('closed');
    }
    actualizarFondo();

    // 3. Forzar al navegador a calcular el estilo con ese estado
    //    y después volver a activar las animaciones
    void menuLateral.offsetHeight;
    sinAnimacion.remove();

    // 4. Al hacer clic: sí hay animación
    btnMenu.addEventListener('click', () => {
        menuLateral.classList.toggle('closed');
        if (!movil.matches) {
            guardado(menuLateral.classList.contains('closed') ? 'cerrado' : 'abierto');
        }
        actualizarFondo();
    });

    fondo.addEventListener('click', cerrar);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && movil.matches && !menuLateral.classList.contains('closed')) cerrar();
    });
    menuLateral.addEventListener('click', (e) => {
        if (movil.matches && e.target.closest('a')) cerrar();
    });
    movil.addEventListener('change', () => {
        // Al cambiar entre móvil y escritorio, el menú vuelve a un estado coherente
        if (movil.matches) menuLateral.classList.add('closed');
        actualizarFondo();
    });
});
