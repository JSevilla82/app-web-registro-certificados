# Cabildo Indígena de la Peñata — Certificados (Flask)

Plataforma para:
- Verificar ciudadanía en censo
- Generar certificados oficiales en **PDF desde el servidor**
- Validar certificados por **QR + URL pública**

## Requisitos

- Python 3.10+ (recomendado 3.11)

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # en Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Configuración

Copia `.env.example` a `.env` y ajusta valores.

En producción **debes** definir un `SECRET_KEY` fijo.

## Ejecutar

```bash
python app.py
```

Abrir:
- Inicio: `/`
- Generar certificado: `/certificado`

## Flujo (sin popups)

1) El usuario ingresa tipo y número de documento
2) Se muestra un modal interno **mínimo 3 segundos**: “Verificando…”
3) Si existe en el censo, se muestra “Estamos generando el documento…”
4) El backend genera el PDF, registra el evento, y se habilita “Descargar”

## Seguridad

- CSRF en requests POST (Flask-WTF)
- Rate limiting en endpoints sensibles (Flask-Limiter)
- Headers de seguridad (Flask-Talisman)
- Validación estricta de entradas (solo dígitos, tipos permitidos)

## Auditoría

Se registra cada certificado en la tabla `documentos_generados`:
- `creado_en`
- `ciudadano_id`
- `codigo` único
- `pdf_path`
- `descargado_en` y `descargas`


##################################################################################

Cómo usarlo (ejemplos)
Listar
python manage_users.py list
python manage_users.py list --limit 200
python manage_users.py list --search "Juan"

Ver un registro
python manage_users.py show --tipo CC --numero 12345678

Crear
python manage_users.py add --nombre "Juan Pérez" --tipo CC --numero 12345678 --nacimiento 1990-05-15

Actualizar
python manage_users.py update --tipo CC --numero 12345678 --nombre "Juan Pérez García"
python manage_users.py update --tipo CC --numero 12345678 --nacimiento 1990-05-15

Eliminar
python manage_users.py delete --tipo CC --numero 12345678

Importar/actualizar desde CSV

CSV con encabezados:
nombre_completo,tipo_documento,numero_documento,fecha_nacimiento

python manage_users.py import-csv datos.csv
python manage_users.py import-csv datos.csv --dry-run

Exportar a CSV
python manage_users.py export-csv export_ciudadanos.csv