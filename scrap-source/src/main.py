"""
Appwrite Function: Video Transcriptor + Facebook Scraper
- Descarga audio de videos (Facebook, TikTok, YouTube) y genera transcripciones
- Extrae comentarios de posts de Facebook
Guarda los resultados en Appwrite Storage.
"""

import os
import json
import base64
import random
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.input_file import InputFile
from appwrite.id import ID
import yt_dlp
from faster_whisper import WhisperModel
from playwright.sync_api import sync_playwright

# Configuración del modelo Whisper
MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")
model = None

# Labels para expandir comentarios
SEE_MORE_LABELS = [
    "See more comments", "View more comments", "Ver más comentarios",
    "View previous comments", "Mostrar comentarios anteriores",
    "Mostrar más comentarios", "Load more comments", "Cargar más comentarios"
]

COMMENT_EXPAND_LABELS = ["See more", "Ver más", "Show more", "Mostrar más"]


def get_whisper_model():
    """Carga el modelo Whisper (singleton para reutilizar entre ejecuciones)"""
    global model
    if model is None:
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return model


def get_cookies(body: Dict[str, Any]) -> Optional[List[Dict]]:
    """
    Obtiene las cookies de Facebook desde el body (base64) o desde ENV.
    Retorna la lista de cookies o None.
    """
    cookies_data = None
    
    # Prioridad 1: cookies en base64 desde el body
    if body.get("cookies_base64"):
        try:
            cookies_data = base64.b64decode(body["cookies_base64"]).decode("utf-8")
        except Exception:
            pass
    
    # Prioridad 2: cookies en base64 desde ENV
    if not cookies_data and os.environ.get("FACEBOOK_COOKIES_BASE64"):
        try:
            cookies_data = base64.b64decode(os.environ["FACEBOOK_COOKIES_BASE64"]).decode("utf-8")
        except Exception:
            pass
    
    # Prioridad 3: cookies como JSON directo desde ENV
    if not cookies_data and os.environ.get("FACEBOOK_COOKIES_JSON"):
        cookies_data = os.environ["FACEBOOK_COOKIES_JSON"]
    
    if not cookies_data:
        return None
    
    try:
        raw_cookies = json.loads(cookies_data)
        return sanitize_cookies(raw_cookies)
    except json.JSONDecodeError:
        return None


def sanitize_cookies(raw_cookies: List[Dict]) -> List[Dict]:
    """Sanitiza cookies para Playwright"""
    clean_cookies = []
    for cookie in raw_cookies:
        clean_cookie = {
            "name": cookie.get("name", ""),
            "value": cookie.get("value", ""),
            "domain": cookie.get("domain", ""),
            "path": cookie.get("path", "/"),
        }
        
        same_site = cookie.get("sameSite") or ""
        if isinstance(same_site, str):
            same_site = same_site.lower()
            if same_site in ["strict", "lax", "none"]:
                clean_cookie["sameSite"] = same_site.capitalize()
            else:
                clean_cookie["sameSite"] = "Lax"
        else:
            clean_cookie["sameSite"] = "Lax"
        
        if "httpOnly" in cookie:
            clean_cookie["httpOnly"] = bool(cookie["httpOnly"])
        if "secure" in cookie:
            clean_cookie["secure"] = bool(cookie["secure"])
        if "expires" in cookie:
            clean_cookie["expires"] = cookie["expires"]
            
        clean_cookies.append(clean_cookie)
    
    return clean_cookies


def save_cookies_to_file(cookies: List[Dict]) -> str:
    """Guarda cookies en archivo temporal para yt-dlp"""
    cookies_path = "/tmp/facebook_cookies.json"
    with open(cookies_path, "w", encoding="utf-8") as f:
        json.dump(cookies, f)
    return cookies_path


# ==================== TRANSCRIPTOR ====================

def descargar_audio(url: str, cookies_path: Optional[str] = None, temp_path: str = "/tmp/temp_audio") -> Optional[str]:
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
    
    if cookies_path and os.path.exists(cookies_path):
        opciones['cookiefile'] = cookies_path

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            ydl.download([url])
        return f"{temp_path}.mp3"
    except Exception as e:
        print(f"❌ Error descargando: {e}")
        return None


def transcribir(archivo: str) -> Dict[str, Any]:
    """Usa Whisper para convertir audio a texto"""
    if not os.path.exists(archivo):
        return {"error": "No se encontró el archivo de audio.", "texto": "", "idioma": ""}

    whisper = get_whisper_model()
    segments, info = whisper.transcribe(archivo, beam_size=5)

    texto_completo = ""
    segmentos_lista: List[Dict[str, Any]] = []

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


# ==================== SCRAPER FACEBOOK ====================

