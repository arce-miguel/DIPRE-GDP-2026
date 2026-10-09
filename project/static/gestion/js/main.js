document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btnPrueba');
    if (btn) {
        btn.addEventListener('click', () => {
            alert('¡JavaScript y estáticos funcionando correctamente!');
        });
    }
});