import React, { useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import HoverFooter from "./components/HoverFooter.jsx";
import WaveMesh from "./components/WaveMesh.jsx";
import "./styles.css";

const DARK_WAVE_COLORS = ["#101318", "#bdc8da", "#4ac3d6"];
const LIGHT_WAVE_COLORS = ["#f4f6f8", "#35435b", "#167d99"];

const links = [
  ["/", "Home", "home", "#0891b2", "#22d3ee"],
  ["/analyzer/", "Analyzer", "analyzer", "#7c3aed", "#d946ef"],
  ["/dashboard/", "Dashboard", "dashboard", "#0ea5e9", "#22c55e"],
  ["/about/", "About", "about", "#f59e0b", "#f43f5e"],
  ["/help/", "Help", "help", "#10b981", "#06b6d4"],
];

const icon = (name, className = "icon") => (
  <svg className={className} aria-hidden="true"><use href={`#icon-${name}`} /></svg>
);

function useTheme() {
  const [dark, setDark] = useState(() => {
    try {
      return localStorage.getItem("icm-theme") !== "light";
    } catch {
      return true;
    }
  });

  React.useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("icm-theme", dark ? "dark" : "light");
    } catch {
      // Theme remains usable when browser storage is disabled.
    }
  }, [dark]);
  return [dark, () => setDark((value) => !value)];
}

