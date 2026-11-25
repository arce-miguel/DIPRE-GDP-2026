/* ============================================================
   Scripts del panel del encargado.
   Cada bloque se activa solo si la página tiene los elementos
   que necesita, así un mismo archivo sirve para todas las páginas.
   Los datos vienen de Django (HTML ya renderizado o JSON); aquí
   solo hay comportamiento: abrir modales, filtrar y verificar.
   ============================================================ */

/* ---------- Principal: accesos rápidos y buscador de equipo ---------- */
document.addEventListener('DOMContentLoaded', () => {
    // Botones que solo llevan a otra página
    document.querySelectorAll('[data-ir]').forEach((boton) => {
        boton.addEventListener('click', () => { window.location.href = boton.dataset.ir; });
    });

    // Buscador de "Equipo disponible"
    const buscador = document.getElementById('buscar-equipo');
    if (!buscador) return;
    buscador.addEventListener('input', () => {
        const texto = buscador.value.trim().toLowerCase();
        document.querySelectorAll('[data-equipo]').forEach((fila) => {
            fila.style.display = fila.dataset.equipo.includes(texto) ? '' : 'none';
        });
    });
});


/* ---------- Tablas de préstamos y devoluciones: filtros, búsqueda y detalle ---------- */
document.addEventListener('DOMContentLoaded', () => {
    const tbody = document.querySelector('.EP-table tbody');
    if (!tbody) return;

    const botones = document.querySelectorAll('.EP-menus-btn-u');
    const buscador = document.getElementById('buscar-tabla');

    // El filtro inicial es el botón que viene marcado como "activo"
    const inicial = document.querySelector('.EP-menus-btn-u.activo');
    let filtro = inicial ? inicial.dataset.filtro : 'todos';

    // ¿Esta fila (o su detalle) pasa el filtro de estado?
    function pasaFiltro(fila) {
        if (filtro === 'todos') return true;
        if (filtro === 'por_devolver') return fila.dataset.devuelto === '0';
        return fila.dataset.estado === filtro;
    }

    function aplicar() {
        const texto = buscador ? buscador.value.trim().toLowerCase() : '';
        tbody.querySelectorAll('tr[data-estado]').forEach((fila) => {
            const visible = pasaFiltro(fila) && (!texto || fila.dataset.busqueda.includes(texto));
            fila.hidden = !visible;
            if (!visible && fila.classList.contains('detalle')) fila.classList.remove('abierta');
        });

        // Si hay filas pero el filtro las oculta todas, se avisa en vez de dejar la tabla vacía
        const filas = tbody.querySelectorAll('tr[data-estado]:not(.detalle)');
        const hayVisibles = Array.from(filas).some((fila) => !fila.hidden);
        let vacia = tbody.querySelector('tr.fila-vacia');
        if (filas.length && !hayVisibles) {
            if (!vacia) {
                vacia = document.createElement('tr');
                vacia.className = 'fila-vacia';
                const celda = document.createElement('td');
                celda.colSpan = document.querySelectorAll('.EP-table thead th').length || 1;
                celda.textContent = 'No hay resultados con este filtro.';
                vacia.appendChild(celda);
                tbody.appendChild(vacia);
            }
            vacia.hidden = false;
        } else if (vacia) {
            vacia.hidden = true;
        }
    }

    botones.forEach((btn) => {
        btn.addEventListener('click', () => {
            botones.forEach((b) => b.classList.remove('activo'));
            btn.classList.add('activo');
            filtro = btn.dataset.filtro;
            aplicar();
        });
    });
    if (buscador) buscador.addEventListener('input', aplicar);
    aplicar();

    // Clic en una fila: abre o cierra su detalle
    tbody.addEventListener('click', (e) => {
        // Si presionaron un botón, enlace o campo, no expandir
        if (e.target.closest('button, a, select, input')) return;

        const fila = e.target.closest('tr');
        if (!fila || fila.classList.contains('detalle')) return;

        const detalle = fila.nextElementSibling;
        if (!detalle || !detalle.classList.contains('detalle')) return;

        const estabaAbierta = detalle.classList.contains('abierta');

        // Cerrar las demás
        tbody.querySelectorAll('tr.detalle.abierta')
             .forEach((tr) => tr.classList.remove('abierta'));

        // Abrir esta (si estaba abierta, queda cerrada)
        if (!estabaAbierta) detalle.classList.add('abierta');
    });
});


