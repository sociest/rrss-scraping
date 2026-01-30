import argparse
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright


def debug_facebook_structure(url: str, cookies_path: Path):
    """Script para inspeccionar la estructura HTML de Facebook y encontrar los comentarios"""
    
    with open(cookies_path, 'r', encoding='utf-8') as f:
        raw_cookies = json.load(f)
    
    # Sanitizar cookies
    clean_cookies = []
    for cookie in raw_cookies:
        clean_cookie = {
            "name": cookie.get("name", ""),
            "value": cookie.get("value", ""),
            "domain": cookie.get("domain", ""),
            "path": cookie.get("path", "/"),
            "sameSite": "Lax"
        }
        clean_cookies.append(clean_cookie)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Siempre visible para debug
        context = browser.new_context()
        context.add_cookies(clean_cookies)
        page = context.new_page()

        print("Navegando...")
        page.goto(url, wait_until="domcontentloaded")
        print(f"URL final: {page.url}")
        
        # Esperar un poco para cargar
        time.sleep(5)
        
        # Buscar todos los elementos que contengan texto de comentarios
        print("\n=== BUSCANDO COMENTARIOS ===")
        
        # Palabras clave que aparecerían en comentarios
        keywords = ["hora", "minuto", "Me gusta", "Responder", "hace"]
        
        for keyword in keywords:
            elements = page.locator(f'*:has-text("{keyword}")').all()
            print(f"\nElementos con '{keyword}': {len(elements)}")
            for i, elem in enumerate(elements[:5]):  # Solo primeros 5
                try:
                    tag = elem.evaluate("el => el.tagName")
                    text = elem.inner_text()[:100]
                    attrs = elem.evaluate("""el => {
                        const attrs = {};
                        for (let attr of el.attributes) {
                            attrs[attr.name] = attr.value;
                        }
                        return attrs;
                    }""")
                    print(f"  [{i}] {tag}: {text}...")
                    if attrs.get('data-testid') or attrs.get('aria-label'):
                        print(f"      Atributos importantes: {attrs}")
                except:
                    pass
        
        # Buscar por patrones de tiempo (1h, 2h, etc.)
        print("\n=== PATRONES DE TIEMPO ===")
        time_elements = page.locator('*:has-text("h ")').all()  # "1h ", "2h ", etc.
        for i, elem in enumerate(time_elements[:5]):
            try:
                parent = elem.locator('..').first  # Elemento padre
                parent_text = parent.inner_text()[:200]
                print(f"  [{i}] Contexto de tiempo: {parent_text}...")
                
                # Ver hermanos
                siblings = parent.locator('../*').all()
                print(f"      Hermanos: {len(siblings)}")
            except:
                pass
        
        print("\n=== PRESIONA ENTER PARA CERRAR ===")
        input()  # Pausa para inspeccionar manualmente
        
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug de estructura HTML de Facebook")
    parser.add_argument("--url", required=True, help="URL del post")
    parser.add_argument("--cookies", default="facebook-cookies.json", help="Archivo de cookies")
    args = parser.parse_args()
    
    debug_facebook_structure(args.url, Path(args.cookies))