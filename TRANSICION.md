```markdown
# TRANSICION.md

📐 **Manual de Transición y Traspaso de Proyecto: Portal Altas RRHH / IT**  
*Este documento establece la línea base técnica, la hoja de ruta y las directrices de entorno para la metodología de desarrollo basada en Stitch, Gemini y Antigravity.*

---

## 🔄 Flujo de Trabajo Integrado (Ciclo de Vida de Features)

Para cada nueva funcionalidad o modificación en el sistema, se seguirá estrictamente el siguiente pipeline secuencial:


```

[ 1. Stitch ] ➔ [ 2. Gemini ] ➔ [ 3. Antigravity ]
Maquetado / UI    Lógica & Backend    Testing & Despliegue

```

1. **Stitch (Diseño y UI):** Prototipado interactivo, layout y definición visual de componentes (dashboards, modales y tablas dinámicas).
2. **Gemini (Arquitectura y Código):** Reglas de negocio en FastAPI, modelos ORM/SQL, scripts JS cliente y lógica de carga masiva/validaciones.
3. **Antigravity (Automatización y DevOps):** Testing E2E con Playwright/Selenium, pruebas unitarias backend con Pytest, CI/CD y despliegues con Uvicorn/Docker.

---

## 📌 Estado Actual y Arquitectura

* **Propósito del Sistema:** Portal web para la gestión de solicitudes de altas de personal de RRHH y su integración operativa con IT (creación de cuentas, asignación de perfiles, legajos y credenciales).
* **Stack Tecnológico:**
  * **Frontend:** HTML5, CSS3, Bootstrap 5, Bootstrap Icons, JS ES6 modular, TomSelect (`dropdownParent: 'body'`) y SheetJS (`XLSX`).
  * **Backend:** Python con FastAPI (rutas `/api/solicitudes`, autenticación y archivos estáticos).
  * **Base de Datos / Fuentes:** Persistencia SQL/ORM e ingesta de CSVs locales como Data Source para legajos y supervisores.
* **Punto de Avance Actual:**
  * Formulario de alta individual con validaciones estrictas (DNI 8 dígitos, Legajo 4 dígitos / autogenerado 7000+ Fuera de Nómina, Teléfono 6-10 dígitos).
  * Selector dinámico TomSelect para supervisores con fallback a lista local.
  * Carga masiva via Drag & Drop de archivos Excel (`.xlsx`).
  * Panel derecho con tabla de solicitudes, filtro/selección masiva, exportación a Excel y modal de credenciales.

---

## 🎨 Capa 1: UI y Frontend para Stitch
*Pantallas y componentes a diseñar o re-maquetar en Stitch antes de implementar en código cliente:*

* **Pantalla de Detalle y Seguimiento de Solicitud:**
  * Vista detallada tipo timeline del flujo de aprobación (*RRHH ➔ IT ➔ Credenciales Generadas*).
* **Panel / Dashboard de IT:**
  * Interfaz para el operador de IT donde gestiona, aprueba o rechaza solicitudes pendientes y genera credenciales activas.
* **Módulo de Edición / Corrección de Errores en Carga Masiva:**
  * Interfaz de previsualización de planilla Excel donde filas con errores de validación (DNI duplicado, legajo inválido) se resalten en rojo y permitan edición in-situ.
* **Modal / Vista de Configuración de Supervisores:**
  * Pantalla para administrar el listado de supervisores (alta/baja de emails y roles) consumidos por el selector dinámico.

---

## 🧠 Capa 2: Lógica Central y Reglas para Gemini
*Estructura de API, reglas de negocio y endpoints que se mantendrán y refinarán directamente en el backend Python:*

* **Robustecimiento de Endpoints API:**
  * `GET /api/solicitudes/reportantes/buscar?q=`: Optimizar búsqueda, filtrado y paginación desde BD/CSV.
  * `POST /api/solicitudes`: Generación automática de legajo ($7000+$) en servidor para casos Fuera de Nómina.
  * `POST /api/solicitudes/masiva`: Procesamiento asíncrono y parseo backend de planillas Excel masivas.
* **Modelos de Base de Datos y Mapeo de Entidades:**
  * Estructura de tablas SQL para Solicitudes, Usuarios/Empleados, Credenciales y Supervisores.
  * Manejo de estados: `PENDIENTE`, `EN_PROCESO`, `APROBADO`, `RECHAZADO`.
* **Mapeo de Fuentes Externas (CSV/Excel):**
  * Lógica para hidratación de datos (*Data Hydration*) e ingesta/sincronización periódica de CSVs locales con la BD.
* **Validaciones de Negocio Backend:**
  * Garantizar unicidad de DNI y Legajo a nivel de API/BD para prevenir inconsistencias.

---

## 🤖 Capa 3: Tareas de Automatización para Antigravity
*Scripts, agentes autónomos y tareas repetitivas de verificación y despliegue a delegar:*

> ⚠️ **Especificación de Entorno Server:** Todos los scripts deben ejecutarse considerando el entorno de ejecución de Python (`uvicorn app.main:app`) y agentes de prueba E2E/Unitarios.

* **Pruebas Automatizadas (Testing):**
  * **Unit Tests (Backend):** Pruebas con `pytest` para validar respuestas de endpoints (DNI, payloads inválidos, comportamiento Fuera de Nómina).
  * **E2E / UI Tests:** Scripts automatizados con Playwright/Selenium simulando carga de formulario, TomSelect, Drag & Drop de Excel y alertas.
* **Pipelines de CI/CD:**
  * Verificación automática de calidad de código (`flake8`, `black`, chequeo de sintaxis JS).
  * Pipeline de integración para ejecutar pruebas unitarias tras cada commit a la rama principal.
* **Monitoreo y Despliegue:**
  * Agente de verificación para validar la integridad física de los archivos CSV locales.
  * Agente de despliegue para levantar el entorno en servidor/Docker (`uvicorn app.main:app --reload`) y ejecutar migraciones de BD automáticas.

```