/* ---------- Modal "Nuevo préstamo": verifica la matrícula en la BD ---------- */
document.addEventListener('DOMContentLoaded', () => {
    const btnNuevo  = document.getElementById('bNew');
    const veil      = document.getElementById('veil');
    const modal     = document.getElementById('modal');
    const btnCerrar = document.getElementById('mC');
    const btnOk     = document.getElementById('mOk');
    const btnVer    = document.getElementById('bVer');
    const fM        = document.getElementById('fM');
    const fN        = document.getElementById('fN');
    const fD        = document.getElementById('fD');
    const vRes      = document.getElementById('vRes');

    // Si esta página no tiene el modal, salimos sin error
    if (!btnNuevo || !veil || !modal || !fM) return;

    const MENSAJE_INICIAL = 'Verifica la matrícula para ver si tiene adeudos o incidentes.';

    // Muestra el resultado y activa/desactiva "Confirmar"
    function mostrar(clase, texto, permitir) {
        vRes.className = 'vres ' + clase;
        vRes.textContent = texto;
        btnOk.disabled = !permitir;
    }

    // Valor para <input type="datetime-local"> (hora local, sin zona)
    function aLocal(fecha) {
        const dos = (n) => String(n).padStart(2, '0');
        return `${fecha.getFullYear()}-${dos(fecha.getMonth() + 1)}-${dos(fecha.getDate())}` +
               `T${dos(fecha.getHours())}:${dos(fecha.getMinutes())}`;
    }

    function abrir() {
        modal.reset();
        fN.value = '';
        mostrar('', MENSAJE_INICIAL, false);

        // Por defecto el equipo se devuelve mañana a las 18:00
        const manana = new Date();
        manana.setDate(manana.getDate() + 1);
        manana.setHours(18, 0, 0, 0);
        fD.min = aLocal(new Date());
        fD.value = aLocal(manana);

        veil.classList.add('on');
        modal.classList.add('on');
        fM.focus();
    }

    function cerrar() {
        veil.classList.remove('on');
        modal.classList.remove('on');
    }

    btnNuevo.addEventListener('click', abrir);
    if (btnCerrar) btnCerrar.addEventListener('click', cerrar);
    veil.addEventListener('click', cerrar);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') cerrar();
    });

    // Verificar matrícula contra la base de datos
    async function verificar() {
        const matricula = fM.value.trim();
        if (!matricula) {
            mostrar('bad', 'Escribe el número de control.', false);
            return;
        }

        try {
            const respuesta = await fetch(
                `${modal.dataset.urlVerificar}?matricula=${encodeURIComponent(matricula)}`,
                { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
            const datos = await respuesta.json();

            fN.value = datos.encontrado ? datos.nombre : '';
            mostrar(datos.encontrado && datos.puede ? 'good' : 'bad', datos.mensaje,
                    datos.encontrado && datos.puede);
        } catch (error) {
            mostrar('bad', 'No se pudo verificar. Intenta de nuevo.', false);
        }
    }

    if (btnVer) btnVer.addEventListener('click', verificar);

    // Enter dentro del campo de matrícula verifica (sin enviar el formulario)
    fM.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            verificar();
        }
    });

    // Si cambian la matrícula, hay que verificar otra vez
    fM.addEventListener('input', () => {
        fN.value = '';
        mostrar('', MENSAJE_INICIAL, false);
    });
});


/* ---------- Modal "Registrar devolución" ---------- */
document.addEventListener('DOMContentLoaded', () => {
    const botonesDevolver = document.querySelectorAll('.btn-devolver1');
    const veil      = document.getElementById('veil-dev');
    const modal     = document.getElementById('modal-dev');
    const btnCerrar = document.getElementById('mC-dev');

    const campoDetalle      = document.getElementById('fDetalle-dev');
    const resumen           = document.getElementById('resumen-dev');
    const checkboxIncidente = document.getElementById('fInc-dev');
    const cajaIncidente     = document.getElementById('incBox-dev');
    const textoIncidente    = document.getElementById('fIncT-dev');

    if (!veil || !modal) return;

    function abrir(e) {
        e.preventDefault();
        const boton = e.currentTarget;

        // Rellenar el formulario con el equipo que se devuelve
        campoDetalle.value = boton.dataset.detalle;
        resumen.querySelector('b').textContent = boton.dataset.equipo;
        resumen.querySelector('small').textContent = boton.dataset.texto;

        // Limpiar el apartado de incidente
        checkboxIncidente.checked = false;
        cajaIncidente.style.display = 'none';
        textoIncidente.value = '';
        textoIncidente.required = false;

        veil.classList.add('on');
        modal.classList.add('on');
    }

    function cerrar() {
        veil.classList.remove('on');
        modal.classList.remove('on');
    }

    botonesDevolver.forEach((boton) => boton.addEventListener('click', abrir));
    if (btnCerrar) btnCerrar.addEventListener('click', cerrar);
    veil.addEventListener('click', cerrar);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') cerrar();
    });

    // El cuadro de incidente solo aparece (y es obligatorio) si marcan la casilla
    checkboxIncidente.addEventListener('change', () => {
        const hay = checkboxIncidente.checked;
        cajaIncidente.style.display = hay ? 'flex' : 'none';
        textoIncidente.required = hay;
        if (hay) textoIncidente.focus(); else textoIncidente.value = '';
    });
});


