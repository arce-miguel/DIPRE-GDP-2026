/* Barra lateral de los paneles (encargado y solicitante): se recuerda abierta/cerrada. */

document.addEventListener('DOMContentLoaded', () => {
    const btnMenu = document.getElementById('btn-menu');
    const menuLateral = document.getElementById('menu-lateral');

    // Si la página no tiene el botón o el menú, salimos sin error
    if (!btnMenu || !menuLateral) return;

    // Seguro: si el archivo se cargara dos veces, no duplicar el clic
    if (btnMenu.dataset.listo) return;
    btnMenu.dataset.listo = '1';

    // 1. Desactivar animaciones por un instante
    const sinAnimacion = document.createElement('style');
    sinAnimacion.textContent = '*{transition:none !important}';
    document.head.appendChild(sinAnimacion);

    // 2. Aplicar el estado guardado
    if (localStorage.getItem('estadoMenu') === 'abierto') {
        menuLateral.classList.remove('closed');
    } else {
        menuLateral.classList.add('closed');
    }

    // 3. Forzar al navegador a calcular el estilo con ese estado
    //    y después volver a activar las animaciones
    void menuLateral.offsetHeight;
    sinAnimacion.remove();

    // 4. Al hacer clic: sí hay animación
    btnMenu.addEventListener('click', () => {
        menuLateral.classList.toggle('closed');

        localStorage.setItem(
            'estadoMenu',
            menuLateral.classList.contains('closed') ? 'cerrado' : 'abierto'
        );
    });
});
