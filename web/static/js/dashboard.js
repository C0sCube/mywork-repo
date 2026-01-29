/* ================= AUTH ================= */
(async function enforceAuth() {
    try {
        const r = await fetch("/auth-check");
        const data = await r.json();
        if (!data.logged_in) {
            alert("Session Expired. Log in Again.");
            window.location = "/login";
        }
    } catch {
        alert("Unable to verify. Redirecting to login.");
        window.location = "/login";
    }
})();

/* ================= STATE ================= */
let selectedFiles = [];
let amcRegistry = {};
let currentPage = 1;
const pageSize = 15;

/* ================= INIT ================= */
document.addEventListener("DOMContentLoaded", async () => {
    bindActions();
    await loadRegistry();
    await loadLogs();

    setInterval(() => {
        const auto = document.getElementById("autoRefresh");
        if (auto?.checked) loadLogs();
    }, 15000);
});

/* ================= ACTION BINDINGS ================= */
function bindActions() {
    document.querySelector("[data-action='open-upload']")
        ?.addEventListener("click", () => toggleModal(true));

    document.querySelector("[data-action='close-upload']")
        ?.addEventListener("click", () => toggleModal(false));

    document.querySelectorAll("[data-action='new-tab']")
        .forEach(a => a.addEventListener("click", openInNewTab));

    document.querySelector("[data-action='refresh-logs']")
        ?.addEventListener("click", () => loadLogs());

    document.getElementById("pdfs")
        ?.addEventListener("change", onFileSelect);

    document.getElementById("uploadForm")
        ?.addEventListener("submit", uploadFiles);
}

/* ================= NAV ================= */
function openInNewTab(e) {
    e.preventDefault();
    window.open(e.currentTarget.href, "_blank");
}

/* ================= MODAL ================= */
function toggleModal(state) {
    const modal = document.getElementById("uploadModal");
    if (!modal) return;
    modal.classList.toggle("show", state);
}

/* ================= REGISTRY ================= */
async function loadRegistry() {
    try {
        const resp = await fetch("/company_registry");
        amcRegistry = await resp.json();
    } catch {
        amcRegistry = {};
    }
}

/* ================= FILE UPLOAD ================= */
function onFileSelect(e) {
    const sizeDiv = document.getElementById("sizeDisplay");
    const files = Array.from(e.target.files);

    files.forEach(f => {
        if (!selectedFiles.some(x => x.name === f.name && x.size === f.size)) {
            selectedFiles.push(f);
        }
    });

    updateUploadDisplay();
    e.target.value = "";
}

async function uploadFiles(ev) {
    ev.preventDefault();
    if (!selectedFiles.length) return alert("No files selected.");

    const consoleDiv = document.getElementById("uploadConsole");

    for (let i = 0; i < selectedFiles.length; i++) {
        const fd = new FormData();
        fd.append("pdfs", selectedFiles[i]);

        const row = consoleDiv.children[i];
        row.textContent = `Uploading… (${i + 1}/${selectedFiles.length})`;

        try {
            await fetch("/upload", { method: "POST", body: fd });
            row.textContent = `${selectedFiles[i].name} ✔`;
        } catch {
            row.textContent = `${selectedFiles[i].name} ❌`;
        }
    }

    alert("All uploads submitted.");
    window.location.reload();
}

function updateUploadDisplay() {
    const consoleDiv = document.getElementById("uploadConsole");
    const sizeDiv = document.getElementById("sizeDisplay");

    consoleDiv.innerHTML = "";
    let total = 0;

    selectedFiles.forEach((f, i) => {
        total += f.size;
        const d = document.createElement("div");
        d.innerHTML = `${f.name} (${(f.size / 1048576).toFixed(2)} MB)`;
        consoleDiv.appendChild(d);
    });

    sizeDiv.textContent = `Size ${(total / 1048576).toFixed(2)} Mb / 50 Mb`;
}

/* ================= LOGS ================= */
async function loadLogs() {
    const logsConsole = document.getElementById("logsConsole");
    logsConsole.innerHTML = "<p>Loading…</p>";

    try {
        const resp = await fetch(
            `/status_data?page=${currentPage}&size=${pageSize}`
        );
        const data = await resp.json();

        if (!data.success || !data.rows.length) {
            logsConsole.innerHTML = "<p>No status yet.</p>";
            renderPagination(1);
            return;
        }

        renderTable(data.rows);
        renderPagination(data.totalPages);

    } catch (err) {
        console.error(err);
        logsConsole.innerHTML = "<p>Error loading logs.</p>";
    }
}

