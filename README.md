# 🏷️ Rastreador Automático de Precios y Ofertas

Proyecto de rastreo y monitoreo de precios en tiempo real construido con **Python**, **PostgreSQL** y **Streamlit**, optimizado tanto para desarrollo local como para despliegue en producción en **Render** (Render Web Service + Render PostgreSQL).

---

## 📁 Estructura del Proyecto

```text
rastreador-precios/
├── app.py              # Aplicación web interactiva en Streamlit
├── db.py               # Módulo de conexión y operaciones CRUD con PostgreSQL
├── scraper.py          # Módulo de extracción de precios (Books to Scrape, Steam, genérico)
├── schema.sql          # Esquema DDL de tablas e índices para PostgreSQL
├── requirements.txt    # Dependencias del proyecto
├── .env                # Configuración de variables de entorno (DATABASE_URL)
├── .gitignore          # Archivos y carpetas excluidas de Git
└── README.md           # Guía de uso y despliegue
```

---

## 🛠️ Requisitos e Instalación Local

### 1. Requisitos Previos
* Python 3.10 o superior
* PostgreSQL 14 o superior instalado y en ejecución

### 2. Configurar la Base de Datos Local
El archivo `.env` ya se encuentra configurado con la cadena de conexión local:
```env
DATABASE_URL=postgresql://postgres:franchesco03@localhost:5432/rastreador_precios
```

### 3. Activar el Entorno Virtual e Instalar Dependencias
```powershell
# En Windows PowerShell:
.\venv\Scripts\Activate.ps1

# O si creas un nuevo entorno:
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4. Ejecutar la Aplicación
```powershell
.\venv\Scripts\streamlit run app.py
```
La aplicación abrirá automáticamente en tu navegador en `http://localhost:8501`.

---

## 🚀 Despliegue en Producción (Render)

### Paso 1: Crear la Base de Datos en Render
1. En [Render Dashboard](https://dashboard.render.com/), haz clic en **New +** > **PostgreSQL**.
2. Dale un nombre (ej. `rastreador-db`) y selecciona el plan gratuito.
3. Una vez creada, copia la **Internal Database URL** (o External si te conectas desde fuera de Render).

### Paso 2: Crear el Web Service en Render
1. Sube este repositorio a GitHub / GitLab.
2. En Render Dashboard, haz clic en **New +** > **Web Service**.
3. Conecta tu repositorio.
4. Configura los siguientes parámetros:
   - **Environment / Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. En la sección **Environment Variables**:
   - Agrega `DATABASE_URL` con el valor de la URL de tu base de datos de Render.
   *(Nota: `db.py` ya reemplaza automáticamente cualquier prefijo `postgres://` por `postgresql://`).*
6. Haz clic en **Create Web Service**. Las tablas se inicializarán automáticamente al arrancar la app.

---

## 🔍 Tiendas Soportadas Inicialmente
* **Books to Scrape**: `https://books.toscrape.com/catalogue/...`
* **Steam**: `https://store.steampowered.com/app/...`
* **Genérico / Otras**: Detección mediante metadatos Schema.org (`itemprop="price"`) y selectores comunes.
