// ---------------- INIT ----------------

document.addEventListener("DOMContentLoaded", () => {
  enforceAuth();

  document.querySelectorAll("[data-action='back']").forEach((el) => {
    el.addEventListener("click", goBackToMain);
  });

  initValidation();
});

// ---------------- AUTH CHECK ----------------

async function enforceAuth() {
  try {
    const r = await fetch("/auth-check");

    if (!r.ok) {
      window.location = "/login";
      return;
    }

    const data = await r.json();

    if (!data.logged_in) {
      window.location = "/login";
    }
  } catch (err) {
    window.location = "/login";
  }
}

function goBackToMain(e) {
  e.preventDefault();

  if (window.opener) {
    window.opener.focus();
    window.close();
  } else {
    window.location.href = "/dashboard";
  }
}

// ---------------- VALIDATION ----------------

function initValidation() {
  const pdfInput = document.getElementById("pdfInput");
  const csvInput = document.getElementById("csvInput");

  // PDF upload → use setLoadedState
  pdfInput?.addEventListener("change", () => {
    if (!pdfInput.files.length) return;
    setLoadedState(pdfInput, "PDF");
  });

  // CSV upload → mark loaded + parse
  csvInput?.addEventListener("change", (event) => {
    if (!csvInput.files.length) return;
    setLoadedState(csvInput, "CSV");
    handleCsvUpload(event);
  });
}

function setLoadedState(input, type) {
  const card = input.closest(".validation-card");
  if (!card) return;

  card.classList.add("is-loaded");

  const pageContainer = document.querySelector(".page-container");
  if (pageContainer) pageContainer.classList.add("is-loaded");

  const upload = card.querySelector(".validation-upload");
  if (upload) upload.remove();

  // Only PDF injects content here
  if (type === "PDF") {
    const body = card.querySelector(".validation-card-body");
    if (!body) return;

    const content = document.createElement("div");
    content.className = "validation-content";
    renderPDF(input.files[0], content);
    body.appendChild(content);
  }
}

let pdfDoc = null;
const pageElements = [];

function renderPDF(file, container) {
    const url = URL.createObjectURL(file);

    const viewer = document.createElement("iframe");
    viewer.id = "pdfViewer";
    viewer.dataset.pdfUrl = url;

    viewer.src = url;
    viewer.style.width = "100%";
    viewer.style.height = "100%";
    viewer.style.border = "0";

    container.appendChild(viewer);
}


function createPageList(totalPages) {
  const pageList = document.getElementById("pageList");
  pageList.innerHTML = "";

  for (let i = 1; i <= totalPages; i++) {
    const btn = document.createElement("button");

    btn.textContent = i;
    btn.className = "btn btn-outline-secondary btn-sm";

    btn.addEventListener("click", () => {
      const viewer = document.getElementById("pdfViewer");

      if (!viewer) return;

      const pdfUrl = viewer.dataset.pdfUrl;

      viewer.src = `${pdfUrl}#page=${i}`;
    });

    pageList.appendChild(btn);
  }
}

let validationRecords = [];
let currentValidationIndex = 0;

const validationMetrics = [
  "alpha",
  "arithmetic_mean_ratio",
  "average_div_yield",
  "average_pb",
  "average_pe",
  "avg_maturity",
  "beta",
  "correlation_ratio",
  "downside_deviation",
  "information_ratio",
  "macaulay",
  "mod_duration",
  "port_turnover_ratio",
  "r_squared_ratio",
  "roe_ratio",
  "sharpe",
  "sortino_ratio",
  "std_dev",
  "tracking_error",
  "treynor_ratio",
  "upside_deviation",
  "ytm",
];

function handleCsvUpload(event) {
  const input = event.target;
  const file = input.files?.[0];
  if (!file) return;

  Papa.parse(file, {
    header: true,
    skipEmptyLines: true,
    complete(result) {
      validationRecords = result.data;
      if (!validationRecords.length) return;

      const card = input.closest(".validation-card");
      card.classList.add("is-loaded");

      const upload = card.querySelector(".validation-upload");
      if (upload) upload.remove();

      const tpl = document.getElementById("csvFormTemplate");
      if (tpl) {
        const content = tpl.content.cloneNode(true);
        card.querySelector(".validation-card-body").appendChild(content);

        // Now safe to render sidebar + select record
        renderValidationPages();
        selectValidationRecord(0);
      } else {
        console.error("CSV form template not found in DOM");
      }
    },
    error(error) {
      console.error("CSV parse error:", error);
    },
  });
}

