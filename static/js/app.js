// Same-tab flow with 5-second ad gate
document.addEventListener("DOMContentLoaded", () => {
  const urlInput = document.getElementById("videoUrl");
  const formatSel = document.getElementById("format");
  const btn = document.getElementById("downloadBtn");
  const status = document.getElementById("status");
  const gate = document.getElementById("gate");
  const countSpan = document.getElementById("count");
  const continueBtn = document.getElementById("continueBtn");

  let pendingToken = null;

  async function startDownload() {
    const url = (urlInput.value || "").trim();
    const format = formatSel.value || "mp4";

    if (!url) {
      status.textContent = "Please paste a valid URL.";
      return;
    }
    status.textContent = "Fetching links…";
    btn.disabled = true;

    try {
      const resp = await fetch("/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, format })
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        throw new Error(data.error || "Server error");
      }
      // Show ad gate for 5s
      pendingToken = data.token;
      openGate();
    } catch (e) {
      status.textContent = "Failed: " + e.message;
    } finally {
      btn.disabled = false;
    }
  }

  function openGate() {
    if (!gate) return;
    let t = 5;
    countSpan.textContent = String(t);
    gate.classList.remove("hidden");
    gate.setAttribute("aria-hidden", "false");
    continueBtn.disabled = true;

    const intv = setInterval(() => {
      t -= 1;
      countSpan.textContent = String(t);
      if (t <= 0) {
        clearInterval(intv);
        continueBtn.disabled = false;
      }
    }, 1000);
  }

  async function finishGate() {
    if (!pendingToken) return;
    status.textContent = "Starting download…";
    gate.classList.add("hidden");
    gate.setAttribute("aria-hidden", "true");

    // Trigger same-tab streamed download
    window.location.href = "/download/" + encodeURIComponent(pendingToken);
    pendingToken = null;
  }

  btn?.addEventListener("click", startDownload);
  continueBtn?.addEventListener("click", finishGate);
});
