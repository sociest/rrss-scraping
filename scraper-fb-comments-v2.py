import argparse
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from playwright.sync_api import sync_playwright


def load_cookies(cookies_path: Path):
    if not cookies_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de cookies: {cookies_path}")
    with open(cookies_path, "r", encoding="utf-8") as f:
        raw_cookies = json.load(f)
    
    # Sanitize cookies for Playwright
    clean_cookies = []
    for cookie in raw_cookies:
        clean_cookie = {
            "name": cookie.get("name", ""),
            "value": cookie.get("value", ""),
            "domain": cookie.get("domain", ""),
            "path": cookie.get("path", "/"),
        }
        
        # Handle sameSite - normalize to valid values
        same_site = cookie.get("sameSite") or ""
        if isinstance(same_site, str):
            same_site = same_site.lower()
            if same_site in ["strict", "lax", "none"]:
                clean_cookie["sameSite"] = same_site.capitalize()
            else:
                clean_cookie["sameSite"] = "Lax"  # Default safe value
        else:
            clean_cookie["sameSite"] = "Lax"  # Default safe value
        
        # Optional fields
        if "httpOnly" in cookie:
            clean_cookie["httpOnly"] = bool(cookie["httpOnly"])
        if "secure" in cookie:
            clean_cookie["secure"] = bool(cookie["secure"])
        if "expires" in cookie:
            clean_cookie["expires"] = cookie["expires"]
            
        clean_cookies.append(clean_cookie)
    
    return clean_cookies


def navigate_to_comments(page):
    """Navegar específicamente a la sección de comentarios"""
    print("🔍 Buscando sección de comentarios...")
    
    # Scroll hacia abajo para encontrar los comentarios
    for scroll_attempt in range(10):
        print(f"  Scroll intento {scroll_attempt + 1}...")
        
        # Buscar indicadores de comentarios
        comment_indicators = [
            'text="Comentarios"',
            'text="Comments"', 
            '[aria-label*="comment"]',
            '[data-testid*="comment"]',
            'text="Comentar"',
            'text="Comment"',
            'span:has-text("h")',  # Buscar timestamps como "1h", "2h"
            'span:has-text("21 h")',
            'span:has-text("2 h")'
        ]
        
        for indicator in comment_indicators:
            try:
                elements = page.locator(indicator)
                if elements.count() > 0:
                    print(f"  ✅ Encontrado indicador: {indicator} ({elements.count()} elementos)")
                    # Hacer scroll al primer elemento encontrado
                    elements.first.scroll_into_view_if_needed(timeout=2000)
                    time.sleep(2)
                    return True
            except:
                continue
        
        # Scroll general hacia abajo
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(2)
    
    print("  ❌ No se encontraron indicadores de comentarios")
    return False


