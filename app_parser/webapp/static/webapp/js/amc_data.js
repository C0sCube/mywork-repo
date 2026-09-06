// ---------------- AMC DATA RENDER ----------------

function loadAMCData() {
    const tbody = document.getElementById("amc-table-body");
    if (!tbody) return;

    fetch("/amc_data_registry")
        .then(res => res.json())
        .then(data => {

            tbody.innerHTML = "";

            // View returns registry directly
            const registry = data || {};

            console.log("Registry:", registry);
            console.log("Registry Count:", Object.keys(registry).length);

            Object.entries(registry).forEach(([id, amc]) => {

                console.log("AMC:", id, amc);

                const fs0 = amc.fs_class?.["0"] || "-";
                const fs1 = amc.fs_class?.["1"] || "-";
                const sidClass = amc.sid_class || "-";

                let website = "-";

                if (amc.amc_website && amc.amc_website.trim()) {
                    website = `
                        <a href="${amc.amc_website}" target="_blank">Open</a>
                    `;
                }

                const row = document.createElement("tr");

                row.innerHTML = `
                    <td>${id}</td>
                    <td>${amc.amc_name || "-"}</td>
                    <td>${fs0}</td>
                    <td>${fs1}</td>
                    <td>${sidClass}</td>
                    <td>${website}</td>
                `;

                tbody.appendChild(row);
            });

            console.log("Rows Rendered:", tbody.children.length);
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