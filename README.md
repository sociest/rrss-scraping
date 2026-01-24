# Análisis Electoral: Scraping y Transcripción

Herramientas para descargar audio/video de publicaciones en redes sociales y transcribir el contenido usando IA.

## Características

- 🎬 Descarga de audio/video desde Facebook, TikTok y YouTube
- 🎙️ Transcripción automática con Whisper
- 💬 Scraping de comentarios de posts públicos en Facebook
- 📊 Procesamiento batch de múltiples URLs

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

### Transcripción de una sola URL

```bash
python transcriptor.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --outdir datos-crudos
```

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
