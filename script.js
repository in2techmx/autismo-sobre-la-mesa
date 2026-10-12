/* ═══════════════════════════════════════════════════════
   EL AUTISMO SOBRE LA MESA — Interactive Behaviors
   ═══════════════════════════════════════════════════════
   Progressive enhancement layer. The page works without
   JS thanks to CSS scroll-driven animations. This adds:
   1. Reading progress bar
   2. Active chapter navigation
   3. Fallback animations for older browsers
   4. Stat ribbon duplication for seamless marquee
   ═══════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // Guard for SSR / test environments
  if (typeof document === 'undefined' || typeof window === 'undefined') return;

  /* ─── 1. READING PROGRESS BAR ─── */
  const progressBar = document.getElementById('readingProgress');

  function updateProgress() {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    if (progressBar) {
      progressBar.style.width = progress + '%';
    }
  }

  /* ─── 2. CHAPTER NAVIGATION — Active dot tracking ─── */
  const navDots = document.querySelectorAll('.nav-dot');
  const sections = [];

  navDots.forEach(function (dot) {
    const href = dot.getAttribute('href');
    if (href) {
      const target = document.querySelector(href);
      if (target) {
        sections.push({ el: target, dot: dot });
      }
    }
  });

  function updateActiveNav() {
    const scrollPos = window.scrollY + window.innerHeight * 0.35;

    let activeIndex = 0;
    for (let i = sections.length - 1; i >= 0; i--) {
      if (sections[i].el.offsetTop <= scrollPos) {
        activeIndex = i;
        break;
      }
    }

    sections.forEach(function (section, index) {
      if (index === activeIndex) {
        section.dot.classList.add('active');
      } else {
        section.dot.classList.remove('active');
      }
    });
  }

  /* ─── 3. STAT RIBBON — Duplicate for seamless marquee ─── */
  const ribbonTrack = document.querySelector('.stat-ribbon__track');
  if (ribbonTrack) {
    const clone = ribbonTrack.innerHTML;
    ribbonTrack.innerHTML = clone + clone;
  }

  /* ─── 4. FALLBACK: IntersectionObserver for older browsers ─── */
  function supportsScrollTimeline() {
    return CSS.supports('animation-timeline', 'view()');
  }

  if (!supportsScrollTimeline()) {
    // Fallback: use IntersectionObserver for reveal animations
    const revealElements = document.querySelectorAll(
      '.narrative-block, .sensory-list__item, .sense-map__item, ' +
      '.profile-card, .journey-step, .strategy-card, .alert-sign, ' +
      '.team-member, .resource-item, .chapter__number, .chapter__title, ' +
      '.immersive-divider__text'
    );

    const observerOptions = {
      root: null,
      rootMargin: '0px 0px -60px 0px',
      threshold: 0.15
    };

    const revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0) scale(1)';
          entry.target.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
          revealObserver.unobserve(entry.target);
        }
      });
    }, observerOptions);

    revealElements.forEach(function (el) {
      // Reset initial state for fallback
      el.style.opacity = '0';
      el.style.transform = 'translateY(30px)';
      el.style.animation = 'none';
      revealObserver.observe(el);
    });
  }

  /* ─── 5. SMOOTH SCROLL for nav dots ─── */
  navDots.forEach(function (dot) {
    dot.addEventListener('click', function (e) {
      e.preventDefault();
      const href = this.getAttribute('href');
      const target = document.querySelector(href);
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });

  /* ─── 6. THROTTLED SCROLL HANDLER ─── */
  let ticking = false;

  function onScroll() {
    if (!ticking) {
      requestAnimationFrame(function () {
        updateProgress();
        updateActiveNav();
        ticking = false;
      });
      ticking = true;
    }
  }

  window.addEventListener('scroll', onScroll, { passive: true });

  // Initial call
  updateProgress();
  updateActiveNav();

  /* ─── 7. CHARACTER FRAME TILT (subtle 3D on hover) ─── */
  const characterFrames = document.querySelectorAll('.character-frame');

  characterFrames.forEach(function (frame) {
    frame.addEventListener('mousemove', function (e) {
      const rect = frame.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const deltaX = (x - rect.width / 2) / (rect.width / 2);
      const deltaY = (y - rect.height / 2) / (rect.height / 2);
      const rotX = (-(deltaY * 6)).toFixed(2);
      const rotY = (deltaX * 6).toFixed(2);

      frame.style.transform =
        'perspective(800px) rotateX(' + rotX + 'deg) rotateY(' + rotY + 'deg) translateY(-8px) scale(1.01)';
    });

    frame.addEventListener('mouseleave', function () {
      frame.style.transform = '';
    });
  });

  /* ─── 8. CUADERNO / LIBRO INTERACTIVO TFM (Flipbook) ─── */
  const tfmPages = document.querySelectorAll('.tfm-page');
  const tfmDots = document.querySelectorAll('.tfm-dot');
  const tfmPrevBtn = document.getElementById('tfmPrevBtn');
  const tfmNextBtn = document.getElementById('tfmNextBtn');
  let currentTfmPage = 1;
  const totalTfmPages = tfmPages.length;

  function showTfmPage(pageNum) {
    if (pageNum < 1 || pageNum > totalTfmPages) return;
    currentTfmPage = pageNum;

    tfmPages.forEach(function (page) {
      const p = parseInt(page.getAttribute('data-page'), 10);
      if (p === currentTfmPage) {
        page.classList.add('active');
      } else {
        page.classList.remove('active');
      }
    });

    tfmDots.forEach(function (dot) {
      const p = parseInt(dot.getAttribute('data-page'), 10);
      if (p === currentTfmPage) {
        dot.classList.add('active');
      } else {
        dot.classList.remove('active');
      }
    });

    if (tfmPrevBtn) tfmPrevBtn.disabled = currentTfmPage === 1;
    if (tfmNextBtn) tfmNextBtn.disabled = currentTfmPage === totalTfmPages;
  }

  if (tfmPrevBtn) {
    tfmPrevBtn.addEventListener('click', function () {
      showTfmPage(currentTfmPage - 1);
    });
  }

  if (tfmNextBtn) {
    tfmNextBtn.addEventListener('click', function () {
      showTfmPage(currentTfmPage + 1);
    });
  }

  tfmDots.forEach(function (dot) {
    dot.addEventListener('click', function () {
      const page = parseInt(this.getAttribute('data-page'), 10);
      showTfmPage(page);
    });
  });

  // Soporte de swipe táctil para móviles en el libro
  const tfmBook = document.getElementById('tfmBook');
  if (tfmBook) {
    let touchStartX = 0;
    let touchEndX = 0;

    tfmBook.addEventListener('touchstart', function (e) {
      touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    tfmBook.addEventListener('touchend', function (e) {
      touchEndX = e.changedTouches[0].screenX;
      const diff = touchStartX - touchEndX;
      if (Math.abs(diff) > 40) {
        if (diff > 0) {
          // Swipe a la izquierda -> siguiente
          showTfmPage(currentTfmPage + 1);
        } else {
          // Swipe a la derecha -> anterior
          showTfmPage(currentTfmPage - 1);
        }
      }
    }, { passive: true });
  }

  /* ─── 9. CUESTIONARIO INTERACTIVO BAMBI (18 Ítems + Ítems Inversos) ─── */
  const BAMBI_ITEMS = [
    { id: 1, text: "1. Llora o grita durante las comidas.", factor: "refusal", reverse: false },
    { id: 2, text: "2. Gira la cara o el cuerpo para alejarse de la comida cuando se le ofrece.", factor: "refusal", reverse: false },
    { id: 3, text: "3. Permanece sentado/a en la mesa hasta que termina la comida. (Ítem inverso)", factor: "disruptive", reverse: true },
    { id: 4, text: "4. Escupe o expulsa la comida que ya se ha metido en la boca.", factor: "refusal", reverse: false },
    { id: 5, text: "5. Muestra conductas agresivas durante las comidas (golpear, empujar, pellizcar).", factor: "disruptive", reverse: false },
    { id: 6, text: "6. Muestra conductas autolesivas durante las comidas (morderse, golpearse).", factor: "disruptive", reverse: false },
    { id: 7, text: "7. Es disruptivo/a durante las comidas (empuja o avienta los platos, cubiertos o comida).", factor: "disruptive", reverse: false },
    { id: 8, text: "8. Cierra la boca con fuerza cuando se le presenta o acerca la comida.", factor: "refusal", reverse: false },
    { id: 9, text: "9. Es flexible con las rutinas de la comida (ej. horarios, lugar en la mesa o utensilios). (Ítem inverso)", factor: "disruptive", reverse: true },
    { id: 10, text: "10. Está dispuesto/a a probar alimentos nuevos. (Ítem inverso)", factor: "selectivity", reverse: true },
    { id: 11, text: "11. Le desagradan ciertos alimentos y se niega a comerlos.", factor: "selectivity", reverse: false },
    { id: 12, text: "12. Se niega a comer alimentos que requieren mucha masticación.", factor: "refusal", reverse: false },
    { id: 13, text: "13. Prefiere que le sirvan los mismos alimentos en cada comida.", factor: "selectivity", reverse: false },
    { id: 14, text: "14. Prefiere alimentos \"crujientes\" (ej. snacks, galletas saladas, cereales secos).", factor: "selectivity", reverse: false },
    { id: 15, text: "15. Acepta y consume una variedad de alimentos. (Ítem inverso)", factor: "selectivity", reverse: true },
    { id: 16, text: "16. Prefiere que los alimentos se le sirvan de una manera o presentación particular.", factor: "selectivity", reverse: false },
    { id: 17, text: "17. Prefiere únicamente alimentos dulces (ej. caramelos, cereales azucarados, postres).", factor: "selectivity", reverse: false },
    { id: 18, text: "18. Prefiere alimentos preparados de una forma específica (ej. principalmente fritos, fríos o crudos).", factor: "selectivity", reverse: false }
  ];

  const FACTOR_LABELS = {
    refusal: "🧃 Rechazo Alimentario",
    selectivity: "🥦 Selectividad Alimentaria",
    disruptive: "🪑 Conductas en la Mesa"
  };

  const LIKERT_OPTIONS = [
    { val: 1, label: "1 • Nunca / Raramente" },
    { val: 2, label: "2 • Pocas veces" },
    { val: 3, label: "3 • A veces" },
    { val: 4, label: "4 • A menudo" },
    { val: 5, label: "5 • Siempre" }
  ];

  const bambiToggleBtn = document.getElementById('bambiToggleBtn');
  const bambiForm = document.getElementById('bambiForm');
  const bambiQuestionsList = document.getElementById('bambiQuestionsList');
  const bambiCalcBtn = document.getElementById('bambiCalcBtn');
  const bambiResetBtn = document.getElementById('bambiResetBtn');
  const bambiResults = document.getElementById('bambiResults');

  function renderBambiQuestions() {
    if (!bambiQuestionsList) return;
    let html = '';
    BAMBI_ITEMS.forEach(function (item) {
      let optionsHtml = '';
      LIKERT_OPTIONS.forEach(function (opt) {
        const checked = opt.val === 1 ? 'checked' : '';
        optionsHtml +=
          '<label class="bambi-option-label">' +
          '<input type="radio" name="bambi_q_' + item.id + '" value="' + opt.val + '" ' + checked + '>' +
          '<span>' + opt.label + '</span>' +
          '</label>';
      });

      html +=
        '<div class="bambi-item">' +
        '<div class="bambi-item__top">' +
        '<span class="bambi-item__q">' + item.text + '</span>' +
        '<span class="bambi-item__tag">' + FACTOR_LABELS[item.factor] + '</span>' +
        '</div>' +
        '<div class="bambi-item__options">' + optionsHtml + '</div>' +
        '</div>';
    });
    bambiQuestionsList.innerHTML = html;
  }

  if (bambiToggleBtn && bambiForm) {
    renderBambiQuestions();
    bambiToggleBtn.addEventListener('click', function () {
      const isHidden = bambiForm.hasAttribute('hidden');
      if (isHidden) {
        bambiForm.removeAttribute('hidden');
        bambiToggleBtn.setAttribute('aria-expanded', 'true');
        bambiToggleBtn.textContent = '🔼 Ocultar Cuestionario BAMBI';
      } else {
        bambiForm.setAttribute('hidden', '');
        bambiToggleBtn.setAttribute('aria-expanded', 'false');
        bambiToggleBtn.textContent = '📝 Realizar Cuestionario BAMBI Interactivo (18 preguntas)';
      }
    });
  }

  if (bambiCalcBtn) {
    bambiCalcBtn.addEventListener('click', function () {
      let total = 0;
      let refusal = 0;
      let selectivity = 0;
      let disruptive = 0;

      BAMBI_ITEMS.forEach(function (item) {
        const selected = document.querySelector('input[name="bambi_q_' + item.id + '"]:checked');
        const rawVal = selected ? parseInt(selected.value, 10) : 1;
        const scoredVal = item.reverse ? (6 - rawVal) : rawVal;

        total += scoredVal;
        if (item.factor === 'refusal') refusal += scoredVal;
        if (item.factor === 'selectivity') selectivity += scoredVal;
        if (item.factor === 'disruptive') disruptive += scoredVal;
      });

      const totalEl = document.getElementById('bambiTotalScore');
      const interpEl = document.getElementById('bambiClinicalInterpretation');
      const adviceEl = document.getElementById('bambiClinicalAdvice');

      if (totalEl) totalEl.textContent = String(total);

      if (total >= 34) {
        if (interpEl) {
          interpEl.textContent = 'Puntaje ≥ 34: Dificultad Alimentaria Clínicamente Significativa';
          interpEl.style.color = '#A64B3A';
        }
        if (adviceEl) {
          adviceEl.textContent =
            'Estadísticamente, una puntuación igual o superior a 34 puntos en el inventario BAMBI indica desafíos importantes en la alimentación. Te recomendamos llevar este desglose como línea base a un equipo multidisciplinar (Terapia Ocupacional en Integración Sensorial, Nutrición Pediátrica y Logopedia) y acompañar en casa sin presiones ni castigos.';
        }
      } else {
        if (interpEl) {
          interpEl.textContent = 'Puntaje < 34: Dificultad Leve o Moderada (Dentro del rango esperado)';
          interpEl.style.color = '#4A6340';
        }
        if (adviceEl) {
          adviceEl.textContent =
            'El puntaje total se ubica por debajo del umbral clínico de 34 puntos. Aun así, observa qué dimensión obtuvo mayor puntaje para acompañar con anticipación visual, exposición gradual (Escalera Sensorial) y alimentos puente.';
        }
      }

      document.getElementById('bambiRefusalScore').textContent = refusal + ' / 25 ptos';
      document.getElementById('bambiSelectivityScore').textContent = selectivity + ' / 40 ptos';
      document.getElementById('bambiDisruptiveScore').textContent = disruptive + ' / 25 ptos';

      document.getElementById('bambiRefusalBar').style.width = ((refusal / 25) * 100).toFixed(0) + '%';
      document.getElementById('bambiSelectivityBar').style.width = ((selectivity / 40) * 100).toFixed(0) + '%';
      document.getElementById('bambiDisruptiveBar').style.width = ((disruptive / 25) * 100).toFixed(0) + '%';

      if (bambiResults) {
        bambiResults.removeAttribute('hidden');
        bambiResults.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  }

  if (bambiResetBtn) {
    bambiResetBtn.addEventListener('click', function () {
      renderBambiQuestions();
      if (bambiResults) bambiResults.setAttribute('hidden', '');
    });
  }

})();
