/**
 * ICM — Main JavaScript Entry Point
 * Token-aware interactions: theme toggle, reveal-on-load stagger,
 * drop-zone upload, mobile nav. No framework needed.
 */

// ── CSRF Token helper (Django) ──────────────────────────────────────────────
function getCookie(name) {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith(name + '='));
    return cookieValue ? decodeURIComponent(cookieValue.split('=')[1]) : null;
}

const CSRF_TOKEN = getCookie('csrftoken');

// ── Theme: localStorage persist, default dark, pre-paint class in base.html ─
(function initTheme() {
    const toggle = document.getElementById('theme-toggle');
    const setIcon = () => {
        if (!toggle) return;
        const dark = document.documentElement.classList.contains('dark');
        toggle.querySelector('[data-icon-dark]').style.display = dark ? 'none' : '';
        toggle.querySelector('[data-icon-light]').style.display = dark ? '' : 'none';
    };
    setIcon();
    if (toggle) {
        toggle.addEventListener('click', () => {
            const dark = document.documentElement.classList.toggle('dark');
            try { localStorage.setItem('icm-theme', dark ? 'dark' : 'light'); } catch (e) {}
            setIcon();
        });
    }
})();

// ── Reveal on load: staggered fade-up, fires once ────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const targets = document.querySelectorAll('[data-reveal]');
    if (!('IntersectionObserver' in window) || !targets.length) {
        targets.forEach(el => el.classList.add('is-visible'));
    } else {
        const io = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
        targets.forEach(el => io.observe(el));
    }

    // ── Mobile nav ──────────────────────────────────────────────────────────
    const navBtn = document.getElementById('mobile-nav-btn');
    const navMenu = document.getElementById('mobile-nav-menu');
    if (navBtn && navMenu) {
        navBtn.addEventListener('click', () => {
            navMenu.classList.toggle('hidden');
        });
    }

    // ── Gradient dock: mark current page pill ────────────────────────────────
    document.querySelectorAll('[data-grad-dock] .grad-item').forEach(a => {
        if (a.getAttribute('href') === window.location.pathname) a.classList.add('is-active');
    });

    // ── Nexus UX port: scroll progress bar ───────────────────────────────────
    const prog = document.getElementById('scroll-progress');
    if (prog) {
        const syncProg = () => {
            const h = document.documentElement;
            const max = h.scrollHeight - h.clientHeight;
            prog.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + '%';
        };
        window.addEventListener('scroll', syncProg, { passive: true });
        syncProg();
    }

    // ── Nexus UX port: animated counters (data-count) ────────────────────────
    const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const counters = document.querySelectorAll('[data-count]');
    const runCount = (el) => {
        const end = parseFloat(el.dataset.count);
        const dec = parseInt(el.dataset.decimals || '0', 10);
        const suffix = el.dataset.suffix || '';
        if (reduceMotion || isNaN(end)) { el.textContent = end + suffix; return; }
        const dur = 1500, t0 = performance.now();
        const tick = (t) => {
            const k = Math.min((t - t0) / dur, 1), e = 1 - Math.pow(1 - k, 3);
            el.textContent = (end * e).toFixed(dec) + suffix;
            if (k < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    };
    if ('IntersectionObserver' in window && counters.length) {
        const cio = new IntersectionObserver((entries) => {
            entries.forEach(en => { if (en.isIntersecting) { runCount(en.target); cio.unobserve(en.target); } });
        }, { threshold: 0.4 });
        counters.forEach(el => cio.observe(el));
    } else {
        counters.forEach(runCount);
    }

    // ── Nexus UX port: magnetic buttons (fine pointers only) ─────────────────
    if (window.matchMedia && window.matchMedia('(pointer: fine)').matches && !reduceMotion) {
        document.querySelectorAll('.btn-primary').forEach(btn => {
            btn.classList.add('btn-magnetic');
            btn.addEventListener('mousemove', (e) => {
                const r = btn.getBoundingClientRect();
                const x = (e.clientX - (r.left + r.width / 2)) * 0.25;
                const y = (e.clientY - (r.top + r.height / 2)) * 0.25;
                btn.style.transform = 'translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)';
            });
            btn.addEventListener('mouseleave', () => { btn.style.transform = ''; });
        });
    }

});
