# Análisis Electoral: Scraping y Transcripción

Herramientas para descargar audio/video de publicaciones en redes sociales y transcribir el contenido usando IA.

## Características

- 🎬 Descarga de audio/video desde Facebook, TikTok y YouTube
- 🎙️ Transcripción automática con Whisper
- 💬 Scraping de comentarios de posts públicos en Facebook
- 📊 Procesamiento batch de múltiples URLs
- ☁️ **Appwrite Function** para transcripción y scraping serverless con almacenamiento en bucket

## Requisitos

- Python 3.11+
- ffmpeg (Linux: `sudo apt install ffmpeg`)
- Paquetes Python:
  ```bash
  pip install -r requirements.txt
  ```
- Playwright (solo si usas `scraper-fb.py`):
  ```bash
  python -m playwright install chromium
  ```

## Instalación rápida

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/analisis-electoral.git
cd analisis-electoral

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

### Transcripción de una sola URL (local)

```bash
python src/transcriptor.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --outdir datos-crudos
```

---

## 🚀 Appwrite Function (Transcriptor + Scraper)

El archivo `src/main.py` es una función de Appwrite que permite:
1. **Transcribir videos** de Facebook, TikTok, YouTube
2. **Scrapear comentarios** de posts de Facebook

### Configuración en Appwrite

1. **Crear un proyecto** en [Appwrite Console](https://cloud.appwrite.io/console)

2. **Crear un bucket** para almacenar los resultados:
   - Ve a Storage → Create Bucket
   - Anota el `BUCKET_ID`

3. **Crear una API Key** con permisos:
   - `storage.files.read`
   - `storage.files.write`

4. **Crear la función**:
   - Ve a Functions → Create Function
   - Selecciona **Python 3.11** como runtime ⚠️ (obligatorio)
   - Configura las variables de entorno:

   | Variable | Descripción |
   |----------|-------------|
   | `APPWRITE_ENDPOINT` | `https://cloud.appwrite.io/v1` o tu endpoint |
   | `APPWRITE_PROJECT_ID` | ID de tu proyecto |
   | `APPWRITE_API_KEY` | API Key con permisos de storage |
   | `APPWRITE_BUCKET_ID` | ID del bucket de resultados |
   | `WHISPER_MODEL_SIZE` | `tiny`, `base`, `small`, `medium`, `large` (default: `small`) |
   | `FACEBOOK_COOKIES_BASE64` | Cookies de Facebook en base64 (opcional) |

5. **Desplegar el código**:
   - Conecta tu repositorio Git o sube manualmente los archivos

### Uso de la función

**GET** - Información de la función:
```bash
curl https://[FUNCTION_URL]
```

#### Transcribir un video:
```bash
curl -X POST https://[FUNCTION_URL] \
  -H "Content-Type: application/json" \
  -d '{
    "action": "transcribe",
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "filename": "mi-transcripcion"
  }'
```

#### Scrapear comentarios de Facebook:
```bash
# Generar cookies en base64
COOKIES_B64=$(cat facebook-cookies.json | base64 -w 0)

# Ejecutar scraping
curl -X POST https://[FUNCTION_URL] \
  -H "Content-Type: application/json" \
  -d '{
    "action": "scrape",
    "url": "https://www.facebook.com/user/posts/123456",
    "cookies_base64": "'"$COOKIES_B64"'",
    "max_clicks": 30
  }'
```

### Respuestas

**Transcripción exitosa:**
```json
{
  "ok": true,
  "message": "Transcripción completada",
  "file_id": "abc123xyz",
  "filename": "transcripcion_20260130.json",
  "idioma": "es",
  "texto_preview": "Texto de los primeros 500 caracteres..."
}
```

**Scraping exitoso:**
```json
{
  "ok": true,
  "message": "Scraping completado",
  "file_id": "xyz789abc",
  "filename": "comments_20260130.json",
  "total_comentarios": 150,
  "preview": [{"author": "Usuario1", "text": "Comentario..."}]
}
```

### Formato de archivos guardados

**Transcripción:**
```json
{
  "url_origen": "https://...",
  "fecha_transcripcion": "2026-01-30T10:30:00",
  "idioma": "es",
  "probabilidad_idioma": 0.98,
  "texto_completo": "Transcripción completa aquí...",
  "segmentos": [
    {"start": 0.0, "end": 2.5, "text": "Primer segmento"}
  ]
}
```

**Comentarios:**
```json
{
  "url_origen": "https://...",
  "fecha_scraping": "2026-01-30T10:30:00",
  "total_comentarios": 150,
  "comentarios": [
    {"author": "Usuario1", "text": "Comentario del usuario..."}
  ]
}
```

---

### Batch de múltiples URLs


```bash
# Crear archivo urls.txt con una URL por línea
echo "https://www.youtube.com/watch?v=..." >> urls.txt
echo "https://www.tiktok.com/..." >> urls.txt

# Ejecutar
python runner.py --list urls.txt --outdir datos-crudos
```

### Scraper de Facebook (posts públicos)

```bash
python scraper-fb.py --url "URL_DEL_POST_PUBLICO" --cookies facebook-cookies.json --headless
```

#### Configurar cookies de Facebook

1. Instala la extensión [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkennddhgpbpiagedomjjfgnpmgfen) en Chrome/Chromium
2. Ve a facebook.com e inicia sesión
3. Abre Cookie-Editor → Selecciona el ícono de exportar (export) 
4. Copia el JSON exportado
5. Crea `facebook-cookies.json` en la raíz del proyecto y pega el contenido

**Ejemplo de estructura**: Ver [facebook-cookies.example.json](facebook-cookies.example.json)

⚠️ **IMPORTANTE**: El archivo `facebook-cookies.json` está en `.gitignore` para proteger tus credenciales. Nunca lo subas a GitHub.

### Scraping de comentarios de Facebook

```bash
python scraper-fb-comments.py --url "URL_DEL_POST_PUBLICO" --cookies facebook-cookies.json --outdir datos-crudos --max-clicks 30
```

## Consideraciones importantes

### Privacidad y Cumplimiento Legal

- ⚠️ Usa solo contenido **público** y con propósitos de investigación
- 📋 Respeta [GDPR](https://gdpr-info.eu/), CCPA y leyes de protección de datos locales
- 🔒 Anonimiza datos personales antes de compartir resultados
- 📖 Revisar políticas de cada plataforma (Facebook, TikTok, YouTube)

### Consejos técnicos

- Muchas URLs requieren sesión/cookies. Si falla descarga: usa navegador con sesión activa
- Agrega pausas entre solicitudes para no saturar servidores
- Usa user-agents realistas y respeta `robots.txt`

## Carpeta de salida

- Los archivos de transcripción se guardan en `datos-crudos/` con nombre `transcripcion_YYYYMMDD-HHMMSS.txt`.
