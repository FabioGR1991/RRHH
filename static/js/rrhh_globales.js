/* ==========================================
   VARIABLES GLOBALES Y CONFIGURACIÓN BASE
   ========================================== */
const PERFILES_PERMITIDOS = ["Operador", "Administrativo", "Supervisión", "Gerencia"];

let checkboxFN = null;
let inputLegajo = null;
let selectPerfil = null;

let legajoPrevio = '';
let perfilPrevio = '';
let datosExcelProcesados = [];

document.addEventListener('DOMContentLoaded', () => {
    checkboxFN = document.getElementById('es_fuera_de_nomina') || document.getElementById('esFueraNomina');
    inputLegajo = document.getElementById('legajo');
    selectPerfil = document.getElementById('perfil_ad');

    if (typeof cargarMisSolicitudes === 'function') {
        cargarMisSolicitudes();
    }
});
