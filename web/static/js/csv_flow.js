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

  // ✅ checkpoint 1 reached
  reachCheckpoint(1);

  document.getElementById("statusConsole").textContent =
    "CSV converted. JSON ready.";

  // enable next actions
  document.getElementById("jsonViewBtn").disabled = false;
  document.getElementById("jsonPushBtn").disabled = false;
});



document.getElementById("jsonViewBtn").addEventListener("click", () => {
  window.open("/viewer/json/generated.json", "_blank");
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
