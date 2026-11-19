// ICM Animations v1.0

// Scroll Reveal Animation
document.addEventListener('DOMContentLoaded', function() {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  // Page entrance animation
  const pageElements = document.querySelectorAll('body > *');
  pageElements.forEach((el, index) => {
    // Skip elements that are already animated
    if (!el.classList.contains('icm-animated')) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      setTimeout(() => {
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
        el.classList.add('icm-animated');
      }, 100 * index);
    }
  });

  // Scroll reveal animation
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, index) => {
      if (entry.isIntersecting) {
        // Add staggered delay for multiple elements
        setTimeout(() => {
          entry.target.classList.add('icm-slide-in-up');
        }, 100 * index);
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  });

  // Observe elements with scroll-reveal class
  document.querySelectorAll('.scroll-reveal').forEach((el) => {
    observer.observe(el);
  });

  // Staggered animation for lists
  document.querySelectorAll('.staggered-list > *').forEach((el, index) => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(15px)';
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
    }, 150 * index);
  });

  // Hover interaction for buttons and cards
  const interactiveElements = document.querySelectorAll('.icm-btn, .icm-card');
  interactiveElements.forEach(el => {
    el.addEventListener('mouseenter', () => {
      el.style.transform = el.classList.contains('icm-card')
        ? 'translateY(-4px)'
        : 'translateY(-2px)';
      el.style.boxShadow = '0 10px 20px rgba(0, 0, 0, 0.19), 0 6px 6px rgba(0, 0, 0, 0.23)';
    });

    el.addEventListener('mouseleave', () => {
      el.style.transform = '';
      el.style.boxShadow = '';
    });
  });

  // Progress bar animation
  document.querySelectorAll('.icm-progress-fill').forEach(el => {
    const width = el.style.width;
    if (width) {
      el.style.width = '0';
      setTimeout(() => {
        el.style.transition = 'width 1s ease-in-out';
        el.style.width = width;
      }, 300);
    }
  });

  // Tab transition
  const tabs = document.querySelectorAll('[role="tab"]');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // Add active class with animation
      tab.classList.add('icm-tab-active');
      setTimeout(() => {
        tab.classList.remove('icm-tab-active');
      }, 300);
    });
  });
});

// Micro-interactions for form elements
document.addEventListener('DOMContentLoaded', function() {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  // Page navigation animation
  const links = document.querySelectorAll('a[href]:not([target="_blank"])');
  links.forEach(link => {
    link.addEventListener('click', function(e) {
      // Check if it's an internal navigation link
      if (this.hostname === window.location.hostname && !e.ctrlKey && !e.metaKey && !e.shiftKey && !e.altKey && e.button === 0) {
        e.preventDefault();
        const href = this.getAttribute('href');

        // Fade out current page
        document.body.style.transition = 'opacity 0.3s ease';
        document.body.style.opacity = '0';

        // Navigate after fade
        setTimeout(() => {
          window.location.href = href;
        }, 300);
      }
    });
  });
});