document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("stagingScanForm");
  const input = document.getElementById("staging_do_no");
  const scanBtn = document.getElementById("scanStagingBtn");
  const closeScannerBtn = document.getElementById("closeScannerBtn");
  const scannerBox = document.getElementById("scannerBox");

  let html5QrCode = null;
  let isStartingScanner = false;
  let lastDecodedText = "";
  let lastDecodedAt = 0;
  let suppressAutoScanUntil = 0;

  if (input) input.focus();

  function showMessage(message) {
    let box = document.getElementById("stagingScanMessage");
    if (!box) {
      box = document.createElement("div");
      box.id = "stagingScanMessage";
      box.className = "alert alert-danger mt-3";
      form.closest(".card-body").appendChild(box);
    }
    box.innerText = message;
  }

  function restoreManualInput() {
    if (!input) return;
    suppressAutoScanUntil = Date.now() + 1500;
    setTimeout(function () {
      input.focus();
      if (input.select) input.select();
    }, 80);
  }

  async function stopScanner(restoreFocus) {
    if (html5QrCode) {
      try { await html5QrCode.stop(); } catch (e) { console.log("Scanner stop ignored", e); }
      try { await html5QrCode.clear(); } catch (e) { console.log("Scanner clear ignored", e); }
      html5QrCode = null;
    }
    if (scannerBox) scannerBox.classList.add("d-none");
    isStartingScanner = false;
    if (restoreFocus) restoreManualInput();
  }

  function normalizeCameraError(err) {
    const raw = err && err.message ? err.message : String(err || "");
    const name = err && err.name ? err.name : "";
    if (!window.isSecureContext) return "Camera chỉ chạy trên HTTPS hoặc localhost. Hãy mở bằng link HTTPS Railway.";
    if (name === "NotAllowedError" || raw.includes("Permission denied")) return "Trình duyệt chưa được cấp quyền Camera.";
    if (name === "NotFoundError") return "Không tìm thấy camera trên thiết bị.";
    if (name === "NotReadableError") return "Camera đang bị app khác sử dụng.";
    return raw || "Không mở được camera.";
  }

  function scannerConfig() {
    const config = {
      fps: 15,
      qrbox: function (w, h) {
        const size = Math.floor(Math.min(w, h) * 0.72);
        return { width: Math.max(240, Math.min(size, 420)), height: Math.max(240, Math.min(size, 420)) };
      },
      disableFlip: true,
      rememberLastUsedCamera: true,
      experimentalFeatures: { useBarCodeDetectorIfSupported: true }
    };

    if (window.Html5QrcodeSupportedFormats) {
      config.formatsToSupport = [
        Html5QrcodeSupportedFormats.QR_CODE,
        Html5QrcodeSupportedFormats.CODE_128,
        Html5QrcodeSupportedFormats.CODE_39,
        Html5QrcodeSupportedFormats.EAN_13,
        Html5QrcodeSupportedFormats.EAN_8
      ];
    }
    return config;
  }

  async function startScanner() {
    if (isStartingScanner) return;
    if (!window.Html5Qrcode) {
      showMessage("Thiếu thư viện Html5Qrcode.");
      return;
    }
    if (!window.isSecureContext) {
      showMessage("Camera chỉ chạy trên HTTPS hoặc localhost.");
      return;
    }

    isStartingScanner = true;
    if (scannerBox) scannerBox.classList.remove("d-none");

    if (html5QrCode) {
      await stopScanner(false);
      if (scannerBox) scannerBox.classList.remove("d-none");
    }

    html5QrCode = new Html5Qrcode("reader");

    try {
      await html5QrCode.start(
        { facingMode: "environment" },
        scannerConfig(),
        async function (decodedText) {
          const cleanText = String(decodedText || "").trim().toUpperCase();
          const now = Date.now();
          if (!cleanText) return;
          if (cleanText === lastDecodedText && now - lastDecodedAt < 900) return;
          lastDecodedText = cleanText;
          lastDecodedAt = now;

          input.value = cleanText;
          await stopScanner(false);
          form.requestSubmit();
        },
        function () {}
      );
      isStartingScanner = false;
    } catch (err) {
      console.error("Camera error", err);
      await stopScanner(true);
      showMessage(normalizeCameraError(err));
    }
  }

  if (input) {
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        form.requestSubmit();
      }
    });
    input.addEventListener("click", function () {
      if (Date.now() < suppressAutoScanUntil) return;
      if (scannerBox && !scannerBox.classList.contains("d-none")) return;
      startScanner();
    });
  }

  if (scanBtn) scanBtn.addEventListener("click", startScanner);
  if (closeScannerBtn) closeScannerBtn.addEventListener("click", function () { stopScanner(true); });
});
