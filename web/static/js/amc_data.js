// ---------------- AUTH CHECK ----------------
async function enforceAuth() {
    try {
        const r = await fetch("/auth-check");
        const data = await r.json();

        if (!data.logged_in) {
            alert("Session expired. Please log in again.");
            window.location = "/login";
        }
    } catch (err) {
        alert("Unable to verify session. Redirecting to login.");
        window.location = "/login";
    }
}

// ---------------- NAVIGATION ----------------
function goBackToMain(e) {
    e.preventDefault();

    if (window.opener) {
        window.opener.focus();
        window.close();
    } else {
        window.location.href = "/";
    }
}

// ---------------- AMC DATA RENDER ----------------
function loadAMCData() {
    const container = document.querySelector(".card-container");
    if (!container) return;

    fetch("/amc_data")
        .then(res => res.json())
        .then(data => {
            Object.entries(data).forEach(([id, amc]) => {
                const card = document.createElement("div");
                card.className = "card";

                card.innerHTML = `
                    <div class="editor-controls">
                        <div class="text">
                            <a href="${amc.amc_website}" target="_blank"
                               style="text-decoration:none; color:#fff">
                                <span><strong>${amc.amc_name}</strong></span>
                            </a>
                            <p class="subtitle">AMC ID: ${id}</p>
                        </div>

                        <div class="right-controls">
                            <img src="/static/img/logo/${id}.png"
                                 alt="Logo"
                                 style="width:65px;height:65px;
                                        background-color:lightblue;
                                        margin-right:20px;
                                        border-radius:8px">
                        </div>
                    </div>
                `;

                container.appendChild(card);
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