/* ---------- Incidentes: tarjetas con filtro y búsqueda ---------- */
document.addEventListener('DOMContentLoaded', () => {

    // Atajo para buscar elementos por su id
    const $ = (id) => document.getElementById(id);

    // Si esta página no tiene la lista de incidentes, salimos sin error
    if (!$('EIn-lista')) return;

    // Los incidentes vienen de la base de datos (json_script de Django)
    const incidentes = JSON.parse($('datos-incidentes').textContent);

    const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
                   'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

    // Los dos filtros
    const FILTROS = [
        { clave: 'abierto',  texto: 'Abiertos'  },
        { clave: 'resuelto', texto: 'Resueltos' },
    ];

    let filtro = 'abierto';   // filtro seleccionado
    let busqueda = '';        // texto escrito en el buscador

    // '2026-11-05' -> '05 nov'
    function formatearFecha(iso) {
        const [, mes, dia] = iso.split('-');
        return `${dia} ${MESES[Number(mes) - 1]}`;
    }

    // 'abierto' o 'resuelto'
    function estadoDe(incidente) {
        return incidente.abierta ? 'abierto' : 'resuelto';
    }

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
        const resuelto = !i.abierta;

        // Abajo a la derecha: botón "Atender" o etiqueta "Resuelto"
        const accion = resuelto
            ? `<span class="EIn-insignia EIn-insignia-resuelto">Resuelto ${i.resuelto ? formatearFecha(i.resuelto) : ''}</span>`
            : `<button class="EIn-btn EIn-btn-sm" data-resolver="${i.id}">${i.resuelta ? 'Saldar adeudo' : 'Resolver'}</button>`;

        // Cómo se resolvió, si ya hay algo registrado
        const solucion = i.solucion
            ? `<p class="EIn-inc-sol"><b>Solución:</b> ${escapar(i.solucion)}</p>`
            : '';

        const adeudo = i.adeudo_pendiente
            ? '<p class="EIn-inc-sol"><b>Adeudo pendiente</b> del solicitante</p>'
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
                <span class="EIn-inc-quien">${escapar(i.estudiante)}${i.matricula ? ' · ' + escapar(i.matricula) : ''}</span>
                ${solucion}${adeudo}

                <div class="EIn-inc-pie">
                    <span>${formatearFecha(i.fecha)} · ${escapar(i.origen)}</span>
                    ${accion}
                </div>

            </div>`;
    }

    function dibujarLista() {
        const texto = busqueda.toLowerCase();

        const visibles = incidentes.filter((i) => {
            const datos = `${i.equipo} ${i.codigo} ${i.estudiante} ${i.matricula}`.toLowerCase();
            return estadoDe(i) === filtro && (!texto || datos.includes(texto));
        });

        $('EIn-lista').innerHTML = visibles.length
            ? visibles.map(tarjetaHTML).join('')
            : '<div class="EIn-vacio">No hay incidentes en esta vista.</div>';
    }

    function dibujar() {
        dibujarFiltros();
        dibujarLista();
    }


    /* ---------- Ventanas (modales) ---------- */

    function cerrarModales() {
        $('EIn-fondo').classList.remove('EIn-on');
        $('EIn-modalNuevo').classList.remove('EIn-on');
        $('EIn-modalResolver').classList.remove('EIn-on');
    }

    function abrirNuevo() {
        $('EIn-descripcion').value = '';
        $('EIn-okNuevo').disabled = true;     // se activa al escribir la descripción

        $('EIn-fondo').classList.add('EIn-on');
        $('EIn-modalNuevo').classList.add('EIn-on');
    }

    function abrirResolver(id) {
        const i = incidentes.find((x) => x.id === id);
        if (!i) return;

        const formulario = $('EIn-modalResolver');
        formulario.action = formulario.dataset.url.replace('/0/', `/${id}/`);

        $('EIn-resolverResumen').innerHTML =
            `<b class="EIn-resumen-titulo">${escapar(i.equipo)} · ${escapar(i.codigo)}</b>` +
            `<small class="EIn-resumen-texto">${escapar(i.tipo)} · ${escapar(i.estudiante)}${i.matricula ? ' (' + escapar(i.matricula) + ')' : ''}</small>`;

        // Qué resoluciones tiene sentido ofrecer según el tipo de incidente
        const select = $('EIn-resolucion');
        select.innerHTML = i.opciones.map((o) =>
            `<option value="${escapar(o.clave)}">${escapar(o.texto)}</option>`).join('');
        select.disabled = i.resuelta;                         // el equipo ya se atendió
        $('EIn-campoResolucion').style.display = i.resuelta ? 'none' : '';

        // El apartado del adeudo solo aplica si el solicitante todavía debe
        $('EIn-campoSaldo').style.display = i.adeudo_pendiente ? '' : 'none';
        $('EIn-saldo').disabled = !i.adeudo_pendiente;
        $('EIn-saldo').value = '';

        $('EIn-fondo').classList.add('EIn-on');
        formulario.classList.add('EIn-on');
    }


    /* ---------- Eventos ---------- */

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

        if (objetivo.closest('#EIn-btnNuevo')) { abrirNuevo(); return; }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') cerrarModales();
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

    dibujar();
});

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('modalContactar');
    if (!modal) return;

    const titulo = document.getElementById('mcTitulo');
    const equipoEl = document.getElementById('mcEquipo');
    const subtituloEl = document.getElementById('mcSubtitulo');
    const mensajeEl = document.getElementById('mcMensaje');
    const btnCorreo = document.getElementById('mcBtnCorreo');
    const correoTexto = document.getElementById('mcCorreoTexto');
    const btnCopiar = document.getElementById('mcCopiar');

    function actualizarMailto() {
        const correo = btnCorreo.dataset.correo || '';
        const asunto = encodeURIComponent('Recordatorio de devolución de equipo - DIPRE');
        const cuerpo = encodeURIComponent(mensajeEl.value);
        btnCorreo.href = `mailto:${correo}?subject=${asunto}&body=${cuerpo}`;
    }

document.querySelectorAll('.btn-contactar').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation(); // Evita que el clic active el evento de la fila <tr>

            const { nombre, matricula, correo, equipo, codigo, limite, retraso } = btn.dataset;
            const primerNombre = nombre.split(' ')[0];

            titulo.textContent = `Contactar a ${nombre}`;
            equipoEl.textContent = `${equipo} · ${codigo}`;
            subtituloEl.textContent = `${matricula} · ${retraso}`;
            correoTexto.textContent = correo || 'Sin correo registrado';
            btnCorreo.dataset.correo = correo || '';

            mensajeEl.value = `Hola ${primerNombre}, te escribimos del área de préstamos de equipo. Tu préstamo de ${equipo} (${codigo}) venció el ${limite} (${retraso}). Por favor devuélvelo lo antes posible. Gracias.`;

            actualizarMailto();
            modal.hidden = false;
        });
    });

    mensajeEl.addEventListener('input', actualizarMailto);

    btnCopiar.addEventListener('click', () => {
        navigator.clipboard.writeText(mensajeEl.value);
        btnCopiar.textContent = '¡Copiado!';
        setTimeout(() => btnCopiar.textContent = 'Copiar mensaje', 2000);
    });

    document.getElementById('mcCerrar').addEventListener('click', () => modal.hidden = true);
    modal.addEventListener('click', e => { if (e.target === modal) modal.hidden = true; });
});
//modal de inventario o algo asi
// --- Modal Agregar Equipo (Inventario) ---
const modalInventario = document.getElementById('modalInventario');
const btnAgregarEquipo = document.getElementById('btnAgregarEquipo');

if (modalInventario && btnAgregarEquipo) {
    const formInventario = document.getElementById('formInventario');
    const miNombre = document.getElementById('miNombre');
    const miCodigo = document.getElementById('miCodigo');
    const miCancelar = document.getElementById('miCancelar');
    const miGuardar = document.getElementById('miGuardar');

    const validarInventario = () => {
        miGuardar.disabled = !(miNombre.value.trim() && miCodigo.value.trim());
    };

    btnAgregarEquipo.addEventListener('click', () => {
        formInventario.reset();
        validarInventario();
        modalInventario.hidden = false;
        miNombre.focus();
    });

    miNombre.addEventListener('input', validarInventario);
    miCodigo.addEventListener('input', validarInventario);
    miCancelar.addEventListener('click', () => modalInventario.hidden = true);
    modalInventario.addEventListener('click', (e) => {
        if (e.target === modalInventario) modalInventario.hidden = true;
    });
}
const modalEditEq = document.getElementById('modal-editar-equipo');

if (modalEditEq) {
    document.addEventListener('click', (e) => {
        const btnEditar = e.target.closest('.btn-editar-equipo');
        if (btnEditar) {
            document.getElementById('edit-inv-id').value = btnEditar.dataset.id;
            document.getElementById('edit-inv-nombre').value = btnEditar.dataset.nombre;
            document.getElementById('edit-inv-codigo').value = btnEditar.dataset.codigo;
            document.getElementById('edit-inv-categoria').value = btnEditar.dataset.categoria;
            document.getElementById('edit-inv-estado').value = btnEditar.dataset.estado;
            modalEditEq.hidden = false;
            document.getElementById('edit-inv-nombre').focus();
            return;
        }

        if (e.target === modalEditEq || e.target.closest('[data-cerrar="modal-editar-equipo"]')) {
            modalEditEq.hidden = true;
        }
    });
}