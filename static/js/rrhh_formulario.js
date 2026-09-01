/* ==========================================
   FORMULARIO DE ALTA INDIVIDUAL
   ========================================== */
document.addEventListener('DOMContentLoaded', () => {
    const altaForm = document.getElementById('altaForm');
    if (!altaForm) return;

    const inputDni = document.getElementById('dni');
    const inputLegajo = document.getElementById('legajo');
    const inputTelefono = document.getElementById('telefono');
    const selectPerfil = document.getElementById('perfil_ad');
    const checkboxFN = document.getElementById('esFueraNomina');
    const alertMsg = document.getElementById('alertMsg');

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

        const payload = {
            nombre: document.getElementById('nombre').value.trim(),
            apellido: document.getElementById('apellido').value.trim(),
            dni: dniVal,
            legajo: esFueraNomina ? '' : legajoVal,
            telefono: telefonoVal,
            reporta_a: document.getElementById('reporta_a').value.trim(),
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