/* ================= STATE ================= */
let selectedFiles = [];
let amcRegistry = {};
let currentPage = 1;
const pageSize = 25;

/* ================= INIT ================= */
document.addEventListener("DOMContentLoaded", async () => {
    bindActions();
    await loadRegistry();
    await loadLogs();

    // setInterval(() => {
    //     const auto = document.getElementById("autoRefresh");
    //     if (auto?.checked) loadLogs();
    // }, 15000);
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
        console.log(err);
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
      <th style = "width:40px">#</th>
      <th class ="file-tab">File</th>
      <th style = "width:150px" >User</th>
      <th style = "width:120px" >Start Time</th>
      <th style = "width:110px" >Status</th>
      <th class ="error-tab">Error</th>
      <th style = "width:75px" >JSON</th>
      <th style = "width:45px" >CSV</th>
      <th style = "width:65px" >Push</th>
      <th style = "width:40px" >Rpr</th>
    </tr>`;


    rows.forEach((row, i) => {
        const tr = document.createElement("tr");
        const isPushed = row.status === "PUSHED";
        const jsonName = row.file_name.replace(".pdf", ".json");

        const pushCell = row.json_path ? `<label class="switch">
            <input type="checkbox" data-action="push-slider" data-job-id="${row.id}" ${isPushed ? "checked disabled" : ""}><span></span>
            </label>`: "-";

        
        const isNonReprocessable = row.file_name?.endsWith("_SID.pdf") || row.file_name?.endsWith("_KIM.pdf");


        tr.innerHTML = `
        <td>${(currentPage - 1) * pageSize + i + 1}</td>
        <td><a href="/viewer/pdf/${row.file_name}" target="_blank">${row.file_name}</a></td>
        <td>${formatUser(row.uploaded_by)}</td>
        <td>${formatUTCDate(row.end_time)}</td>
        <td class="${getStatusClass(row.status)}">${row.status|| "-"}</td>
        <td lass="error-tab">${row.error || "-"}</td>
        <td>${row.json_path ? `<a href="/viewer/json/dashboard/${row.file_name.replace(".pdf", ".json")}" target="_blank" class="menu__link"><span class="material-symbols-outlined">file_json</span></a>` : ""} ${row.json_path ? `<a href="/download_dashboard_json/${encodeURIComponent(jsonName)}" class="menu__link"><span class="material-symbols-outlined">download</span></a>` : ""}</td>
        <td>${row.json_path ? `<a href="/dash_csv?path=${encodeURIComponent(row.json_path)}" class="menu__link"><span class="material-symbols-outlined">docs</span></a>` : "-"}</td>
        <td>${pushCell}</td>
        <td><span class="material-symbols-outlined icon-action ${isNonReprocessable ? "repr-disabled" : ""}" ${isNonReprocessable ? "" : `onclick="confirmReprocess(${row.id})"`}>autorenew</span></td>`;
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
    }).replace(",", "");
}

function getStatusClass(status) {
  if (status === "PUSHED" || status === "PARSED") {
    return "status-green";
  }

  if (status === "PARSE_FAILED" || status === "PUSH_FAILED" || status === "INVALID_TYPE") {
    return "status-red";
  }

  return "";
}

function formatUser(u) {
  if (!u) return "-";

  const parts = u.split(".");
  if (parts.length !== 2) return u;

  const cap = s => s[0].toUpperCase() + s.slice(1).toLowerCase();

  return `${cap(parts[0])}.${cap(parts[1])}`;
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
      credentials: "same-origin",   // ✅ ensure session cookie
      headers: {
        "Accept": "application/json" // ✅ expect JSON
      }
    });

    const contentType = resp.headers.get("content-type");

    if (!contentType || !contentType.includes("application/json")) {
      const text = await resp.text();
      throw new Error("Server returned non-JSON: " + text.slice(0, 120));
    }

    const result = await resp.json();

    if (!resp.ok || !result.success) {
      throw new Error(result.message || "Reprocess failed");
    }

    alert("Reprocess triggered successfully.");
    loadLogs();

  } catch (err) {
    console.error(err);
    alert("Reprocess error: " + err.message);
  }
}


// ---------------- AUTH ----------------
// async function enforceAuth() {
//     try {
//         const r = await fetch("/auth-check");

//         if (!r.ok) {
//             window.location = "/login";
//             return;
//         }

//         const data = await r.json();

//         if (!data.logged_in) {
//             window.location = "/login";
//         }

//     } catch (err) {
//         window.location = "/login";
//     }
// }

// ---------------- NAV ----------------
// function goBackToMain(e) {
//   e.preventDefault();
//   if (window.opener) {
//     window.opener.focus();
//     window.close();
//   } else {
//    window.location.href = "/dashboard";

//   }
// }
