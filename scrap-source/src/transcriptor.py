import os
import argparse
from datetime import datetime
from pathlib import Path
import yt_dlp
from faster_whisper import WhisperModel

# Usamos "small" porque es rápido y preciso. 
# Si quieres más precisión (pero más lento), cambia a "medium".
MODEL_SIZE = "small"
print(f"⚙️  Cargando modelo '{MODEL_SIZE}' (esto descarga unos 500MB la primera vez)...")

model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

def descargar_audio(url):
    """Descarga solo el audio y lo guarda como temp_audio.mp3"""
    print(f"⬇️  Descargando audio de: {url}")
    
    opciones = {
        'format': 'bestaudio/best',
        'outtmpl': 'temp_audio.%(ext)s', 
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
        return "temp_audio.mp3"
    except Exception as e:
        print(f"❌ Error descargando: {e}")
        return None

def transcribir(archivo):
    """Usa la IA para convertir audio a texto"""
    if not os.path.exists(archivo):
        return "Error: No se encontró el archivo de audio."

    print("🎙️  La IA está escuchando y transcribiendo...")
    
    # beam_size=5 ayuda a que la IA explore mejores traducciones
    segments, info = model.transcribe(archivo, beam_size=5)

    print(f"🌍 Idioma detectado: {info.language.upper()} (Probabilidad: {info.language_probability:.2f})")
    print("-" * 50)

    texto_completo = ""
    for segment in segments:
        # Imprimimos en tiempo real con marcas de tiempo
        linea = f"[{segment.start:.1f}s -> {segment.end:.1f}s] {segment.text}"
        print(linea)
        texto_completo += segment.text + " "
    
    print("-" * 50)
    return texto_completo

def limpiar():
    """Borra el archivo temporal"""
    if os.path.exists("temp_audio.mp3"):
        os.remove("temp_audio.mp3")
        print("🧹 Archivo temporal eliminado.")

# --- EJECUCIÓN ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Descarga audio y transcribe con Faster-Whisper")
    parser.add_argument("--url", help="URL del video (Facebook, TikTok, YouTube)")
    parser.add_argument("--outdir", default="datos-crudos", help="Carpeta destino para transcripción")
    args = parser.parse_args()

    url = args.url or "https://www.facebook.com/cesardockweilersuarez/videos/1399478394994936"

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        archivo = descargar_audio(url)
        if archivo:
            texto = transcribir(archivo)

            # Guardar con nombre único
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            outpath = outdir / f"transcripcion_{stamp}.txt"
            with open(outpath, "w", encoding="utf-8") as f:
                f.write(texto)
            print(f"✅ ¡Listo! Guardado en '{outpath}'")
        else:
            print("❌ No se pudo descargar el audio. Revisa la URL o cookies si es Facebook/TikTok.")
    finally:
        limpiar()