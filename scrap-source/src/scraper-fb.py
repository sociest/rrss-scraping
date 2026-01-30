import json
import random
import time
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

def run(url: str, cookies_path: str, headless: bool = True):
    # 1. Cargar cookies exportadas del navegador (JSON de Playwright o similar)
    cp = Path(cookies_path)
    if not cp.exists():
        raise FileNotFoundError(f"No se encontró el archivo de cookies: {cp}")
    with open(cp, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()

        # 2. Inyectar cookies para sesión autenticada
        context.add_cookies(cookies)

        page = context.new_page()

        # 3. Navegar al post del candidato
        print("Navegando al post...")
        page.goto(url, wait_until="domcontentloaded")

        # 4. Pequeña espera aleatoria
        time.sleep(random.uniform(2, 5))

        # 5. Extraer texto del post (selector común en posts)
        try:
            locator = page.locator('div[data-ad-preview="message"]').first
            post_content = locator.inner_text(timeout=5000)
            print("\n--- TEXTO ENCONTRADO ---")
            print(post_content)
            print("------------------------\n")
        except Exception as e:
            print(f"No pude leer el texto. El selector pudo cambiar. Detalle: {e}")

        # 6. Captura de pantalla para ver el estado
        page.screenshot(path="prueba_exito.png")

        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper básico de Facebook con Playwright")
    parser.add_argument("--url", required=True, help="URL del post público del candidato")
    parser.add_argument("--cookies", default="facebook-cookies.json", help="Ruta al JSON de cookies")
    parser.add_argument("--headless", action="store_true", help="Ejecutar en modo headless")
    args = parser.parse_args()

    run(args.url, args.cookies, headless=args.headless)