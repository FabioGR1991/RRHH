import asyncio
import os
from config.database import SessionLocal, engine, Base
from src.models.solicitud import SolicitudAlta
from src.services.solicitudes_workflow_service import aprobar_y_aprovisionar_solicitud_service

# Ensure DB tables exist
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# 1. Clean or create a test solicitud
test_sol = db.query(SolicitudAlta).filter(SolicitudAlta.dni == '99999001').first()
if test_sol:
    db.delete(test_sol)
    db.commit()

test_sol = SolicitudAlta(
    nombre='TestNombre',
    apellido='TestApellido',
    dni='99999001',
    legajo='1899',
    perfil_ad='Operador',
    reporta_a='juan.perez@tandemtech.com.ar',
    es_fuera_de_nomina=False,
    estado='PENDIENTE'
)
db.add(test_sol)
db.commit()
db.refresh(test_sol)
print(f"Created test solicitud id={test_sol.id}")

# 2. Approve and provision via workflow service
res = asyncio.run(aprobar_y_aprovisionar_solicitud_service(test_sol.id, db))
print("Workflow Result Status:", res['status'])
print("Estado final:", res['estado_final'])
print("Servicios ejecutados:", list(res['estado_servicios'].keys()))
for svc, details in res['estado_servicios'].items():
    print(f"  - {svc}: {details.get('status')} ({details.get('msg')})")

pdf_path = res.get('pdf_path')
print("PDF generado:", res['pdf_generado'], pdf_path)
assert os.path.exists(res.get('pdf_path')), f"File does not exist: {res.get('pdf_path')}"
print("PDF exists on disk! Size:", os.path.getsize(pdf_path), "bytes")

# Check QR
qr_path = res.get('credenciales', {}).get('qr_path')
print("QR generado:", qr_path)
if qr_path and os.path.exists(qr_path):
    print("QR exists on disk! Size:", os.path.getsize(qr_path), "bytes")

db.refresh(test_sol)
print("DB Record status:", test_sol.estado)
print("DB has json_credenciales:", bool(test_sol.json_credenciales))

# Clean up test record
db.delete(test_sol)
db.commit()
db.close()
print("INTEGRATION TEST PASSED SUCCESSFULLY!")