function AppShell({ page, children, root }) {
  const [dark, toggleTheme] = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const { authenticated, username } = root.dataset;
  const csrf = getCsrfToken(root);
  const waveColors = dark ? DARK_WAVE_COLORS : LIGHT_WAVE_COLORS;

  React.useEffect(() => {
    const progress = document.getElementById("scroll-progress");
    const syncProgress = () => {
      const documentElement = document.documentElement;
      const max = documentElement.scrollHeight - documentElement.clientHeight;
      if (progress) progress.style.width = `${max > 0 ? (documentElement.scrollTop / max) * 100 : 0}%`;
    };
    window.addEventListener("scroll", syncProgress, { passive: true });
    syncProgress();

    const revealTargets = document.querySelectorAll("[data-reveal]");
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    let observer;
    if ("IntersectionObserver" in window && !reduceMotion) {
      observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1, rootMargin: "0px 0px -40px 0px" });
      revealTargets.forEach((target) => observer.observe(target));
    } else {
      revealTargets.forEach((target) => target.classList.add("is-visible"));
    }

    const magneticButtons = window.matchMedia?.("(pointer: fine)").matches && !reduceMotion
      ? document.querySelectorAll(".btn-primary")
      : [];
    magneticButtons.forEach((button) => {
      const onMove = (event) => {
        const rect = button.getBoundingClientRect();
        const x = (event.clientX - (rect.left + rect.width / 2)) * 0.25;
        const y = (event.clientY - (rect.top + rect.height / 2)) * 0.25;
        button.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
      };
      const onLeave = () => { button.style.transform = ""; };
      button.classList.add("btn-magnetic");
      button.addEventListener("mousemove", onMove);
      button.addEventListener("mouseleave", onLeave);
    });

    return () => {
      window.removeEventListener("scroll", syncProgress);
      observer?.disconnect();
      magneticButtons.forEach((button) => {
        button.classList.remove("btn-magnetic");
        button.style.transform = "";
      });
    };
  }, []);

  return (
    <div className="text-foreground font-x min-h-screen flex flex-col antialiased">
      <WaveMesh colors={waveColors} />
      <header className="site-header sticky top-0 z-40 w-full bg-background/80 backdrop-blur-md">
        <div className="flex h-14 w-full items-center justify-between gap-2 px-2 sm:px-3">
          <div className="flex items-center gap-2 min-w-0">
            <a href="/" className="flex items-center gap-2.5 shrink-0">
              <span className="icm-header-logo" role="img" aria-label="Logo IT Career Match" />
              <span className="font-mono text-sm font-semibold tracking-tight">ICM</span>
              <span className="badge badge-accent font-mono text-[10px] uppercase tracking-widest">AI v2.4</span>
            </a>
            <nav className="hidden md:flex items-center gap-2 text-sm" aria-label="Navigasi utama" data-grad-dock>
              {links.map(([href, label, symbol, from, to]) => (
                <a key={href} href={href} className={`grad-item grad-item-top ${page === symbol ? "is-active" : ""}`}
                  style={{ "--gf": from, "--gt": to }} aria-label={label}>
                  {icon(symbol, "grad-icon")}<span className="grad-label">{label}</span>
                </a>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button id="theme-toggle" type="button" className="btn !px-2.5 !py-2" title="Toggle theme"
              aria-label="Toggle theme" onClick={toggleTheme}>
              {icon(dark ? "sun" : "moon")}
            </button>
            {authenticated === "true" ? (
              <>
                <span className="hidden sm:block font-mono text-xs text-muted-foreground">{username}</span>
                <form action="/logout/" method="post" className="inline">
                  <input type="hidden" name="csrfmiddlewaretoken" value={csrf} />
                  <button type="submit" className="btn !px-2.5 !py-2" title="Sign Out" aria-label="Sign Out">
                    {icon("logout")}
                  </button>
                </form>
              </>
            ) : (
              <>
                <a href="/login/" className="hidden sm:inline-flex btn !py-2 text-xs">Sign In</a>
                <a href="/register/" className="hidden sm:inline-flex btn btn-primary !py-2 text-xs">Get Started</a>
              </>
            )}
            <button type="button" className="btn !px-2.5 !py-2 md:hidden" aria-label="Menu"
              aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>
              {icon("menu")}
            </button>
          </div>
        </div>
        {menuOpen && (
          <div className="md:hidden border-t border-edge">
            <nav className="mx-auto max-w-5xl px-4 py-2 flex flex-col text-sm">
              {links.map(([href, label]) => <a key={href} href={href} className="px-2 py-2.5 text-muted-foreground hover:text-foreground">{label}</a>)}
              {authenticated !== "true" && <div className="flex gap-2 py-2">
                <a href="/login/" className="btn flex-1 text-xs">Sign In</a>
                <a href="/register/" className="btn btn-primary flex-1 text-xs">Get Started</a>
              </div>}
            </nav>
          </div>
        )}
      </header>

      <Messages />
      <main className="flex-1 w-full">{children}</main>
      <HoverFooter />
      <nav className="grad-dock md:hidden" aria-label="Navigasi cepat" data-grad-dock>
        {links.map(([href, label, symbol, from, to]) => (
          <a key={href} href={href} style={{ "--gf": from, "--gt": to }} className={`grad-item ${page === symbol ? "is-active" : ""}`} aria-label={label}>
            {icon(symbol, "grad-icon")}<span className="grad-label">{label}</span>
          </a>
        ))}
      </nav>
    </div>
  );
}

function Messages() {
  const container = document.getElementById("icm-messages");
  if (!container) return null;
  return <div aria-live="polite" aria-atomic="true" className="fixed top-16 right-4 z-50 space-y-2 max-w-sm">
    {[...container.children].map((message, index) => <div key={index}
      className={`p-4 rounded-xl border shadow-lg flex items-center gap-3 text-sm bg-card text-card-foreground ${
        message.dataset.level === "error" ? "border-destructive/40" :
          message.dataset.level === "success" ? "border-success/40" : "border-border"
      }`}>
      {icon(message.dataset.level === "error" ? "error" : message.dataset.level === "success" ? "success" : "about", "icon icon-lg shrink-0")}
      <span>{message.textContent}</span>
    </div>)}
  </div>;
}

function Section({ children, className = "" }) {
  return <section className={`w-full max-w-3xl px-2 sm:px-3 ${className}`}>
    <div className="section-frame px-4 py-10 sm:px-8">{children}</div>
  </section>;
}

function Eyebrow({ children }) { return <span className="eyebrow">{children}</span>; }

function HomePage() {
  return <Section>
    <div data-reveal><Eyebrow>AI-Powered IT Career Matchmaking v2.4</Eyebrow>
      <h1 className="mt-4 text-3xl sm:text-4xl font-semibold tracking-tight leading-tight">Stop Guessing Your IT Career.</h1>
      <p className="mt-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">Know your CV compatibility score instantly</p>
    </div>
    <div data-reveal data-delay="150"><p className="mt-6 text-sm leading-relaxed text-foreground/70">Dual-engine neural platform powered by SentenceTransformer embeddings dan TF-IDF 5.000 features. Dua mode: bandingkan CV dengan lowongan, atau dapatkan rekomendasi karier dari CV saja.</p></div>
    <div className="mt-8 flex flex-col sm:flex-row gap-3" data-reveal data-delay="300">
      <a href="/analyzer/?mode=match" className="btn btn-primary flex-1">{icon("work")}Analyze CV vs Job</a>
      <a href="/analyzer/?mode=career" className="btn flex-1">{icon("spark")}Career Recommendations</a>
    </div>
    <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-3">
      {[["86.88%", "Match Precision"], ["91.25%", "Role F1"], ["324", "IT Roles"], ["120+", "Skills"]].map(([value, label]) =>
        <div key={label} className="card p-4 text-center"><p className="font-mono text-xl font-semibold text-accent">{value}</p>
          <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p></div>)}
    </div>
  </Section>;
}

function AuthPage({ register, root }) {
  const errors = readFieldErrors("icm-form-errors");
  const title = register ? "Create Account" : "Welcome Back";
  return <Section>
    <div className="mx-auto w-full max-w-md" data-reveal>
      <div className="text-center"><Eyebrow>ICM</Eyebrow><h1 className="mt-4 text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">{register ? "Start analyzing your IT career" : "Sign in to your account"}</p></div>
      <div className="auth-card card mt-8 p-8">
        <form method="post" action={register ? "/register/" : "/login/"} noValidate>
          <input type="hidden" name="csrfmiddlewaretoken" value={getCsrfToken(root)} />
          <div className="space-y-5">
            {register && <Field name="username" label="Username" placeholder="Username unik" autocomplete="username" error={errors.username?.error} value={errors.username?.value} />}
            {register && <Field name="email" label="Email" type="email" placeholder="name@example.com" autocomplete="email" error={errors.email?.error} value={errors.email?.value} />}
            {!register && <Field name="username" label="Username" placeholder="Username" autocomplete="username" error={errors.username?.error} value={errors.username?.value} />}
            <Field name="password" label="Password" type="password" placeholder={register ? "Password (min 8 karakter)" : "Password"}
              autocomplete={register ? "new-password" : "current-password"} error={errors.password?.error} />
          </div>
          <button type="submit" className="btn btn-primary w-full mt-7">{register ? "Create Account" : "Sign In"}</button>
        </form>
        <p className="text-center text-xs text-muted-foreground mt-6">
          {register ? "Already have an account?" : "Don't have an account?"}
          <a href={register ? "/login/" : "/register/"} className="text-accent font-semibold hover:underline ml-1">{register ? "Sign in" : "Create one"}</a>
        </p>
      </div>
    </div>
  </Section>;
}

function readFieldErrors(id) {
  const container = document.getElementById(id);
  if (!container) return {};
  return Object.fromEntries([...container.children].map((item) => [item.dataset.field, {
    error: item.textContent.trim(),
    value: item.dataset.value || "",
  }]));
}

function Field({ name, label, type = "text", placeholder, autocomplete, error, value }) {
  return <div><label htmlFor={`id_${name}`} className="label">{label}</label>
    <input id={`id_${name}`} name={name} type={type} className="field" placeholder={placeholder} autoComplete={autocomplete}
      defaultValue={value} required />
    {error && <p className="mt-1 text-xs text-destructive">{error}</p>}</div>;
}

function getCsrfToken(root) {
  return root.dataset.csrf ||
    document.querySelector("#icm-csrf-token input[name='csrfmiddlewaretoken']")?.value ||
    "";
}

function AnalyzerPage({ root }) {
  const params = new URLSearchParams(window.location.search);
  const [mode, setMode] = useState(root.dataset.mode === "career" || params.get("mode") === "career" ? "career" : "match");
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInput = useRef(null);
  const errors = readFieldErrors("icm-form-errors");

  function acceptFile(selected, fromDrop = false) {
    const nextFile = selected?.[0];
    if (!nextFile) return;
    if (nextFile.size > 5 * 1024 * 1024) {
      setFileError(`File "${nextFile.name}" ${(nextFile.size / 1024 / 1024).toFixed(1)}MB melebihi batas 5MB.`);
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      return;
    }
    setFileError("");
    setFile(nextFile);
    if (fromDrop && fileInput.current) fileInput.current.files = selected;
  }

  return <Section>
    <div data-reveal><Eyebrow>Analyzer</Eyebrow><h1 className="mt-4 text-2xl font-semibold tracking-tight">Analisis CV</h1>
      <p className="mt-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">CV vs Job • Rekomendasi Karier</p></div>
    <div data-reveal data-delay="150"><p className="mt-6 text-sm leading-relaxed text-foreground/70">Upload CV, pilih mode, dapatkan skor kecocokan, skill gap, dan roadmap. PDF/DOCX maksimal 5MB.</p></div>
    <form method="post" action="/analyzer/" encType="multipart/form-data" className="mt-8 space-y-6" data-reveal data-delay="300"
      onSubmit={() => setSubmitting(true)}>
      <input type="hidden" name="csrfmiddlewaretoken" value={getCsrfToken(root)} />
      <fieldset className="m-0 border-0 p-0"><legend className="label">Mode analisis</legend>
        <div className="grid grid-cols-2 gap-3">
          {[["match", "CV vs Job", "Bandingkan CV dengan satu lowongan spesifik."], ["career", "Career", "Rekomendasi 3 jalur karier dari CV saja."]].map(([value, label, text]) =>
            <label key={value} className="card cursor-pointer p-4 has-[:checked]:border-accent">
              <input type="radio" name="mode" value={value} checked={mode === value} onChange={() => setMode(value)} className="accent-current" />
              <span className="mt-2 block text-sm font-semibold">{label}</span><span className="block text-xs text-muted-foreground">{text}</span>
            </label>)}
        </div>
      </fieldset>
      <div><span className="label" id="cv-label">File CV</span>
        <div role="button" tabIndex={0} aria-labelledby="cv-label"
          className={`drop-zone ${file ? "has-file" : ""} ${dragActive ? "drag-active" : ""}`}
          onClick={() => fileInput.current?.click()}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              fileInput.current?.click();
            }
          }}
          onDragEnter={(event) => { event.preventDefault(); setDragActive(true); }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={() => setDragActive(false)}
          onDrop={(event) => { event.preventDefault(); setDragActive(false); acceptFile(event.dataTransfer.files, true); }}>
          {icon("upload", "icon icon-lg text-muted-foreground mx-auto")}
          <p className="mt-2 text-sm font-medium">Klik atau seret file ke sini</p>
          <span className="mt-1 block font-mono text-xs text-muted-foreground">{file ? `${file.name} (${(file.size / 1024).toFixed(0)} KB)` : "PDF / DOCX, maks 5MB"}</span>
          <input ref={fileInput} id="id_cv_file" name="cv_file" type="file" accept=".pdf,.docx" className="hidden"
            onClick={(event) => event.stopPropagation()}
            onChange={(event) => acceptFile(event.target.files)} />
        </div>
        {(fileError || errors.cv_file?.error) && <p className="mt-2 text-xs text-destructive" role="alert">{fileError || errors.cv_file.error}</p>}
      </div>
      <div hidden={mode !== "match"}><label className="label" htmlFor="id_job_description">Job description</label>
        <textarea id="id_job_description" name="job_description" rows="8" placeholder="Tempel deskripsi pekerjaan lengkap di sini..." className="field"
          defaultValue={errors.job_description?.value} />
        {errors.job_description?.error && <p className="mt-2 text-xs text-destructive" role="alert">{errors.job_description.error}</p>}
      </div>
      <button type="submit" disabled={submitting} aria-busy={submitting} className="btn btn-primary w-full">
        {icon("spark")}<span>{submitting ? "Menganalisis…" : "Jalankan Analisis"}</span>
      </button>
    </form>
  </Section>;
}

