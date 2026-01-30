# Análisis Electoral: Scraping y Transcripción

Herramientas para descargar audio/video de publicaciones en redes sociales y transcribir el contenido usando IA.

## Características

- 🎬 Descarga de audio/video desde Facebook, TikTok y YouTube
- 🎙️ Transcripción automática con Whisper
- 💬 Scraping de comentarios de posts públicos en Facebook
- 📊 Procesamiento batch de múltiples URLs
- ☁️ **Appwrite Function** para transcripción serverless con almacenamiento en bucket

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

## 🚀 Appwrite Function (Transcriptor Serverless)

El archivo `src/main.py` es una función de Appwrite que permite transcribir videos y guardar automáticamente las transcripciones en un bucket de Appwrite Storage.

### Configuración en Appwrite

1. **Crear un proyecto** en [Appwrite Console](https://cloud.appwrite.io/console)

2. **Crear un bucket** para almacenar las transcripciones:
   - Ve a Storage → Create Bucket
   - Anota el `BUCKET_ID`

3. **Crear una API Key** con permisos:
   - `storage.files.read`
   - `storage.files.write`

4. **Crear la función**:
   - Ve a Functions → Create Function
   - Selecciona **Python 3.11** como runtime
   - Configura las variables de entorno:

   | Variable | Descripción |
   |----------|-------------|
   | `APPWRITE_ENDPOINT` | `https://cloud.appwrite.io/v1` o tu endpoint |
   | `APPWRITE_PROJECT_ID` | ID de tu proyecto |
   | `APPWRITE_API_KEY` | API Key con permisos de storage |
   | `APPWRITE_BUCKET_ID` | ID del bucket de transcripciones |
   | `WHISPER_MODEL_SIZE` | `tiny`, `base`, `small`, `medium`, `large` (default: `small`) |

5. **Desplegar el código**:
   - Conecta tu repositorio Git o sube manualmente los archivos

### Uso de la función

**GET** - Información de la función:
```bash
curl https://[REGION].cloud.appwrite.io/v1/functions/[FUNCTION_ID]/executions
```

**POST** - Transcribir un video:
```bash
curl -X POST https://[FUNCTION_URL] \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "filename": "mi-transcripcion"
  }'
```

### Respuesta exitosa

```json
{
  "ok": true,
  "message": "Transcripción completada y guardada",
  "file_id": "abc123xyz",
  "filename": "mi-transcripcion.json",
  "idioma": "es",
  "texto_preview": "Texto de los primeros 500 caracteres..."
}
```

### Formato del archivo guardado

La transcripción se guarda como JSON en el bucket con la siguiente estructura:

```json
{
  "url_origen": "https://...",
  "fecha_transcripcion": "2026-01-29T10:30:00",
  "idioma": "es",
  "probabilidad_idioma": 0.98,
  "texto_completo": "Transcripción completa aquí...",
  "segmentos": [
    {"start": 0.0, "end": 2.5, "text": "Primer segmento"},
    {"start": 2.5, "end": 5.0, "text": "Segundo segmento"}
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
