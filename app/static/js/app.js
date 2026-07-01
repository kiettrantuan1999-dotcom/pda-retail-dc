function showToast(msg, ok=true){
  const el = document.getElementById("appToast");
  const body = document.getElementById("toastBody");
  if(!el || !body) return;
  body.innerText = msg;
  el.className = "toast " + (ok ? "text-bg-success" : "text-bg-danger");
  new bootstrap.Toast(el).show();
}
function focusFirst(){
  const x = document.querySelector("input[autofocus], .scan-input");
  if(x){ setTimeout(()=>x.focus(), 100); }
}
window.addEventListener("load", focusFirst);

(function () {
  const CHECK_INTERVAL_MS = 30000;
  const RELOAD_DELAY_SECONDS = 5;
  const VERSION_KEY = "supra_wes_app_version";
  const RELOAD_FLAG_KEY = "supra_wes_reloading_for_update";

  let updateDetected = false;
  let countdownTimer = null;

  function createUpdatePopup() {
    let popup = document.getElementById("appUpdatePopup");
    if (popup) return popup;

    popup = document.createElement("div");
    popup.id = "appUpdatePopup";
    popup.className = "app-update-popup d-none";
    popup.innerHTML = `
      <div class="app-update-card" role="alert" aria-live="assertive">
        <div class="app-update-badge">CẬP NHẬT HỆ THỐNG</div>
        <div class="app-update-title">Có phiên bản mới</div>
        <div class="app-update-message">
          Ứng dụng sẽ tự tải lại sau <b id="appUpdateCountdown">5</b> giây để nhận bản mới.
        </div>
        <button type="button" class="app-update-button" id="appUpdateReloadNow">Tải lại ngay</button>
      </div>
    `;
    document.body.appendChild(popup);

    const reloadNow = document.getElementById("appUpdateReloadNow");
    if (reloadNow) {
      reloadNow.addEventListener("click", function () {
        reloadForUpdate();
      });
    }

    return popup;
  }

  function reloadForUpdate() {
    sessionStorage.setItem(RELOAD_FLAG_KEY, "1");
    window.location.reload();
  }

  function showUpdatePopup() {
    if (updateDetected) return;
    updateDetected = true;

    const popup = createUpdatePopup();
    popup.classList.remove("d-none");

    let remaining = RELOAD_DELAY_SECONDS;
    const countdown = document.getElementById("appUpdateCountdown");
    if (countdown) countdown.innerText = String(remaining);

    countdownTimer = setInterval(function () {
      remaining -= 1;
      if (countdown) countdown.innerText = String(Math.max(remaining, 0));
      if (remaining <= 0) {
        clearInterval(countdownTimer);
        reloadForUpdate();
      }
    }, 1000);
  }

  async function checkAppVersion() {
    if (updateDetected) return;

    try {
      const response = await fetch("/api/app/version?ts=" + Date.now(), {
        cache: "no-store",
        credentials: "same-origin"
      });
      if (!response.ok) return;

      const payload = await response.json();
      const serverVersion = String(payload.version || payload.data?.version || "").trim();
      if (!serverVersion) return;

      const storedVersion = sessionStorage.getItem(VERSION_KEY);
      if (!storedVersion) {
        sessionStorage.setItem(VERSION_KEY, serverVersion);
        sessionStorage.removeItem(RELOAD_FLAG_KEY);
        return;
      }

      if (storedVersion !== serverVersion) {
        sessionStorage.setItem(VERSION_KEY, serverVersion);
        showUpdatePopup();
        return;
      }

      if (sessionStorage.getItem(RELOAD_FLAG_KEY) === "1") {
        sessionStorage.removeItem(RELOAD_FLAG_KEY);
      }
    } catch (err) {
      // Không làm gián đoạn thao tác scan nếu mất mạng tạm thời.
    }
  }

  window.addEventListener("load", function () {
    checkAppVersion();
    setInterval(checkAppVersion, CHECK_INTERVAL_MS);
  });
})();