function DashboardPage() {
  const stats = readJson("icm-stats") || {};
  const analyses = readJson("icm-analyses") || [];
  return <Section>
    <div data-reveal><Eyebrow>Dashboard</Eyebrow><h1 className="mt-4 text-2xl font-semibold tracking-tight">Riwayat Analisis</h1>
      <p className="mt-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">10 analisis terakhir • progres skill</p></div>
    <div className="mt-8 grid grid-cols-3 gap-3" data-reveal data-delay="150">
      <Stat value={stats.total_analyses ?? 0} label="Total" />
      <Stat value={`${Math.round((stats.average_score || 0) * 100)}%`} label="Rerata" />
      <Stat value={stats.top_role || "-"} label="Top role" truncate />
    </div>
    <div className="mt-8 space-y-3" data-reveal data-delay="300">
      {analyses.length ? analyses.map((item) => <a key={item.id} href={`/analyzer/result/${item.id}/`}
        className="card block p-4 transition-colors hover:border-ring"><div className="flex items-center justify-between gap-3 text-sm">
          <div className="min-w-0"><p className="truncate font-medium">{item.cv_file}</p>
            <p className="mt-0.5 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">{item.mode} • {formatDate(item.created_at)}</p></div>
          <div className="shrink-0 text-right"><p className="font-mono text-lg font-semibold">{Math.round((item.compatibility_score || 0) * 100)}%</p>
            <p className="font-mono text-[10px] uppercase tracking-wider text-accent">{item.compatibility_level}</p></div>
        </div></a>) : <div className="card p-8 text-center">{icon("inbox", "icon icon-lg text-muted-foreground mx-auto")}
          <p className="mt-3 text-sm font-medium">Belum ada analisis</p><p className="mt-1 text-xs text-muted-foreground">Upload CV pertama Anda untuk melihat skor di sini.</p>
          <a href="/analyzer/" className="btn btn-primary mt-5">Mulai Analisis</a></div>}
    </div>
  </Section>;
}

