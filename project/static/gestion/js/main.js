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


//encargado dev
document.addEventListener('DOMContentLoaded', () => {
    const botonesDevolver = document.querySelectorAll('.btn-devolver1');
    const veil            = document.getElementById('veil');
    const modal           = document.getElementById('modal');
    const btnCerrar       = document.getElementById('mC');
    const btnOk           = document.getElementById('mOk');
    
    const checkboxIncidente   = document.getElementById('fInc');
    const cajaIncidente       = document.getElementById('incBox');
    const campoIncidenteTexto = document.getElementById('fIncT');

    if (botonesDevolver.length === 0 || !veil || !modal) return;

    function abrir(e) {
        e.preventDefault(); // Evita comportamientos extraños del botón
        
        // Limpiar formulario al abrir
        if (checkboxIncidente) checkboxIncidente.checked = false;
        if (cajaIncidente) cajaIncidente.style.display = 'none';
        if (campoIncidenteTexto) campoIncidenteTexto.value = '';

        // Activar velo y modal con la clase 'on'
        veil.classList.add('on');
        modal.classList.add('on');
    }

    function cerrar() {
        veil.classList.remove('on');
        modal.classList.remove('on');
    }

    // Vincular cada botón de la tabla
    botonesDevolver.forEach(boton => {
        boton.addEventListener('click', abrir);
    });

    // Cerrar con el botón cancelar
    if (btnCerrar) btnCerrar.addEventListener('click', cerrar);

    // Cerrar al hacer clic en el fondo oscuro
    veil.addEventListener('click', cerrar);

    // Cerrar con la tecla Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') cerrar();
    });

    // Controlar el despliegue del textarea (expande el modal)
    if (checkboxIncidente) {
        checkboxIncidente.addEventListener('change', function() {
            if (this.checked) {
                cajaIncidente.style.display = 'flex'; // Muestra la caja y amplía el modal
                if (campoIncidenteTexto) campoIncidenteTexto.focus();
            } else {
                cajaIncidente.style.display = 'none'; // Oculta la caja y reduce el modal
                if (campoIncidenteTexto) campoIncidenteTexto.value = '';
            }
        });
    }

    // Botón confirmar devolución
    if (btnOk) btnOk.addEventListener('click', () => {
        const datosDevolucion = {
            huboIncidente: checkboxIncidente ? checkboxIncidente.checked : false,
            descripcion: campoIncidenteTexto ? campoIncidenteTexto.value.trim() : ''
        };
        console.log('Datos de devolución listos para enviar:', datosDevolucion);
        // Aquí irá tu lógica para conectar con Django
        cerrar();
    });
});

