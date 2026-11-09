document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btnPrueba');
    if (btn) {
        btn.addEventListener('click', () => {
            alert('¡JavaScript y estáticos funcionando correctamente!');
        });
    }
});
document.addEventListener('DOMContentLoaded', () => {
  const btnNuevo = document.getElementById('bNew');
  const veil     = document.getElementById('veil');
  const modal    = document.getElementById('modal');
  const btnCerrar = document.getElementById('mC');

  // Si esta página no tiene el modal, salimos sin dar error
  if (!btnNuevo || !veil || !modal) return;

  btnNuevo.addEventListener('click', () => {
    veil.classList.add('on');
    modal.classList.add('on');
  });

  btnCerrar.addEventListener('click', () => {
    veil.classList.remove('on');
    modal.classList.remove('on');
  });

  // Opcional: cerrar al tocar el fondo oscuro
  veil.addEventListener('click', () => {
    veil.classList.remove('on');
    modal.classList.remove('on');
  });
});

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
document.addEventListener('DOMContentLoaded', () => {
  const botones = document.querySelectorAll('.EP-menus-btn-u');

  botones.forEach(btn => {
    btn.addEventListener('click', () => {
      botones.forEach(b => b.classList.remove('activo'));
      btn.classList.add('activo');
    });
  });
});
document.addEventListener('DOMContentLoaded', () => {
    const tbody = document.querySelector('.EP-table tbody');
    if (!tbody) return;

    tbody.addEventListener('click', (e) => {
        // Si presionaron un botón o enlace, no expandir
        if (e.target.closest('button') || e.target.closest('a')) return;

        const fila = e.target.closest('tr');
        if (!fila || fila.classList.contains('detalle')) return;

        const detalle = fila.nextElementSibling;
        if (!detalle || !detalle.classList.contains('detalle')) return;

        const estabaAbierta = detalle.classList.contains('abierta');

        // Cerrar las demás
        tbody.querySelectorAll('tr.detalle.abierta')
             .forEach(tr => tr.classList.remove('abierta'));

        // Abrir esta (si estaba abierta, queda cerrada)
        if (!estabaAbierta) detalle.classList.add('abierta');
    });
});
document.addEventListener('DOMContentLoaded', () => {
    const tbody = document.querySelector('.EP-table tbody');
    if (!tbody) return;

    tbody.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-devolver');
        if (!btn) return;

        if (!confirm('¿Registrar la devolución de este equipo?')) return;

        const detalle = btn.closest('tr.detalle');
        const fila = detalle.previousElementSibling;   // la fila del préstamo

        // Cambiar la etiqueta de estado
        const estado = fila.querySelector('td > span');
        estado.textContent = 'Devuelto';
        estado.className = 's-devuelto';

        // Quitar el botón y cerrar el detalle
        btn.remove();
        detalle.classList.remove('abierta');
    });
});
document.addEventListener('DOMContentLoaded', () => {
    const btnNuevo = document.getElementById('bNew');
    const veil     = document.getElementById('veil');
    const modal    = document.getElementById('modal');
    const btnCerrar = document.getElementById('mC');
    const btnOk    = document.getElementById('mOk');
    const btnVer   = document.getElementById('bVer');
    const fM       = document.getElementById('fM');
    const fN       = document.getElementById('fN');
    const vRes     = document.getElementById('vRes');

    // Si esta página no tiene el modal, salimos sin dar error
    if (!btnNuevo || !veil || !modal) return;

    // Datos de prueba (después vendrán de la base de datos)
    const estudiantes = {
        A01234: { nombre: 'Ana Pérez',    adeudos: 1, incidentes: 0 },
        A01877: { nombre: 'Luis Ramírez', adeudos: 0, incidentes: 1 },
        A02011: { nombre: 'María Torres', adeudos: 0, incidentes: 0 },
        A01590: { nombre: 'Carlos Medina', adeudos: 0, incidentes: 0 },
    };

    const MENSAJE_INICIAL = 'Verifica la matrícula para ver si tiene adeudos o incidentes.';

    // Muestra el resultado y activa/desactiva "Confirmar"
    function mostrar(clase, texto, permitir) {
        vRes.className = 'vres ' + clase;
        vRes.textContent = texto;
        btnOk.disabled = !permitir;
    }

    function abrir() {
        fM.value = '';
        fN.value = '';
        mostrar('', MENSAJE_INICIAL, false);
        veil.classList.add('on');
        modal.classList.add('on');
        fM.focus();
    }

    function cerrar() {
        veil.classList.remove('on');
        modal.classList.remove('on');
    }

    // Abrir y cerrar
    btnNuevo.addEventListener('click', abrir);
    if (btnCerrar) btnCerrar.addEventListener('click', cerrar);
    veil.addEventListener('click', cerrar);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') cerrar();
    });

    // Verificar matrícula
    function verificar() {
        const mat = fM.value.trim().toUpperCase();

        if (!mat) {
            mostrar('bad', 'Escribe el número de control.', false);
            return;
        }

        const e = estudiantes[mat];
        if (!e) {
            fN.value = '';
            mostrar('bad', 'Matrícula no encontrada.', false);
            return;
        }

        fN.value = e.nombre;

        const pendientes = [];
        if (e.adeudos)    pendientes.push(e.adeudos + (e.adeudos > 1 ? ' adeudos' : ' adeudo'));
        if (e.incidentes) pendientes.push(e.incidentes + (e.incidentes > 1 ? ' incidentes' : ' incidente'));

        if (pendientes.length) {
            mostrar('bad', e.nombre + ' tiene ' + pendientes.join(' y ') + ' pendiente. No puede solicitar préstamo.', false);
        } else {
            mostrar('good', e.nombre + ': sin adeudos ni incidentes. Puede solicitar préstamo.', true);
        }
    }

    if (btnVer) btnVer.addEventListener('click', verificar);

    // Enter dentro del campo de matrícula también verifica
    if (fM) fM.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') verificar();
    });

    // Si cambian la matrícula, hay que verificar otra vez
    if (fM) fM.addEventListener('input', () => {
        fN.value = '';
        mostrar('', MENSAJE_INICIAL, false);
    });

    // Confirmar préstamo
    if (btnOk) btnOk.addEventListener('click', () => {
        const datos = {
            matricula: fM.value.trim().toUpperCase(),
            estudiante: fN.value,
            equipo: document.getElementById('fE').value,
            limite: document.getElementById('fD').value,
            observaciones: document.getElementById('fO').value,
        };
        console.log('Préstamo a registrar:', datos);
        // Aquí después irá el envío a Django
        cerrar();
    });
});
