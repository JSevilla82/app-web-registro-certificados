# Plataforma de Certificados Verificables (PDF + Código + QR)

Este proyecto nació de una necesidad real: en el **Cabildo Indígena La Peñata** en sincelejo sucre, se requería una herramienta para **generar certificados de forma ágil**, con **control administrativo**, y con un mecanismo de **verificación confiable** para evitar falsificaciones o dudas sobre su autenticidad.

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

## Capturas 

<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/005e83dd-d34c-4341-8aa5-662ad38345d1" width="300"/></td>
    <td><img src="https://github.com/user-attachments/assets/a4e90f96-e6b5-4633-b040-173db4953e76" width="300"/></td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/71e1d033-eae3-4ddd-b953-b8301eef564e" width="300"/></td>
    <td><img src="https://github.com/user-attachments/assets/121c2252-241d-4faf-94a0-881ddf0f8ef4" width="300"/></td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/ab70c9fb-5ed5-4d2a-89ee-e8c31e8dcd65" width="300"/></td>
    <td><img src="https://github.com/user-attachments/assets/c2956f05-5398-4d4c-a83d-62ca1508fd46" width="300"/></td>
  </tr>
</table>

<img width="1352" height="910" alt="Screenshot_1 (1)" src="https://github.com/user-attachments/assets/a029aa8e-cb51-4b34-9912-3d52eff046f4" />
![certificado_CIP202601210125486161_page-0001 (2)](https://github.com/user-attachments/assets/c1b39540-0948-4c1a-9efc-971e6d8c4150)

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

---

**Autor:** Jairo Sevilla — *Proyecto en desarrollo*