def extract_comments_aggressive(page) -> List[Dict]:
    """Extracción agresiva usando múltiples estrategias"""
    results = []
    
    print("🎯 Buscando comentarios con estrategia agresiva...")
    
    # Estrategia 1: Buscar por patrones de tiempo específicos
    time_patterns = ["h", "min", "21 h", "2 h", "hace"]
    
    for pattern in time_patterns:
        try:
            time_elements = page.locator(f'*:has-text("{pattern}")').all()
            print(f"  Patrón '{pattern}': {len(time_elements)} elementos")
            
            for time_elem in time_elements[:10]:  # Máximo 10 por patrón
                try:
                    # Obtener el contexto padre que podría contener el comentario completo
                    parent = time_elem.locator('..').first
                    grandparent = time_elem.locator('../..').first
                    
                    # Intentar extraer de diferentes niveles
                    for context in [time_elem, parent, grandparent]:
                        try:
                            full_text = context.inner_text().strip()
                            
                            # Filtrar contenido que claramente no es un comentario
                            if len(full_text) < 500 and not any(skip in full_text.lower() for skip in 
                                ["inicio", "video", "explorar", "reels", "chats no leídos"]):
                                
                                # Intentar separar autor y texto
                                lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                                
                                if len(lines) >= 2:
                                    # El primer elemento que no sea tiempo podría ser el autor
                                    potential_author = ""
                                    potential_text = ""
                                    
                                    for line in lines:
                                        if not any(t in line for t in time_patterns) and len(line) > 2:
                                            if not potential_author and len(line) < 50:
                                                potential_author = line
                                            elif potential_author and len(line) > 5:
                                                potential_text = line
                                                break
                                    
                                    if potential_author and potential_text:
                                        comment = {
                                            "author": potential_author,
                                            "text": potential_text,
                                            "raw_context": full_text[:200]  # Para debug
                                        }
                                        
                                        # Evitar duplicados
                                        if not any(c["author"] == comment["author"] and c["text"] == comment["text"] 
                                                 for c in results):
                                            results.append(comment)
                                            print(f"    ✓ Comentario: {potential_author[:20]}... | {potential_text[:40]}...")
                        except:
                            continue
                except:
                    continue
        except:
            continue
    
    # Estrategia 2: Buscar por estructura típica de comentarios
    print("  🔍 Buscando por estructura de comentarios...")
    
    try:
        # Buscar divs que contengan tanto nombres como texto (selector más simple)
        possible_comments = page.locator('div:has(strong)').all()
        print(f"  Elementos con strong: {len(possible_comments)}")
        
        for elem in possible_comments[:20]:  # Máximo 20
            try:
                full_text = elem.inner_text().strip()
                
                # Filtrar elementos demasiado largos o que claramente no son comentarios
                if 20 < len(full_text) < 300 and not any(skip in full_text.lower() for skip in 
                    ["inicio", "video", "explorar", "reels", "notificaciones", "chats no leídos"]):
                    
                    # Buscar strong elements (nombres)
                    strong_elements = elem.locator('strong').all()
                    potential_authors = [s.inner_text().strip() for s in strong_elements if s.inner_text().strip()]
                    
                    if potential_authors:
                        author = potential_authors[0]
                        # El texto completo menos el autor
                        text_lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                        text_without_author = [line for line in text_lines if line != author and len(line) > 3]
                        
                        if text_without_author:
                            text = " ".join(text_without_author)
                            
                            comment = {
                                "author": author,
                                "text": text[:200],  # Limitar longitud
                                "source": "structure"
                            }
                            
                            # Evitar duplicados
                            if not any(c["author"] == comment["author"] and c["text"][:50] == comment["text"][:50] 
                                     for c in results):
                                results.append(comment)
                                print(f"    ✓ Estructura: {author[:20]}... | {text[:40]}...")
            except:
                continue
    except Exception as e:
        print(f"  ❌ Error en estrategia de estructura: {e}")
    
    return results


def run_v2(url: str, cookies_path: Path, outdir: Path, headless: bool = True):
    cookies = load_cookies(cookies_path)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    outfile = outdir / f"comments_{stamp}.jsonl"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        print("🚀 Navegando al post...")
        page.goto(url, wait_until="domcontentloaded")
        print(f"URL final: {page.url}")
        
        # Espera inicial más larga
        time.sleep(5)
        
        # Navegar específicamente a comentarios
        navigate_to_comments(page)
        
        # Esperar más tiempo para cargar comentarios
        time.sleep(3)
        
        # Extraer con estrategia agresiva
        comments = extract_comments_aggressive(page)
        
        # Guardar resultados
        with open(outfile, "w", encoding="utf-8") as f:
            for c in comments:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        
        print(f"✅ Guardado: {outfile} ({len(comments)} comentarios)")
        
        if not headless and len(comments) == 0:
            print("\n=== DEBUG: Presiona ENTER para cerrar y revisar manualmente ===")
            input()

        context.close()
        browser.close()
        
    return comments


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper v2 de comentarios de Facebook")
    parser.add_argument("--url", required=True, help="URL del post")
    parser.add_argument("--cookies", default="facebook-cookies.json", help="Archivo de cookies")
    parser.add_argument("--outdir", default="datos-crudos", help="Carpeta de salida")
    parser.add_argument("--headless", action="store_true", help="Modo headless")
    args = parser.parse_args()

    run_v2(args.url, Path(args.cookies), Path(args.outdir), headless=args.headless)