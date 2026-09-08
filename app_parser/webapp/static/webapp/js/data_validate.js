// ---------------- INIT ----------------

import * as pdfjsLib from "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.7.76/pdf.min.mjs";
pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.7.76/pdf.worker.min.mjs";

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

// function renderPDF(file, container) {
//     const url = URL.createObjectURL(file);

//     container.innerHTML = "";

//     const pdfViewer = document.createElement("div");
//     pdfViewer.id = "pdfViewer";
//     pdfViewer.className = "pdf-viewer";

//     container.appendChild(pdfViewer);
//     const loadingTask = pdfjsLib.getDocument({
//         url: url
//     });

//     loadingTask.promise.then((pdf) => {
//         pdfDoc = pdf;

//         for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber++) {
//             renderPDFPage(pageNumber, pdfViewer);
//         }
//     }).catch((error) => {
//         console.error("PDF load error:", error);
//     });
// }

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

async function renderPDFPage(pageNumber, container) {
    try {
        const page = await pdfDoc.getPage(pageNumber);

        const pageWrapper = document.createElement("div");
        pageWrapper.className = "pdf-page";
        pageWrapper.dataset.pageNumber = pageNumber;

        const canvas = document.createElement("canvas");
        canvas.className = "pdf-canvas";

        const context = canvas.getContext("2d");

        const viewport = page.getViewport({
            scale: 1.5
        });

        canvas.width = viewport.width;
        canvas.height = viewport.height;

        pageWrapper.appendChild(canvas);
        container.appendChild(pageWrapper);

        await page.render({
            canvasContext: context,
            viewport: viewport
        }).promise;

    } catch (error) {
        console.error(`Error rendering PDF page ${pageNumber}:`, error);
    }
}


// function loadPDFPage(pageNumber) {
//     const page = document.querySelector(
//         `.pdf-page[data-page-number="${pageNumber}"]`
//     );

//     if (!page) {
//         console.warn("PDF page not rendered:", pageNumber);
//         return;
//     }

//     page.scrollIntoView({
//         behavior: "smooth",
//         block: "start"
//     });
// }

