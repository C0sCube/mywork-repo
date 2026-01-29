const bar = document.querySelector(".bar");
const checks = document.querySelectorAll(".check");

function resetLoader() {
  bar.style.width = "0%";
  checks.forEach(c => {
    c.style.transform = "scale(0.75)";
    c.style.backgroundColor = "#535353";
  });
}

function reachCheckpoint(step) {
  if (step === 1) {
    bar.style.width = "50%";
    checks[0].style.transform = "scale(1)";
    checks[0].style.backgroundColor = "rgb(0,205,0)";
  }

  if (step === 2) {
    bar.style.width = "100%";
    checks[1].style.transform = "scale(1)";
    checks[1].style.backgroundColor = "rgb(0,205,0)";
  }
}


const csvInput = document.getElementById("csvInput");
const convertBtn = document.getElementById("csvConvertBtn");

let generatedJsonFile = null;


csvInput.addEventListener("change", () => {
  convertBtn.disabled = !csvInput.files.length;
});

convertBtn.addEventListener("click", async () => {
  resetLoader();



  const fd = new FormData();
  fd.append("csv", csvInput.files[0]);

  document.getElementById("statusConsole").textContent = "Converting CSV → JSON…";

  const res = await fetch("/convert_csv", {
    method: "POST",
    body: fd
  });

  const data = await res.json();

  if (!data.success) {
    document.getElementById("statusConsole").textContent = data.error;
    return;
  }

  generatedJsonFile = data.json_file;

  // ✅ checkpoint 1 reached
  reachCheckpoint(1);

  document.getElementById("statusConsole").textContent =
    "CSV converted. JSON ready.";

  // enable next actions
  document.getElementById("jsonViewBtn").disabled = false;
  document.getElementById("jsonPushBtn").disabled = false;
});



document.getElementById("jsonViewBtn").addEventListener("click", () => {
  if (!generatedJsonFile) {
    alert("No JSON available yet");
    return;
  }
  window.open(`/viewer/json/csv/${generatedJsonFile}`, "_blank");
});



jsonPushBtn.addEventListener("click", async () => {
  document.getElementById("statusConsole").textContent = "Pushing to Admin Panel…";

  const res = await fetch("/push_job/123", { method: "POST" });
  const data = await res.json();

  if (data.success) {
    reachCheckpoint(2);
    document.getElementById("statusConsole").textContent = "Pushed successfully.";
  } else {
    document.getElementById("statusConsole").textContent = data.error;
  }
});

// ---------------- NAVIGATION ----------------
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


function goBackToMain(e) {
    e.preventDefault();

    if (window.opener) {
        window.opener.focus();
        window.close();
    } else {
        window.location.href = "/";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    enforceAuth();


    document.querySelectorAll("[data-action='back']").forEach(el => {
        el.addEventListener("click", goBackToMain);
    });
});
