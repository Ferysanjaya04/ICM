"use strict";

// Render saved result metadata only. Never fetch the current Resume or rerun AI.
window.ICMTransparency = (() => {
  const names = { semantic: "Semantik", skill: "Skill", experience: "Pengalaman", education: "Pendidikan" };
  const number = value => typeof value === "number" && Number.isFinite(value) ? value : null;
  const pages = value => Array.isArray(value)
    ? [...new Set(value.filter(n => Number.isInteger(n) && n > 0))].slice(0, 30) : [];
  const paragraph = (container, text, className) => {
    const p = document.createElement("p");
    p.className = className;
    p.textContent = text;
    container.append(p);
  };
  function quality(data) {
    return data?.extraction_quality ?? data?.analysis_metadata?.extraction_quality ??
      data?.profile_summary?.extraction_quality ?? { status: "unknown" };
  }
  function renderQuality(container, data, className = "result-empty", compact = false) {
    container.replaceChildren();
    container.setAttribute("aria-label", "Kualitas pembacaan CV");
    const q = quality(data);
    const statuses = {
      text_extracted: "Teks berhasil diekstrak.",
      needs_review: "Hasil pembacaan perlu diperiksa.",
      partial: "CV hanya terbaca sebagian. Analisis terbatas pada teks yang tersedia.",
      failed: "CV tidak berhasil dibaca. Gunakan dokumen lain sebelum menafsirkan hasil analisis.",
      unknown: "Informasi kualitas tidak tersedia."
    };
    paragraph(container, `Status pembacaan CV: ${statuses[q.status] || statuses.unknown}`, className);
    const warnings = Array.isArray(q.warnings) ? q.warnings.map(w => typeof w === "string" ? w : w?.code) : [];
    const failed = pages(q.failed_pages);
    const ocr = pages(q.ocr_pages);
    const low = pages(q.low_text_pages);
    if (failed.length) paragraph(container, `Halaman tidak terbaca: ${failed.join(", ")}.`, className);
    if (pages(q.ocr_failed_pages).length) paragraph(container, `OCR gagal pada halaman ${pages(q.ocr_failed_pages).join(", ")}; hasil mungkin tidak lengkap.`, className);
    if (ocr.length) paragraph(container, `OCR dijalankan pada halaman ${ocr.join(", ")}; periksa kembali istilah teknis.`, className);
    if (warnings.some(w => ["reading_order_uncertain", "heuristic_column_order_review"].includes(w))) {
      paragraph(container, "Urutan baca kolom belum dapat dipastikan; periksa kembali keterkaitan isi CV.", className);
    }
    if (low.length && !ocr.length) paragraph(container, `Teks native sedikit pada halaman ${low.join(", ")}; sebagian isi mungkin tidak terbaca.`, className);
    if (warnings.includes("docx_tables_linearized_row_order")) paragraph(container, "Tabel dibaca per baris; periksa keterkaitan antar kolom.", className);
    if (warnings.includes("docx_images_not_extracted")) paragraph(container, "Teks dalam gambar DOCX belum dibaca.", className);
    if (warnings.includes("ambiguous_technical_token_not_corrected")) paragraph(container, "Ada istilah teknis OCR yang ambigu; teks tidak dikoreksi otomatis.", className);
    if (!compact && Array.isArray(q.pages) && q.pages.length) {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = "Rincian pembacaan per halaman";
      details.append(summary);
      const methods = { native_text: "Teks native", ocr: "OCR", failed: "Gagal dibaca" };
      for (const page of q.pages.slice(0, 30)) {
        if (!Number.isInteger(page.page) || page.page < 1) continue;
        let text = `Halaman ${page.page}: ${methods[page.method] || "Metode tidak tersedia"}.`;
        if (page.ocr_status === "failed") text += " OCR gagal.";
        if (["skipped_budget", "unavailable"].includes(page.ocr_status)) text += " OCR tidak dapat dijalankan.";
        const score = number(page.ocr_confidence?.mean_word_score);
        if (page.ocr_confidence?.source === "tesseract_word_data" && score !== null && score >= 0 && score <= 100) {
          text += ` Nilai engine OCR rata-rata ${score.toFixed(2)}/100; bukan persentase akurasi.`;
        } else if (page.ocr_attempted) text += " Nilai keyakinan OCR tidak tersedia.";
        paragraph(details, text, className);
      }
      container.append(details);
    }
  }
  function renderAssessment(container, data, className = "result-empty") {
    container.replaceChildren();
    const info = data?.analysis_metadata?.scoring_info ?? data?.scoring_info;
    const weight = number(info?.observed_weight);
    if (weight === null || weight < 0 || weight > 1) {
      paragraph(container, "Informasi cakupan penilaian tidak tersedia.", className);
    } else {
      paragraph(container, `Cakupan penilaian skor: ${(weight * 100).toFixed(0)}% bobot komponen terukur.${info.assessment_status === "partial" || weight < 1 ? " Penilaian parsial." : ""}`, className);
    }
    const unknown = Array.isArray(info?.unknown_components) ? info.unknown_components.filter(k => names[k]) : [];
    if (unknown.length) paragraph(container, `Belum dapat dinilai: ${unknown.map(k => names[k]).join(", ")}. Bukti belum cukup atau persyaratan tidak tersedia; bukan nilai 0%.`, className);
    const coverage = data?.analysis_metadata?.job_understanding?.requirement_coverage ??
      data?.job_understanding?.requirement_coverage;
    const validCount = n => Number.isInteger(n) && n >= 0;
    if (coverage && [coverage.total, coverage.recognized, coverage.unresolved].every(validCount) &&
        coverage.recognized + coverage.unresolved === coverage.total) {
      paragraph(container, `Persyaratan dikenali: ${coverage.recognized} dari ${coverage.total}; belum dapat dipetakan: ${coverage.unresolved}. Ini berbeda dari cakupan bobot skor.`, className);
      if (coverage.unresolved > 0) paragraph(container, "Skill match hanya menilai persyaratan yang dikenali; persyaratan yang belum dipahami tidak dianggap terpenuhi.", className);
    } else paragraph(container, "Informasi cakupan pengenalan persyaratan tidak tersedia.", className);
    if (Array.isArray(coverage?.items) && coverage.items.length) {
      const details = document.createElement('details');const title=document.createElement('summary');title.textContent='Rincian persyaratan & bukti';details.append(title);
      const labels={recognized:'Dikenali; lihat hasil skill match untuk kecocokan',matched:'Terpenuhi berdasarkan bukti',unmatched:'Belum terbukti',unresolved:'Belum dapat dipetakan'};
      for(const item of coverage.items.slice(0,100))if(typeof item.text==='string')paragraph(details,`${item.text} — ${labels[item.status] || 'Status tidak tersedia'}`,className);
      container.append(details);
    }
    const profile = data?.analysis_metadata?.cv_understanding ?? data?.cv_understanding;
    if (Array.isArray(profile?.skills)) {
      const positive = profile.skills.filter(skill => typeof skill.name === 'string' && typeof skill.evidence === 'string');
      if (positive.length) {
        const proof = document.createElement('details');const summary=document.createElement('summary');summary.textContent='Bukti keterampilan dari CV';proof.append(summary);
        for(const skill of positive.slice(0,50)) paragraph(proof, `${skill.name}: ${skill.evidence}`, className);
        container.append(proof);
      }
    }
    paragraph(container, "Skor kecocokan adalah heuristik, bukan peluang diterima kerja. Cakupan skor berbeda dari kelengkapan pembacaan CV.", className);
  }
  function requirementsKnown(role) {
    return !!role && role.requirements_status !== "unknown" && role.source !== "classifier_label" &&
      !["unknown", "legacy_unverified"].includes(role.skill_match_status) &&
      (role.requirements_status === "known" || role.skill_match_available === true) && role.skill_match_available !== false;
  }
  function salaryLabel(role) {
    const meta = role?.salary_metadata;
    if (meta?.status !== "verified" || !role.salary_range || !meta.currency || !meta.payment_period ||
        !(meta.location || meta.market) || !meta.source) return null;
    const source = typeof meta.source === "string" ? meta.source : meta.source.label || meta.source.name || meta.source.dataset;
    if (!source) return null;
    return `Gaji referensi: ${role.salary_range} ${meta.currency} / ${meta.payment_period} (${meta.location || meta.market}). Sumber: ${source}.`;
  }
  return { quality, renderQuality, renderAssessment, requirementsKnown, salaryLabel };
})();