function Stat({ value, label, truncate }) {
  return <div className="card p-4 text-center"><p className={`font-mono ${truncate ? "truncate text-sm" : "text-2xl"} font-semibold`}>{value}</p>
    <p className="mt-1 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">{label}</p></div>;
}

function ResultPage() {
  const analysis = readJson("icm-analysis") || {};
  const score = Number(analysis.compatibility_score || 0);
  const topRoles = analysis.top_roles || [];
  const matched = analysis.skill_gap_matched || [];
  const missing = analysis.skill_gap_missing || [];
  const roadmap = analysis.roadmap || [];
  const circumference = 2 * Math.PI * 70;
  return <Section>
    <div data-reveal><Eyebrow>Hasil analisis</Eyebrow><h1 className="mt-4 text-2xl font-semibold tracking-tight">{analysis.mode}</h1>
      <p className="mt-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">{analysis.cv_file} • {formatDate(analysis.created_at)} • {analysis.processing_time_ms}ms</p></div>
    <div className="mt-8 flex flex-col sm:flex-row items-center gap-6" data-reveal data-delay="150">
      <svg width="140" height="140" viewBox="0 0 160 160" className="shrink-0" aria-label={`Compatibility ${Math.round(score * 100)} percent`}>
        <circle cx="80" cy="80" r="70" fill="none" stroke="var(--border)" strokeWidth="12" />
        <circle cx="80" cy="80" r="70" fill="none" stroke="var(--accent)" strokeWidth="12" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={circumference * (1 - score)} transform="rotate(-90 80 80)" />
        <text x="80" y="76" textAnchor="middle" fontSize="26" fontWeight="700" fill="var(--foreground)" fontFamily="JetBrains Mono, monospace">{Math.round(score * 100)}%</text>
        <text x="80" y="98" textAnchor="middle" fontSize="10" fill="var(--muted-foreground)" fontFamily="JetBrains Mono, monospace">{analysis.compatibility_level}</text>
      </svg>
      <div className="w-full space-y-3 text-sm">
        <div className="card p-4 flex items-center justify-between"><span className="text-muted-foreground">Compatibility level</span><span className="badge badge-accent">{analysis.compatibility_level}</span></div>
        <div className="card p-4 flex items-center justify-between"><span className="text-muted-foreground">Waktu proses</span><span className="font-mono text-xs">{analysis.processing_time_ms} ms</span></div>
      </div>
    </div>
    {topRoles.length > 0 && <div className="mt-8" data-reveal data-delay="300"><span className="label">Top roles</span><div className="space-y-2">
      {topRoles.map((role) => <div key={role.role} className="card p-4 flex items-center justify-between text-sm"><span className="font-medium">{role.role}</span>
        <span className="font-mono text-xs text-muted-foreground">{Math.round(role.score * 100)}%</span></div>)}
    </div></div>}
    <div className="mt-8 grid gap-6 sm:grid-cols-2">
      <SkillList title="Skill cocok" skills={matched} /><SkillList title="Skill hilang" skills={missing} />
    </div>
    {roadmap.length > 0 && <div className="mt-8"><span className="label">Roadmap</span><div className="space-y-2">
      {roadmap.map((item) => <div key={item.skill} className="card p-4 text-sm"><p className="font-medium">{item.skill} <span className="ml-2 badge">{item.priority}</span></p>
        {item.resources?.length > 0 && <p className="mt-1 text-xs text-muted-foreground">{item.resources.join(", ")}</p>}</div>)}
    </div></div>}
    <div className="mt-8 flex flex-col sm:flex-row gap-3"><a href="/analyzer/" className="btn btn-primary flex-1">Analisis Lagi</a>
      <a href="/dashboard/" className="btn flex-1">Kembali ke Dashboard</a></div>
  </Section>;
}

