# 🚀 ROADMAP: Plataforma de Aprovisionamiento y Automatización de Altas (RRHH - IT)

Plataforma web para la automatización y gestión del ciclo de vida de usuarios (Onboarding / IAM), implementando un modelo de **Aprobación de Dos Pasos (Dual Authorization)** entre **Recursos Humanos** (Solicitud) e **IT** (Previsualización, Aprobación y Ejecución).

---

## 📋 Resumen del Flujo Operativo

```text
[ RRHH ]                                         [ EQUIPO DE IT ]
   │                                                    │
   ▼                                                    ▼
1. Completa Formulario                              3. Revisa Solicitudes Pendientes
   (Nombre, Apellido, DNI, Legajo,                      │
    Reporta a, Perfil)                                  ▼
   │                                                4. Click en "Previsualizar Credenciales"
   ▼                                                   (Genera propuesta de User, Mail, Pass)
2. Guarda Solicitud en estado "PENDIENTE"               │
                                                        ├─► Opción A: Modificar/Ajustar propuesta
                                                        └─► Opción B: Confirmar y Ejecutar
                                                        │
                                                        ▼
                                                    5. Se dispara orchestrator.py
                                                       (Crea AD, Gmail, NeoTel, FortiClient)
                                                        │
                                                        ▼
                                                    6. Se genera Output (Dashboard + PDF + Mails)

                                                    📌 Fase 1: Arquitectura Base y Modelado de Datos
Objetivo: Definir la estructura del proyecto en VS Code, la base de datos para la cola de pendientes y los esquemas de datos del sistema.

[x] ~~1.1. Inicialización del Proyecto~~

[x] ~~Configurar repositorio Git y entorno virtual en Python (FastAPI + Pydantic).~~

[x] ~~Crear la estructura modular de carpetas (/config, /src/controllers, /src/core, /src/services, /src/models).~~

[x] ~~Definir el archivo .env.example con las variables de entorno necesarias (claves API, credenciales SSH/LDAP, servidor SMTP).~~

[x] ~~1.2. Base de Datos & Cola de Pendientes~~

[x] ~~Configurar la base de datos (SQLite para desarrollo / PostgreSQL para producción).~~

[x] ~~Diseñar el modelo SolicitudAlta con los siguientes estados: PENDIENTE, EN_PROCESO, COMPLETADO, ERROR_PARCIAL, RECHAZADO.~~

[x] ~~Modificación sobre la marcha: Incorporación del campo reporta_a (Responsable/Jefe directo) en el modelo y esquema Pydantic.~~

[x] ~~Implementar el sistema de Roles y Permisos (Rol RRHH vs. Rol IT / SISTEMAS con autenticación por Cookies/Sesión).~~

🧩 Fase 2: Desarrollo de Módulos de Integración (Servicios Independientes)
Objetivo: Desarrollar y probar por separado la conexión y lógica con cada una de las plataformas externas.

[ ] 2.1. Módulo Core de Lógica de Negocio (src/core/generator.py)

[ ] Implementar la función de resolución de nombres de usuario y sanitización de caracteres especiales/acentos.

[ ] Lógica de resolución de colisiones (alternativas fgomez, fabiogomez, fabiogomez1).

[ ] Implementar la transformación lógica de Legajo para NeoTel (1339 -> 3339).

[ ] Nuevo: Función de generación de propuesta de credenciales (Username, Email, Passwords temporales) para previsualización.

[ ] 2.2. Módulo Active Directory (src/services/ad_service.py)

[ ] Conexión vía LDAP/WinRM/PowerShell.

[ ] Verificación pre-ejecución: Consultar si el username candidato ya existe en AD.

[ ] Creación de usuario en la OU correspondiente según el perfil asignado.

[ ] Asignación de contraseña temporal y flag de "Cambiar contraseña en el próximo inicio de sesión".

[ ] Vinculación a grupos de seguridad (GPO).

[ ] 2.3. Módulo Google Admin / Gmail (src/services/gadmin_service.py)

[ ] Integración con la API Google Workspace Admin SDK mediante Service Account.

[ ] Verificación pre-ejecución: Consultar si la casilla corporativa ya existe en Workspace.

[ ] Creación de la casilla corporativa (@tandemtech.com.ar), asignación de licencias y contraseña inicial.

[ ] 2.4. Módulo NeoTel (src/services/neotel_service.py)

[ ] Telemarketer: Alta de usuario con legajo transformado (3339) y contraseña igual a DNI.

[ ] Extracción de QR: Capturar y almacenar la imagen en Base64/PNG del token 2FA devuelto por la API.

[ ] Posición (Softphone): Alta de posición NombreApellido, contraseña fija Tandem123, selección de protocolo SIP y reescritura del parámetro de configuración reemplazando nat='no' por nat='yes'.

[ ] 2.5. Módulo FortiClient / FortiGate (src/services/fortinet_service.py)

[ ] Automatización vía SSH/Paramiko o REST API en FortiGate.

[ ] Creación de usuario local con contraseña igual a DNI, asignación del mail institucional para 2FA y adición al grupo de túnel VPN.

⚙️ Fase 3: El Orquestador de Altas (src/core/orchestrator.py)
Objetivo: Crear el motor principal que ejecuta las llamadas a todos los servicios en el orden correcto y gestiona los fallos.

[ ] 3.1. Fase de Pre-Validación (Dry-Run / Preview)

[ ] Generar payload de vista previa antes de la ejecución real.

[ ] 3.2. Flujo Secuencial de Ejecución Real

[ ] Ejecutar alta confirmada con los datos previsualizados/ajustados por IT (AD -> Gmail -> NeoTel -> FortiClient).

[ ] 3.3. Manejo de Transacciones y Errores (Rollback/Logging)

[ ] Captura de excepciones por módulo y registro en BD de estado ERROR_PARCIAL o COMPLETADO.

📄 Fase 4: Generación de Documentos y Notificaciones (Outputs)
Objetivo: Generar la documentación para el empleado y disparar las notificaciones por correo.

[ ] 4.1. Generador de Manual / PDF de Bienvenida (src/services/pdf_service.py)

[ ] Renderizar dinámicamente credenciales confirmadas, guías de acceso y QR de NeoTel.

[ ] 4.2. Módulo de Notificaciones por Email (src/services/mail_service.py)

[ ] Enviar correo al responsable en reporta_a y al empleado con el PDF adjunto.

[ ] 4.3. Exportación a CSV (src/controllers/exports.py)

[ ] Descarga de reporte ordenado en formato .csv con las credenciales creadas.

💻 Fase 5: Desarrollo de la Interfaz Web (Frontend)
Objetivo: Construir la plataforma visual adaptada a los roles de RRHH e IT.

[x] ~~5.1. Vista de RRHH (config/templates/rrhh_form.html)~~

[x] ~~Formulario de solicitud (Nombre, Apellido, DNI, Legajo, Reporta a, Perfil).~~

[x] ~~Tabla de historial de solicitudes enviadas y sincronización automática (polling cada 5s).~~

[ ] 5.2. Vista de IT (config/templates/sistemas_dashboard.html)

[x] ~~Dashboard básico y verificación de autenticación de rol SISTEMAS.~~

[ ] Nuevo: Modal de Previsualización de Credenciales (muestra propuesta de Username, Passwords, Mail y permite edición manual previa).

[ ] Botón interactivo 🚀 Confirmar y Ejecutar Alta con barra de progreso en vivo.

[ ] Vista previa final de credenciales creadas + Botones para copiar texto individualmente, descargar PDF y exportar CSV.

🛡️ Fase 6: Pruebas, Seguridad y Auditoría
Objetivo: Asegurar el entorno, validar credenciales y vincular con monitoreo SIEM.

[ ] 6.1. Pruebas de Estrés y Casos Borde

[ ] 6.2. Auditoría en Wazuh SIEM

[ ] 6.3. Despliegue en Producción (Deployment)

📂 Estructura de Directorios del Proyecto

app_rrhh/
├── config/
│   ├── database.py
│   ├── settings.py
│   └── templates/
│       ├── login.html
│       ├── rrhh_form.html
│       └── sistemas_dashboard.html
├── src/
│   ├── controllers/
│   ├── core/
│   │   ├── generator.py
│   │   └── orchestrator.py
│   ├── models/
│   │   ├── solicitud.py
│   │   └── usuario.py
│   └── services/
├── storage/
│   ├── pdfs/
│   └── qrs/
├── .env.example
├── .gitignore
├── requirements.txt
├── ROADMAP.md
└── main.py