function loadPDFPage(pageNumber) {
    const viewer = document.getElementById("pdfViewer");

    if (!viewer) return;

    const pdfUrl = viewer.dataset.pdfUrl;

    if (!pdfUrl) return;

    console.log("Going to PDF page:", pageNumber);

    viewer.src = "about:blank";

    setTimeout(() => {
        viewer.src = `${pdfUrl}#page=${pageNumber}`;
    }, 50);
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
const lockedPages = new Set();
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

                // Buttons now exist because the template has been inserted
                document.getElementById("savePageBtn")?.addEventListener(
                    "click",
                    saveCurrentPage
                );

                document.getElementById("lockPageBtn")?.addEventListener(
                    "click",
                    lockCurrentPage
                );

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

let validationPageNumbers = [];
let paginationStart = 0;

const PAGINATION_VISIBLE = 12;
let currentPageNumber = null;


function renderValidationPages() {
    const pageList = document.getElementById("pageList");
    if (!pageList) return;

    validationPageNumbers = [
        ...new Set(
            validationRecords
                .map(record => Number(record.page_number))
                .filter(Number.isInteger)
        )
    ].sort((a, b) => a - b);

    paginationStart = 0;

    renderPaginationWindow();
}

function renderPaginationWindow() {
    const pageList = document.getElementById("pageList");
    if (!pageList) return;

    pageList.innerHTML = "";

    // UP
    const upButton = document.createElement("button");
    upButton.type = "button";
    upButton.className = "nav-btn pagination-arrow";
    upButton.textContent = "▲";
    upButton.disabled = paginationStart === 0;

    upButton.addEventListener("click", () => {
        paginationStart = Math.max(
            0,
            paginationStart - PAGINATION_VISIBLE
        );

        renderPaginationWindow();
    });

    pageList.appendChild(upButton);

    // PAGE NUMBERS
    const visiblePages = validationPageNumbers.slice(
        paginationStart,
        paginationStart + PAGINATION_VISIBLE
    );

    visiblePages.forEach(pageNumber => {
        const page = document.createElement("button");

        page.type = "button";
        page.className = "nav-btn validation-page-btn";

        if (lockedPages.has(pageNumber)) {
            page.classList.add("page-locked");
        } else {
            page.classList.add("page-unlocked");
        }
        page.textContent = pageNumber;
        page.dataset.page = pageNumber;

        page.addEventListener("click", () => {
            selectValidationPage(pageNumber);
        });

        pageList.appendChild(page);
    });

    // DOWN
    const downButton = document.createElement("button");
    downButton.type = "button";
    downButton.className = "nav-btn pagination-arrow";
    downButton.textContent = "▼";

    downButton.disabled =
        paginationStart + PAGINATION_VISIBLE >=
        validationPageNumbers.length;

    downButton.addEventListener("click", () => {
        paginationStart = Math.min(
            validationPageNumbers.length - PAGINATION_VISIBLE,
            paginationStart + PAGINATION_VISIBLE
        );

        renderPaginationWindow();
    });

    pageList.appendChild(downButton);

    updatePaginationActiveState();
}


function updatePaginationActiveState() {
    const record = validationRecords[currentValidationIndex];

    if (!record) return;

    const currentPage = Number(record.page_number);

    document
        .querySelectorAll(".validation-page-btn")
        .forEach(btn => {
            btn.classList.toggle(
                "active",
                Number(btn.dataset.page) === currentPage
            );
        });
}

function updatePaginationLockState() {
    document
        .querySelectorAll(".validation-page-btn")
        .forEach(btn => {
            const pageNumber = Number(btn.dataset.page);
            const isLocked = lockedPages.has(pageNumber);

            btn.classList.toggle(
                "page-locked",
                isLocked
            );

            btn.classList.toggle(
                "page-unlocked",
                !isLocked
            );
        });
}

/* ---------------------------------------------------------
   SELECT RECORD
--------------------------------------------------------- */

function selectValidationRecord(index) {
    const record = validationRecords[index];

    if (!record) return;

    currentValidationIndex = index;
    const pageNumber = Number(record.page_number);
    currentPageNumber = pageNumber;


    document
        .querySelectorAll(".validation-page-btn")
        .forEach(btn => {
            btn.classList.toggle(
                "active",
                Number(btn.dataset.page) === pageNumber
            );
        });
    loadPDFPage(record.page_number);
    populateValidationForm(record);
    applyPageLockState();
}

function applyPageLockState() {
    const record = validationRecords[currentValidationIndex];

    if (!record) return;

    const pageNumber = Number(record.page_number);
    const isLocked = lockedPages.has(pageNumber);

    document
        .querySelectorAll(".validation-field")
        .forEach(field => {
            field.readOnly = isLocked;
        });

    const lockBtn = document.getElementById("lockPageBtn");

    if (lockBtn) {
        const icon = lockBtn.querySelector(
            ".material-symbols-outlined"
        );

        if (isLocked) {
            lockBtn.title = "Unlock current page";

            if (icon) {
                icon.textContent = "lock";
            }
        } else {
            lockBtn.title = "Lock current page";

            if (icon) {
                icon.textContent = "lock_open";
            }
        }
    }

    updatePaginationLockState();
}

function updatePageColors() {
    document
        .querySelectorAll(".validation-page-btn")
        .forEach(btn => {
            const pageNumber = Number(btn.dataset.page);
            const isLocked = lockedPages.has(pageNumber);

            btn.classList.toggle("page-locked", isLocked);
            btn.classList.toggle("page-unlocked", !isLocked);
        });
}

function populateValidationForm(record) {
    // Basic fields
    document.getElementById("main_scheme_name").value =
        record.main_scheme_name || "nil";
    document.getElementById("benchmark_index").value =
        record.benchmark_index || "nil";
    document.getElementById("monthly_aaum_value").value =
        record.monthly_aaum_value || "nil";
    //   document.getElementById("monthly_aaum_date").value =
    //     record.monthly_aaum_date || "nil";
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

function selectValidationPage(pageNumber) {

    loadPDFPage(pageNumber);

    const recordIndex = validationRecords.findIndex(
        record => Number(record.page_number) === pageNumber
    );

    if (recordIndex === -1) {
        console.warn("No CSV data found for PDF page:", pageNumber);
        return;
    }

    selectValidationRecord(recordIndex);
}


function saveCurrentPage() {
    const record = validationRecords[currentValidationIndex];

    if (!record) return;

    const pageNumber = Number(record.page_number);

    if (lockedPages.has(pageNumber)) {
        return;
    }

    // ---------------------------------------------------------
    // BASIC FIELDS
    // ---------------------------------------------------------

    record.main_scheme_name =
        document.getElementById("main_scheme_name")?.value || "";

    record.benchmark_index =
        document.getElementById("benchmark_index")?.value || "";

    record.monthly_aaum_value =
        document.getElementById("monthly_aaum_value")?.value || "";

    record.scheme_launch_date =
        document.getElementById("scheme_launch_date")?.value || "";


    // ---------------------------------------------------------
    // MINIMUM AMOUNTS
    // min_amt, min_amt_multiple, min_addl_amt, min_addl_amt_multiple
    // ---------------------------------------------------------

    const minAmounts =
        document.getElementById("min_amounts")?.value || "";

    const minValues = minAmounts.split(",");

    record.min_amt = minValues[0]?.trim() || "";
    record.min_amt_multiple = minValues[1]?.trim() || "";
    record.min_addl_amt = minValues[2]?.trim() || "";
    record.min_addl_amt_multiple = minValues[3]?.trim() || "";


    // ---------------------------------------------------------
    // METRICS
    // value--metric
    // ---------------------------------------------------------

    const metricsText =
        document.getElementById("metricsGrid")?.value || "";

    metricsText
        .split("\n")
        .map(line => line.trim())
        .filter(Boolean)
        .forEach(line => {
            const separatorIndex = line.lastIndexOf("--");

            if (separatorIndex === -1) return;

            const value = line
                .slice(0, separatorIndex)
                .trim();

            const metric = line
                .slice(separatorIndex + 2)
                .trim();

            if (!metric) return;

            record[metric] =
                isEmpty(value) || value === "nil"
                    ? ""
                    : value;
        });


    // ---------------------------------------------------------
    // FUND MANAGERS
    // name--since--experience--qualification
    // ---------------------------------------------------------

    const managerText =
        document.getElementById("fundManagerText")?.value || "";

    const managers = managerText
        .split("\n")
        .map(line => line.trim())
        .filter(Boolean);

    // Find the manager indexes that already exist
    // in the original CSV record.
    const managerIndexes = Object.keys(record)
        .filter(key => /^name_\d+$/.test(key))
        .map(key => Number(key.split("_")[1]))
        .sort((a, b) => a - b);

    managers.forEach((manager, position) => {
        const index = managerIndexes[position];

        if (index === undefined) return;

        const values = manager.split("--");

        record[`name_${index}`] =
            values[0]?.trim() || "";

        record[`managing_fund_since_${index}`] =
            values[1]?.trim() || "";

        record[`total_exp_${index}`] =
            values[2]?.trim() || "";

        record[`qualification_${index}`] =
            values[3]?.trim() || "";
    });

    // Clear any existing manager rows that were removed
    // from the form.
    managerIndexes.slice(managers.length).forEach(index => {
        record[`name_${index}`] = "";
        record[`managing_fund_since_${index}`] = "";
        record[`total_exp_${index}`] = "";
        record[`qualification_${index}`] = "";
    });


    // ---------------------------------------------------------
    // LOAD
    // ---------------------------------------------------------

    record.entry =
        document.getElementById("entry")?.value || "";

    record.exit =
        document.getElementById("exit")?.value || "";


    // ---------------------------------------------------------
    // IMPORTANT:
    // These remain untouched:
    //
    // record.amc_name
    // record.mutual_fund_name
    // record.monthly_aaum_date
    // ---------------------------------------------------------

    console.log("Saved page:", pageNumber);
}

function lockCurrentPage() {
    const record = validationRecords[currentValidationIndex];

    if (!record) return;

    const pageNumber = Number(record.page_number);

    // Already locked → unlock
    if (lockedPages.has(pageNumber)) {
        lockedPages.delete(pageNumber);

        applyPageLockState();

        console.log("Unlocked page:", pageNumber);

        return;
    }

    // Currently unlocked → save first, then lock
    saveCurrentPage();

    lockedPages.add(pageNumber);

    applyPageLockState();

    console.log("Locked page:", pageNumber);
}


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