/* ================= TABLE RENDER ================= */
function renderTable(rows) {
    const logsConsole = document.getElementById("logsConsole");
    const table = document.createElement("table");
    table.className = "status-table";

    table.innerHTML = `
    <tr>
      <th style = "width:40px" >#</th>
      <th style = "width:180px" >File</th>
      <th style = "width:130px" >Processed</th>
      <th style = "width:90px" >Status</th>
      <th style = "width:150px" >User</th>
      <th style = "width:fill">Error</th>
      <th style = "width:60px" >JSON</th>
      <th style = "width:60px" >CSV</th>
      <th style = "width:70px" >Push</th>
      <th style = "width:60px" >RePr</th>
    </tr>`;


    rows.forEach((row, i) => {
        const tr = document.createElement("tr");
        const isPushed = row.status === "PUSHED";

        const pushCell = row.json_path
            ? `
    <label class="switch">
      <input
        type="checkbox"
        data-action="push-slider"
        data-job-id="${row.id}"
        ${isPushed ? "checked disabled" : ""}
      >
      <span></span>
    </label>
  `
            : "-";



        tr.innerHTML = `
        <td>${(currentPage - 1) * pageSize + i + 1}</td>
        <td><a href="/viewer/pdf/${row.file_name}" target="_blank">${row.file_name}</a></td>
        <td>${formatUTCDate(row.end_time)}</td>
        <td>${row.status || "-"}</td>
        <td>${row.uploaded_by}</td>
        <td>${row.error || "-"}</td>
        <td> ${row.json_path ? `<a href="/viewer/json/dashboard/${row.file_name.replace(".pdf", ".json")}" target="_blank" class="menu__link"><span class="material-symbols-outlined">file_json</span></a>` : "-"}</td>
        <td> ${row.json_path ? `<a href="/download_csv?path=${encodeURIComponent(row.json_path)}" class="menu__link"><span class="material-symbols-outlined">docs</span></a>` : "-"}</td>
        <td>${pushCell}</td>
        <td><button class="icon-btn" onclick="confirmReprocess(${row.id})"><span class="material-symbols-outlined">autorenew</span></button></td> `;
        table.appendChild(tr);
    });

    logsConsole.innerHTML = "";
    logsConsole.appendChild(table);
}

/* ================= PAGINATION ================= */
function renderPagination(totalPages) {
    const pag = document.getElementById("logpagination");
    pag.innerHTML = "";

    const prev = document.createElement("a");
    prev.textContent = "‹";
    prev.dataset.page = Math.max(1, currentPage - 1);
    pag.appendChild(prev);

    for (let p = 1; p <= totalPages; p++) {
        const a = document.createElement("a");
        a.textContent = p;
        a.dataset.page = p;
        if (p === currentPage) a.classList.add("active");
        pag.appendChild(a);
    }

    const next = document.createElement("a");
    next.textContent = "›";
    next.dataset.page = Math.min(totalPages, currentPage + 1);
    pag.appendChild(next);
}

/* pagination click */
document.addEventListener("click", e => {
    const link = e.target.closest("#logpagination a[data-page]");
    if (!link) return;

    e.preventDefault();
    const page = Number(link.dataset.page);
    if (page === currentPage) return;

    currentPage = page;
    loadLogs();
});

/* ================= UTILS ================= */
function formatUTCDate(dateString) {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleString("en-GB", {
        day: "2-digit",
        month: "2-digit",
        year: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "UTC"
    });
}


/* ================= PUSH HANDLER ================= */

document.addEventListener("change", async (e) => {
  const slider = e.target.closest("[data-action='push-slider']");
  if (!slider) return;

  const jobId = slider.dataset.jobId;

  // prevent double triggers
  slider.disabled = true;

  const ok = confirm("Are you sure you want to push this JSON to Admin Panel?");
  if (!ok) {
    slider.checked = false;   // rollback UI
    slider.disabled = false;
    return;
  }

  try {
    const resp = await fetch(`/push_job/${jobId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });

    const result = await resp.json();

    if (!resp.ok || !result.success) {
      throw new Error(result.error || "Push failed");
    }

    // ✅ success → freeze ON
    slider.checked = true;
    slider.disabled = true;

  } catch (err) {
    alert("Push failed: " + err.message);
    slider.checked = false;   // rollback
    slider.disabled = false;
  }
});


/* ================= REPROCESS ================= */

async function confirmReprocess(jobId) {
  const ok = confirm("Reprocess this file? This will reset its push state.");
  if (!ok) return;

  try {
    const resp = await fetch(`/reprocess/${jobId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });

    const result = await resp.json();

    if (!resp.ok || !result.success) {
      throw new Error(result.message || "Reprocess failed");
    }

    alert("Reprocess triggered successfully.");

    // 🔥 IMPORTANT: refresh table so slider resets
    loadLogs();

  } catch (err) {
    alert("Reprocess error: " + err.message);
  }
}
