# 🚀 ROADMAP: Plataforma de Aprovisionamiento y Automatización de Altas (RRHH - IT)

Plataforma web para la automatización y gestión del ciclo de vida de usuarios (Onboarding / IAM), implementando un modelo de **Aprobación de Dos Pasos (Dual Authorization)** entre **Recursos Humanos** (Solicitud) e **IT** (Previsualización, Aprobación y Ejecución).

---

## 📋 Resumen del Flujo Operativo

```text
[ RRHH ]                                                [ EQUIPO DE IT ]
   │                                                           │
   ▼                                                           ▼
1. Completa Formulario / Carga Masiva (Excel)           3. Revisa Solicitudes Pendientes
   (Nombre, Apellido, DNI, Legajo,                             │
    Reporta a, Perfil, Fuera de Nómina)                        ▼
   │                                                    4. Click en "Previsualizar Credenciales"
   ▼                                                       (Genera propuesta de User, Mail, Pass, Neo, Forti)
2. Guarda Solicitud en estado "PENDIENTE"                      │
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

[x] ~~Definir el archivo .env.example y gestión de entorno con las variables necesarias (claves API, credenciales SSH/LDAP, servidor SMTP).~~

[x] ~~Configuración y estabilización de dependencias base (requirements.txt: FastAPI, Uvicorn, SQLAlchemy, Pandas, OpenPyXL, Python-Multipart).~~

[x] ~~1.2. Base de Datos & Cola de Pendientes~~

[x] ~~Configurar la base de datos (SQLite para desarrollo / PostgreSQL para producción).~~

[x] ~~Diseñar el modelo SolicitudAlta con los estados: PENDIENTE, EN_PROCESO, COMPLETADO, ERROR_PARCIAL, RECHAZADO.~~

[x] ~~Incorporación del campo reporta_a (Responsable/Jefe directo) y flag es_fuera_de_nomina en modelo y esquemas Pydantic.~~

[x] ~~Validaciones y restricciones de unicidad a nivel base de datos (DNI y Legajo únicos).~~

[x] ~~Implementar el sistema de Roles y Permisos (Rol RRHH vs. Rol IT / SISTEMAS con autenticación por Cookies/Sesión).~~

🧩 Fase 2: Desarrollo de Módulos de Integración (Servicios Independientes)
Objetivo: Desarrollar y probar por separado la conexión y lógica con cada una de las plataformas externas.

[x] ~~2.1. Módulo Core de Lógica de Negocio (src/core/generator.py)~~

[x] ~~Implementar la función de resolución de nombres de usuario y sanitización de caracteres especiales/acentos.~~

[x] ~~Lógica de resolución de colisiones (alternativas fgomez, fabiogomez, fabiogomez1).~~

[x] ~~Implementar la transformación lógica de Legajo para NeoTel.~~

[x] ~~Función de generación de propuesta de credenciales (Username, Email, Passwords temporales, NeoTel, FortiClient, X-Lite alineados a la planilla operativa) para previsualización.~~

[x] ~~Desacoplamiento de rutas en src/controllers/solicitudes_controller.py para limpiar main.py y estandarizar respuestas API.~~

[x] ~~Endpoint /api/solicitudes/siguiente-legajo-fn para autogeneración incremental de legajos para personal Fuera de Nómina (Rango 7000+).~~

[ ] 2.2. Módulo Active Directory (src/services/ad_service.py)

[ ] Conexión vía LDAP/WinRM/PowerShell.

[ ] Verificación pre-ejecución: Consultar si el username candidato ya existe en AD.

[ ] Creación de usuario en la OU correspondiente según el perfil asignado.

[ ] Asignación de contraseña temporal predeterminada (T4nd3m**) y flag de "Cambiar contraseña en el próximo inicio de sesión".

[ ] Vinculación a grupos de seguridad (GPO).

[ ] 2.3. Módulo Google Admin / Gmail (src/services/gadmin_service.py)

[ ] Integración con la API Google Workspace Admin SDK mediante Service Account.

[ ] Verificación pre-ejecución: Consultar si la casilla corporativa ya existe en Workspace.

[ ] Creación de la casilla corporativa (@tandemtech.com.ar), asignación de licencias y contraseña inicial (T4nd3m**).

[ ] 2.4. Módulo NeoTel (src/services/neotel_service.py)

[ ] Telemarketer: Alta de usuario con legajo transformado y contraseña igual a DNI.

[ ] Extracción de QR: Capturar y almacenar la imagen en Base64/PNG del token 2FA devuelto por la API.

[ ] Posición (Softphone / X-Lite): Alta de posición NombreApellido, contraseña fija Tandem123, selección de protocolo SIP y reescritura del parámetro nat='yes'.

[ ] 2.5. Módulo FortiClient / FortiGate (src/services/fortinet_service.py)

[ ] Automatización vía SSH/Paramiko o REST API en FortiGate.

[ ] Creación de usuario local NombreApellido con contraseña igual a DNI, asignación del mail institucional para 2FA y adición al grupo de túnel VPN.

⚙️ Fase 3: El Orquestador de Altas (src/core/orchestrator.py)
Objetivo: Crear el motor principal que ejecuta las llamadas a todos los servicios en el orden correcto y gestiona los fallos.

[x] ~~3.1. Fase de Pre-Validación (Dry-Run / Preview)~~

[x] ~~Generar payload de vista previa antes de la ejecución real mediante /api/solicitudes/{id}/preview.~~

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

[ ] 4.3. Exportación a CSV / Excel (src/controllers/exports.py)

[ ] Descarga de reporte ordenado en formato .csv / .xlsx coincidente con el esquema de la planilla interna.

💻 Fase 5: Desarrollo de la Interfaz Web (Frontend)
Objetivo: Construir la plataforma visual adaptada a los roles de RRHH e IT.

[x] ~~5.1. Vista de RRHH (config/templates/rrhh_form.html)~~

[x] ~~Formulario de solicitud individual (Nombre, Apellido, DNI, Legajo, Reporta a, Perfil, Fuera de Nómina).~~

[x] ~~Automatización de campo Legajo / Perfil al marcar el switch "Empleado Fuera de Nómina".~~

[x] ~~Módulo de Carga Masiva desde archivo Excel (.xlsx, .xls) con interfaz Drag & Drop y botón de descarga de plantilla especificada.~~

[x] ~~Parseo dinámico con filtrado y mapeo de perfiles permitidos (Operador, Administrativo, Supervisión, Gerencia).~~

[x] ~~Feedback de errores granulares de carga masiva: tarjeta con scroll que lista número de fila Excel, nombre de postulante y motivo del fallo (ej. DNI/Legajo duplicado).~~

[x] ~~Tabla de historial de solicitudes enviadas por RRHH y sincronización automática en tiempo real (polling cada 5s).~~

[ ] 5.2. Vista de IT (config/templates/sistemas_dashboard.html)

[x] ~~Dashboard básico y verificación de autenticación de rol SISTEMAS.~~

[x] ~~Modal de Previsualización de Credenciales (muestra propuesta de Mail Corp, Usuario AD, Usuario/Clave Fortinet, Usuario/Clave NeoTel y Dispositivo X-Lite).~~

[ ] Botón interactivo 🚀 Confirmar y Ejecutar Alta con feedback visual / barra de progreso en vivo.

[ ] Vista previa final de credenciales creadas + Botones para copiar texto individualmente, descargar PDF y exportar CSV.

🛡️ Fase 6: Pruebas, Seguridad y Auditoría
Objetivo: Asegurar el entorno, validar credenciales y vincular con monitoreo SIEM.

[ ] 6.1. Pruebas de Estrés y Casos Borde

[ ] 6.2. Auditoría en Wazuh SIEM

[ ] 6.3. Despliegue en Producción (Deployment)

📂 Estructura de Directorios del Proyecto

RRHH
├── ROADMAP.md
├── config
│   ├── database.py
│   ├── settings.py
│   └── templates
│       ├── login.html
│       ├── rrhh_form.html
│       └── sistemas_dashboard.html
├── main.py
├── requirements.txt
├── src
│   ├── controllers
│   │   └── solicitudes_controller.py
│   ├── core
│   │   └── generator.py
│   ├── models
│   │   ├── solicitud.py
│   │   └── usuario.py
│   └── services
│       ├── ad_service
│       ├── email_service.py
│       ├── fortinet_service
│       ├── gadmin_service
│       ├── neo_service
│       ├── pdf_service.py
│       └── xlite_service
└── storage
    ├── pdfs
    └── qrs
(venv) 