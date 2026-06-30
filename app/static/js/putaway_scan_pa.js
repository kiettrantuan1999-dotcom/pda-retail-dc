document.addEventListener("DOMContentLoaded", function () {
  const palletInput = document.getElementById("pallet_id");
  const findPalletBtn = document.getElementById("findPalletBtn");
  const resultBox = document.getElementById("resultBox");
  const scannerBox = document.getElementById("scannerBox");
  const scanPalletBtn = document.getElementById("scanPalletBtn");
  const closeScannerBtn = document.getElementById("closeScannerBtn");

  let html5QrCode = null;
  let isStartingScanner = false;
  let lastDecodedText = "";
  let lastDecodedAt = 0;
  let suppressAutoScanUntil = 0;

  if (palletInput) palletInput.focus();

  function showMessage(type, message) {
    if (!resultBox) return;
    resultBox.classList.remove("d-none", "alert-success", "alert-danger", "alert-info", "alert-warning");
    resultBox.classList.add(type);
    resultBox.innerText = message;
  }

  function restoreManualInput(targetInput) {
    if (!targetInput) return;
    suppressAutoScanUntil = Date.now() + 1500;
    setTimeout(function () {
      targetInput.focus();
      if (targetInput.select) targetInput.select();
    }, 80);
  }

  async function stopScanner(restoreFocus) {
    const targetToRestore = palletInput;

    if (html5QrCode) {
      try { await html5QrCode.stop(); } catch (e) { console.log("Scanner stop ignored", e); }
      try { await html5QrCode.clear(); } catch (e) { console.log("Scanner clear ignored", e); }
      html5QrCode = null;
    }
    if (scannerBox) scannerBox.classList.add("d-none");
    isStartingScanner = false;

    if (restoreFocus) restoreManualInput(targetToRestore);
  }

  async function findPallet() {
    const pallet = palletInput.value.trim().toUpperCase();
    if (!pallet) {
      showMessage("alert-danger", "Vui lòng quét hoặc nhập mã PA.");
      palletInput.focus();
      return;
    }

    showMessage("alert-info", "Đang tìm nhiệm vụ cất hàng...");

    try {
      const res = await fetch("/api/putaway/pallet/" + encodeURIComponent(pallet));
      const data = await res.json();

      if (!data.ok) {
        showMessage("alert-danger", data.error || "Không tìm thấy PA.");
        return;
      }

      const palletId = (data.data && data.data.pallet_id ? data.data.pallet_id : pallet).trim().toUpperCase();
      if (!palletId) {
        showMessage("alert-danger", "PA này chưa có nhiệm vụ cất hàng.");
        return;
      }

      window.location.href = "/putaway/" + encodeURIComponent(palletId);
    } catch (err) {
      showMessage("alert-danger", err.message || "Lỗi kết nối server.");
    }
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
        Html5QrcodeSupportedFormats.CODE_39
      ];
    }
    return config;
  }

  async function startScanner() {
    if (isStartingScanner) return;
    if (!window.Html5Qrcode) {
      showMessage("alert-danger", "Thiếu thư viện Html5Qrcode.");
      return;
    }
    if (!window.isSecureContext) {
      showMessage("alert-danger", "Camera chỉ chạy trên HTTPS hoặc localhost.");
      return;
    }

    isStartingScanner = true;
    if (scannerBox) scannerBox.classList.remove("d-none");
    if (resultBox) resultBox.classList.add("d-none");

    if (html5QrCode) {
      await stopScanner();
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

          palletInput.value = cleanText;
          await stopScanner();
          await findPallet();
        },
        function () {}
      );
      isStartingScanner = false;
    } catch (err) {
      console.error("Camera error", err);
      await stopScanner();
      showMessage("alert-danger", normalizeCameraError(err));
    }
  }

  if (findPalletBtn) findPalletBtn.addEventListener("click", findPallet);
  if (palletInput) {
    palletInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        findPallet();
      }
    });
    palletInput.addEventListener("click", function () {
      if (Date.now() < suppressAutoScanUntil) return;
      if (scannerBox && !scannerBox.classList.contains("d-none")) return;
      startScanner();
    });
  }
  if (scanPalletBtn) scanPalletBtn.addEventListener("click", startScanner);
  if (closeScannerBtn) closeScannerBtn.addEventListener("click", function () { stopScanner(true); });
});
