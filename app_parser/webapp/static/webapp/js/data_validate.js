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

    if (type === "CSV") {
        renderCSV(input.files[0], content);
    }
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

    container.appendChild(message);
}