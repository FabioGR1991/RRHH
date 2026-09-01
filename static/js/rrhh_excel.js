/* ==========================================
   SELECCIÓN Y EXPORTACIÓN DE TABLA A EXCEL
   ========================================== */

function toggleSelectAll(master) {
    // Solo seleccionar/desseleccionar casillas HABILITADAS (Aprobadas)
    const checkboxes = document.querySelectorAll('.item-check:not(:disabled)');
    checkboxes.forEach(cb => cb.checked = master.checked);
    actualizarSeleccion();
}

function actualizarSeleccion() {
    const checkboxesHabilitados = document.querySelectorAll('.item-check:not(:disabled)');
    const seleccionados = document.querySelectorAll('.item-check:checked');
    const btnExportar = document.getElementById('btnExportarSeleccionados');
    const cantLabel = document.getElementById('cantSeleccionados');
    const checkAll = document.getElementById('checkAll');

    if (cantLabel) {
        cantLabel.textContent = seleccionados.length;
    }
    
    if (btnExportar) {
        if (seleccionados.length > 0) {
            btnExportar.classList.remove('d-none');
        } else {
            btnExportar.classList.add('d-none');
        }
    }

    if (checkAll) {
        if (checkboxesHabilitados.length > 0) {
            checkAll.disabled = false;
            checkAll.checked = checkboxesHabilitados.length === seleccionados.length;
        } else {
            checkAll.checked = false;
            checkAll.disabled = true; // Deshabilita el check general si no hay registros aprobados
        }
    }
}

async function exportarSeleccionados() {
    const seleccionados = Array.from(document.querySelectorAll('.item-check:checked')).map(cb => parseInt(cb.value));

    if (seleccionados.length === 0) return;

    const btnExportar = document.getElementById('btnExportarSeleccionados');
    if (btnExportar) btnExportar.disabled = true;

    try {
        const response = await fetch('/api/solicitudes/exportar-excel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: seleccionados })
        });

        if (!response.ok) throw new Error('Error al generar la planilla Excel en el servidor.');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Reporte_Solicitudes_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        alert('No se pudo descargar el archivo Excel: ' + err.message);
    } finally {
        if (btnExportar) btnExportar.disabled = false;
    }
}


/* ==========================================
   CARGA MASIVA VÍA EXCEL (SHEETJS)
   ========================================== */

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length) leerExcel(files[0]);
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) leerExcel(e.target.files[0]);
        });
    }
});

function leerExcel(archivo) {
    const reader = new FileReader();
    reader.onload = function(e) {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        const jsonData = XLSX.utils.sheet_to_json(firstSheet, { defval: "" });

        if (!jsonData.length) {
            renderizarResultadoMasivo(0, ["El archivo Excel está vacío."]);
            return;
        }

        datosExcelProcesados = jsonData.map((row) => {
            let perfilIngresado = String(row.Perfil || row["Perfil AD"] || '').trim();
            const perfilValido = typeof PERFILES_PERMITIDOS !== 'undefined' 
                ? PERFILES_PERMITIDOS.find(p => p.toLowerCase() === perfilIngresado.toLowerCase()) 
                : null;
            const perfilFinal = perfilValido || "Operador";

            return {
                nombre: String(row.Nombre || '').trim(),
                apellido: String(row.Apellido || '').trim(),
                dni: String(row.DNI || '').trim(),
                legajo: String(row.Legajo || '').trim(),
                telefono: String(row.Telefono || row["Teléfono"] || '').trim(),
                reporta_a: String(row["Reporta A"] || row.ReportaA || '').trim(),
                perfil_ad: perfilFinal,
                es_fuera_de_nomina: false
            };
        });

        const cantRegistros = document.getElementById('cantRegistros');
        if (cantRegistros) cantRegistros.textContent = datosExcelProcesados.length;

        document.getElementById('previewMasivo')?.classList.remove('d-none');
        document.getElementById('alertMsgMasivo')?.classList.add('d-none');
    };
    reader.readAsBuffer ? reader.readAsBuffer(archivo) : reader.readAsArrayBuffer(archivo);
}

function limpiarExcel() {
    if (typeof datosExcelProcesados !== 'undefined') {
        datosExcelProcesados = [];
    }
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
    document.getElementById('previewMasivo')?.classList.add('d-none');
}

async function procesarCargaMasiva() {
    const btn = document.getElementById('btnProcesarMasivo');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Procesando solicitudes...`;
    }

    let correctos = 0;
    let errores = [];

    for (let i = 0; i < datosExcelProcesados.length; i++) {
        const item = datosExcelProcesados[i];
        const numFila = i + 2;

        try {
            const res = await fetch('/api/solicitudes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(item)
            });

            const data = await res.json();

            if (res.ok) {
                correctos++;
            } else {
                const motivo = data.detail || "Error al procesar la solicitud.";
                errores.push(`Fila ${numFila} (${item.nombre} ${item.apellido}): ${motivo}`);
            }
        } catch (err) {
            errores.push(`Fila ${numFila} (${item.nombre} ${item.apellido}): Error de conexión con el servidor.`);
        }
    }

    if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i class="bi bi-upload me-2"></i>Procesar y Enviar a IT`;
    }

    renderizarResultadoMasivo(correctos, errores);
    if (typeof cargarMisSolicitudes === 'function') cargarMisSolicitudes();
}

function renderizarResultadoMasivo(correctos, errores) {
    const alertBox = document.getElementById('alertMsgMasivo');
    if (!alertBox) return;

    alertBox.classList.remove('d-none');

    const totalFallos = errores.length;
    const tipoAlerta = totalFallos === 0 ? 'success' : (correctos > 0 ? 'warning' : 'danger');

    let html = `
        <div class="fw-bold mb-1">
            <i class="bi ${totalFallos === 0 ? 'bi-check-circle-fill' : 'bi-exclamation-triangle-fill'} me-1"></i>
            Proceso terminado: ${correctos} exitosas, ${totalFallos} con error.
        </div>
    `;

    if (totalFallos > 0) {
        html += `
            <div class="mt-2 text-start">
                <div class="fw-bold small text-danger mb-1">Detalle de inconvenientes:</div>
                <ul class="list-group list-group-flush border rounded bg-white small" style="max-height: 180px; overflow-y: auto;">
        `;

        errores.forEach(err => {
            html += `<li class="list-group-item list-group-item-danger py-1 px-2 text-wrap small"><sup>•</sup> ${err}</li>`;
        });

        html += `
                </ul>
            </div>
        `;
    }

    alertBox.className = `alert alert-${tipoAlerta} p-3 mb-3`;
    alertBox.innerHTML = html;

    if (totalFallos === 0) {
        limpiarExcel();
    }
}

function descargarPlantilla() {
    const wb = XLSX.utils.book_new();

    const wsData = [
        ["Nombre", "Apellido", "DNI", "Legajo", "Telefono", "Reporta A", "Perfil"],
        ["Juan", "Pérez", "38999888", "1234", "1155443322", "Carlos Gómez", "Operador"],
        ["María", "López", "40111222", "1235", "1166778899", "Ana Martinez", "Administrativo"],
        ["Pedro", "Sosa", "35444555", "1236", "1122334455", "Roberto Diaz", "Supervisión"],
        ["Laura", "Gimenez", "30999111", "1237", "1133221100", "Directorio", "Gerencia"]
    ];

    const ws = XLSX.utils.aoa_to_sheet(wsData);
    XLSX.utils.book_append_sheet(wb, ws, "Plantilla_Altas");
    XLSX.writeFile(wb, "Plantilla_Altas_RRHH.xlsx");
}