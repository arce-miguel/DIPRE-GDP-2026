document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btnPrueba');
    if (btn) {
        btn.addEventListener('click', () => {
            alert('¡JavaScript y estáticos funcionando correctamente!');
        });
    }
});


document.addEventListener('DOMContentLoaded', () => {
    const btnMenu = document.getElementById('btn-menu');
    const menuLateral = document.getElementById('menu-lateral');

    // Si por alguna razón el botón o el menú no existen en la página actual, salimos para evitar errores
    if (!btnMenu || !menuLateral) return;

    // 1. Al cargar la página, revisamos qué estado se guardó
    const estadoMenu = localStorage.getItem('estadoMenu');

    // Si el estado guardado es 'abierto', removemos la clase 'closed' para que se muestre
    if (estadoMenu === 'abierto') {
        menuLateral.classList.remove('closed');
    } else {
        // Opcional: Asegurar que inicie cerrado si no hay registro o está guardado como cerrado
        menuLateral.classList.add('closed');
    }

    // 2. Al hacer clic en el botón del menú
    btnMenu.addEventListener('click', () => {
        // Alternamos la clase 'closed'
        menuLateral.classList.toggle('closed');
        
        // 3. Guardamos el estado actual en el localStorage
        if (menuLateral.classList.contains('closed')) {
            localStorage.setItem('estadoMenu', 'cerrado');
        } else {
            localStorage.setItem('estadoMenu', 'abierto');
        }
    });
});
