# 🏎️ F1 Reaction Timer — Despliegue en Railway (gratis)

## Pasos (≈ 5 minutos)

### 1. Sube el código a GitHub

Crea un repo en https://github.com/new y sube los archivos:

```bash
git init
git add .
git commit -m "F1 Reaction Timer"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

### 2. Crea un proyecto en Railway

1. Ve a **https://railway.app** y regístrate con GitHub (gratis)
2. **New Project → Deploy from GitHub repo** → selecciona tu repo
3. Railway detecta Flask y empieza a construir automáticamente

### 3. Añade PostgreSQL

1. En tu proyecto: **+ Add Service → Database → PostgreSQL**
2. Railway añade `DATABASE_URL` a tu app automáticamente — no hay que tocar nada

### 4. Genera tu URL pública

Servicio Flask → **Settings → Networking → Generate Domain**

Obtendrás algo como: `https://f1-reaction-xxxx.up.railway.app` 🎉

---

## Local (sin cambios)

```bash
pip install -r requirements.txt
python app.py   # → http://localhost:5000
```

Localmente usa SQLite; en producción usa PostgreSQL. Todo automático.
