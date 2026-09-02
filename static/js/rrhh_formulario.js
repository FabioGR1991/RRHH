/* ==========================================
   FORMULARIO DE ALTA INDIVIDUAL
   ========================================== */
document.addEventListener('DOMContentLoaded', () => {
    const altaForm = document.getElementById('altaForm');
    if (!altaForm) return;

    const inputDni = document.getElementById('dni');
    const inputLegajo = document.getElementById('legajo');
    const inputTelefono = document.getElementById('telefono');
    const selectReportaA = document.getElementById('reporta_a');
    const selectPerfil = document.getElementById('perfil_ad');
    const checkboxFN = document.getElementById('esFueraNomina');
    const alertMsg = document.getElementById('alertMsg');

    let tomSelectInstance = null;

    // Lista por defecto de supervisores habilitados
    const SUPERVISORES_HABILITADOS = [
        {"nombre": "Juan Pérez", "email": "juan.perez@tandemtech.com.ar", "rol": "Gerente de Operaciones"},
        {"nombre": "María González", "email": "maria.gonzalez@tandemtech.com.ar", "rol": "Team Leader Contact Center"},
        {"nombre": "Carlos Rodríguez", "email": "carlos.rodriguez@tandemtech.com.ar", "rol": "Planificador WFM"},
        {"nombre": "Ana Martínez", "email": "ana.martinez@tandemtech.com.ar", "rol": "Supervisora Turno Mañana"},
        {"nombre": "Lucas Gómez", "email": "lucas.gomez@tandemtech.com.ar", "rol": "Jefe de Sistemas"}
    ];

    // Inicializar TomSelect y cargar los supervisores
    async function inicializarSelectorSupervisores() {
        if (!selectReportaA) return;

        let lista = SUPERVISORES_HABILITADOS;

        try {
            const res = await fetch('/api/solicitudes/reportantes/buscar?q=');
            if (res.ok) {
                const data = await res.json();
                if (Array.isArray(data) && data.length > 0) {
                    lista = data;
                }
            }
        } catch (err) {
            console.warn('Usando lista de supervisores local');
        }

        // Formatear opciones para TomSelect
        const options = lista.map(sup => {
            const email = typeof sup === 'string' ? sup : sup.email;
            const nombre = typeof sup === 'object' && sup.nombre ? sup.nombre : email;
            const rol = typeof sup === 'object' && sup.rol ? sup.rol : '';

            return {
                value: email,
                text: `${nombre} (${email})`,
                subtext: rol
            };
        });

        // Inicializar TomSelect con buscador dinámico
        tomSelectInstance = new TomSelect('#reporta_a', {
            options: options,
            valueField: 'value',
            labelField: 'text',
            searchField: ['text', 'value', 'subtext'],
            create: false, // Bloquea ingresar texto libre no listado
            maxOptions: 50,
            placeholder: 'Escriba para buscar supervisor...',
            dropdownParent: 'body', // Flota el desplegable por encima sin empujar/tapar el diseño
            render: {
                option: function(data, escape) {
                    return `<div>
                        <div class="fw-bold">${escape(data.text)}</div>
                        ${data.subtext ? `<div class="small text-muted">${escape(data.subtext)}</div>` : ''}
                    </div>`;
                }
            }
        });
    }

    inicializarSelectorSupervisores();

    // Manejo del switch "Fuera de Nómina"
    if (checkboxFN && inputLegajo) {
        checkboxFN.addEventListener('change', () => {
            if (checkboxFN.checked) {
                inputLegajo.value = '';
                inputLegajo.disabled = true;
                inputLegajo.removeAttribute('required');
            } else {
                inputLegajo.disabled = false;
                inputLegajo.setAttribute('required', 'required');
            }
        });
    }

    altaForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (alertMsg) alertMsg.classList.add('d-none');

        const dniVal = inputDni ? inputDni.value.trim() : '';
        const legajoVal = inputLegajo ? inputLegajo.value.trim() : '';
        const telefonoVal = inputTelefono ? inputTelefono.value.trim() : '';
        const reportaAVal = tomSelectInstance ? tomSelectInstance.getValue() : '';
        const esFueraNomina = checkboxFN ? checkboxFN.checked : false;

        // --- VALIDACIONES DE CAMPOS ---
        
        // 1. DNI (8 dígitos exactos)
        if (!/^\d{8}$/.test(dniVal)) {
            mostrarError('El DNI debe tener exactamente 8 dígitos numéricos.');
            inputDni?.focus();
            return;
        }

        // 2. Legajo (4 dígitos exactos, solo si no es Fuera de Nómina)
        if (!esFueraNomina && !/^\d{4}$/.test(legajoVal)) {
            mostrarError('El Legajo debe tener exactamente 4 dígitos numéricos.');
            inputLegajo?.focus();
            return;
        }

        // 3. Teléfono (entre 6 y 10 dígitos)
        if (!/^\d{6,10}$/.test(telefonoVal)) {
            mostrarError('El Teléfono debe tener entre 6 y 10 dígitos numéricos.');
            inputTelefono?.focus();
            return;
        }

        // 4. Validar supervisor seleccionado
        if (!reportaAVal) {
            mostrarError('Debe seleccionar un supervisor de la lista.');
            tomSelectInstance?.focus();
            return;
        }

        const payload = {
            nombre: document.getElementById('nombre').value.trim(),
            apellido: document.getElementById('apellido').value.trim(),
            dni: dniVal,
            legajo: esFueraNomina ? '' : legajoVal,
            telefono: telefonoVal,
            reporta_a: reportaAVal,
            perfil_ad: selectPerfil ? selectPerfil.value : '',
            es_fuera_de_nomina: esFueraNomina
        };

        try {
            const response = await fetch('/api/solicitudes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const resData = await response.json();

            if (response.ok) {
                if (alertMsg) {
                    alertMsg.className = "alert alert-success";
                    alertMsg.innerHTML = '<i class="bi bi-check-lg me-2"></i>Solicitud enviada con éxito a IT.';
                    alertMsg.classList.remove('d-none');
                }
                altaForm.reset();
                if (tomSelectInstance) tomSelectInstance.clear();
                if (inputLegajo) inputLegajo.disabled = false;
                if (selectPerfil) selectPerfil.disabled = false;
                if (typeof cargarMisSolicitudes === 'function') cargarMisSolicitudes();
            } else {
                mostrarError(resData.detail || 'Error al enviar la solicitud.');
            }
        } catch (err) {
            mostrarError('Error de conexión con el servidor.');
        }
    });

    function mostrarError(mensaje) {
        if (!alertMsg) return;
        alertMsg.className = "alert alert-danger";
        alertMsg.textContent = mensaje;
        alertMsg.classList.remove('d-none');
    }
});