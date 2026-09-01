/* ==========================================
   FORMULARIO DE ALTA INDIVIDUAL
   ========================================== */
document.addEventListener('DOMContentLoaded', () => {
    const altaForm = document.getElementById('altaForm');
    if (!altaForm) return;

    altaForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const alertMsg = document.getElementById('alertMsg');
        if (alertMsg) alertMsg.classList.add('d-none');

        const payload = {
            nombre: document.getElementById('nombre').value,
            apellido: document.getElementById('apellido').value,
            dni: document.getElementById('dni').value,
            legajo: inputLegajo ? inputLegajo.value : '',
            telefono: document.getElementById('telefono').value,
            reporta_a: document.getElementById('reporta_a').value,
            perfil_ad: selectPerfil ? selectPerfil.value : '',
            es_fuera_de_nomina: checkboxFN ? checkboxFN.checked : false
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
                if (alertMsg) {
                    alertMsg.className = "alert alert-danger";
                    alertMsg.textContent = resData.detail || 'Error al enviar la solicitud.';
                    alertMsg.classList.remove('d-none');
                }
            }
        } catch (err) {
            if (alertMsg) {
                alertMsg.className = "alert alert-danger";
                alertMsg.textContent = 'Error de conexión con el servidor.';
                alertMsg.classList.remove('d-none');
            }
        }
    });
});
