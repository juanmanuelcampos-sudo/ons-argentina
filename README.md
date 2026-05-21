# ONs Argentina — Informe Interactivo

Aplicación web para análisis de Obligaciones Negociables argentinas con precios en vivo desde BYMA.

## Estructura

```
ons_app/
├── main.py            ← servidor FastAPI
├── requirements.txt   ← dependencias Python
├── render.yaml        ← configuración de Render
└── static/
    └── index.html     ← informe interactivo
```

## Deploy en Render (paso a paso)

1. Subir este repositorio a GitHub (ver instrucciones abajo)
2. En render.com → New → Web Service → conectar el repo
3. Render detecta render.yaml automáticamente → Deploy

## Subir a GitHub

```bash
cd ons_app
git init
git add .
git commit -m "primer deploy"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/ons-argentina.git
git push -u origin main
```

## Correr localmente

```bash
pip install -r requirements.txt
uvicorn main:app --reload
# Abrir http://localhost:8000
```