function SkillList({ title, skills }) {
  return <div><span className="label">{title} ({skills.length})</span><div className="flex flex-wrap gap-2">
    {skills.length ? skills.map((skill) => <span key={skill} className="badge">{skill}</span>) : <p className="text-xs text-muted-foreground">Tidak ada.</p>}
  </div></div>;
}

function AboutPage() {
  const members = [["Ihsan (Leader)", "Fitur 2 — Career Recommendation & Deployment"], ["Johanes", "Fitur 1 — CV-Job Matching & NLP Pipeline"], ["Fery", "Data & Desain UI/UX"], ["Farel", "Dokumentasi & Laporan"]];
  return <Section><div data-reveal><Eyebrow>Tentang ICM</Eyebrow><h1 className="mt-4 text-2xl sm:text-3xl font-semibold tracking-tight leading-tight">IT Career CV Analyzer &amp; Matchmaking System</h1></div>
    <div data-reveal data-delay="150"><p className="mt-6 text-sm leading-relaxed text-foreground/70">ICM membantu talenta IT menilai kecocokan CV terhadap lowongan dan menemukan jalur karier yang tepat — berbasis NLP, bukan tebakan.</p></div>
    <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-3" data-reveal data-delay="300">
      {[["86.88%", "CV–Job Matching"], ["91.25%", "Rekomendasi Karier"], ["2", "Fitur AI"], ["4", "Anggota Tim"]].map(([value, label]) =>
        <div key={label} className="card p-4 text-center"><p className="font-mono text-xl font-semibold">{value}</p><p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p></div>)}
    </div>
    <article className="card mt-8 p-6"><h2 className="font-mono text-xs font-semibold uppercase tracking-wider">Cara Kerja</h2>
      <ol className="mt-3 space-y-2.5 text-sm text-foreground/70 list-decimal list-inside leading-relaxed">
        <li>Upload CV (PDF) di halaman <a href="/analyzer/" className="text-accent hover:underline">Analyzer</a>.</li>
        <li>Pilih mode: <strong className="text-foreground">CV vs Job</strong> (butuh Job Description) atau <strong className="text-foreground">Rekomendasi Karier</strong> (CV saja).</li>
        <li>Pipeline NLP mengekstrak skill, menghitung skor kecocokan, dan memetakan skill gap.</li>
        <li>Hasil tampil di <a href="/dashboard/" className="text-accent hover:underline">Dashboard</a>: skor, skill cocok vs hilang, roadmap upgrade.</li>
      </ol>
    </article>
    <article className="card mt-4 p-6"><h2 className="font-mono text-xs font-semibold uppercase tracking-wider">Teknologi</h2>
      <div className="mt-3 flex flex-wrap gap-2 font-mono text-xs">{["Django 5 + DRF", "SentenceTransformer all-MiniLM-L6-v2", "TF-IDF + Logistic Regression", "SQLite", "React + JSX"].map((tech) => <span key={tech} className="badge">{tech}</span>)}</div>
    </article>
    <article className="card mt-4 p-6"><h2 className="font-mono text-xs font-semibold uppercase tracking-wider">Tim</h2>
      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">{members.map(([name, role]) => <div key={name} className="p-4 rounded-lg bg-secondary border border-border"><p className="font-semibold">{name}</p><p className="text-xs text-muted-foreground mt-0.5">{role}</p></div>)}</div>
      <p className="mt-4 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">Politeknik Negeri Lampung • 2026</p>
    </article>
    <div className="mt-8"><a href="/analyzer/?mode=match" className="btn btn-primary w-full">{icon("rocket")}Coba Analisis Sekarang</a></div>
  </Section>;
}

