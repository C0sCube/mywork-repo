
// ---------------- AMC DATA RENDER ----------------

function loadAMCData() {
    const container = document.querySelector(".card-container");
    if (!container) return;

    fetch("/amc_data_registry")
        .then(res => res.json())
        .then(data => {
            container.innerHTML = ""; // clear existing (optional but sane)

            Object.entries(data).forEach(([id, amc]) => {
                const col = document.createElement("div");
                col.className = "col-12 col-md-6 col-xl-4";
                const card = document.createElement("div");
                card.className = "card tool-card h-100";

                card.innerHTML = `
                    <div class="card-body d-flex align-items-center justify-content-between gap-3">
                        <div class="text">
                            <a href="${amc.amc_website}" target="_blank"
                               style="text-decoration:none; color:#fff">
                                <span><strong>${amc.amc_name}</strong></span>
                            </a>
                            <p class="text-secondary small mb-0">AMC ID: ${id}</p>
                        </div>

                        <div class="right-controls">
                            <img src="/logo/${id}"
                                 alt="Logo"
                                 onerror="this.onerror=null; this.src='/static/default.png';"
                                 class="amc-logo"
                                 style="margin-right:0">
                        </div>
                    </div>
                `;

                col.appendChild(card);
                container.appendChild(col);
            });
        })
        .catch(err => {
            console.error("Error loading AMC data:", err);
        });
}

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", () => {
    enforceAuth();
    loadAMCData();

    document.querySelectorAll("[data-action='back']").forEach(el => {
        el.addEventListener("click", goBackToMain);
    });
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
