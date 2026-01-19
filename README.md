# Plataforma de Certificados Verificables (PDF + Código + QR)

Este proyecto nació de una necesidad real: en el **Cabildo Indígena La Peñata** (comunidad a la que pertenezco) se requería una herramienta para **generar certificados de forma ágil**, con **control administrativo**, y con un mecanismo de **verificación confiable** para evitar falsificaciones o dudas sobre su autenticidad.

La idea fue construir una aplicación web sencilla de usar, pero sólida por dentro: permite emitir certificados en PDF, registrar cada emisión y que cualquier entidad receptora pueda **validar el documento** usando un **código único** y un **QR**.

---

## ¿Qué problema resuelve?

En muchos procesos comunitarios y administrativos, los certificados se manejan de forma manual:
- se tarda más en emitirlos,
- es fácil perder el control de qué se generó y cuándo,
- y para terceros es difícil confirmar si un certificado es real.

Cuando un documento puede verificarse públicamente, se vuelve más **seguro**, **confiable** y **auditable**.

---

## ¿Qué ofrece la aplicación?

- **Emisión de certificados (PDF):** generación automática con datos del titular y fecha/hora de emisión, más un **código único**.
- **Verificación pública:** cada certificado incorpora un **QR** que lleva a una página donde se valida su autenticidad.
- **Panel de administración:** login para emisión y gestión, trazabilidad de actividad y administración del registro de ciudadanos.
- **Certificados especiales:** permite emitir documentos con contenido adicional/personalizado según el caso.

---

## Enfoque de seguridad y confianza

Además de funcionar, el proyecto se desarrolló con una mentalidad de **ciberseguridad práctica**, especialmente porque se trata de documentos que deben ser confiables.

- **Códigos únicos + verificación pública:** evita que “un PDF” por sí solo sea tomado como válido; el sistema confirma si existe y corresponde a lo registrado.
- **Tokens de verificación:** el flujo de emisión usa tokens temporales para controlar que solo se generen certificados tras una validación correcta.
- **Protección ante abuso (anti intentos):** controles de intentos y bloqueos temporales (por ejemplo en validaciones sensibles), para reducir automatizaciones o fuerza bruta.
- **Seguridad de sesión y formularios:** protección típica de aplicaciones web (manejo de sesión y medidas como **CSRF** en formularios del panel/admin).
- **Auditoría/trazabilidad:** registro de emisiones y eventos relevantes, útil para seguimiento y detección de comportamientos anómalos.
- **Cuidado de datos sensibles:** `.env`, base de datos local y archivos generados se excluyen del repositorio (pensado para publicar el proyecto sin exponer información real).

> Nota: este repositorio está publicado con fines de portafolio. No incluye datos reales.

---

## Cómo está organizada (estructura general)

La aplicación está dividida por responsabilidades para mantener el código claro y escalable:

- **Rutas / endpoints:** vistas públicas, API y administración.
- **Modelos:** usuarios, ciudadanos, certificados, intentos/bloqueos, etc.
- **Servicios:** lógica reutilizable (generación, verificación, búsquedas).
- **Generador de PDF:** componente dedicado para crear documentos de forma consistente.

Estructura aproximada:
- `app.py` / `run.py`: arranque y configuración
- `backend/`: rutas y lógica principal
- `models/`: persistencia / modelos
- `services/`: servicios
- `templates/` y `static/`: interfaz (HTML/CSS/JS)

---

## Tecnologías usadas

- **Python + Flask**
- **SQLAlchemy + SQLite**
- **ReportLab** (PDF)
- **HTML/CSS/JS**
- **QR** para verificación

---

## Lo más valioso del proyecto

Este proyecto demuestra habilidades en:
- construcción de una solución completa (UI + backend + datos),
- generación de PDFs desde servidor,
- verificación de autenticidad con códigos/QR,
- organización del código por capas,
- seguridad aplicada a un caso real (tokens, control de intentos, CSRF, auditoría y manejo de datos sensibles).

---

## Capturas / Demo (opcional)

Puedes agregar aquí:
- captura del formulario de verificación,
- captura del panel admin,
- captura de la página de validación,
- ejemplo de PDF (con datos anonimizados).

---

## Próximos pasos (ideas de mejora)

- Soporte para **múltiples tipos de certificados** y **plantillas** configurables.
- Habilitar modo **multitenant** para que la misma plataforma pueda ser usada por **varios cabildos del pueblo Zenú**, manteniendo **datos y certificados separados por cabildo** (configuración, usuarios, registros y verificación).
- Exportación de **reportes de auditoría** (por fechas, por cabildo, por tipo de certificado).
- **Roles y permisos** (multiusuario con distintos niveles de acceso).
- Migración a **PostgreSQL** para despliegues en producción.
- Firma digital criptográfica (si el contexto lo requiere).

---

## Aviso

Este repositorio se comparte como muestra de trabajo.  
Si vas a reutilizar la idea en un entorno real, asegúrate de ajustar políticas de privacidad, infraestructura y controles según el contexto.

---

**Autor:** Jairo Sevilla — *Proyecto en desarrollo*