//Encargado inicentes
document.addEventListener('DOMContentLoaded', () => {

    // Atajo para buscar elementos por su id
    const $ = (id) => document.getElementById(id);

    // Si esta página no tiene la lista de incidentes, salimos sin error
    if (!$('EIn-lista')) return;


    /* ==========================================================
       1. DATOS DE PRUEBA (después vendrán de Django)
       ========================================================== */

    // Fecha de "hoy" fija para que la demo se vea siempre igual.
    // En el proyecto real usa: const HOY = new Date().toISOString().slice(0, 10);
    const HOY = '2026-11-08';

    const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
                   'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

    // "resuelto" es la fecha en que se resolvió (o null si sigue abierto)
    const incidentes = [
        { equipo: 'Laptop Dell Latitude', codigo: 'LAP-014',
          estudiante: 'Ana Pérez', matricula: 'A01234',
          tipo: 'Daño', fecha: '2026-11-06', origen: 'Al devolver',
          descripcion: 'Pantalla rayada en la esquina superior.',
          resuelto: null, solucion: '' },

        { equipo: 'Proyector Epson', codigo: 'PRO-001',
          estudiante: 'Luis Ramírez', matricula: 'A01877',
          tipo: 'Falla', fecha: '2026-11-07', origen: 'Revisión posterior',
          descripcion: 'No enciende la lámpara.',
          resuelto: null, solucion: '' },

        { equipo: 'Cable HDMI 5 m', codigo: 'CAB-012',
          estudiante: 'Sofía Núñez', matricula: 'A02145',
          tipo: 'Faltante', fecha: '2026-11-05', origen: 'Al devolver',
          descripcion: 'Falta el adaptador.',
          resuelto: null, solucion: '' },

        { equipo: 'Tablet Samsung', codigo: 'TAB-005',
          estudiante: 'María Torres', matricula: 'A02011',
          tipo: 'Daño', fecha: '2026-11-02', origen: 'Revisión posterior',
          descripcion: 'Funda rota.',
          resuelto: '2026-11-04', solucion: 'Se reemplazó la funda.' },
    ];

    // Icono de cada tipo (deben existir en tu bloque de iconos SVG)
    const ICONOS = {
        'Daño':     'alerta',
        'Falla':    'ajustes',
        'Faltante': 'inventario',
        'Pérdida':  'buscar',
    };

    // Los dos filtros
    const FILTROS = [
        { clave: 'abierto',  texto: 'Abiertos'  },
        { clave: 'resuelto', texto: 'Resueltos' },
    ];


    /* ==========================================================
       2. ESTADO (lo que cambia mientras se usa la página)
       ========================================================== */

    let filtro = 'abierto';   // filtro seleccionado
    let busqueda = '';        // texto escrito en el buscador
    let seleccionado = null;  // posición del incidente que se va a resolver


    /* ==========================================================
       3. FUNCIONES DE APOYO
       ========================================================== */

    // '2026-11-05' -> '05 nov'
    function formatearFecha(iso) {
        const [anio, mes, dia] = iso.split('-');
        return `${dia} ${MESES[Number(mes) - 1]}`;
    }

    // 'abierto' o 'resuelto'
    function estadoDe(incidente) {
        return incidente.resuelto ? 'resuelto' : 'abierto';
    }

    // Cuántos incidentes hay en cada filtro
    function contar(clave) {
        return incidentes.filter((i) => estadoDe(i) === clave).length;
    }

    // Evita que un texto escrito con < o > rompa la página
    function escapar(texto) {
        return String(texto)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // Aviso corto abajo de la pantalla
function mostrarAviso(texto) {
        const aviso = $('EIn-aviso');
        if (!aviso) return;
        aviso.textContent = texto;
        aviso.style.opacity = 1;
        setTimeout(() => { aviso.style.opacity = 0; }, 1900);
    }


    /* ==========================================================
       4. DIBUJAR FILTROS Y TARJETAS
       ========================================================== */

    function dibujarFiltros() {
        $('EIn-chips').innerHTML = FILTROS.map((f) => `
            <button class="EIn-chip ${filtro === f.clave ? 'EIn-chip-on' : ''}"
                    data-filtro="${f.clave}">
                ${f.texto}<b class="EIn-chip-num">${contar(f.clave)}</b>
            </button>
        `).join('');
    }

    // HTML de la tarjeta de un incidente
    function tarjetaHTML(i) {
        const resuelto = Boolean(i.resuelto);

        // Abajo a la derecha: botón "Resolver" o etiqueta "Resuelto"
        const accion = resuelto
            ? `<span class="EIn-insignia EIn-insignia-resuelto">Resuelto ${formatearFecha(i.resuelto)}</span>`
            : `<button class="EIn-btn EIn-btn-sm" data-resolver="${i.indice}">Resolver</button>`;

        // La solución solo se muestra en los resueltos que la tengan
        const solucion = resuelto && i.solucion
            ? `<p class="EIn-inc-sol"><b>Solución:</b> ${escapar(i.solucion)}</p>`
            : '';

        return `
            <div class="EIn-inc ${resuelto ? 'EIn-inc-resuelto' : ''}">

                <div class="EIn-inc-cab">
                    <div class="EIn-inc-textos">
                        <b class="EIn-inc-equipo">${escapar(i.equipo)}</b>
                        <small class="EIn-inc-codigo">${escapar(i.codigo)}</small>
                    </div>
                    <span class="EIn-etiqueta">${escapar(i.tipo)}</span>
                </div>

                <p class="EIn-inc-desc">${escapar(i.descripcion)}</p>
                <span class="EIn-inc-quien">${escapar(i.estudiante)} · ${escapar(i.matricula)}</span>
                ${solucion}

                <div class="EIn-inc-pie">
                    <span>${formatearFecha(i.fecha)} · ${i.origen}</span>
                    ${accion}
                </div>

            </div>`;
    }

function dibujarLista() {
        const texto = busqueda.toLowerCase();

        const visibles = incidentes
            .map((i, indice) => ({ ...i, indice }))
            .filter((i) => {
                const datos = `${i.equipo} ${i.codigo} ${i.estudiante} ${i.matricula}`.toLowerCase();
                return estadoDe(i) === filtro && (!texto || datos.includes(texto));
            });

        $('EIn-lista').innerHTML = visibles.length
            ? visibles.map(tarjetaHTML).join('')
            : '<div class="EIn-vacio">No hay incidentes en esta vista.</div>';

        if ($('EIn-contador')) {
            $('EIn-contador').textContent =
                `Mostrando ${visibles.length} de ${incidentes.length} incidentes`;
        }
    }

    function dibujar() {
        dibujarFiltros();
        dibujarLista();
    }


    /* ==========================================================
       5. VENTANAS (MODALES)
       ========================================================== */

    function cerrarModales() {
        $('EIn-fondo').classList.remove('EIn-on');
        $('EIn-modalNuevo').classList.remove('EIn-on');
        $('EIn-modalResolver').classList.remove('EIn-on');
    }

    // ---------- Ventana "Registrar incidente" ----------

    function abrirNuevo() {
        $('EIn-descripcion').value = '';
        $('EIn-okNuevo').disabled = true;     // se activa al escribir la descripción

        $('EIn-fondo').classList.add('EIn-on');
        $('EIn-modalNuevo').classList.add('EIn-on');
    }

    function registrarIncidente() {
        // La opción del equipo viene como: "Equipo · Código · Estudiante · Matrícula"
        const [equipo, codigo, estudiante, matricula] = $('EIn-equipo').value.split(' · ');

        incidentes.unshift({
            equipo, codigo, estudiante, matricula,
            tipo: $('EIn-tipo').value,
            fecha: HOY,
            origen: 'Revisión posterior',
            descripcion: $('EIn-descripcion').value.trim(),
            resuelto: null,
            solucion: '',
        });

        filtro = 'abierto';
        dibujar();
        cerrarModales();
        mostrarAviso('Incidente registrado');
    }

    // ---------- Ventana "Marcar como resuelto" ----------

    function abrirResolver(indice) {
        seleccionado = indice;
        const i = incidentes[indice];

        $('EIn-resolverResumen').innerHTML =
            `<b class="EIn-resumen-titulo">${escapar(i.equipo)} · ${escapar(i.codigo)}</b>` +
            `<small class="EIn-resumen-texto">${escapar(i.tipo)} · ${escapar(i.estudiante)} (${escapar(i.matricula)})</small>`;

        $('EIn-solucion').value = '';

        $('EIn-fondo').classList.add('EIn-on');
        $('EIn-modalResolver').classList.add('EIn-on');
    }

    function confirmarResolucion() {
        incidentes[seleccionado].resuelto = HOY;
        incidentes[seleccionado].solucion = $('EIn-solucion').value.trim();

        dibujar();
        cerrarModales();
        mostrarAviso('Incidente marcado como resuelto');
    }


    /* ==========================================================
       6. EVENTOS (qué pasa cuando el usuario hace clic o escribe)
       ========================================================== */

    // Un solo "oyente" de clics para toda la página
    document.addEventListener('click', (e) => {
        const objetivo = e.target;
        let boton;

        // Cambiar de filtro
        if ((boton = objetivo.closest('[data-filtro]'))) {
            filtro = boton.dataset.filtro;
            dibujar();
            return;
        }

        // Botón "Resolver" de una tarjeta
        if ((boton = objetivo.closest('[data-resolver]'))) {
            abrirResolver(Number(boton.dataset.resolver));
            return;
        }

        // Cerrar: tocar el fondo oscuro o un botón con data-cerrar
        if (objetivo.id === 'EIn-fondo' || objetivo.closest('[data-cerrar]')) {
            cerrarModales();
            return;
        }

        if (objetivo.closest('#EIn-btnNuevo'))    { abrirNuevo(); return; }
        if (objetivo.closest('#EIn-okNuevo'))     { registrarIncidente(); return; }
        if (objetivo.closest('#EIn-okResolver'))  { confirmarResolucion(); return; }
    });

    // El botón "Registrar" solo se activa si hay descripción
    $('EIn-descripcion').addEventListener('input', (e) => {
        $('EIn-okNuevo').disabled = !e.target.value.trim();
    });

    // Buscador
    $('EIn-buscar').addEventListener('input', (e) => {
        busqueda = e.target.value;
        dibujarLista();
    });


    /* ==========================================================
       7. ARRANQUE
       ========================================================== */

    dibujar();
});