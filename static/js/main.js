document.addEventListener('DOMContentLoaded', () => {
  const elAnio = document.getElementById('year');
  if (elAnio) elAnio.textContent = new Date().getFullYear();

  const desplegables = Array.from(document.querySelectorAll('.nav-dropdown'));
  desplegables.forEach((desplegable) => {
    const btnToggle = desplegable.querySelector('.nav-dropdown__toggle');
    const menuOpciones = desplegable.querySelector('.nav-dropdown__menu');
    if (!btnToggle) return;

    const posicionarMenu = () => {
      if (!menuOpciones) return;
      const rect = btnToggle.getBoundingClientRect();
      menuOpciones.style.position = 'fixed';
      menuOpciones.style.top = `${Math.round(rect.bottom)}px`;
      menuOpciones.style.left = `${Math.round(rect.left + 8)}px`;
      menuOpciones.style.zIndex = '2000';
    };

    const cerrarDesplegable = () => {
      desplegable.classList.remove('open');
      btnToggle.setAttribute('aria-expanded', 'false');
      if (menuOpciones) {
        menuOpciones.style.position = '';
        menuOpciones.style.top = '';
        menuOpciones.style.left = '';
        menuOpciones.style.zIndex = '';
      }
    };

    const abrirDesplegable = () => {
      desplegables.forEach((otro) => {
        if (otro !== desplegable) {
          otro.classList.remove('open');
          const t = otro.querySelector('.nav-dropdown__toggle');
          if (t) t.setAttribute('aria-expanded', 'false');
        }
      });

      desplegable.classList.add('open');
      btnToggle.setAttribute('aria-expanded', 'true');
      posicionarMenu();
    };

    btnToggle.addEventListener('click', (evento) => {
      evento.preventDefault();
      const estaAbierto = desplegable.classList.contains('open');
      if (estaAbierto) cerrarDesplegable(); else abrirDesplegable();
    });

    document.addEventListener('click', (evento) => {
      if (!desplegable.contains(evento.target)) cerrarDesplegable();
    });

    document.addEventListener('keydown', (evento) => {
      if (evento.key === 'Escape') cerrarDesplegable();
    });

    window.addEventListener('resize', () => {
      if (desplegable.classList.contains('open')) posicionarMenu();
    });
  });

  const navMovil = document.getElementById('navMobile');
  if (navMovil) {
    const btnToggleMovil = navMovil.querySelector('.nav-mobile__toggle');
    const objetivosCerrar = Array.from(navMovil.querySelectorAll('[data-nav-close]'));
    const enlaces = Array.from(navMovil.querySelectorAll('a.nav-mobile__link, a.nav-mobile__sublink'));
    const grupos = Array.from(navMovil.querySelectorAll('.nav-mobile__group'));

    const abrirNavMovil = () => {
      navMovil.classList.add('open');
      document.body.classList.add('no-scroll');
      if (btnToggleMovil) btnToggleMovil.setAttribute('aria-expanded', 'true');

      const grupoCertificados = navMovil.querySelector('.nav-mobile__group');
      if (grupoCertificados) {
        grupoCertificados.classList.add('open');
        const btnGrupo = grupoCertificados.querySelector('.nav-mobile__group-btn');
        if (btnGrupo) btnGrupo.setAttribute('aria-expanded', 'true');
      }
    };

    const cerrarNavMovil = () => {
      navMovil.classList.remove('open');
      document.body.classList.remove('no-scroll');
      if (btnToggleMovil) btnToggleMovil.setAttribute('aria-expanded', 'false');
    };

    if (btnToggleMovil) {
      btnToggleMovil.addEventListener('click', () => {
        const estaAbierto = navMovil.classList.contains('open');
        if (estaAbierto) cerrarNavMovil(); else abrirNavMovil();
      });
    }

    objetivosCerrar.forEach((el) => el.addEventListener('click', cerrarNavMovil));
    enlaces.forEach((a) => a.addEventListener('click', cerrarNavMovil));

    grupos.forEach((grupo) => {
      const boton = grupo.querySelector('.nav-mobile__group-btn');
      if (!boton) return;
      boton.setAttribute('aria-expanded', grupo.classList.contains('open') ? 'true' : 'false');
      boton.addEventListener('click', () => {
        grupo.classList.toggle('open');
        boton.setAttribute('aria-expanded', grupo.classList.contains('open') ? 'true' : 'false');
      });
    });

    document.addEventListener('keydown', (evento) => {
      if (evento.key === 'Escape') cerrarNavMovil();
    });
  }

  function soloDigitos(str) {
    return (str || '').replace(/\D/g, '');
  }

  function dormir(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  const tarjetaCert = document.getElementById('certCard');
  const segundosMinTransicion = tarjetaCert ? Number(tarjetaCert.getAttribute('data-min-transition') || '2') : 2;
  const msMinTransicion = Math.max(0, Math.round(segundosMinTransicion * 1000));

  const pasoFormulario = document.getElementById('stepForm');
  const pasoFechaNacimiento = document.getElementById('stepBirthdate');
  const pasoConfirmacion = document.getElementById('stepConfirm');
  const pasoCargando = document.getElementById('stepLoading');
  const pasoListo = document.getElementById('stepReady');
  const pasoError = document.getElementById('stepError');

  const tituloCargando = document.getElementById('loadingTitle');
  const subtituloCargando = document.getElementById('loadingSubtitle');

  const formulario = document.getElementById('certForm');
  const inputNumero = document.getElementById('docNumber');
  const selectTipo = document.getElementById('docType');
  const btnVerificar = document.getElementById('btnVerificar');

  const inputFechaNacimiento = document.getElementById('birthdateInput');
  const errorFechaNacimiento = document.getElementById('birthError');
  const btnConfirmarFecha = document.getElementById('btnConfirmarFecha');
  const btnSalir = document.getElementById('btnSalir');
  const btnOpenCalendar = document.getElementById('btnOpenCalendar');

  const confirmNombre = document.getElementById('confirmNombre');
  const confirmDoc = document.getElementById('confirmDoc');
  const btnConfirmAtras = document.getElementById('btnConfirmAtras');
  const btnConfirmGenerar = document.getElementById('btnConfirmGenerar');

  const bloqueErrorFormulario = document.getElementById('formError');
  const textoErrorFormulario = document.getElementById('formErrorText');
  const resNombre = document.getElementById('resNombre');
  const resDoc = document.getElementById('resDoc');
  const resCodigo = document.getElementById('resCodigo');
  const mensajeListo = document.getElementById('readyMsg');
  const btnDescargar = document.getElementById('btnDescargar');
  const btnVerCertificado = document.getElementById('btnVerCertificado');
  const verifyLink = document.getElementById('verifyLink');
  const btnOtraConsulta = document.getElementById('btnOtraConsulta');

  const textoError = document.getElementById('errorText');
  const btnReintentar = document.getElementById('btnReintentar');

  const tokenCsrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

  let ciudadanoActual = null;
  let documentoActual = { tipo: '', numero: '' };
  let tokenPendiente = null;

  function mostrarPaso(step) {
    if (pasoFormulario) pasoFormulario.style.display = 'none';
    if (pasoFechaNacimiento) pasoFechaNacimiento.style.display = 'none';
    if (pasoConfirmacion) pasoConfirmacion.style.display = 'none';
    if (pasoCargando) pasoCargando.style.display = 'none';
    if (pasoListo) pasoListo.style.display = 'none';
    if (pasoError) pasoError.style.display = 'none';
    if (step) step.style.display = 'block';

  }

  function mostrarCargando(title, subtitle) {
    if (tituloCargando) tituloCargando.textContent = title || 'Procesando...';
    if (subtituloCargando) subtituloCargando.textContent = subtitle || 'Por favor espere';
    mostrarPaso(pasoCargando);
  }

  function mostrarErrorFormulario(message) {
    if (!bloqueErrorFormulario || !textoErrorFormulario) return;
    textoErrorFormulario.textContent = message;
    bloqueErrorFormulario.style.display = 'block';
  }

  function ocultarErrorFormulario() {
    if (!bloqueErrorFormulario) return;
    bloqueErrorFormulario.style.display = 'none';
  }

  function mostrarErrorFecha(message) {
    if (!errorFechaNacimiento) return;
    errorFechaNacimiento.textContent = message;
    errorFechaNacimiento.style.display = 'block';
  }

  function ocultarErrorFecha() {
    if (!errorFechaNacimiento) return;
    errorFechaNacimiento.style.display = 'none';
  }

  function bloquearFormulario(locked) {
    if (btnVerificar) btnVerificar.disabled = locked;
    if (selectTipo) selectTipo.disabled = locked;
    if (inputNumero) inputNumero.disabled = locked;
  }

  // POST JSON con CSRF (si existe) y respuesta ya parseada.
  async function postJson(url, payload) {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(tokenCsrf ? { 'X-CSRFToken': tokenCsrf } : {})
      },
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  }

  function reiniciarFlujo() {
    ocultarErrorFormulario();
    ocultarErrorFecha();
    bloquearFormulario(false);

    ciudadanoActual = null;
    documentoActual = { tipo: '', numero: '' };
    tokenPendiente = null;

    if (inputFechaNacimiento) {
      inputFechaNacimiento.value = '';
      inputFechaNacimiento.classList.remove('has-value');
    }
    if (formulario) formulario.reset();

    mostrarPaso(pasoFormulario);
  }

  function mostrarConfirmacion(token, ciudadano) {
    tokenPendiente = token;
    ciudadanoActual = ciudadano;

    if (confirmNombre) confirmNombre.textContent = ciudadano?.nombre || '';
    if (confirmDoc) {
      const tipo = ciudadano?.tipo_doc || '';
      const mask = ciudadano?.num_doc_mask || '';
      confirmDoc.textContent = `${tipo} ${mask}`.trim();
    }

    mostrarPaso(pasoConfirmacion);
  }

  if (tarjetaCert) mostrarPaso(pasoFormulario);

  if (inputNumero) {
    inputNumero.addEventListener('input', () => {
      inputNumero.value = soloDigitos(inputNumero.value);
    });
  }

  if (inputFechaNacimiento) {
    const syncBirthdateClass = () => {
      inputFechaNacimiento.classList.toggle('has-value', !!inputFechaNacimiento.value);
    };
    inputFechaNacimiento.addEventListener('change', syncBirthdateClass);
    inputFechaNacimiento.addEventListener('input', syncBirthdateClass);
    syncBirthdateClass();
  }

  if (btnOpenCalendar && inputFechaNacimiento) {
    btnOpenCalendar.addEventListener('click', () => {
      try {
        inputFechaNacimiento.focus();
        if (typeof inputFechaNacimiento.showPicker === 'function') {
          inputFechaNacimiento.showPicker();
        }
      } catch (_) {
        inputFechaNacimiento.focus();
      }
    });
  }


  if (btnOtraConsulta) btnOtraConsulta.addEventListener('click', reiniciarFlujo);
  if (btnReintentar) btnReintentar.addEventListener('click', reiniciarFlujo);
  if (btnSalir) btnSalir.addEventListener('click', reiniciarFlujo);

  if (btnConfirmAtras) {
    btnConfirmAtras.addEventListener('click', () => {
      mostrarPaso(pasoFechaNacimiento);
      if (inputFechaNacimiento) inputFechaNacimiento.focus();
    });
  }

  if (btnConfirmGenerar) {
    btnConfirmGenerar.addEventListener('click', async () => {
      if (!tokenPendiente) {
        mostrarPaso(pasoFormulario);
        return;
      }
      await generarCertificadoConToken(tokenPendiente);
    });
  }

  // Micro-animación para dar feedback visual mientras el backend genera el PDF.
  async function animarGeneracion() {
    mostrarCargando('Generando certificado...', 'Preparando documento');
    await dormir(msMinTransicion);

    if (subtituloCargando) {
    subtituloCargando.innerHTML = 'Aplicando firma del Capitán Menor.<br>Registrando documento en el sistema de verificación.';
    }
    await dormir(2000);
  }

  // Genera el certificado en el servidor usando un token de verificación y actualiza la vista de resultados.
  async function generarCertificadoConToken(token) {
    const genPromise = postJson('/api/certificados/generar', { token }).catch(() => ({ ok: false, data: { message: 'Error de conexión' } }));
    const animPromise = animarGeneracion();

    const [genRes] = await Promise.all([genPromise, animPromise]);

    if (!genRes.ok || !genRes.data?.success) {
      bloquearFormulario(false);
      mostrarPaso(pasoError);
      if (textoError) textoError.textContent = genRes.data?.message || 'No fue posible generar el documento.';
      return;
    }

    if (resNombre) resNombre.textContent = ciudadanoActual?.nombre || '';
    if (resDoc) resDoc.textContent = ciudadanoActual?.num_doc_mask || '';
    if (resCodigo) resCodigo.textContent = genRes.data?.codigo || '';

    const urlDescarga = genRes.data?.download_url || '#';
    const urlVista = genRes.data?.view_url || '#';
    const urlVerificacion = genRes.data?.verify_url || '#';

    if (btnDescargar) btnDescargar.href = urlDescarga;
    if (btnVerCertificado) btnVerCertificado.href = urlVista;

    if (verifyLink) {
      verifyLink.href = urlVerificacion;
      verifyLink.textContent = urlVerificacion;
    }

    if (mensajeListo) {
      if (genRes.data?.recently_generated) {
        mensajeListo.textContent = 'Encontramos un certificado generado recientemente.';
      } else {
        mensajeListo.textContent = 'Puede descargar el archivo o visualizarlo en línea.';
      }
    }

    mostrarPaso(pasoListo);
  }

  if (btnConfirmarFecha) {
    btnConfirmarFecha.addEventListener('click', async () => {
      ocultarErrorFecha();

      const selectedIso = inputFechaNacimiento ? inputFechaNacimiento.value : '';
      if (!selectedIso) {
        mostrarErrorFecha('Debe seleccionar una fecha.');
        return;
      }

      mostrarCargando('Verificando identidad...', 'Validando fecha de nacimiento');

      const verifyPromise = postJson('/api/verificar/fecha-nacimiento', {
        tipo: documentoActual.tipo,
        numero: documentoActual.numero,
        birthdate: selectedIso
      }).catch(() => ({ ok: false, status: 0, data: { message: 'Error de conexión' } }));

      const [res] = await Promise.all([verifyPromise, dormir(msMinTransicion)]);

      if (!res.ok || !res.data?.success) {
        const seconds = res.data?.retry_after_seconds;
        if (seconds) {
          const mins = Math.ceil(seconds / 60);
          mostrarErrorFecha(`${res.data?.message || 'No fue posible validar.'} Tiempo de espera: ${mins} min.`);
        } else {
          mostrarErrorFecha(res.data?.message || 'No fue posible validar.');
        }
        mostrarPaso(pasoFechaNacimiento);
        return;
      }

      const token = res.data.token;
      ciudadanoActual = res.data.data;

      mostrarConfirmacion(token, ciudadanoActual);
    });
  }

  if (formulario) {
    formulario.addEventListener('submit', async (e) => {
      e.preventDefault();
      ocultarErrorFormulario();
      ocultarErrorFecha();

      const tipo = selectTipo?.value || '';
      const numero = soloDigitos(inputNumero?.value || '');

      if (!tipo || !numero) {
        mostrarErrorFormulario('Debe seleccionar el tipo e ingresar el número de documento.');
        return;
      }

      bloquearFormulario(true);
      mostrarCargando('Verificando identidad...', 'Consultando base de datos oficial del Cabildo');

      documentoActual = { tipo, numero };

      const verifyPromise = postJson('/api/verificar', { tipo, numero }).catch(() => ({ ok: false, data: { message: 'Error de conexión' } }));
      const [verifyRes] = await Promise.all([verifyPromise, dormir(msMinTransicion)]);

      if (!verifyRes.ok || !verifyRes.data?.success) {
        bloquearFormulario(false);
        mostrarPaso(pasoError);

        const seconds = verifyRes.data?.retry_after_seconds;
        if (seconds) {
          const mins = Math.ceil(seconds / 60);
          if (textoError) textoError.textContent = `${verifyRes.data?.message || 'No fue posible verificar la información.'} Tiempo de espera: ${mins} min.`;
        } else {
          if (textoError) textoError.textContent = verifyRes.data?.message || 'No fue posible verificar la información.';
        }
        return;
      }

      if (verifyRes.data?.requires_birthdate) {
        ciudadanoActual = verifyRes.data.data;
        if (inputFechaNacimiento) {
          inputFechaNacimiento.value = '';
          inputFechaNacimiento.classList.remove('has-value');
        }
        mostrarPaso(pasoFechaNacimiento);
        return;
      }

      // Token directo
      const token = verifyRes.data.token;
      ciudadanoActual = verifyRes.data.data;

      await generarCertificadoConToken(token);
    });
  }

  
  const tarjetaAdminCert = document.getElementById('adminCertCard');
  const formularioAdminCert = document.getElementById('adminCertForm');
  const inputAdminNumeroDoc = document.getElementById('adminDocNumber');
  const pasoAdminCertFormulario = document.getElementById('adminCertStepForm');
  const pasoAdminCertConfirm = document.getElementById('adminCertStepConfirm');
  const pasoAdminCertCargando = document.getElementById('adminCertStepLoading');
  const pasoAdminCertListo = document.getElementById('adminCertStepReady');
  const pasoAdminCertError = document.getElementById('adminCertStepError');

  const tituloAdminCargando = document.getElementById('adminLoadingTitle');
  const subtituloAdminCargando = document.getElementById('adminLoadingSubtitle');

  const bloqueErrorAdminFormulario = document.getElementById('adminFormError');
  const textoErrorAdminFormulario = document.getElementById('adminFormErrorText');

  const adminResNombre = document.getElementById('adminResNombre');
  const adminResDoc = document.getElementById('adminResDoc');
  const adminResCodigo = document.getElementById('adminResCodigo');
  const mensajeAdminListo = document.getElementById('adminReadyMsg');
  const btnAdminDescargar = document.getElementById('adminBtnDescargar');
  const btnAdminVerCertificado = document.getElementById('adminBtnVerCertificado');
  const enlaceAdminVerificacion = document.getElementById('adminVerifyLink');
  const btnAdminOtraConsulta = document.getElementById('adminBtnOtraConsulta');

  const adminConfirmNombre = document.getElementById('adminConfirmNombre');
  const adminConfirmDoc = document.getElementById('adminConfirmDoc');
  const btnAdminAtras = document.getElementById('adminBtnAtras');
  const btnAdminGenerarFinal = document.getElementById('adminBtnGenerarFinal');

  const textoAdminErrorCert = document.getElementById('adminCertErrorText');
  const btnAdminReintentar = document.getElementById('adminBtnReintentar');

  if (tarjetaAdminCert && formularioAdminCert && pasoAdminCertFormulario && pasoAdminCertConfirm && pasoAdminCertCargando && pasoAdminCertListo && pasoAdminCertError) {
    const minSecAttr = Number(tarjetaAdminCert.getAttribute('data-min-transition') || '0');
    const bodyMinSec = Number(document.body.getAttribute('data-ui-min-transition') || '2');
    const minMs = Math.max(0, Math.round(((minSecAttr || bodyMinSec || 2)) * 1000));

    let numeroPendiente = '';
    let ciudadanoPendiente = null;

    const mostrarPaso = (step) => {
      pasoAdminCertFormulario.style.display = 'none';
      pasoAdminCertConfirm.style.display = 'none';
      pasoAdminCertCargando.style.display = 'none';
      pasoAdminCertListo.style.display = 'none';
      pasoAdminCertError.style.display = 'none';
      step.style.display = 'block';
      step.classList.add('fade-in');
    };

    const mostrarErrorFormulario = (msg) => {
      if (!bloqueErrorAdminFormulario || !textoErrorAdminFormulario) return;
      textoErrorAdminFormulario.textContent = msg;
      bloqueErrorAdminFormulario.style.display = 'block';
    };

    const ocultarErrorFormulario = () => {
      if (!bloqueErrorAdminFormulario) return;
      bloqueErrorAdminFormulario.style.display = 'none';
    };

    const reset = () => {
      ocultarErrorFormulario();
      numeroPendiente = '';
      ciudadanoPendiente = null;
      if (inputAdminNumeroDoc) inputAdminNumeroDoc.value = '';
      mostrarPaso(pasoAdminCertFormulario);
    };

    const mostrarCargando = (title, subtitle) => {
      if (tituloAdminCargando) tituloAdminCargando.textContent = title || 'Procesando...';
      if (subtituloAdminCargando) subtituloAdminCargando.textContent = subtitle || 'Por favor espere';
      mostrarPaso(pasoAdminCertCargando);
    };

    const animarExito = async () => {
      mostrarCargando('Generando certificado...', 'Preparando documento');
      await dormir(1200);
      if (subtituloAdminCargando) {
      subtituloAdminCargando.textContent = 'Aplicando firma del Capitán Menor.<br>Registrando documento en el sistema de verificación.';
       }
       await dormir(1200);
    };

    if (inputAdminNumeroDoc) {
      inputAdminNumeroDoc.addEventListener('input', () => {
        inputAdminNumeroDoc.value = soloDigitos(inputAdminNumeroDoc.value);
      });
    }

    if (btnAdminOtraConsulta) btnAdminOtraConsulta.addEventListener('click', reset);
    if (btnAdminReintentar) btnAdminReintentar.addEventListener('click', reset);
    if (btnAdminAtras) {
      btnAdminAtras.addEventListener('click', () => {
        mostrarPaso(pasoAdminCertFormulario);
        if (inputAdminNumeroDoc) inputAdminNumeroDoc.focus();
      });
    }

    mostrarPaso(pasoAdminCertFormulario);

    formularioAdminCert.addEventListener('submit', async (e) => {
      e.preventDefault();
      ocultarErrorFormulario();

      const numero = soloDigitos(inputAdminNumeroDoc?.value || '');
      if (!numero) {
        mostrarErrorFormulario('Debe ingresar el número de documento.');
        mostrarPaso(pasoAdminCertFormulario);
        return;
      }

      mostrarCargando('Validando en el censo...', 'Comprobando afiliación');

      const valPromise = postJson('/api/admin/certificados/validar', { numero })
        .catch(() => ({ ok: false, data: { message: 'Error de conexión' } }));

      const [valRes] = await Promise.all([valPromise, dormir(minMs)]);

      if (!valRes.ok || !valRes.data?.success) {
        mostrarPaso(pasoAdminCertError);
        if (textoAdminErrorCert) textoAdminErrorCert.textContent = valRes.data?.message || 'No fue posible validar el documento.';
        return;
      }

      numeroPendiente = numero;
      ciudadanoPendiente = valRes.data?.data || null;
      if (adminConfirmNombre) adminConfirmNombre.textContent = ciudadanoPendiente?.nombre || '';
      if (adminConfirmDoc) {
        const tipo = ciudadanoPendiente?.tipo_doc || '';
        const mask = ciudadanoPendiente?.num_doc_mask || '';
        adminConfirmDoc.textContent = `${tipo} ${mask}`.trim();
      }

      mostrarPaso(pasoAdminCertConfirm);
    });

    const ejecutarGeneracionFinal = async () => {
      if (!numeroPendiente || !ciudadanoPendiente) {
        mostrarPaso(pasoAdminCertFormulario);
        return;
      }

      mostrarCargando('Procesando...', 'Enviando solicitud');

      const genPromise = postJson('/api/admin/certificados/generar', { numero: numeroPendiente })
        .catch(() => ({ ok: false, data: { message: 'Error de conexión' } }));

      const [genRes] = await Promise.all([genPromise, dormir(minMs)]);

      if (!genRes.ok || !genRes.data?.success) {
        mostrarPaso(pasoAdminCertError);
        if (textoAdminErrorCert) textoAdminErrorCert.textContent = genRes.data?.message || 'No fue posible generar el documento.';
        return;
      }

      await animarExito();

      const ciudadano = genRes.data?.data || {};
      if (adminResNombre) adminResNombre.textContent = ciudadano.nombre || '';
      if (adminResDoc) adminResDoc.textContent = ciudadano.num_doc_mask || '';
      if (adminResCodigo) adminResCodigo.textContent = genRes.data?.codigo || '';

      const urlDescarga = genRes.data?.download_url || '#';
      const urlVista = genRes.data?.view_url || '#';
      const urlVerificacion = genRes.data?.verify_url || '#';

      if (btnAdminDescargar) btnAdminDescargar.href = urlDescarga;
      if (btnAdminVerCertificado) btnAdminVerCertificado.href = urlVista;

      if (enlaceAdminVerificacion) {
        enlaceAdminVerificacion.href = urlVerificacion;
        enlaceAdminVerificacion.textContent = urlVerificacion;
      }

      if (mensajeAdminListo) {
        if (genRes.data?.recently_generated) {
          mensajeAdminListo.textContent = 'Encontramos un certificado generado recientemente (Admin).';
        } else {
          mensajeAdminListo.textContent = 'Puede descargar el archivo o visualizarlo en línea.';
        }
      }

      mostrarPaso(pasoAdminCertListo);
    };

    if (btnAdminGenerarFinal) btnAdminGenerarFinal.addEventListener('click', ejecutarGeneracionFinal);
  }

  const tarjetaAdminEspecial = document.getElementById('adminSpecialCard');
  const formularioAdminEspecialDoc = document.getElementById('adminSpecialDocForm');
  const formularioAdminEspecialTexto = document.getElementById('adminSpecialTextForm');
  const inputAdminEspecialNumero = document.getElementById('adminSpecialDocNumber');
  const inputAdminEspecialTexto = document.getElementById('adminSpecialTexto');

  const pasoAdminEspecialDoc = document.getElementById('adminSpecialStepDoc');
  const pasoAdminEspecialTexto = document.getElementById('adminSpecialStepText');
  const pasoAdminEspecialConfirm = document.getElementById('adminSpecialStepConfirm');
  const pasoAdminEspecialCargando = document.getElementById('adminSpecialStepLoading');
  const pasoAdminEspecialListo = document.getElementById('adminSpecialStepReady');
  const pasoAdminEspecialError = document.getElementById('adminSpecialStepError');

  const tituloAdminEspecialCargando = document.getElementById('adminSpecialLoadingTitle');
  const subtituloAdminEspecialCargando = document.getElementById('adminSpecialLoadingSubtitle');

  const bloqueErrorAdminEspecialDoc = document.getElementById('adminSpecialFormError');
  const textoErrorAdminEspecialDoc = document.getElementById('adminSpecialFormErrorText');
  const bloqueErrorAdminEspecialTexto = document.getElementById('adminSpecialTextError');
  const textoErrorAdminEspecialTexto = document.getElementById('adminSpecialTextErrorText');

  const resAdminEspecialNombre = document.getElementById('adminSpecialResNombre');
  const resAdminEspecialDoc = document.getElementById('adminSpecialResDoc');
  const previewAdminEspecialIntro = document.getElementById('adminSpecialIntroPreview');

  const confirmAdminEspecialNombre = document.getElementById('adminSpecialConfirmNombre');
  const confirmAdminEspecialDoc = document.getElementById('adminSpecialConfirmDoc');
  const confirmAdminEspecialTexto = document.getElementById('adminSpecialConfirmTexto');
  const btnAdminEspecialAtras = document.getElementById('adminSpecialBtnAtras');
  const btnAdminEspecialGenerarFinal = document.getElementById('adminSpecialBtnGenerarFinal');
  const btnAdminEspecialCambiarDoc2 = document.getElementById('adminSpecialBtnCambiarDoc2');

  const listoAdminEspecialNombre = document.getElementById('adminSpecialReadyNombre');
  const listoAdminEspecialDoc = document.getElementById('adminSpecialReadyDoc');
  const listoAdminEspecialCodigo = document.getElementById('adminSpecialReadyCodigo');
  const btnAdminEspecialDescargar = document.getElementById('adminSpecialBtnDescargar');
  const btnAdminEspecialVer = document.getElementById('adminSpecialBtnVerCertificado');
  const enlaceAdminEspecialVerificacion = document.getElementById('adminSpecialVerifyLink');

  const btnAdminEspecialCambiarDoc = document.getElementById('adminSpecialBtnCambiarDoc');
  const btnAdminEspecialOtra = document.getElementById('adminSpecialBtnOtra');
  const btnAdminEspecialReintentar = document.getElementById('adminSpecialBtnReintentar');
  const textoAdminEspecialError = document.getElementById('adminSpecialErrorText');

  if (
    tarjetaAdminEspecial &&
    formularioAdminEspecialDoc &&
    formularioAdminEspecialTexto &&
    pasoAdminEspecialDoc &&
    pasoAdminEspecialTexto &&
    pasoAdminEspecialConfirm &&
    pasoAdminEspecialCargando &&
    pasoAdminEspecialListo &&
    pasoAdminEspecialError
  ) {
    const minSecAttr = Number(tarjetaAdminEspecial.getAttribute('data-min-transition') || '0');
    const bodyMinSec = Number(document.body.getAttribute('data-ui-min-transition') || '2');
    const minMs = Math.max(0, Math.round(((minSecAttr || bodyMinSec || 2)) * 1000));

    let selectedNumero = '';
    let selectedCiudadano = null;
    let textoPendiente = '';

    const mostrarPaso = (step) => {
      pasoAdminEspecialDoc.style.display = 'none';
      pasoAdminEspecialTexto.style.display = 'none';
      pasoAdminEspecialConfirm.style.display = 'none';
      pasoAdminEspecialCargando.style.display = 'none';
      pasoAdminEspecialListo.style.display = 'none';
      pasoAdminEspecialError.style.display = 'none';
      step.style.display = 'block';
      step.classList.add('fade-in');
    };

    const mostrarCargando = (title, subtitle) => {
      if (tituloAdminEspecialCargando) tituloAdminEspecialCargando.textContent = title || 'Procesando...';
      if (subtituloAdminEspecialCargando) subtituloAdminEspecialCargando.textContent = subtitle || 'Por favor espere';
      mostrarPaso(pasoAdminEspecialCargando);
    };

    const showDocError = (msg) => {
      if (!bloqueErrorAdminEspecialDoc || !textoErrorAdminEspecialDoc) return;
      textoErrorAdminEspecialDoc.textContent = msg;
      bloqueErrorAdminEspecialDoc.style.display = 'block';
    };

    const hideDocError = () => {
      if (bloqueErrorAdminEspecialDoc) bloqueErrorAdminEspecialDoc.style.display = 'none';
    };

    const showTextError = (msg) => {
      if (!bloqueErrorAdminEspecialTexto || !textoErrorAdminEspecialTexto) return;
      textoErrorAdminEspecialTexto.textContent = msg;
      bloqueErrorAdminEspecialTexto.style.display = 'block';
    };

    const hideTextError = () => {
      if (bloqueErrorAdminEspecialTexto) bloqueErrorAdminEspecialTexto.style.display = 'none';
    };

    const resetAll = () => {
      hideDocError();
      hideTextError();
      selectedNumero = '';
      selectedCiudadano = null;
      textoPendiente = '';
      if (inputAdminEspecialNumero) inputAdminEspecialNumero.value = '';
      if (inputAdminEspecialTexto) inputAdminEspecialTexto.value = '';
      mostrarPaso(pasoAdminEspecialDoc);
    };

    const volverATexto = () => {
      hideTextError();
      textoPendiente = '';
      mostrarPaso(pasoAdminEspecialTexto);
      if (inputAdminEspecialTexto) inputAdminEspecialTexto.focus();
    };

    const capitalizarPrimera = (t) => {
      const s = (t || '').trim();
      if (!s) return '';
      return s.charAt(0).toUpperCase() + s.slice(1);
    };

    const animarExito = async () => {
      mostrarCargando('Generando certificado especial...', 'Preparando documento');
      await dormir(1200);
      if (subtituloAdminEspecialCargando) {
      subtituloAdminEspecialCargando.textContent = 'Aplicando firma del Capitán Menor.<br>Registrando documento en el sistema de verificación.';
      }
      await dormir(2400);
    };

    

    // Solo números
    if (inputAdminEspecialNumero) {
      inputAdminEspecialNumero.addEventListener('input', () => {
        inputAdminEspecialNumero.value = soloDigitos(inputAdminEspecialNumero.value);
      });
    }

    if (btnAdminEspecialCambiarDoc) btnAdminEspecialCambiarDoc.addEventListener('click', resetAll);
    if (btnAdminEspecialCambiarDoc2) btnAdminEspecialCambiarDoc2.addEventListener('click', resetAll);
    if (btnAdminEspecialOtra) btnAdminEspecialOtra.addEventListener('click', resetAll);
    if (btnAdminEspecialReintentar) btnAdminEspecialReintentar.addEventListener('click', resetAll);
    if (btnAdminEspecialAtras) btnAdminEspecialAtras.addEventListener('click', volverATexto);

    mostrarPaso(pasoAdminEspecialDoc);

    formularioAdminEspecialDoc.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideDocError();

      const numero = soloDigitos(inputAdminEspecialNumero?.value || '');
      if (!numero) {
        showDocError('Debe ingresar el número de documento.');
        mostrarPaso(pasoAdminEspecialDoc);
        return;
      }

      selectedNumero = numero;

      mostrarCargando('Validando en el censo...', 'Comprobando afiliación');

      const valPromise = postJson('/api/admin/certificados/especial/validar', { numero })
        .catch(() => ({ ok: false, data: { message: 'Error de conexión' } }));

      const [valRes] = await Promise.all([valPromise, dormir(minMs)]);

      if (!valRes.ok || !valRes.data?.success) {
        mostrarPaso(pasoAdminEspecialError);
        if (textoAdminEspecialError) textoAdminEspecialError.textContent = valRes.data?.message || 'No fue posible validar el documento.';
        return;
      }

      selectedCiudadano = valRes.data?.data || null;

      // UI
      if (resAdminEspecialNombre) resAdminEspecialNombre.textContent = selectedCiudadano?.nombre || '';
      if (resAdminEspecialDoc) resAdminEspecialDoc.textContent = `${selectedCiudadano?.tipo_doc || ''} ${selectedCiudadano?.num_doc_mask || ''}`.trim();

      const intro = `${selectedCiudadano?.nombre || ''} identificado(a) con ${selectedCiudadano?.tipo_doc || ''} No. ${selectedNumero}.`;
      if (previewAdminEspecialIntro) previewAdminEspecialIntro.textContent = intro;

      mostrarPaso(pasoAdminEspecialTexto);
    });

    const ejecutarGeneracionEspecial = async () => {
      if (!selectedNumero || !selectedCiudadano || !textoPendiente) {
        mostrarPaso(pasoAdminEspecialDoc);
        return;
      }

      mostrarCargando('Procesando...', 'Enviando solicitud');

      const genPromise = postJson('/api/admin/certificados/especial/generar', { numero: selectedNumero, texto: textoPendiente })
        .catch(() => ({ ok: false, data: { message: 'Error de conexión' } }));

      const [genRes] = await Promise.all([genPromise, dormir(minMs)]);

      if (!genRes.ok || !genRes.data?.success) {
        mostrarPaso(pasoAdminEspecialError);
        if (textoAdminEspecialError) textoAdminEspecialError.textContent = genRes.data?.message || 'No fue posible generar el documento.';
        return;
      }

      await animarExito();

      const ciudadano = genRes.data?.data || {};
      if (listoAdminEspecialNombre) listoAdminEspecialNombre.textContent = ciudadano.nombre || '';
      if (listoAdminEspecialDoc) listoAdminEspecialDoc.textContent = ciudadano.num_doc_mask ? `${ciudadano.tipo_doc || ''} ${ciudadano.num_doc_mask}`.trim() : '';
      if (listoAdminEspecialCodigo) listoAdminEspecialCodigo.textContent = genRes.data?.codigo || '';

      const urlDescarga = genRes.data?.download_url || '#';
      const urlVista = genRes.data?.view_url || '#';
      const urlVerificacion = genRes.data?.verify_url || '#';

      if (btnAdminEspecialDescargar) btnAdminEspecialDescargar.href = urlDescarga;
      if (btnAdminEspecialVer) btnAdminEspecialVer.href = urlVista;
      if (enlaceAdminEspecialVerificacion) {
        enlaceAdminEspecialVerificacion.href = urlVerificacion;
        enlaceAdminEspecialVerificacion.textContent = urlVerificacion;
      }

      mostrarPaso(pasoAdminEspecialListo);
    };

    if (btnAdminEspecialGenerarFinal) {
      btnAdminEspecialGenerarFinal.addEventListener('click', ejecutarGeneracionEspecial);
    }

    formularioAdminEspecialTexto.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideTextError();

      if (!selectedNumero || !selectedCiudadano) {
        mostrarPaso(pasoAdminEspecialDoc);
        return;
      }

      const raw = (inputAdminEspecialTexto?.value || '');
      const texto = capitalizarPrimera(raw);

      if (!texto) {
        showTextError('Debe escribir el texto personalizado.');
        mostrarPaso(pasoAdminEspecialTexto);
        return;
      }

      textoPendiente = texto;

      if (confirmAdminEspecialNombre) confirmAdminEspecialNombre.textContent = selectedCiudadano?.nombre || '';
      if (confirmAdminEspecialDoc) confirmAdminEspecialDoc.textContent = `${selectedCiudadano?.tipo_doc || ''} ${selectedCiudadano?.num_doc_mask || ''}`.trim();
      if (confirmAdminEspecialTexto) confirmAdminEspecialTexto.textContent = textoPendiente;

      mostrarPaso(pasoAdminEspecialConfirm);
    });
  }

  const formularioLoginAdmin = document.getElementById('adminLoginForm');
  const tarjetaLoginAdmin = document.getElementById('adminLoginCard');
  const pasoLoginAdminFormulario = document.getElementById('adminStepForm');
  const pasoLoginAdminCargando = document.getElementById('adminStepLoading');
  const bloqueErrorLoginAdmin = document.getElementById('adminError');
  const textoErrorLoginAdmin = document.getElementById('adminErrorText');

  if (formularioLoginAdmin && pasoLoginAdminFormulario && pasoLoginAdminCargando) {
    const minSecAttr = tarjetaLoginAdmin ? Number(tarjetaLoginAdmin.getAttribute('data-min-transition') || '0') : 0;
    const bodyMinSec = Number(document.body.getAttribute('data-ui-min-transition') || '2');
    const minMs = Math.max(0, Math.round(((minSecAttr || bodyMinSec || 2)) * 1000));

    const showAdminStep = (step) => {
      pasoLoginAdminFormulario.style.display = 'none';
      pasoLoginAdminCargando.style.display = 'none';
      step.style.display = 'block';
      step.classList.add('fade-in');
    };

    const showAdminError = (msg) => {
      if (!bloqueErrorLoginAdmin || !textoErrorLoginAdmin) return;
      textoErrorLoginAdmin.textContent = msg;
      bloqueErrorLoginAdmin.style.display = 'block';
    };

    const hideAdminError = () => {
      if (!bloqueErrorLoginAdmin) return;
      bloqueErrorLoginAdmin.style.display = 'none';
    };

    showAdminStep(pasoLoginAdminFormulario);

    formularioLoginAdmin.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideAdminError();

      const user = (document.getElementById('adminUser')?.value || '').trim();
      const pass = (document.getElementById('adminPass')?.value || '').trim();

      if (!user || !pass) {
        showAdminError('Debe ingresar usuario y contraseña.');
        showAdminStep(pasoLoginAdminFormulario);
        return;
      }

      showAdminStep(pasoLoginAdminCargando);
      await dormir(minMs);
      formularioLoginAdmin.submit();
    });
  }

  // -----------------------------
  // Admin: Cambio de contrasena
  const formularioCambioClave = document.getElementById('adminChangePassForm');
  const tarjetaCambioClave = document.getElementById('adminChangeCard');
  const pasoCambioClaveFormulario = document.getElementById('adminChangeStepForm');
  const pasoCambioClaveCargando = document.getElementById('adminChangeStepLoading');
  const bloqueErrorCambioClave = document.getElementById('adminChangeError');
  const textoErrorCambioClave = document.getElementById('adminChangeErrorText');

  if (formularioCambioClave && pasoCambioClaveFormulario && pasoCambioClaveCargando) {
    const minSecAttr = tarjetaCambioClave ? Number(tarjetaCambioClave.getAttribute('data-min-transition') || '0') : 0;
    const bodyMinSec = Number(document.body.getAttribute('data-ui-min-transition') || '2');
    const minMs = Math.max(0, Math.round(((minSecAttr || bodyMinSec || 2)) * 1000));

    const mostrarPaso = (step) => {
      pasoCambioClaveFormulario.style.display = 'none';
      pasoCambioClaveCargando.style.display = 'none';
      step.style.display = 'block';
      step.classList.add('fade-in');
    };

    const showError = (msg) => {
      if (!bloqueErrorCambioClave || !textoErrorCambioClave) return;
      textoErrorCambioClave.textContent = msg;
      bloqueErrorCambioClave.style.display = 'block';
    };

    const hideError = () => {
      if (!bloqueErrorCambioClave) return;
      bloqueErrorCambioClave.style.display = 'none';
    };

    mostrarPaso(pasoCambioClaveFormulario);

    formularioCambioClave.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideError();

      const p1 = (document.getElementById('newPass')?.value || '').trim();
      const p2 = (document.getElementById('confirmPass')?.value || '').trim();

      if (!p1 || !p2) {
        showError('Debe ingresar y confirmar la contrasena.');
        mostrarPaso(pasoCambioClaveFormulario);
        return;
      }

      if (p1 !== p2) {
        showError('Las contrasenas no coinciden.');
        mostrarPaso(pasoCambioClaveFormulario);
        return;
      }

      mostrarPaso(pasoCambioClaveCargando);
      await dormir(minMs);
      formularioCambioClave.submit();
    });
  }

  // -----------------------------
  // Admin: Gestión de ciudadanos
  const inputAdminCiudadanoNumero = document.getElementById('numero');
  if (inputAdminCiudadanoNumero) {
    inputAdminCiudadanoNumero.addEventListener('input', () => {
      inputAdminCiudadanoNumero.value = soloDigitos(inputAdminCiudadanoNumero.value);
    });
  }

  const formulariosConfirmacion = Array.from(document.querySelectorAll('form[data-confirm]'));
  formulariosConfirmacion.forEach((formularioEl) => {
    formularioEl.addEventListener('submit', async (e) => {
      const msg = formularioEl.getAttribute('data-confirm') || '¿Está seguro?';

      const canSwal = !!(window.Swal && typeof window.Swal.fire === 'function');
      if (!canSwal) {
        if (!window.confirm(msg)) {
          e.preventDefault();
          e.stopPropagation();
        }
        return;
      }

      e.preventDefault();
      e.stopPropagation();

      const submitBtn = formularioEl.querySelector('button[type="submit"]');
      const isDanger = !!(submitBtn && submitBtn.classList.contains('btn-small--danger'));
      const isWarn = !!(submitBtn && submitBtn.classList.contains('btn-small--warn'));

      const title = isDanger ? 'Confirmar eliminación' : (isWarn ? 'Confirmar cambio' : 'Confirmación');
      const confirmText = isDanger ? 'Sí, eliminar' : 'Sí, continuar';

      const result = await window.Swal.fire({
        title,
        text: msg,
        icon: isDanger ? 'warning' : 'question',
        showCancelButton: true,
        confirmButtonText: confirmText,
        cancelButtonText: 'Cancelar',
        reverseButtons: true,
        focusCancel: true,
        confirmButtonColor: isDanger ? '#d33' : (isWarn ? '#d4af37' : '#0f3a5f'),
      });

      if (result.isConfirmed) {
        formularioEl.submit();
      }
    });
  });

  const flashEl = document.querySelector('[data-flash-kind][data-flash-text]');
  if (flashEl && window.Swal && typeof window.Swal.fire === 'function') {
    const kind = (flashEl.getAttribute('data-flash-kind') || 'info').toLowerCase();
    const text = flashEl.getAttribute('data-flash-text') || '';

    const iconMap = {
      success: 'success',
      error: 'error',
      warning: 'warning',
      info: 'info',
    };

    const titleMap = {
      success: 'Listo',
      error: 'Error',
      warning: 'Atención',
      info: 'Información',
    };

    window.Swal.fire({
      title: titleMap[kind] || 'Información',
      text,
      icon: iconMap[kind] || 'info',
      confirmButtonText: 'Aceptar',
      confirmButtonColor: '#0B2F4E',
    });
  }

  const verificacionCargando = document.getElementById('verifyLoading');
  const verificacionContenido = document.getElementById('verifyContent');
  const verificacionSegundosMinimos = Number(document.body.getAttribute('data-verify-min-seconds') || '0');

  if (verificacionCargando && verificacionContenido) {
    const enabled = (verificacionCargando.getAttribute('data-enable') || '1') === '1';
    if (!enabled) {
      verificacionCargando.style.display = 'none';
      verificacionContenido.style.display = 'block';
    } else {
      const ms = Math.max(0, Math.round((verificacionSegundosMinimos || segundosMinTransicion || 2) * 1000));
      verificacionContenido.style.display = 'none';
      verificacionCargando.style.display = 'block';
      dormir(ms).then(() => {
        verificacionCargando.style.display = 'none';
        verificacionContenido.style.display = 'block';
        verificacionContenido.classList.add('fade-in');
      });
    }
  }
});
