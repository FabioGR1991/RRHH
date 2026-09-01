/* --- HISTORIAL DE SOLICITUDES RRHH CON AUTO-REFRESCO --- */

let pollingIntervalRRHH = null;

document.addEventListener('DOMContentLoaded', () => {
    // Carga inicial al cargar la página
    cargarMisSolicitudes();

    // Iniciar actualización automática en segundo plano
    iniciarPollingSolicitudes();
});

function iniciarPollingSolicitudes() {
    detenerPollingSolicitudes();

    // Ejecuta la consulta automáticamente cada 5000 ms (5 segundos)
    pollingIntervalRRHH = setInterval(() => {
        // Solo actualiza si la pestaña del navegador está activa y visible
        if (!document.hidden) {
            cargarMisSolicitudes(true);
        }
    }, 5000);
}

function detenerPollingSolicitudes() {
    if (pollingIntervalRRHH) {
        clearInterval(pollingIntervalRRHH);
        pollingIntervalRRHH = null;
    }
}

async function cargarMisSolicitudes(silencioso = false) {
    try {
        // Preservar elementos seleccionados antes de recargar
        const prevSeleccionados = Array.from(document.querySelectorAll('.item-check:checked')).map(cb => String(cb.value));

        const response = await fetch('/api/solicitudes');
        if (!response.ok) {
            throw new Error(`Error en servidor: ${response.status}`);
        }

        const data = await response.json();
        const tbody = document.getElementById('tablaMisSolicitudes');
        
        if (!tbody) {
            console.error("No se encontró el elemento #tablaMisSolicitudes en el HTML.");
            return;
        }

        if (!Array.isArray(data) || data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No has generado solicitudes todavía.</td></tr>`;
            if (typeof actualizarSeleccion === 'function') actualizarSeleccion();
            return;
        }

        let html = '';

        data.forEach(sol => {
            const esAprobado = sol.estado === 'PROCESADO' || sol.estado === 'APROBADO';
            const isChecked = (esAprobado && prevSeleccionados.includes(String(sol.id))) ? 'checked' : '';
            
            let estadoHtml = '';
            let checkboxHtml = '';

            if (esAprobado) {
                // Si está aprobado, habilitamos el checkbox
                checkboxHtml = `<input class="form-check-input item-check" type="checkbox" value="${sol.id}" ${isChecked} onchange="actualizarSeleccion()">`;
                
                estadoHtml = `
                    <div class="d-flex align-items-center gap-2">
                        <span class="badge bg-success py-2 px-2">
                            <i class="bi bi-check-circle me-1"></i> Aprobado
                        </span>
                        <button type="button" class="btn btn-sm btn-outline-primary py-1 px-2" onclick="verDetalleAprobado(${sol.id})" title="Ver credenciales procesadas">
                            <i class="bi bi-folder2-open"></i>
                        </button>
                    </div>
                `;
            } else {
                // Si no está aprobado, el checkbox estará deshabilitado o no visible
                checkboxHtml = `<input class="form-check-input item-check" type="checkbox" value="${sol.id}" disabled title="Solo se pueden exportar solicitudes aprobadas">`;
                
                estadoHtml = `
                    <span class="badge bg-warning text-dark py-2 px-2">
                        <i class="bi bi-hourglass-split me-1"></i> Pendiente IT
                    </span>
                `;
            }

            const fnBadge = sol.es_fuera_de_nomina ? '<span class="badge bg-warning text-dark me-1">FN</span>' : '';
            const perfilMostrar = sol.perfil_ad || sol.perfil || 'Operador';

            html += `
                <tr class="${!esAprobado ? 'opacity-75' : ''}">
                    <td class="ps-3">
                        ${checkboxHtml}
                    </td>
                    <td class="fw-bold text-secondary">#${sol.id}</td>
                    <td>
                        <div class="fw-bold">${sol.nombre || ''} ${sol.apellido || ''}</div>
                        <div class="small text-muted">DNI: ${sol.dni || 'N/A'}</div>
                    </td>
                    <td>
                        <div>${fnBadge}${sol.legajo || 'N/A'}</div>
                        <div class="small text-muted"><i class="bi bi-telephone me-1"></i>${sol.telefono || 'N/A'}</div>
                    </td>
                    <td><span class="small text-muted">${sol.reporta_a || 'N/A'}</span></td>
                    <td><span class="badge bg-secondary">${perfilMostrar}</span></td>
                    <td>${estadoHtml}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;

        if (typeof actualizarSeleccion === 'function') {
            actualizarSeleccion();
        }
    } catch (err) {
        console.error('Error al cargar historial:', err);
        if (!silencioso) {
            const tbody = document.getElementById('tablaMisSolicitudes');
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-3 text-danger"><i class="bi bi-exclamation-triangle me-1"></i> Error al cargar el historial. Revisa la consola (F12).</td></tr>`;
            }
        }
    }
}

