# Guía de Contribución

Gracias por tu interés en contribuir al proyecto **Análisis Electoral**.

## Antes de comenzar

1. **Privacidad y cumplimiento legal**:
   - No subas datos personales, comentarios de usuarios reales, o información privada.
   - Respeta las políticas de privacidad de las plataformas (Facebook, TikTok, YouTube).
   - Usa datos públicos y anonimizados solo para propósitos de investigación.

2. **Seguridad**:
   - Nunca comitas credenciales, tokens, o cookies en el repositorio.
   - Usa archivos `.env` o `.example` para configuraciones sensibles.

## Configuración local

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/analisis-electoral.git
cd analisis-electoral

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de ejemplo para credenciales
cp .env.example .env
# Editar .env y agregar tus credenciales si es necesario
```

## Cambios típicos

- Mejoras en scripts de scraping
- Correcciones de bugs
- Mejor documentación
- Soporte para nuevas plataformas

Antes de hacer push: verifica que no hay datos sensibles en tu commit.

```bash
# Revisar cambios antes de commitear
git diff --cached
```

## Estilo de código

- Sigue PEP 8
- Usa type hints cuando sea posible
- Agrega docstrings en funciones públicas

¡Gracias por ayudar a mejorar el proyecto!
