/* White Border Tool — UI wiring. Depends on app.js (window.WhiteBorder). */
(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const $all = (sel) => Array.from(document.querySelectorAll(sel));

  const dropzone = $("#dropzone");
  const fileInput = $("#fileInput");
  const fileList = $("#fileList");
  const fileCount = $("#fileCount");
  const clearBtn = $("#clearBtn");
  const processBtn = $("#processBtn");
  const progressWrap = $("#progressWrap");
  const progressBar = $("#progressBar");
  const progressLabel = $("#progressLabel");
  const brandToggle = $("#brandToggle");
  const brandGrid = $("#brandGrid");
  const resultsSection = $("#resultsSection");
  const resultsGrid = $("#resultsGrid");
  const downloadAllBtn = $("#downloadAllBtn");
  const emptyState = $("#emptyState");

  /** @type {{id:number, file:File, url:string}[]} */
  let queue = [];
  let nextId = 1;
  let results = [];

  // ── brand chip grid ─────────────────────────────────────────────────
  for (const [key, [label]] of Object.entries(window.WhiteBorder.SUPPORTED_BRANDS)) {
    const chip = document.createElement("label");
    chip.className = "chip";
    chip.innerHTML = `<input type="checkbox" value="${key}" checked /><span>${label}</span>`;
    brandGrid.appendChild(chip);
  }

  function setBrandGridEnabled(enabled) {
    brandGrid.classList.toggle("disabled", !enabled);
    $all('#brandGrid input[type="checkbox"]').forEach((cb) => (cb.disabled = !enabled));
  }
  brandToggle.addEventListener("change", () => setBrandGridEnabled(brandToggle.checked));
  setBrandGridEnabled(brandToggle.checked);

  // ── file intake ──────────────────────────────────────────────────────
  function acceptFiles(fileListLike) {
    const incoming = Array.from(fileListLike).filter((f) => /^image\/(jpeg|png)$/.test(f.type));
    for (const file of incoming) {
      queue.push({ id: nextId++, file, url: URL.createObjectURL(file) });
    }
    renderFileList();
  }

  function removeFile(id) {
    const idx = queue.findIndex((q) => q.id === id);
    if (idx !== -1) {
      URL.revokeObjectURL(queue[idx].url);
      queue.splice(idx, 1);
      renderFileList();
    }
  }

  function renderFileList() {
    fileList.innerHTML = "";
    fileCount.textContent = queue.length ? `${queue.length} image${queue.length === 1 ? "" : "s"} ready` : "";
    emptyState.hidden = queue.length !== 0;
    clearBtn.hidden = queue.length === 0;
    processBtn.disabled = queue.length === 0;

    for (const item of queue) {
      const row = document.createElement("li");
      row.className = "file-row";
      row.innerHTML = `
        <img class="file-thumb" src="${item.url}" alt="" />
        <span class="file-name" title="${item.file.name}">${item.file.name}</span>
        <span class="file-size">${formatBytes(item.file.size)}</span>
        <button class="file-remove" type="button" aria-label="Remove">&times;</button>
      `;
      row.querySelector(".file-remove").addEventListener("click", () => removeFile(item.id));
      fileList.appendChild(row);
    }
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  clearBtn.addEventListener("click", () => {
    queue.forEach((q) => URL.revokeObjectURL(q.url));
    queue = [];
    renderFileList();
  });

  fileInput.addEventListener("change", (e) => {
    acceptFiles(e.target.files);
    fileInput.value = "";
  });

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("drag-active");
    })
  );
  ["dragleave", "dragend"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("drag-active");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-active");
    if (e.dataTransfer?.files?.length) acceptFiles(e.dataTransfer.files);
  });
  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  // ── processing ───────────────────────────────────────────────────────
  processBtn.addEventListener("click", runProcessing);

  async function runProcessing() {
    if (!queue.length) return;
    processBtn.disabled = true;
    clearBtn.disabled = true;
    progressWrap.hidden = false;
    progressBar.style.width = "0%";
    resultsGrid.innerHTML = "";
    results = [];

    const outputSide = Number($('input[name="size"]:checked').value);
    const showBrand = brandToggle.checked;
    const enabledBrands = showBrand
      ? new Set($all('#brandGrid input[type="checkbox"]:checked').map((cb) => cb.value))
      : null;

    const total = queue.length;
    for (let i = 0; i < total; i++) {
      const item = queue[i];
      progressLabel.textContent = `Processing ${i + 1} / ${total} — ${item.file.name}`;
      try {
        const result = await window.WhiteBorder.processFile(item.file, { outputSide, showBrand, enabledBrands });
        const stem = item.file.name.replace(/\.[^.]+$/, "");
        const outName = `${stem}_insta.jpg`;
        results.push({ name: outName, blob: result.blob, placement: result.placement, brand: result.brand });
        addResultCard(outName, result);
      } catch (err) {
        addErrorCard(item.file.name, err);
      }
      progressBar.style.width = `${Math.round(((i + 1) / total) * 100)}%`;
      // yield to the UI thread between files
      await new Promise((r) => setTimeout(r, 0));
    }

    progressLabel.textContent = `Done — ${results.length} / ${total} processed`;
    processBtn.disabled = false;
    clearBtn.disabled = false;
    resultsSection.hidden = results.length === 0;
    downloadAllBtn.hidden = results.length < 2;
    if (results.length) resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function addResultCard(name, result) {
    const url = URL.createObjectURL(result.blob);
    const card = document.createElement("div");
    card.className = "result-card";
    const badge = result.brand ? window.WhiteBorder.SUPPORTED_BRANDS[result.brand][0] : null;
    card.innerHTML = `
      <a class="result-thumb" href="${url}" download="${name}">
        <img src="${url}" alt="${name}" loading="lazy" />
      </a>
      <div class="result-meta">
        <span class="result-name" title="${name}">${name}</span>
        <span class="result-tags">
          <span class="tag">${result.placement}</span>
          ${badge ? `<span class="tag tag-brand">${badge}</span>` : ""}
        </span>
      </div>
      <a class="btn btn-small btn-ghost" href="${url}" download="${name}">Download</a>
    `;
    resultsGrid.appendChild(card);
  }

  function addErrorCard(name, err) {
    const card = document.createElement("div");
    card.className = "result-card result-card-error";
    card.innerHTML = `
      <div class="result-error-icon">!</div>
      <div class="result-meta">
        <span class="result-name" title="${name}">${name}</span>
        <span class="result-tags"><span class="tag tag-error">${String(err.message || err)}</span></span>
      </div>
    `;
    resultsGrid.appendChild(card);
  }

  downloadAllBtn.addEventListener("click", async () => {
    downloadAllBtn.disabled = true;
    downloadAllBtn.textContent = "Zipping…";
    try {
      const zip = new JSZip();
      for (const r of results) zip.file(r.name, r.blob);
      const blob = await zip.generateAsync({ type: "blob" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "whiteborder_output.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
    } finally {
      downloadAllBtn.disabled = false;
      downloadAllBtn.textContent = "Download all (.zip)";
    }
  });

  // warm up the font as soon as the page is interactive
  window.WhiteBorder.ensureFont();
})();