/* ---------------------------------------------------------
   PAGE SIDEBAR
--------------------------------------------------------- */

function renderValidationPages() {
  const pageList = document.getElementById("pageList");
  if (!pageList) return;

  pageList.innerHTML = "";

  validationRecords.forEach((record, index) => {
    const page = document.createElement("button");
    page.type = "button";
    page.className = "nav-btn";
    page.textContent = `${record.page_number}`;
    page.dataset.index = index;

    page.addEventListener("click", () => {
      selectValidationRecord(index);
    });

    pageList.appendChild(page);
  });
}

/* ---------------------------------------------------------
   SELECT RECORD
--------------------------------------------------------- */

function selectValidationRecord(index) {
  const record = validationRecords[index];
  if (!record) return;

  currentValidationIndex = index;

  // highlight active button
  document
    .querySelectorAll(".validation-page-btn")
    .forEach((btn, i) => btn.classList.toggle("active", i === index));

  // sync with PDF viewer
  if (typeof loadPDFPage === "function") {
    loadPDFPage(record.page_number); // 👈 scrolls PDF to that page
  }

  // update form fields
  populateValidationForm(record);
}

function populateValidationForm(record) {
  // Basic fields
  document.getElementById("main_scheme_name").value =
    record.main_scheme_name || "nil";
  document.getElementById("benchmark_index").value =
    record.benchmark_index || "nil";
  document.getElementById("monthly_aaum_value").value =
    record.monthly_aaum_value || "nil";
  document.getElementById("monthly_aaum_date").value =
    record.monthly_aaum_date || "nil";
  document.getElementById("scheme_launch_date").value =
    record.scheme_launch_date || "nil";

  document.getElementById("min_amounts").value = [
    record.min_amt || "nil",
    record.min_amt_multiple || "nil",
    record.min_addl_amt || "nil",
    record.min_addl_amt_multiple || "nil",
  ].join(",");

  // Metrics compact string (loop through all)
  const metricsCombined = validationMetrics
    .map((metric) => {
      const value = isEmpty(record[metric]) ? "nil" : record[metric];
      return `${value}--${metric}`;
    })
    .join("\n");
  document.getElementById("metricsGrid").value = metricsCombined;

  // Fund managers compact string (loop through all name_x)
  const managers = [];
  Object.keys(record).forEach((key) => {
    if (key.startsWith("name_") && !isEmpty(record[key])) {
      const index = key.split("_")[1];
      const since = isEmpty(record[`managing_fund_since_${index}`])
        ? "nil"
        : record[`managing_fund_since_${index}`];
      const exp = isEmpty(record[`total_exp_${index}`])
        ? "nil"
        : record[`total_exp_${index}`];
      const qual = isEmpty(record[`qualification_${index}`])
        ? "nil"
        : record[`qualification_${index}`];
      managers.push(`${record[key]}--${since}--${exp}--${qual}`);
    }
  });
  document.getElementById("fundManagerText").value = managers.join("\n");

  // Load
  document.getElementById("entry").value = record.entry || "";
  document.getElementById("exit").value = record.exit || "";
}

/* ---------------------------------------------------------
   HELPERS
--------------------------------------------------------- */

function setField(id, value) {
  const field = document.getElementById(id);

  if (!field) {
    return;
  }

  field.value = isEmpty(value) ? "nil" : value;
}

function isEmpty(value) {
  return value === undefined || value === null || value === "";
}

function formatBenchmark(value) {
  if (isEmpty(value)) {
    return "nil";
  }

  try {
    const parsed = JSON.parse(value);

    if (Array.isArray(parsed)) {
      return parsed.join(", ");
    }
  } catch (_) {
    // Keep original value.
  }

  return value;
}

function formatLabel(value) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}