/* --- VER DETALLE Y CREDENCIALES --- */
async function verDetalleAprobado(id) {
    const container = document.getElementById('detalleCredencialesContent');
    if (!container) return;
    
    container.innerHTML = `<div class="text-center py-4 text-muted"><span class="spinner-border spinner-border-sm me-1"></span> Cargando credenciales...</div>`;

    const modalElement = document.getElementById('modalVerCredencialesRRHH');
    if (!modalElement) return;
    
    const modal = new bootstrap.Modal(modalElement);
    modal.show();

    try {
        const response = await fetch(`/api/solicitudes/${id}/preview`);
        const data = await response.json();

        if (response.ok) {
            if (data.es_fuera_de_nomina) {
                container.innerHTML = `
                    <div class="col-12">
                        <div class="alert alert-info py-2 small mb-2">
                            <i class="bi bi-info-circle-fill me-1"></i> <strong>Empleado Fuera de Nómina:</strong> No posee cuentas de Active Directory, Gmail corporativo ni VPN.
                        </div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-bold small mb-1">Usuario NEO</label>
                        <input type="text" class="form-control form-control-sm" value="${data.usuario_neo || '-'}" readonly>
                        <div class="form-text text-muted font-monospace small">Clave: <span class="badge bg-light text-dark border">${data.clave_neo || '-'}</span></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-bold small mb-1">Posición X-Lite</label>
                        <input type="text" class="form-control form-control-sm" value="${data.posicion_xlite || '-'}" readonly>
                        <div class="form-text text-muted font-monospace small">Clave: <span class="badge bg-light text-dark border">${data.clave_xlite || '-'}</span></div>
                    </div>
                `;
            } else {
                container.innerHTML = `
                    <div class="col-md-6">
                        <label class="form-label fw-bold small mb-1">Usuario AD / Correo</label>
                        <input type="text" class="form-control form-control-sm" value="${data.usuario_ad || '-'}" readonly>
                        <div class="form-text text-muted font-monospace small">Clave predeterminada: <span class="badge bg-light text-dark border">${data.clave_ad_mail || '-'}</span></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-bold small mb-1">Mail Corporativo</label>
                        <input type="text" class="form-control form-control-sm" value="${data.email || '-'}" readonly>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-bold small mb-1">Usuario Fortinet (VPN 100 F)</label>
                        <input type="text" class="form-control form-control-sm" value="${data.usuario_fortinet || '-'}" readonly>
                        <div class="form-text text-muted font-monospace small">Clave (DNI): <span class="badge bg-light text-dark border">${data.clave_fortinet || '-'}</span></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-bold small mb-1">Usuario NEO</label>
                        <input type="text" class="form-control form-control-sm" value="${data.usuario_neo || '-'}" readonly>
                        <div class="form-text text-muted font-monospace small">Clave: <span class="badge bg-light text-dark border">${data.clave_neo || '-'}</span></div>
                    </div>
                    <div class="col-md-12">
                        <label class="form-label fw-bold small mb-1">Dispositivo posición (X-Lite)</label>
                        <input type="text" class="form-control form-control-sm" value="${data.posicion_xlite || '-'}" readonly>
                        <div class="form-text text-muted font-monospace small">Clave: <span class="badge bg-light text-dark border">${data.clave_xlite || '-'}</span></div>
                    </div>
                `;
            }
        } else {
            container.innerHTML = `<div class="alert alert-danger">Error: ${data.detail || 'No se pudieron recuperar las credenciales'}</div>`;
        }
    } catch (err) {
        container.innerHTML = `<div class="alert alert-danger">Error de conexión con el servidor.</div>`;
    }
}