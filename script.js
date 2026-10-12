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

})();
