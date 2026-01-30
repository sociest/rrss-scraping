"""
Appwrite Function: Video Transcriptor
Descarga audio de videos (Facebook, TikTok, YouTube) y genera transcripciones
usando Faster-Whisper, guardando el resultado en Appwrite Storage.
"""

import os
import json
from datetime import datetime
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.input_file import InputFile
from appwrite.id import ID
import yt_dlp
from faster_whisper import WhisperModel

# Configuración del modelo Whisper
MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")
model = None


def get_whisper_model():
    """Carga el modelo Whisper (singleton para reutilizar entre ejecuciones)"""
    global model
    if model is None:
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return model


def descargar_audio(url: str, temp_path: str = "/tmp/temp_audio") -> str | None:
    """Descarga solo el audio y lo guarda como archivo mp3"""
    opciones = {
        'format': 'bestaudio/best',
        'outtmpl': f'{temp_path}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True
    }

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            ydl.download([url])
        return f"{temp_path}.mp3"
    except Exception as e:
        print(f"❌ Error descargando: {e}")
        return None


def transcribir(archivo: str) -> dict:
    """Usa Whisper para convertir audio a texto"""
    if not os.path.exists(archivo):
        return {"error": "No se encontró el archivo de audio.", "texto": "", "idioma": ""}

    whisper = get_whisper_model()
    segments, info = whisper.transcribe(archivo, beam_size=5)

    texto_completo = ""
    segmentos_lista = []

    for segment in segments:
        segmentos_lista.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text
        })
        texto_completo += segment.text + " "

    return {
        "texto": texto_completo.strip(),
        "idioma": info.language,
        "probabilidad_idioma": info.language_probability,
        "segmentos": segmentos_lista
    }


def limpiar(archivo: str):
    """Borra el archivo temporal"""
    if archivo and os.path.exists(archivo):
        os.remove(archivo)


def main(context):
    """
    Función principal de Appwrite.
    
    Espera un body JSON con:
    - url: URL del video a transcribir (requerido)
    - filename: Nombre personalizado para el archivo (opcional)
    
    Variables de entorno requeridas:
    - APPWRITE_ENDPOINT: Endpoint de Appwrite
    - APPWRITE_PROJECT_ID: ID del proyecto
    - APPWRITE_API_KEY: API Key con permisos de storage
    - APPWRITE_BUCKET_ID: ID del bucket donde guardar transcripciones
    - WHISPER_MODEL_SIZE: Tamaño del modelo (tiny, base, small, medium, large) - default: small
    """
    
    # Manejar petición GET (información de la función)
    if context.req.method == "GET":
        return context.res.json({
            "ok": True,
            "message": "Video Transcriptor Function",
            "usage": {
                "method": "POST",
                "body": {
                    "url": "URL del video (Facebook, TikTok, YouTube)",
                    "filename": "Nombre personalizado (opcional)"
                }
            }
        })

    # Validar método POST
    if context.req.method != "POST":
        return context.res.json({
            "ok": False,
            "error": "Método no permitido. Use POST."
        }, 405)

    # Obtener y validar el body
    try:
        body = context.req.body if isinstance(context.req.body, dict) else json.loads(context.req.body)
    except (json.JSONDecodeError, TypeError):
        return context.res.json({
            "ok": False,
            "error": "Body JSON inválido"
        }, 400)

    url = body.get("url")
    if not url:
        return context.res.json({
            "ok": False,
            "error": "Se requiere el campo 'url'"
        }, 400)

    # Validar variables de entorno
    required_env = ["APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY", "APPWRITE_BUCKET_ID"]
    missing_env = [env for env in required_env if not os.environ.get(env)]
    if missing_env:
        return context.res.json({
            "ok": False,
            "error": f"Faltan variables de entorno: {', '.join(missing_env)}"
        }, 500)

    archivo_audio = None
    archivo_transcripcion = None

    try:
        context.log(f"⬇️ Descargando audio de: {url}")
        
        # Descargar audio
        archivo_audio = descargar_audio(url)
        if not archivo_audio:
            return context.res.json({
                "ok": False,
                "error": "No se pudo descargar el audio. Verifica la URL."
            }, 400)

        context.log("🎙️ Transcribiendo audio...")
        
        # Transcribir
        resultado = transcribir(archivo_audio)
        
        if "error" in resultado:
            return context.res.json({
                "ok": False,
                "error": resultado["error"]
            }, 500)

        context.log(f"🌍 Idioma detectado: {resultado['idioma'].upper()}")

        # Preparar archivo de transcripción
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = body.get("filename", f"transcripcion_{stamp}")
        
        # Crear archivo JSON con toda la información
        transcripcion_data = {
            "url_origen": url,
            "fecha_transcripcion": datetime.now().isoformat(),
            "idioma": resultado["idioma"],
            "probabilidad_idioma": resultado["probabilidad_idioma"],
            "texto_completo": resultado["texto"],
            "segmentos": resultado["segmentos"]
        }
        
        archivo_transcripcion = f"/tmp/{filename}.json"
        with open(archivo_transcripcion, "w", encoding="utf-8") as f:
            json.dump(transcripcion_data, f, ensure_ascii=False, indent=2)

        # Inicializar cliente de Appwrite
        client = Client()
        client.set_endpoint(os.environ.get("APPWRITE_ENDPOINT"))
        client.set_project(os.environ.get("APPWRITE_PROJECT_ID"))
        client.set_key(os.environ.get("APPWRITE_API_KEY"))

        storage = Storage(client)
        bucket_id = os.environ.get("APPWRITE_BUCKET_ID")

        context.log(f"📤 Subiendo transcripción al bucket: {bucket_id}")

        # Subir archivo al bucket
        result = storage.create_file(
            bucket_id=bucket_id,
            file_id=ID.unique(),
            file=InputFile.from_path(archivo_transcripcion)
        )

        context.log(f"✅ Transcripción guardada con ID: {result['$id']}")

        return context.res.json({
            "ok": True,
            "message": "Transcripción completada y guardada",
            "file_id": result["$id"],
            "filename": f"{filename}.json",
            "idioma": resultado["idioma"],
            "texto_preview": resultado["texto"][:500] + "..." if len(resultado["texto"]) > 500 else resultado["texto"]
        })

    except Exception as e:
        context.error(f"❌ Error: {str(e)}")
        return context.res.json({
            "ok": False,
            "error": str(e)
        }, 500)

    finally:
        # Limpiar archivos temporales
        limpiar(archivo_audio)
        limpiar(archivo_transcripcion)
