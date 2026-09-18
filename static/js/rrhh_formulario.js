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
    const legajoReqMark = document.getElementById('legajoReqMark');

    let tomSelectInstance = null;

    const SUPERVISORES_HABILITADOS = [
        {"nombre": "Juan Pérez", "email": "juan.perez@tandemtech.com.ar", "rol": "Gerente de Operaciones"},
        {"nombre": "María González", "email": "maria.gonzalez@tandemtech.com.ar", "rol": "Team Leader Contact Center"},
        {"nombre": "Carlos Rodríguez", "email": "carlos.rodriguez@tandemtech.com.ar", "rol": "Planificador WFM"},
        {"nombre": "Ana Martínez", "email": "ana.martinez@tandemtech.com.ar", "rol": "Supervisora Turno Mañana"},
        {"nombre": "Lucas Gómez", "email": "lucas.gomez@tandemtech.com.ar", "rol": "Jefe de Sistemas"}
    ];

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

        if (window.TomSelect) {
            tomSelectInstance = new TomSelect('#reporta_a', {
                options: options,
                valueField: 'value',
                labelField: 'text',
                searchField: ['text', 'value', 'subtext'],
                create: false,
                maxOptions: 50,
                placeholder: 'Escriba para buscar supervisor directo...',
                dropdownParent: 'body',
                render: {
                    option: function(data, escape) {
                        return `<div class="py-1">
                            <div class="fw-semibold text-dark">${escape(data.text)}</div>
                            ${data.subtext ? `<small class="text-muted">${escape(data.subtext)}</small>` : ''}
                        </div>`;
                    }
                }
            });
        }
    }

    inicializarSelectorSupervisores();

    // Manejo del switch Fuera de Nómina
    if (checkboxFN && inputLegajo) {
        checkboxFN.addEventListener('change', () => {
            if (checkboxFN.checked) {
                inputLegajo.value = '';
                inputLegajo.disabled = true;
                inputLegajo.removeAttribute('required');
                inputLegajo.placeholder = 'Autogenerado 7000+ (FN)';
                if (legajoReqMark) legajoReqMark.classList.add('d-none');
            } else {
                inputLegajo.disabled = false;
                inputLegajo.setAttribute('required', 'required');
                inputLegajo.placeholder = 'Ej. 1339';
                if (legajoReqMark) legajoReqMark.classList.remove('d-none');
            }
        });
    }

    // Submit del Formulario
    altaForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (alertMsg) alertMsg.classList.add('d-none');

        const dniVal = inputDni ? inputDni.value.trim() : '';
        const legajoVal = inputLegajo ? inputLegajo.value.trim() : '';
        const telefonoVal = inputTelefono ? inputTelefono.value.trim() : '';
        const reportaAVal = tomSelectInstance ? tomSelectInstance.getValue() : (selectReportaA ? selectReportaA.value : '');
        const esFueraNomina = checkboxFN ? checkboxFN.checked : false;
        const nombreVal = document.getElementById('nombre')?.value.trim() || '';
        const apellidoVal = document.getElementById('apellido')?.value.trim() || '';
        const perfilVal = selectPerfil ? selectPerfil.value : '';

        // Validaciones
        if (!nombreVal || !apellidoVal) {
            mostrarError('Por favor, ingrese el nombre y apellido.');
            return;
        }
        if (!/^\d{8}$/.test(dniVal)) {
            mostrarError('El DNI debe tener exactamente 8 dígitos numéricos.');
            inputDni?.focus();
            return;
        }
        if (!esFueraNomina && !/^\d{4}$/.test(legajoVal)) {
            mostrarError('El Legajo debe tener exactamente 4 dígitos numéricos.');
            inputLegajo?.focus();
            return;
        }
        if (!/^\d{6,10}$/.test(telefonoVal)) {
            mostrarError('El Teléfono debe tener entre 6 y 10 dígitos numéricos.');
            inputTelefono?.focus();
            return;
        }
        if (!perfilVal) {
            mostrarError('Debe seleccionar un perfil Active Directory.');
            selectPerfil?.focus();
            return;
        }
        if (!reportaAVal) {
            mostrarError('Debe seleccionar un supervisor de la lista.');
            tomSelectInstance?.focus();
            return;
        }

        const btnSubmit = document.getElementById('btnSubmitAlta');
        const originalBtnHtml = btnSubmit ? btnSubmit.innerHTML : '';
        if (btnSubmit) {
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Procesando...';
        }

        const payload = {
            nombre: nombreVal,
            apellido: apellidoVal,
            dni: dniVal,
            legajo: esFueraNomina ? '' : legajoVal,
            telefono: telefonoVal,
            reporta_a: reportaAVal,
            perfil_ad: perfilVal,
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
                    alertMsg.className = "alert alert-success d-flex align-items-center mb-3";
                    alertMsg.innerHTML = '<i class="bi bi-check-circle-fill fs-5 me-2"></i><div><strong>¡Solicitud enviada!</strong> El alta se ha registrado exitosamente.</div>';
                    alertMsg.classList.remove('d-none');
                }
                altaForm.reset();
                if (tomSelectInstance) tomSelectInstance.clear();
                if (inputLegajo) {
                    inputLegajo.disabled = false;
                    inputLegajo.setAttribute('required', 'required');
                    inputLegajo.placeholder = 'Ej. 1339';
                }
                if (legajoReqMark) legajoReqMark.classList.remove('d-none');
                if (typeof cargarMisSolicitudes === 'function') cargarMisSolicitudes();
            } else {
                mostrarError(resData.detail || 'Error al enviar la solicitud.');
            }
        } catch (err) {
            mostrarError('Error de conexión con el servidor.');
        } finally {
            if (btnSubmit) {
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = originalBtnHtml;
            }
        }
    });

    function mostrarError(mensaje) {
        if (!alertMsg) return;
        alertMsg.className = "alert alert-danger d-flex align-items-center mb-3";
        alertMsg.innerHTML = `<i class="bi bi-exclamation-triangle-fill fs-5 me-2"></i><div>${mensaje}</div>`;
        alertMsg.classList.remove('d-none');
    }
});
