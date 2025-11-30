# Berries App (PWA + Offline Sync) — v4 FULL

## Instalación (Windows)
```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python app.py
```
Abrir: http://localhost:5000

Usuarios de prueba:
- admin / admin123
- capturista / corte123

## Funciones
- Login/roles (admin, capturista)
- Captura con tamaño (4/5/6/12 oz) y precio por fruto+tamaño (editable)
- Consultas con filtros + Exportar CSV
- Semana de pago (por cortadora, columnas por tamaño) + Exportar CSV
- Reportes completos (por fruto/sector/cortadora, columnas por tamaño)
- Catálogos completos (frutos, sectores, cortadoras, tamaños y lista de precios)
- PWA offline: captura sin red + sincronización cuando regresa internet