function HelpPage() {
  const faqs = [
    ["Format CV apa yang didukung?", <p>PDF dan DOCX, maksimal 5MB. Gunakan PDF teks (bukan hasil scan/foto) agar parser NLP bisa membaca isinya.</p>],
    ["Apa beda mode Match vs Career?", <p><strong className="text-foreground">CV vs Job</strong> membandingkan CV dengan satu Job Description spesifik. <strong className="text-foreground">Career</strong> hanya butuh CV, lalu merekomendasikan 3 jalur karier terbaik dari profil skill Anda.</p>],
    ["Bagaimana skor dihitung?", <p>Skor 0–100% dari cosine similarity embedding SentenceTransformer + klasifikasi TF-IDF/LR. Level: LOW (&lt;40), MEDIUM (40–60), HIGH (60–80), EXCELLENT (&gt;80).</p>],
    ["Kenapa upload gagal / Analysis failed?", <ul><li>Pastikan file PDF/DOCX ≤ 5MB dan tidak corrupt.</li><li>Mode Match wajib mengisi Job Description.</li><li>Coba logout lalu login ulang bila sesi kedaluwarsa.</li></ul>],
    ["Tidak bisa login?", <ul><li>Cek username &amp; password (case-sensitive).</li><li>Belum punya akun? <a href="/register/" className="text-accent hover:underline">Daftar di sini</a>.</li><li>Lupa password? Reset via manage.py shell → u.set_password(...).</li></ul>],
    ["Apakah data CV saya aman?", <p>File hanya diproses sementara lalu dihapus setelah analisis. Hasil tersimpan privat per akun. Detail: <a href="/privacy/" className="text-accent hover:underline">Kebijakan Privasi</a>.</p>],
  ];
  return <Section><div data-reveal><Eyebrow>Help &amp; FAQ</Eyebrow><h1 className="mt-4 text-2xl font-semibold tracking-tight">Butuh Bantuan?</h1>
    <p className="mt-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">Upload • Skor • Akun • Error</p></div>
    <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3" data-reveal data-delay="150">
      <a href="/analyzer/" className="card p-5 transition-colors hover:border-ring"><p className="flex items-center gap-2 font-semibold text-sm">{icon("upload", "icon feature-icon")}Mulai Analisis CV</p><p className="text-xs text-muted-foreground mt-1">Upload PDF + Job Description, dapatkan skor instan.</p></a>
      <a href="/dashboard/" className="card p-5 transition-colors hover:border-ring"><p className="flex items-center gap-2 font-semibold text-sm">{icon("dashboard", "icon feature-icon")}Lihat Dashboard</p><p className="text-xs text-muted-foreground mt-1">Riwayat 10 analisis terakhir + statistik skor.</p></a>
    </div>
    <div className="mt-4 space-y-3" data-reveal data-delay="300">{faqs.map(([question, answer]) =>
      <details key={question} className="card p-5 group"><summary className="font-semibold text-sm cursor-pointer list-none flex items-center justify-between">{question}{icon("chevron", "icon icon-chevron text-accent")}</summary>
        <div className="text-sm text-muted-foreground mt-3 leading-relaxed [&_ul]:list-disc [&_ul]:list-inside [&_ul]:space-y-1">{answer}</div></details>)}</div>
    <div className="card mt-4 p-6 text-center"><p className="font-semibold text-sm">Masih terkendala?</p><p className="font-mono text-[11px] text-muted-foreground mt-1 mb-4">Ihsan • Johanes • Fery • Farel — Polinela 2026</p>
      <a href="/analyzer/" className="btn btn-primary">{icon("retry")}Coba Lagi di Analyzer</a></div>
  </Section>;
}

