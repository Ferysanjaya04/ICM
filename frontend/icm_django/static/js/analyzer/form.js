/**
 * Analyzer feature JS: drop-zone upload + mode switch.
 * Loaded only on analyzer/form.html via extra_js block.
 */
document.addEventListener('DOMContentLoaded', () => {
    // ── File Upload: drop-zone + label + size guard (5MB) ──
    const fileInput = document.getElementById('id_cv_file');
    const dropZone  = document.getElementById('drop-zone');
    const fileLabel = document.getElementById('file-label');
    const MAX_SIZE  = 5 * 1024 * 1024;

    const setFile = (files) => {
        if (!files.length) return;
        const f = files[0];
        const errEl = document.getElementById('file-size-error');
        if (f.size > MAX_SIZE) {
            if (errEl) { errEl.textContent = 'File "' + f.name + '" ' + (f.size / 1024 / 1024).toFixed(1) + 'MB melebihi batas 5MB.'; errEl.hidden = false; }
            dropZone.classList.remove('has-file');
            fileInput.value = '';
            return;
        }
        if (errEl) { errEl.textContent = ''; errEl.hidden = true; }
        fileInput.files = files;
        if (fileLabel) fileLabel.textContent = f.name + ' (' + (f.size / 1024).toFixed(0) + ' KB)';
        if (dropZone) dropZone.classList.add('has-file');
    };

    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());
        ['dragover', 'dragenter'].forEach(ev => dropZone.addEventListener(ev, e => {
            e.preventDefault();
            dropZone.classList.add('drag-active');
        }));
        ['dragleave', 'drop'].forEach(ev => dropZone.addEventListener(ev, e => {
            e.preventDefault();
            dropZone.classList.remove('drag-active');
        }));
        dropZone.addEventListener('drop', e => setFile(e.dataTransfer.files));
        fileInput.addEventListener('change', () => setFile(fileInput.files));
    }

    // ── Mode switch: toggle job-description field ──
    const modeInputs = document.querySelectorAll('input[name="mode"]');
    const jdWrap = document.getElementById('jd-wrap');
    const syncMode = () => {
        const mode = document.querySelector('input[name="mode"]:checked');
        if (jdWrap && mode) jdWrap.hidden = mode.value !== 'match';
    };
    modeInputs.forEach(el => el.addEventListener('change', syncMode));
    syncMode();

    // ── Drop-zone keyboard access (Enter/Space opens picker) ──
    if (dropZone && fileInput) {
        dropZone.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
        });
    }

    // ── Submit loading state: prevent double-submit ──
    const form = document.getElementById('analyzer-form');
    const submitBtn = document.getElementById('analyze-submit');
    if (form && submitBtn) {
        form.addEventListener('submit', () => {
            if (submitBtn.disabled) return;
            submitBtn.disabled = true;
            const label = submitBtn.querySelector('span');
            if (label) label.textContent = submitBtn.dataset.loadingText || 'Menganalisis…';
            submitBtn.setAttribute('aria-busy', 'true');
        });
    }
});
