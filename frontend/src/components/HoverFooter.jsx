import { useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "motion/react";

const footerSections = [
  {
    title: "Navigasi",
    links: [
      { label: "Beranda", href: "/" },
      { label: "Analyzer CV", href: "/analyzer/" },
      { label: "Dashboard", href: "/dashboard/" },
      { label: "Tentang ICM", href: "/about/" },
    ],
  },
  {
    title: "Bantuan",
    links: [
      { label: "Panduan & FAQ", href: "/help/" },
      { label: "Kebijakan Privasi", href: "/privacy/" },
      { label: "Mulai analisis", href: "/analyzer/?mode=match" },
    ],
  },
];

const quickLinks = [
  { label: "Beranda", href: "/", icon: "home" },
  { label: "Analyzer", href: "/analyzer/", icon: "analyzer" },
  { label: "Bantuan", href: "/help/", icon: "help" },
];

function Icon({ name, className = "" }) {
  return (
    <svg className={`icon ${className}`} aria-hidden="true">
      <use href={`#icon-${name}`} />
    </svg>
  );
}

function TextHoverEffect({ text = "ICM" }) {
  const svgRef = useRef(null);
  const [maskPosition, setMaskPosition] = useState({ cx: "50%", cy: "50%" });
  const [hovered, setHovered] = useState(false);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return undefined;

    const updatePosition = (event) => {
      const rect = svg.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      setMaskPosition({
        cx: `${((event.clientX - rect.left) / rect.width) * 100}%`,
        cy: `${((event.clientY - rect.top) / rect.height) * 100}%`,
      });
    };

    svg.addEventListener("pointermove", updatePosition);
    return () => svg.removeEventListener("pointermove", updatePosition);
  }, []);

  return (
    <svg
      ref={svgRef}
      className="footer-wordmark"
      viewBox="0 0 300 100"
      role="img"
      aria-label="ICM"
      onPointerEnter={() => setHovered(true)}
      onPointerLeave={() => setHovered(false)}
    >
      <defs>
        <linearGradient id="footer-text-gradient">
          <stop offset="0%" stopColor="#eab308" />
          <stop offset="25%" stopColor="#ef4444" />
          <stop offset="50%" stopColor="#80eeb4" />
          <stop offset="75%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
        <motion.radialGradient
          id="footer-reveal-mask"
          gradientUnits="userSpaceOnUse"
          r="25%"
          initial={{ cx: "50%", cy: "50%" }}
          animate={maskPosition}
          transition={{ duration: reduceMotion ? 0 : 0.18, ease: "easeOut" }}
        >
          <stop offset="0%" stopColor="white" />
          <stop offset="100%" stopColor="black" />
        </motion.radialGradient>
        <mask id="footer-text-mask">
          <rect width="100%" height="100%" fill="url(#footer-reveal-mask)" />
        </mask>
      </defs>
      <text
        x="50%"
        y="52%"
        textAnchor="middle"
        dominantBaseline="middle"
        className="footer-wordmark-outline"
        style={{ opacity: hovered ? 0.65 : 0 }}
      >
        {text}
      </text>
      <motion.text
        x="50%"
        y="52%"
        textAnchor="middle"
        dominantBaseline="middle"
        className="footer-wordmark-trace"
        initial={reduceMotion ? false : { strokeDashoffset: 1000 }}
        animate={{ strokeDashoffset: 0 }}
        transition={{ duration: reduceMotion ? 0 : 3, ease: "easeInOut" }}
      >
        {text}
      </motion.text>
      <text
        x="50%"
        y="52%"
        textAnchor="middle"
        dominantBaseline="middle"
        className="footer-wordmark-color"
        stroke="url(#footer-text-gradient)"
        mask="url(#footer-text-mask)"
      >
        {text}
      </text>
    </svg>
  );
}

function FooterBackgroundGradient() {
  return <div className="footer-background-gradient" aria-hidden="true" />;
}

export default function HoverFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="site-footer">
      <FooterBackgroundGradient />
      <div className="site-footer-content">
        <div className="site-footer-grid">
          <section className="footer-brand" aria-label="Tentang ICM">
            <a href="/" className="footer-brand-link">
              <span className="footer-brand-mark" aria-hidden="true">
                <span className="footer-brand-logo" />
              </span>
              <span>ICM</span>
            </a>
            <p>
              IT Career CV Analyzer membantu mencocokkan CV dengan lowongan dan
              menemukan rekomendasi jalur karier IT.
            </p>
            <a className="footer-about-link" href="/about/">
              Kenali proyek ICM <span aria-hidden="true">→</span>
            </a>
          </section>

          {footerSections.map((section) => (
            <nav key={section.title} aria-label={section.title} className="footer-link-section">
              <h2>{section.title}</h2>
              <ul>
                {section.links.map((link) => (
                  <li key={link.href}>
                    <a href={link.href}>{link.label}</a>
                  </li>
                ))}
              </ul>
            </nav>
          ))}

          <section className="footer-info">
            <h2>Informasi</h2>
            <div className="footer-info-item">
              <Icon name="about" />
              <span>Politeknik Negeri Lampung</span>
            </div>
            <div className="footer-info-item">
              <Icon name="work" />
              <span>Ihsan · Johanes · Fery · Farel</span>
            </div>
            <a className="footer-contact-link" href="/help/">
              Butuh bantuan? Buka panduan
            </a>
          </section>
        </div>

        <div className="footer-wordmark-wrap">
          <TextHoverEffect />
        </div>

        <div className="site-footer-bottom">
          <p>© {year} ICM · Politeknik Negeri Lampung</p>
          <nav aria-label="Tautan cepat" className="footer-quick-links">
            {quickLinks.map((link) => (
              <a key={link.href} href={link.href} aria-label={link.label} title={link.label}>
                <Icon name={link.icon} />
              </a>
            ))}
          </nav>
        </div>
      </div>
    </footer>
  );
}