function PrivacyPage() {
  const entries = [
    ["1. File CV sementara", "File yang diupload hanya disimpan sementara selama proses analisis lalu dihapus otomatis. Yang tersimpan permanen hanya hasil skor, skill gap, dan roadmap — terikat ke akun Anda."],
    ["2. Yang kami simpan", "Nama file, job description yang Anda tempel, hasil analisis (skor, level, top roles, skill cocok/hilang), waktu proses, dan timestamp. Tidak ada pelacakan iklan, tidak ada penjualan data."],
    ["3. Akses & hapus", "Hasil hanya bisa dilihat akun pemiliknya (UUID per analisis). Minta hapus riwayat kapan saja lewat tim — Ihsan • Johanes • Fery • Farel, Informatics Engineering, Polinela."],
    ["4. Keamanan", "CSRF protection aktif di semua form, password di-hash Django, session-based auth. Jangan upload dokumen berisi NIK, nomor rekening, atau data sensitif lain — CV ringkas cukup."],
  ];
  return <Section><div data-reveal><Eyebrow>Kebijakan privasi</Eyebrow><h1 className="mt-4 text-2xl font-semibold tracking-tight">Data Anda, milik Anda</h1>
    <p className="mt-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">Terakhir diperbarui • 2026</p></div>
    <div className="mt-8 space-y-6 text-sm leading-relaxed text-foreground/70" data-reveal data-delay="150">{entries.map(([heading, text]) =>
      <div key={heading}><h2 className="font-mono text-xs font-semibold uppercase tracking-wider text-foreground">{heading}</h2><p className="mt-2">{text}</p></div>)}</div>
    <div className="mt-8 flex flex-col sm:flex-row gap-3" data-reveal data-delay="300"><a href="/analyzer/" className="btn btn-primary flex-1">Kembali ke Analyzer</a><a href="/help/" className="btn flex-1">Bantuan &amp; FAQ</a></div>
  </Section>;
}

