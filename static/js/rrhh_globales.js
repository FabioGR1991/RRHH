/* ==========================================
   VARIABLES GLOBALES Y CONFIGURACIÓN BASE
   ========================================== */
window.__RRHH_MODULAR_LOADED__ = true;

const PERFILES_PERMITIDOS = ["Operador", "Administrativo", "Supervisión", "Gerencia"];

let checkboxFN = null;
let inputLegajo = null;
let selectPerfil = null;

let legajoPrevio = '';
let perfilPrevio = '';
let datosExcelProcesados = [];

document.addEventListener('DOMContentLoaded', () => {
    checkboxFN = document.getElementById('esFueraNomina');
    inputLegajo = document.getElementById('legajo');
    selectPerfil = document.getElementById('perfil_ad');
});
