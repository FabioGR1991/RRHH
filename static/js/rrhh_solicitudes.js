/* ===================================================================
   ARCHIVO: rrhh_solicitudes.js
   DESCRIPCIÓN: Historial de solicitudes, tabla dinámica, modal de credenciales y polling.
   =================================================================== */

let pollingIntervalRRHH = null;

document.addEventListener('DOMContentLoaded', () => {
    cargarMisSolicitudes();
    iniciarPollingSolicitudes();
});

function iniciarPollingSolicitudes() {
    detenerPollingSolicitudes();
    pollingIntervalRRHH = setInterval(() => {
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
    const tbody = document.getElementById('tablaMisSolicitudes');
    const totalBadge = document.getElementById('totalSolicitudesContador');
    const resumenPaginacion = document.getElementById('resumenSolicitudesPaginacion');

    try {
        const prevSeleccionados = Array.from(document.querySelectorAll('.item-check:checked')).map(cb => String(cb.value));
        const response = await fetch('/api/solicitudes');
        if (!response.ok) throw new Error(`Error en servidor: ${response.status}`);

        const data = await response.json();
        if (!tbody) return;

        if (!Array.isArray(data) || data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No has generado solicitudes todavía.</td></tr>`;
            if (totalBadge) totalBadge.textContent = '0';
            if (resumenPaginacion) resumenPaginacion.textContent = 'Mostrando 0 solicitudes';
            if (typeof actualizarSeleccion === 'function') actualizarSeleccion();
            return;
        }

        if (totalBadge) totalBadge.textContent = data.length;
        if (resumenPaginacion) resumenPaginacion.textContent = `Mostrando 1 a ${data.length} de ${data.length} solicitudes`;

        let html = '';

        data.forEach(sol => {
            const esAprobado = sol.estado === 'PROCESADO' || sol.estado === 'APROBADO';
            const isChecked = (esAprobado && prevSeleccionados.includes(String(sol.id))) ? 'checked' : '';
            const fnBadge = sol.es_fuera_de_nomina 
                ? '<small class="text-danger fw-semibold d-block" style="font-size: 0.72rem;">F. Nómina</small>' 
                : `<small class="text-muted d-block">LEG-${sol.legajo || 'N/A'}</small>`;
            const perfilMostrar = sol.perfil_ad || sol.perfil || 'Operador';
            const correoGenerado = sol.email || `${(sol.nombre || '').charAt(0).toLowerCase()}${(sol.apellido || '').toLowerCase()}@tandemtech.com.ar`;

            html += `
                <tr class="${!esAprobado ? 'opacity-75' : ''}">
                    <td class="text-center">
                        ${esAprobado ? `
                            <input class="form-check-input item-check m-0" type="checkbox" value="${sol.id}" ${isChecked} onchange="actualizarSeleccion()">
                        ` : `
                            <input class="form-check-input item-check m-0" type="checkbox" value="${sol.id}" disabled title="Solo se pueden exportar solicitudes aprobadas">
                        `}
                    </td>
                    <td>
                        <div class="fw-semibold text-dark">${sol.nombre || ''} ${sol.apellido || ''}</div>
                        <small class="text-muted" style="font-size: 0.72rem;">${correoGenerado}</small>
                    </td>
                    <td>
                        <div class="fw-medium">${sol.dni || 'N/A'}</div>
                        ${fnBadge}
                    </td>
                    <td>
                        <span class="small text-muted text-truncate d-inline-block" style="max-width: 140px;" title="${sol.reporta_a || 'N/A'}">${sol.reporta_a || 'N/A'}</span>
                    </td>
                    <td>
                        <span class="badge bg-secondary bg-opacity-10 text-secondary border-0">${perfilMostrar}</span>
                    </td>
                    <td>
                        ${esAprobado ? `
                            <span class="badge-aprobado">
                                <i class="bi bi-check-circle-fill"></i> Aprobado
                            </span>
                        ` : `
                            <span class="badge-pendiente">
                                <i class="bi bi-hourglass-split"></i> Pendiente IT
                            </span>
                        `}
                    </td>
                    <td class="text-end">
                        <button class="btn-action-icon" onclick="verDetalleAprobado(${sol.id})" title="Ver Credenciales y Detalle" type="button">
                            <i class="bi bi-key-fill"></i>
                        </button>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
        if (typeof actualizarSeleccion === 'function') actualizarSeleccion();
    } catch (err) {
        console.error('Error al cargar historial:', err);
        if (!silencioso && tbody) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-3 text-danger"><i class="bi bi-exclamation-triangle me-1"></i> Error al cargar el historial. Revisa la consola (F12).</td></tr>`;
        }
    }
}

async function verDetalleAprobado(id) {
    const container = document.getElementById('detalleCredencialesContent');
    if (!container) return;

    container.innerHTML = `
        <div class="text-center py-5 text-muted">
            <div class="spinner-border text-primary spinner-border-sm mb-2" role="status"></div>
            <div>Recuperando credenciales y perfiles de acceso...</div>
        </div>
    `;

    const modalElement = document.getElementById('modalVerCredencialesRRHH');
    if (!modalElement) return;

    const modal = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
    modal.show();

    try {
        const response = await fetch(`/api/solicitudes/${id}/preview`);
        const data = await response.json();

        if (response.ok) {
            const esFN = data.es_fuera_de_nomina;
            const nombreCompleto = `${data.nombre || 'Colaborador'} ${data.apellido || ''}`.trim();
            const legajoTexto = esFN ? 'Personal Fuera de Nómina' : `Legajo #${data.legajo || 'N/A'}`;
            const perfilTexto = data.perfil_ad || 'Operador';
            const upnUsuario = data.usuario_ad || (data.email ? data.email.split('@')[0] : 'N/A');

            let htmlBanner = `
                <div class="d-flex align-items-center justify-content-between p-3 rounded-3 mb-3 bg-light border">
                    <div>
                        <span class="badge ${data.estado === 'PENDIENTE' ? 'bg-warning text-dark' : 'bg-success bg-opacity-10 text-success'} mb-1">
                            <i class="bi ${data.estado === 'PENDIENTE' ? 'bi-hourglass-split' : 'bi-check-circle-fill'} me-1"></i>
                            ${data.estado === 'PENDIENTE' ? 'En Proceso IT' : 'Proceso Concluido'}
                        </span>
                        <h6 class="fw-bold mb-0 text-dark">${nombreCompleto}</h6>
                        <small class="text-muted">${perfilTexto} • ${legajoTexto}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-primary" id="btnCopiarCredencialesModal" onclick="copiarCredencialesJson()">
                        <i class="bi bi-clipboard me-1"></i> Copiar Todo
                    </button>
                </div>
            `;

            let htmlCards = '';
            if (esFN) {
                htmlCards = `
                    <div class="col-12">
                        <div class="alert alert-info py-2 small mb-2 d-flex align-items-center">
                            <i class="bi bi-info-circle-fill fs-5 me-2"></i>
                            <div><strong>Empleado Fuera de Nómina:</strong> No posee cuentas de Active Directory corporativo ni VPN. Se generan accesos específicos para NeoTel y X-Lite.</div>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">USUARIO NEO</span>
                            <div class="fw-bold text-dark font-monospace">${data.usuario_neo || '-'}</div>
                            <small class="text-muted">Clave: <strong class="badge bg-white text-dark border">${data.clave_neo || '-'}</strong></small>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">POSICIÓN X-LITE</span>
                            <div class="fw-bold text-dark font-monospace">${data.posicion_xlite || '-'}</div>
                            <small class="text-muted">Clave: <strong class="badge bg-white text-dark border">${data.clave_xlite || '-'}</strong></small>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">RESPONSABLE ASIGNADO</span>
                            <div class="fw-semibold text-dark">${data.reporta_a || '-'}</div>
                            <small class="text-muted">Reporte Operativo Directo</small>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">MODALIDAD CONTRACTUAL</span>
                            <div class="fw-semibold text-secondary"><i class="bi bi-briefcase me-1"></i> Contractor / Fuera de Nómina</div>
                            <small class="text-muted">Legajo Asignado: ${data.legajo || '7000+'}</small>
                        </div>
                    </div>
                `;
            } else {
                htmlCards = `
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">USUARIO DE RED (UPN)</span>
                            <div class="fw-bold text-dark font-monospace">${upnUsuario}</div>
                            <small class="text-muted">Active Directory Domain User</small>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">CONTRASEÑA PROVISIONAL</span>
                            <div class="d-flex align-items-center justify-content-between">
                                <span class="fw-bold text-dark font-monospace">${data.clave_ad_mail || '-'}</span>
                                <span class="badge bg-warning text-dark" style="font-size: 0.65rem;">Requiere cambio</span>
                            </div>
                            <small class="text-muted">Válida para primer inicio</small>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">BUZÓN OFFICE 365 / CORREO</span>
                            <div class="fw-bold text-dark text-truncate">${data.email || '-'}</div>
                            <small class="text-muted">Licencia Corporativa asignada</small>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">GRUPO DE SEGURIDAD / PERFIL</span>
                            <div class="fw-bold text-dark">${perfilTexto}</div>
                            <small class="text-muted">OU y Políticas asignadas</small>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">VPN FORTINET (100F)</span>
                            <div class="fw-bold text-dark font-monospace">${data.usuario_fortinet || '-'}</div>
                            <small class="text-muted">Clave (DNI): <strong class="badge bg-white text-dark border">${data.clave_fortinet || '-'}</strong></small>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">USUARIO NEO</span>
                            <div class="fw-bold text-dark font-monospace">${data.usuario_neo || '-'}</div>
                            <small class="text-muted">Clave: <strong class="badge bg-white text-dark border">${data.clave_neo || '-'}</strong></small>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">POSICIÓN X-LITE</span>
                            <div class="fw-bold text-dark font-monospace">${data.posicion_xlite || '-'}</div>
                            <small class="text-muted">Clave: <strong class="badge bg-white text-dark border">${data.clave_xlite || '-'}</strong></small>
                        </div>
                    </div>
                    <div class="col-12 col-md-6">
                        <div class="credential-card">
                            <span class="key-tag">SUPERVISOR ASIGNADO</span>
                            <div class="fw-semibold text-dark">${data.reporta_a || '-'}</div>
                            <small class="text-muted">Líder directo de reporte</small>
                        </div>
                    </div>
                `;
            }

            window._credencialesActualesModal = data;

            container.innerHTML = `
                ${htmlBanner}
                <div class="row g-3">
                    ${htmlCards}
                </div>
            `;
        } else {
            container.innerHTML = `<div class="alert alert-danger mb-0"><i class="bi bi-exclamation-octagon-fill me-2"></i> ${data.detail || 'No se pudieron recuperar las credenciales'}</div>`;
        }
    } catch (err) {
        container.innerHTML = `<div class="alert alert-danger mb-0"><i class="bi bi-exclamation-triangle-fill me-2"></i> Error de conexión con el servidor.</div>`;
    }
}

function copiarCredencialesJson() {
    const data = window._credencialesActualesModal;
    if (!data) return;

    let texto = `FICHA DE CREDENCIALES - ${data.nombre || ''} ${data.apellido || ''}\n`;
    texto += `Legajo: ${data.legajo || 'N/A'}\n`;
    texto += `Perfil: ${data.perfil_ad || ''}\n`;
    texto += `Reporta a: ${data.reporta_a || ''}\n`;
    texto += `------------------------------------\n`;
    if (data.es_fuera_de_nomina) {
        texto += `Modalidad: Fuera de Nómina (Contractor)\n`;
        texto += `Usuario NEO: ${data.usuario_neo || '-'}\nClave NEO: ${data.clave_neo || '-'}\n`;
        texto += `Posición X-Lite: ${data.posicion_xlite || '-'}\nClave X-Lite: ${data.clave_xlite || '-'}\n`;
    } else {
        texto += `Usuario AD: ${data.usuario_ad || '-'}\n`;
        texto += `Clave Inicial: ${data.clave_ad_mail || '-'}\n`;
        texto += `Correo: ${data.email || '-'}\n`;
        texto += `VPN Fortinet: ${data.usuario_fortinet || '-'}\nClave VPN: ${data.clave_fortinet || '-'}\n`;
        texto += `Usuario NEO: ${data.usuario_neo || '-'}\nClave NEO: ${data.clave_neo || '-'}\n`;
        texto += `Posición X-Lite: ${data.posicion_xlite || '-'}\nClave X-Lite: ${data.clave_xlite || '-'}\n`;
    }

    if (navigator.clipboard) {
        navigator.clipboard.writeText(texto).then(() => {
            const btn = document.getElementById('btnCopiarCredencialesModal');
            if (btn) {
                const original = btn.innerHTML;
                btn.innerHTML = '<i class="bi bi-check-lg me-1"></i> ¡Copiado!';
                btn.classList.replace('btn-outline-primary', 'btn-success');
                setTimeout(() => {
                    btn.innerHTML = original;
                    btn.classList.replace('btn-success', 'btn-outline-primary');
                }, 2000);
            }
        });
    }
}

function imprimirFichaCredenciales() {
    window.print();
}