def expand_comments(page, max_clicks: int = 30) -> int:
    """Expande la lista de comentarios haciendo click en 'ver más'"""
    clicks = 0
    
    for _ in range(3):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
    
    for _ in range(max_clicks):
        button = None
        selectors = [f'span:has-text("{label}")' for label in SEE_MORE_LABELS] + \
                   [f'div:has-text("{label}")' for label in SEE_MORE_LABELS] + \
                   ['[aria-label*="comments"]', '[role="button"]:has-text("más")', '[role="button"]:has-text("more")']
        
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=1000):
                    button = locator
                    break
            except:
                continue
                
        if button:
            try:
                button.click(timeout=3000)
                clicks += 1
                time.sleep(random.uniform(1.5, 3))
            except:
                break
        else:
            page.evaluate("window.scrollBy(0, 500)")
            time.sleep(1)
            break
    
    return clicks


def expand_long_comments(page) -> int:
    """Expande 'See more' dentro de cada comentario"""
    expanded = 0
    for label in COMMENT_EXPAND_LABELS:
        try:
            buttons = page.locator(f'span:has-text("{label}")').all()
            for button in buttons[:10]:
                try:
                    if button.is_visible():
                        button.click(timeout=1000)
                        expanded += 1
                        time.sleep(0.3)
                except:
                    continue
        except:
            continue
    return expanded


def extract_comments(page) -> List[Dict]:
    """Extrae comentarios de la página"""
    results = []
    selectors = [
        '[data-testid="UFI2Comment/root_depth_0"]',
        '[data-testid="comment"]',
        'div[aria-label="Comment"]',
        'div[role="article"]',
        '[data-ad-preview="message"]',
    ]
    
    comment_blocks = None
    for selector in selectors:
        blocks = page.locator(selector)
        if blocks.count() > 0:
            comment_blocks = blocks
            break
    
    if not comment_blocks:
        return results
        
    total = comment_blocks.count()
    
    for i in range(total):
        try:
            block = comment_blocks.nth(i)
            
            author = ""
            for auth_sel in ['strong', 'a[role="link"] strong', 'h3 a']:
                try:
                    auth_elem = block.locator(auth_sel).first
                    if auth_elem.count() > 0:
                        author = auth_elem.inner_text(timeout=1000).strip()
                        if author:
                            break
                except:
                    continue
            
            texts = []
            for text_sel in ['span[dir="auto"]:not(:has(strong))', '[dir="auto"]']:
                try:
                    spans = block.locator(text_sel)
                    if spans.count() > 0:
                        span_texts = spans.all_inner_texts()
                        for text in span_texts:
                            text = text.strip()
                            if text and text != author and len(text) > 1:
                                texts.append(text)
                except:
                    continue
            
            unique_texts = list(dict.fromkeys(texts))
            body = " ".join(unique_texts) if unique_texts else ""
            
            if (author and len(author) > 1) or (body and len(body) > 2):
                comment = {"author": author, "text": body}
                if comment not in results:
                    results.append(comment)
                    
        except:
            continue
    
    return results


def scrape_facebook_comments(url: str, cookies: List[Dict], max_clicks: int = 30) -> List[Dict]:
    """Ejecuta el scraper de comentarios de Facebook"""
    comments = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        page.goto(url, wait_until="domcontentloaded")
        time.sleep(random.uniform(3, 6))

        expand_comments(page, max_clicks=max_clicks)
        expand_long_comments(page)
        comments = extract_comments(page)

        context.close()
        browser.close()
    
    return comments


# ==================== UTILS ====================

def limpiar(archivo: Optional[str]):
    """Borra el archivo temporal"""
    if archivo and os.path.exists(archivo):
        os.remove(archivo)


def get_appwrite_client() -> Client:
    """Inicializa el cliente de Appwrite"""
    client = Client()
    client.set_endpoint(os.environ.get("APPWRITE_ENDPOINT"))
    client.set_project(os.environ.get("APPWRITE_PROJECT_ID"))
    client.set_key(os.environ.get("APPWRITE_API_KEY"))
    return client


def upload_to_bucket(client: Client, data: Any, filename: str) -> Dict:
    """Sube datos a Appwrite Storage"""
    storage = Storage(client)
    bucket_id = os.environ.get("APPWRITE_BUCKET_ID")
    
    filepath = f"/tmp/{filename}"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    result = storage.create_file(
        bucket_id=bucket_id,
        file_id=ID.unique(),
        file=InputFile.from_path(filepath)
    )
    
    limpiar(filepath)
    return result


# ==================== MAIN FUNCTION ====================

