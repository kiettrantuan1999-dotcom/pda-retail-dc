document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("putawayForm");
  const locationInput = document.getElementById("location_id");
  const qtyInput = document.getElementById("qty_putaway");
  const locationCheckBox = document.getElementById("locationCheckBox");

  const resultBox = document.getElementById("resultBox");
  const successBox = document.getElementById("successBox");
  const scannerBox = document.getElementById("scannerBox");
  const scanLocationBtn = document.getElementById("scanLocationBtn");
  const closeScannerBtn = document.getElementById("closeScannerBtn");
  const successLocation = document.getElementById("successLocation");
  const successQty = document.getElementById("successQty");
  const successWarning = document.getElementById("successWarning");

  let html5QrCode = null;
  let isStartingScanner = false;
  let lastDecodedText = "";
  let lastDecodedAt = 0;
  let suppressAutoScanUntil = 0;

  if (locationInput) locationInput.focus();

  function showMessage(type, message) {
    if (!resultBox) return;
    resultBox.classList.remove("d-none", "alert-success", "alert-danger", "alert-info", "alert-warning");
    resultBox.classList.add(type);
    resultBox.innerText = message;
  }

  function showLocationCheck(type, message) {
    if (!locationCheckBox) return;
    locationCheckBox.classList.remove("d-none", "alert-success", "alert-danger", "alert-info", "alert-warning");
    locationCheckBox.classList.add(type);
    locationCheckBox.innerText = message;
  }

  function getSuggestedAisles() {
    return Array.from(document.querySelectorAll(".suggested-aisle"))
      .map(function (el) { return String(el.dataset.aisle || "").trim().toUpperCase(); })
      .filter(Boolean);
  }

  function locationAisle(locationId) {
    const text = String(locationId || "").trim().toUpperCase();
    if (!text) return "";
    return text.split("-")[0].split("_")[0].split(".")[0];
  }

  function validateLocationClient() {
    if (!locationInput) return true;
    const locationId = locationInput.value.trim().toUpperCase();
    if (!locationId) return false;

    const suggested = getSuggestedAisles();
    const aisle = locationAisle(locationId);

    if (suggested.length && aisle && !suggested.includes(aisle)) {
      showLocationCheck("alert-warning", `⚠ Vị trí ngoài dãy gợi ý. Dãy gợi ý: ${suggested.join(", ")}`);
      return true;
    }

    if (suggested.length) {
      showLocationCheck("alert-success", `✅ Vị trí thuộc dãy gợi ý: ${aisle}`);
    } else {
      showLocationCheck("alert-info", "ℹ Chưa có rule dãy. Vui lòng kiểm tra thực tế trước khi xác nhận.");
    }
    return true;
  }

  document.querySelectorAll(".suggested-location-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const loc = btn.dataset.location || "";
      if (!loc || !locationInput) return;
      locationInput.value = loc;
      validateLocationClient();
      if (qtyInput) qtyInput.focus();
    });
  });

  if (locationInput) {
    locationInput.addEventListener("input", validateLocationClient);
    locationInput.addEventListener("blur", validateLocationClient);
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
    const targetToRestore = locationInput;

    if (html5QrCode) {
      try { await html5QrCode.stop(); } catch (e) { console.log("Scanner stop ignored", e); }
      try { await html5QrCode.clear(); } catch (e) { console.log("Scanner clear ignored", e); }
      html5QrCode = null;
    }
    if (scannerBox) scannerBox.classList.add("d-none");
    isStartingScanner = false;

    if (restoreFocus) restoreManualInput(targetToRestore);
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
        const width = Math.floor(w * 0.82);
        const height = Math.floor(h * 0.32);
        return { width: Math.max(260, Math.min(width, 520)), height: Math.max(130, Math.min(height, 220)) };
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
        Html5QrcodeSupportedFormats.ITF
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

          locationInput.value = cleanText;
          await stopScanner();
          validateLocationClient();
          if (qtyInput) qtyInput.focus();
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

  if (scanLocationBtn) scanLocationBtn.addEventListener("click", startScanner);
  if (locationInput) {
    locationInput.addEventListener("click", function () {
      if (Date.now() < suppressAutoScanUntil) return;
      if (scannerBox && !scannerBox.classList.contains("d-none")) return;
      startScanner();
    });
  }
  if (closeScannerBtn) closeScannerBtn.addEventListener("click", function () { stopScanner(true); });

  if (!form) return;

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const locationValue = locationInput.value.trim().toUpperCase();
    const qtyValue = qtyInput.value;

    if (!locationValue) {
      showMessage("alert-danger", "Vui lòng quét hoặc nhập vị trí.");
      locationInput.focus();
      return;
    }

    if (!qtyValue || Number(qtyValue) <= 0) {
      showMessage("alert-danger", "Số lượng cất phải lớn hơn 0.");
      qtyInput.focus();
      return;
    }

    validateLocationClient();
    showMessage("alert-info", "Đang xử lý cất hàng...");

    const formData = new FormData(form);
    formData.set("location_id", locationValue);

    try {
      const response = await fetch("/api/putaway/confirm", { method: "POST", body: formData });
      const data = await response.json();

      if (data.ok) {
        resultBox.classList.add("d-none");
        form.classList.add("d-none");
        if (successLocation) successLocation.innerText = locationValue;
        if (successQty) successQty.innerText = qtyValue;
        if (data.data && data.data.location_warning && successWarning) {
          successWarning.innerText = data.data.location_warning;
          successWarning.classList.remove("d-none");
        }
        if (successBox) successBox.classList.remove("d-none");
      } else {
        showMessage("alert-danger", data.error || "Cất hàng thất bại.");
      }
    } catch (err) {
      showMessage("alert-danger", err.message || "Lỗi kết nối server.");
    }
  });
});
