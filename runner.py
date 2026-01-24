import argparse
from pathlib import Path
from datetime import datetime

from transcriptor import descargar_audio, transcribir, limpiar


def process_url(url: str, outdir: Path):
    try:
        archivo = descargar_audio(url)
        if not archivo:
            print(f"❌ Falló descarga para: {url}")
            return
        texto = transcribir(archivo)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        outpath = outdir / f"transcripcion_{stamp}.txt"
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"✅ Guardado: {outpath}")
    finally:
        limpiar()


def main():
    parser = argparse.ArgumentParser(description="Procesa múltiples URLs y transcribe audio")
    parser.add_argument("--list", required=True, help="Archivo de texto con una URL por línea")
    parser.add_argument("--outdir", default="datos-crudos", help="Carpeta de salida")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    list_path = Path(args.list)
    if not list_path.exists():
        raise FileNotFoundError(f"No existe el archivo de lista: {list_path}")

    urls = [line.strip() for line in list_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"🔎 Procesando {len(urls)} URLs...")
    for url in urls:
        print(f"\n➡️  URL: {url}")
        process_url(url, outdir)


if __name__ == "__main__":
    main()
