import argparse
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


SEE_MORE_LABELS = [
    "See more comments",
    "View more comments", 
    "Ver más comentarios",
    "View previous comments",
    "Mostrar comentarios anteriores",
    "Mostrar más comentarios",
    "Load more comments",
    "Cargar más comentarios"
]

COMMENT_EXPAND_LABELS = [
    "See more",
    "Ver más", 
    "Show more",
    "Mostrar más"
]


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


def expand_comments(page, max_clicks: int = 30):
    clicks = 0
    
    # Primero intentar hacer scroll hacia abajo para cargar contenido
    print("Haciendo scroll para cargar comentarios...")
    for _ in range(3):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
    
    # Luego buscar botones de "ver más comentarios"
    for _ in range(max_clicks):
        button = None
        # Intentar múltiples selectores para botones de más comentarios
        selectors = [
            f'span:has-text("{label}")' for label in SEE_MORE_LABELS
        ] + [
            f'div:has-text("{label}")' for label in SEE_MORE_LABELS  
        ] + [
            '[aria-label*="comments"]',
            '[role="button"]:has-text("más")',
            '[role="button"]:has-text("more")'
        ]
        
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=1000):
                    button = locator
                    print(f"Encontrado botón con selector: {selector}")
                    break
            except:
                continue
                
        if button:
            try:
                button.click(timeout=3000)
                clicks += 1
                print(f"Click #{clicks} en 'ver más comentarios'")
                time.sleep(random.uniform(1.5, 3))
                continue
            except Exception as e:
                print(f"Error haciendo click: {e}")
                break
        else:
            # Si no encontramos botón, intentar scroll adicional
            page.evaluate("window.scrollBy(0, 500)")
            time.sleep(1)
            break
    
    return clicks


def expand_long_comments(page):
    # Expande "See more" dentro de cada comentario
    expanded = 0
    for label in COMMENT_EXPAND_LABELS:
        try:
            buttons = page.locator(f'span:has-text("{label}")').all()
            for button in buttons[:10]:  # Limitar para evitar loops infinitos
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
    results = []
    # Selectores específicos para Facebook Watch y posts regulares
    selectors = [
        # Facebook Watch
        '[data-testid="UFI2Comment/root_depth_0"]',
        '[data-testid="comment"]', 
        # Posts regulares
        'div[aria-label="Comment"]',
        'div[role="article"]',
        # Fallbacks genéricos
        '[data-ad-preview="message"]',
        'div:has(> div > span[dir="auto"]):has(strong)',
        # Para la estructura que viste en la imagen
        'div:has(> div > div > strong):has(span[dir="auto"])'
    ]
    
    comment_blocks = None
    used_selector = None
    for selector in selectors:
        blocks = page.locator(selector)
        count = blocks.count()
        if count > 0:
            comment_blocks = blocks
            used_selector = selector
            print(f"✅ Usando selector: {selector} ({count} elementos)")
            break
    
    if not comment_blocks:
        print("❌ No se encontraron comentarios con ningún selector")
        # Debug: mostrar algunos elementos de la página
        print("Elementos disponibles en la página:")
        try:
            all_divs = page.locator('div').all()[:20]  # Primeros 20 divs
            for i, div in enumerate(all_divs):
                try:
                    text = div.inner_text()[:100]  # Primeros 100 chars
                    if text.strip():
                        print(f"  div[{i}]: {text}...")
                except:
                    pass
        except:
            pass
        return results
        
    total = comment_blocks.count()
    print(f"Procesando {total} elementos encontrados...")
    
    for i in range(total):
        try:
            block = comment_blocks.nth(i)
            
            # Buscar autor con múltiples estrategias
            author = ""
            author_selectors = [
                'strong',
                'a[role="link"] strong', 
                'span[dir="auto"] strong',
                'h3 a',
                'a[href*="profile"]'
            ]
            
            for auth_sel in author_selectors:
                try:
                    auth_elem = block.locator(auth_sel).first
                    if auth_elem.count() > 0:
                        author = auth_elem.inner_text(timeout=1000).strip()
                        if author:
                            break
                except:
                    continue
            
            # Buscar texto del comentario con múltiples estrategias
            text_selectors = [
                'span[dir="auto"]:not(:has(strong))',  # Texto sin el nombre
                'div[data-ad-preview="message"]',
                '[dir="auto"]',
                'div > span'
            ]
            
            texts = []
            for text_sel in text_selectors:
                try:
                    spans = block.locator(text_sel)
                    if spans.count() > 0:
                        span_texts = spans.all_inner_texts()
                        for text in span_texts:
                            text = text.strip()
                            # Filtrar texto que no sea el nombre del autor
                            if text and text != author and len(text) > 1:
                                texts.append(text)
                except:
                    continue
            
            # Limpiar textos duplicados y concatenar
            unique_texts = []
            for text in texts:
                if text not in unique_texts:
                    unique_texts.append(text)
            
            body = " ".join(unique_texts) if unique_texts else ""
            
            # Solo agregar si tenemos contenido útil
            if (author and len(author) > 1) or (body and len(body) > 2):
                comment = {"author": author, "text": body}
                if comment not in results:  # Evitar duplicados
                    results.append(comment)
                    print(f"  ✓ Comentario {len(results)}: {author[:20]}... | {body[:50]}...")
                    
        except Exception as e:
            print(f"❌ Error procesando comentario {i}: {e}")
            continue
    
    return results


def run(url: str, cookies_path: Path, outdir: Path, headless: bool = True, max_clicks: int = 30):
    cookies = load_cookies(cookies_path)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    outfile = outdir / f"comments_{stamp}.jsonl"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        print("Navegando al post...")
        page.goto(url, wait_until="domcontentloaded")
        print(f"URL final después de redirección: {page.url}")
        time.sleep(random.uniform(3, 6))

        print("Expandiendo lista de comentarios...")
        clicks = expand_comments(page, max_clicks=max_clicks)
        print(f"Clicks en 'ver más comentarios': {clicks}")

        print("Expandiendo comentarios largos...")
        expanded = expand_long_comments(page)
        print(f"Comentarios expandidos: {expanded}")

        print("Extrayendo comentarios...")
        comments = extract_comments(page)
        with open(outfile, "w", encoding="utf-8") as f:
            for c in comments:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        print(f"✅ Guardado: {outfile} ({len(comments)} comentarios)")

        context.close()
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper de comentarios de un post de Facebook usando Playwright")
    parser.add_argument("--url", required=True, help="URL del post público del candidato")
    parser.add_argument("--cookies", default="facebook-cookies.json", help="Ruta al JSON de cookies")
    parser.add_argument("--outdir", default="datos-crudos", help="Carpeta de salida para JSONL")
    parser.add_argument("--headless", action="store_true", help="Ejecutar en modo headless")
    parser.add_argument("--max-clicks", type=int, default=30, help="Clicks máximos en 'ver más comentarios'")
    args = parser.parse_args()

    run(args.url, Path(args.cookies), Path(args.outdir), headless=args.headless, max_clicks=args.max_clicks)