def main(context):
    """
    Función principal de Appwrite.
    
    Modos de operación:
    1. Transcriptor: {"action": "transcribe", "url": "...", "filename": "..."}
    2. Scraper FB:   {"action": "scrape", "url": "...", "max_clicks": 30}
    
    Variables de entorno requeridas:
    - APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, APPWRITE_API_KEY, APPWRITE_BUCKET_ID
    
    Variables de entorno opcionales:
    - WHISPER_MODEL_SIZE: tiny, base, small, medium, large (default: small)
    - FACEBOOK_COOKIES_BASE64 o FACEBOOK_COOKIES_JSON
    """
    
    # GET - Info de la función
    if context.req.method == "GET":
        return context.res.json({
            "ok": True,
            "message": "Video Transcriptor + Facebook Scraper",
            "actions": {
                "transcribe": {
                    "description": "Transcribe audio de un video",
                    "params": {"url": "required", "filename": "optional", "cookies_base64": "optional"}
                },
                "scrape": {
                    "description": "Extrae comentarios de un post de Facebook",
                    "params": {"url": "required", "max_clicks": "optional (default: 30)", "cookies_base64": "required"}
                }
            }
        })

    if context.req.method != "POST":
        return context.res.json({"ok": False, "error": "Método no permitido. Use POST."}, 405)

    # Parse body
    try:
        body = context.req.body if isinstance(context.req.body, dict) else json.loads(context.req.body)
    except (json.JSONDecodeError, TypeError):
        return context.res.json({"ok": False, "error": "Body JSON inválido"}, 400)

    action = body.get("action", "transcribe")
    url = body.get("url")
    
    if not url:
        return context.res.json({"ok": False, "error": "Se requiere el campo 'url'"}, 400)

    # Validar env vars
    required_env = ["APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY", "APPWRITE_BUCKET_ID"]
    missing_env = [env for env in required_env if not os.environ.get(env)]
    if missing_env:
        return context.res.json({"ok": False, "error": f"Faltan variables de entorno: {', '.join(missing_env)}"}, 500)

    try:
        cookies = get_cookies(body)
        client = get_appwrite_client()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        # ============ SCRAPE FACEBOOK ============
        if action == "scrape":
            if not cookies:
                return context.res.json({
                    "ok": False,
                    "error": "Se requieren cookies de Facebook para el scraping"
                }, 400)

            context.log(f"🔍 Scrapeando comentarios de: {url}")
            max_clicks = body.get("max_clicks", 30)
            
            comments = scrape_facebook_comments(url, cookies, max_clicks)
            
            if not comments:
                return context.res.json({
                    "ok": False,
                    "error": "No se encontraron comentarios"
                }, 404)

            filename = body.get("filename", f"comments_{stamp}.json")
            data = {
                "url_origen": url,
                "fecha_scraping": datetime.now().isoformat(),
                "total_comentarios": len(comments),
                "comentarios": comments
            }
            
            result = upload_to_bucket(client, data, filename)
            
            context.log(f"✅ {len(comments)} comentarios guardados con ID: {result['$id']}")
            
            return context.res.json({
                "ok": True,
                "message": "Scraping completado",
                "file_id": result["$id"],
                "filename": filename,
                "total_comentarios": len(comments),
                "preview": comments[:5]
            })

        # ============ TRANSCRIBE ============
        else:
            archivo_audio = None
            cookies_path = None
            
            try:
                if cookies:
                    cookies_path = save_cookies_to_file(cookies)
                    context.log("🍪 Cookies cargadas")
                
                context.log(f"⬇️ Descargando audio de: {url}")
                archivo_audio = descargar_audio(url, cookies_path)
                
                if not archivo_audio:
                    return context.res.json({
                        "ok": False,
                        "error": "No se pudo descargar el audio"
                    }, 400)

                context.log("🎙️ Transcribiendo audio...")
                resultado = transcribir(archivo_audio)
                
                if "error" in resultado:
                    return context.res.json({"ok": False, "error": resultado["error"]}, 500)

                context.log(f"🌍 Idioma detectado: {resultado['idioma'].upper()}")

                filename = body.get("filename", f"transcripcion_{stamp}.json")
                data = {
                    "url_origen": url,
                    "fecha_transcripcion": datetime.now().isoformat(),
                    "idioma": resultado["idioma"],
                    "probabilidad_idioma": resultado["probabilidad_idioma"],
                    "texto_completo": resultado["texto"],
                    "segmentos": resultado["segmentos"]
                }
                
                result = upload_to_bucket(client, data, filename)
                context.log(f"✅ Transcripción guardada con ID: {result['$id']}")

                texto_preview = resultado["texto"][:500] + "..." if len(resultado["texto"]) > 500 else resultado["texto"]
                
                return context.res.json({
                    "ok": True,
                    "message": "Transcripción completada",
                    "file_id": result["$id"],
                    "filename": filename,
                    "idioma": resultado["idioma"],
                    "texto_preview": texto_preview
                })
                
            finally:
                limpiar(archivo_audio)
                limpiar(cookies_path)

    except Exception as e:
        context.error(f"❌ Error: {str(e)}")
        return context.res.json({"ok": False, "error": str(e)}, 500)


