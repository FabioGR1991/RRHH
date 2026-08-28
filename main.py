"""
===================================================================
ARCHIVO: main.py
DESCRIPCIÓN: Punto de entrada principal de la aplicación FastAPI.
Maneja:
 - Inicialización de la App y creación de tablas en la Base de Datos.
 - Configuración Middleware de CORS.
 - Vistas HTML de navegación (Login, RRHH y Sistemas).
 - Endpoints generales (Login, Logout).
 - Inclusión de Routers/Módulos externos (solicitudes_controller).
===================================================================
"""

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.database import engine, Base, get_db
from src.models.solicitud import SolicitudAlta
from src.models.usuario import Usuario

# Importación del controlador modularizado de solicitudes
from src.controllers import solicitudes_controller

# Crear las tablas en la base de datos automáticamente al iniciar
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Plataforma de Aprovisionamiento RRHH - IT",
    description="API y Frontend para la gestión de altas de empleados.",
    version="1.0.0"
)

# --- CONFIGURACIÓN DE CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusión del router de solicitudes
app.include_router(solicitudes_controller.router)

templates = Jinja2Templates(directory="config/templates")


# --- ESQUEMAS PYDANTIC ---

class LoginRequest(BaseModel):
    email: str
    password: str

class SolicitudCreate(BaseModel):
    nombre: str
    apellido: str
    dni: str
    legajo: str
    perfil_ad: str
    reporta_a: str  # Campo para el responsable/jefe directo


# --- INICIALIZACIÓN DE DATOS ---

def init_db_users(db: Session):
    if not db.query(Usuario).first():
        users = [
            Usuario(email="rrhh@empresa.com", password_hash="rrhh123", nombre="Operador RRHH", rol="RRHH"),
            Usuario(email="sistemas@empresa.com", password_hash="admin123", nombre="Administrador IT", rol="SISTEMAS")
        ]
        db.add_all(users)
        db.commit()

@app.on_event("startup")
def startup_event():
    db = next(get_db())
    init_db_users(db)


# --- RUTAS DE NAVEGACIÓN (VISTAS HTML) ---

@app.get("/", response_class=HTMLResponse)
def get_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/rrhh", response_class=HTMLResponse)
def get_rrhh_dashboard(request: Request):
    role = request.cookies.get("user_role")
    if role != "RRHH":
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request=request, name="rrhh_form.html")

@app.get("/sistemas", response_class=HTMLResponse)
def get_sistemas_dashboard(request: Request):
    role = request.cookies.get("user_role")
    if role != "SISTEMAS":
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request=request, name="sistemas_dashboard.html")

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("user_role")
    return response


# --- ENDPOINTS API GENERALES ---

@app.post("/api/login")
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == data.email, Usuario.password_hash == data.password).first()
    if not user or not user.activo:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    redirect_url = "/rrhh" if user.rol == "RRHH" else "/sistemas"
    response = Response(content=f'{{"redirect_url": "{redirect_url}"}}', media_type="application/json")
    response.set_cookie(key="user_role", value=user.rol, httponly=True)
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)