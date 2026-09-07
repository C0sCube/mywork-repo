// ---------------- INIT ----------------

document.addEventListener("DOMContentLoaded", () => {
    enforceAuth();

    document.querySelectorAll("[data-action='back']").forEach(el => {
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
    pdfInput?.addEventListener("change", () => {
        if (!pdfInput.files.length) {
            return;
        }

        setLoadedState(pdfInput, "PDF");
    });

    csvInput?.addEventListener("change", () => {
        if (!csvInput.files.length) {
            return;
        }

        setLoadedState(csvInput, "CSV");
    });
}


function setLoadedState(input, type) {

    const card = input.closest(".validation-card");

    if (!card) {
        return;
    }

    card.classList.add("is-loaded");

    const upload = card.querySelector(".validation-upload");

    if (upload) {
        upload.remove();
    }

    const content = document.createElement("div");

    content.className = "validation-content";
    content.dataset.type = type;

    card.querySelector(".validation-card-body").appendChild(content);
}

function setLoadedState(input, type) {

    const card = input.closest(".validation-card");

    if (!card) {
        return;
    }

    card.classList.add("is-loaded");
    const upload = card.querySelector(".validation-upload");
    if (upload) {
        upload.remove();
    }

    const body = card.querySelector(".validation-card-body");

    if (!body) {
        return;
    }

    const content = document.createElement("div");

    content.className = "validation-content";
    content.dataset.type = type;

    body.appendChild(content);

    if (type === "PDF") {
        renderPDF(input.files[0], content);
    }

    // if (type === "CSV") {
    //     renderCSV(input.files[0], content);
    // }
}

function renderPDF(file, container) {

    const url = URL.createObjectURL(file);

    const viewer = document.createElement("iframe");

    viewer.src = url;
    viewer.title = "PDF Viewer";

    viewer.style.width = "100%";
    viewer.style.height = "100%";
    viewer.style.border = "0";

    container.appendChild(viewer);
}

function renderCSV(file, container) {

    const message = document.createElement("div");

    message.textContent = `CSV loaded: ${file.name}`;
    message.className = "csv-loaded-message";

    // container.appendChild(message);
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
    "ytm"
];

const csvInput = document.getElementById("csvInput");

csvInput?.addEventListener("change", handleCsvUpload);


function handleCsvUpload(event) {

    const file = event.target.files?.[0];

    if (!file) {
        return;
    }

    Papa.parse(file, {

        header: true,
        skipEmptyLines: true,

        complete(result) {

            validationRecords = result.data;

            if (!validationRecords.length) {
                return;
            }

            document.getElementById("csvUploadSection").hidden = true;
            document.getElementById("validationContent").hidden = false;

            renderValidationPages();
            selectValidationRecord(0);
        },

        error(error) {
            console.error("CSV parse error:", error);
        }
    });
}


/* ---------------------------------------------------------
   FORM STRUCTURE
--------------------------------------------------------- */

function buildValidationForm() {

    const form = document.getElementById("validationForm");

    if (!form) {
        return;
    }

    form.innerHTML = `
        <div class="mb-3">

            <label
                for="main_scheme_name"
                class="form-label"
            >
                Scheme Name
            </label>

            <input
                type="text"
                id="main_scheme_name"
                class="form-control"
            >

        </div>


        <div class="row g-3 mb-3">

            <div class="col-4">

                <label
                    for="scheme_launch_date"
                    class="form-label"
                >
                    Launch Date
                </label>

                <input
                    type="text"
                    id="scheme_launch_date"
                    class="form-control"
                >

            </div>

            <div class="col-4">

                <label
                    for="monthly_aaum_date"
                    class="form-label"
                >
                    AAUM Date
                </label>

                <input
                    type="text"
                    id="monthly_aaum_date"
                    class="form-control"
                >

            </div>

            <div class="col-4">

                <label
                    for="monthly_aaum_value"
                    class="form-label"
                >
                    AAUM Value
                </label>

                <input
                    type="text"
                    id="monthly_aaum_value"
                    class="form-control"
                >

            </div>

        </div>


        <div class="mb-3">

            <label class="form-label">
                Minimum Amount
            </label>

            <div class="row g-3">

                <div class="col-3">
                    <input
                        type="text"
                        id="min_amt"
                        class="form-control"
                        placeholder="Min Amount"
                    >
                </div>

                <div class="col-3">
                    <input
                        type="text"
                        id="min_amt_multiple"
                        class="form-control"
                        placeholder="Multiple"
                    >
                </div>

                <div class="col-3">
                    <input
                        type="text"
                        id="min_addl_amt"
                        class="form-control"
                        placeholder="Additional Amount"
                    >
                </div>

                <div class="col-3">
                    <input
                        type="text"
                        id="min_addl_amt_multiple"
                        class="form-control"
                        placeholder="Additional Multiple"
                    >
                </div>

            </div>

        </div>


        <div class="mb-3">

            <label
                for="benchmark_index"
                class="form-label"
            >
                Benchmark
            </label>

            <input
                type="text"
                id="benchmark_index"
                class="form-control"
            >

        </div>


        <div class="mb-3">

            <h3>Metrics</h3>

            <div
                id="metricsGrid"
                class="row g-3"
            ></div>

        </div>


        <div class="mb-3">

            <h3>Fund Managers</h3>

            <div class="table-wrapper">

                <div class="table-responsive">

                    <table class="table mb-0">

                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Since</th>
                                <th>Qualification</th>
                                <th>Experience</th>
                            </tr>
                        </thead>

                        <tbody id="fundManagerBody"></tbody>

                    </table>

                </div>

            </div>

        </div>


        <div class="mb-3">

            <h3>Load</h3>

            <div class="table-wrapper">

                <div class="table-responsive">

                    <table class="table mb-0">

                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Value</th>
                            </tr>
                        </thead>

                        <tbody id="loadBody"></tbody>

                    </table>

                </div>

            </div>

        </div>
    `;
}


/* ---------------------------------------------------------
   PAGE SIDEBAR
--------------------------------------------------------- */

function renderValidationPages() {

    const pageList = document.getElementById("pageList");

    if (!pageList) {
        return;
    }

    pageList.innerHTML = "";

    validationRecords.forEach((record, index) => {

        const page = document.createElement("button");

        page.type = "button";
        page.className = "validation-page-btn";
        page.textContent = record.page_number;
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

    if (!record) {
        return;
    }

    currentValidationIndex = index;

    document
        .querySelectorAll(".validation-page-btn")
        .forEach((button, buttonIndex) => {

            button.classList.toggle(
                "active",
                buttonIndex === index
            );

        });


    /*
     * Existing PDF JS.
     * We don't replace or modify it.
     */
    if (typeof loadPDFPage === "function") {
        loadPDFPage(record.page_number);
    }


    populateValidationForm(record);
}


/* ---------------------------------------------------------
   BASIC FIELDS
--------------------------------------------------------- */

function populateValidationForm(record) {

    setField("main_scheme_name", record.main_scheme_name);

    setField(
        "scheme_launch_date",
        record.scheme_launch_date
    );

    setField(
        "monthly_aaum_date",
        record.monthly_aaum_date
    );

    setField(
        "monthly_aaum_value",
        record.monthly_aaum_value
    );

    setField("min_amt", record.min_amt);

    setField(
        "min_amt_multiple",
        record.min_amt_multiple
    );

    setField(
        "min_addl_amt",
        record.min_addl_amt
    );

    setField(
        "min_addl_amt_multiple",
        record.min_addl_amt_multiple
    );

    setField(
        "benchmark_index",
        formatBenchmark(record.benchmark_index)
    );


    renderValidationMetrics(record);
    renderValidationManagers(record);
    renderValidationLoad(record);
}


/* ---------------------------------------------------------
   METRICS
--------------------------------------------------------- */

function renderValidationMetrics(record) {

    const grid = document.getElementById("metricsGrid");

    if (!grid) {
        return;
    }

    grid.innerHTML = "";

    validationMetrics.forEach(metric => {

        let value;

        if (
            Object.prototype.hasOwnProperty.call(
                record,
                metric
            )
        ) {
            value = isEmpty(record[metric])
                ? "NULL"
                : record[metric];
        } else {
            value = `\${value}\${${metric}}`;
        }


        const wrapper = document.createElement("div");

        wrapper.className = "col-12 col-md-6";


        const label = document.createElement("label");

        label.className = "form-label";
        label.textContent = formatLabel(metric);


        const input = document.createElement("input");

        input.type = "text";
        input.className = "form-control validation-field";
        input.value = value;
        input.dataset.metric = metric;


        wrapper.appendChild(label);
        wrapper.appendChild(input);

        grid.appendChild(wrapper);
    });
}


/* ---------------------------------------------------------
   FUND MANAGERS
--------------------------------------------------------- */

function renderValidationManagers(record) {

    const body = document.getElementById("fundManagerBody");

    if (!body) {
        return;
    }

    body.innerHTML = "";

    for (let i = 1; i <= 5; i++) {

        const name = record[`name_${i}`];

        if (isEmpty(name)) {
            continue;
        }


        const row = document.createElement("tr");


        addManagerCell(
            row,
            name
        );

        addManagerCell(
            row,
            record[`managing_fund_since_${i}`]
        );

        addManagerCell(
            row,
            record[`qualification_${i}`]
        );

        addManagerCell(
            row,
            record[`total_exp_${i}`]
        );


        body.appendChild(row);
    }
}


function addManagerCell(row, value) {

    const cell = document.createElement("td");

    const input = document.createElement("input");

    input.type = "text";
    input.className = "form-control validation-field";
    input.value = isEmpty(value) ? "NULL" : value;

    cell.appendChild(input);

    row.appendChild(cell);
}


/* ---------------------------------------------------------
   LOAD
--------------------------------------------------------- */

function renderValidationLoad(record) {

    const body = document.getElementById("loadBody");

    if (!body) {
        return;
    }

    body.innerHTML = "";

    addLoadRow(
        body,
        "Entry",
        record.entry
    );

    addLoadRow(
        body,
        "Exit",
        record.exit
    );
}


function addLoadRow(body, type, value) {

    const row = document.createElement("tr");


    const typeCell = document.createElement("td");

    typeCell.textContent = type;


    const valueCell = document.createElement("td");

    const input = document.createElement("textarea");

    input.className = "form-control validation-field";
    input.rows = 2;
    input.value = isEmpty(value)
        ? "NULL"
        : value;


    valueCell.appendChild(input);

    row.appendChild(typeCell);
    row.appendChild(valueCell);

    body.appendChild(row);
}


/* ---------------------------------------------------------
   HELPERS
--------------------------------------------------------- */

function setField(id, value) {

    const field = document.getElementById(id);

    if (!field) {
        return;
    }

    field.value = isEmpty(value)
        ? "NULL"
        : value;
}


function isEmpty(value) {

    return (
        value === undefined ||
        value === null ||
        value === ""
    );
}


function formatBenchmark(value) {

    if (isEmpty(value)) {
        return "NULL";
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
        .replace(/\b\w/g, char => char.toUpperCase());
}