function readJson(id) {
  const element = document.getElementById(id);
  if (!element) return null;
  try {
    return JSON.parse(element.textContent);
  } catch (error) {
    console.error(`Invalid JSON data in #${id}`, error);
    return null;
  }
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("id-ID", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  }).format(date);
}

const pageTitles = {
  home: "ICM — IT Career CV Analyzer",
  login: "Sign In — ICM",
  register: "Create Account — ICM",
  analyzer: "Analyzer — ICM",
  dashboard: "Dashboard — ICM",
  result: "Hasil Analisis — ICM",
  about: "Tentang — ICM",
  help: "Bantuan & FAQ — ICM",
  privacy: "Privasi — ICM",
};

function Root() {
  const root = document.getElementById("icm-root");
  const page = root.dataset.page;
  const components = {
    home: <HomePage />,
    login: <AuthPage root={root} />,
    register: <AuthPage register root={root} />,
    analyzer: <AnalyzerPage root={root} />,
    dashboard: <DashboardPage />,
    result: <ResultPage />,
    about: <AboutPage />,
    help: <HelpPage />,
    privacy: <PrivacyPage />,
  };
  document.title = pageTitles[page] || pageTitles.home;
  return <AppShell page={page} root={root}>{components[page] || components.home}</AppShell>;
}

const root = document.getElementById("icm-root");
if (root) createRoot(root).render(<Root />);
