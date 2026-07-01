document.addEventListener("DOMContentLoaded", function () {
  const doInput = document.getElementById("do_no");
  const loadPackBtn = document.getElementById("loadPackBtn");
  const confirmPackBtn = document.getElementById("confirmPackBtn");

  const resultBox = document.getElementById("resultBox");
  const packBox = document.getElementById("packBox");
  const skuTableBody = document.getElementById("skuTableBody");

  const actualPackageQty = document.getElementById("actual_package_qty");
  const pickerNameInput = document.getElementById("picker_name");

  const scanDoBtn = document.getElementById("scanDoBtn");
  const closeScannerBtn = document.getElementById("closeScannerBtn");
  const scannerBox = document.getElementById("scannerBox");

  let currentPack = null;
  let html5QrCode = null;
  let isStartingScanner = false;
  let lastDecodedText = "";
  let lastDecodedAt = 0;
  let suppressAutoScanUntil = 0;

  if (doInput) doInput.focus();

  function showMessage(type, message) {
    if (!resultBox) return;
    resultBox.classList.remove(
      "d-none",
      "alert-success",
      "alert-danger",
      "alert-info",
      "alert-warning"
    );
    resultBox.classList.add(type);
    resultBox.innerText = message;
  }

  function clearMessage() {
    if (resultBox) resultBox.classList.add("d-none");
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
    if (html5QrCode) {
      try { await html5QrCode.stop(); } catch (e) { console.log("Scanner stop ignored", e); }
      try { await html5QrCode.clear(); } catch (e) { console.log("Scanner clear ignored", e); }
      html5QrCode = null;
    }
    if (scannerBox) scannerBox.classList.add("d-none");
    isStartingScanner = false;
    if (restoreFocus) restoreManualInput(doInput);
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

          doInput.value = cleanText;
          await stopScanner(false);
          await loadPack();
        },
        function () {}
      );
      isStartingScanner = false;
    } catch (err) {
      console.error("Camera error", err);
      await stopScanner(true);
      showMessage("alert-danger", normalizeCameraError(err));
    }
  }

  function renderSkuTable(rows) {
    skuTableBody.innerHTML = "";

    rows.forEach(function (r) {
      skuTableBody.innerHTML += `
        <tr>
            <td>${r.sku || ""}</td>
            <td>${r.barcode || ""}</td>
            <td>${r.product_name || ""}</td>
            <td class="text-end fw-bold">${r.qty_pick || 0}</td>
        </tr>
      `;
    });
  }

  async function loadPack() {
    const doNo = doInput.value.trim().toUpperCase();

    if (!doNo) {
      showMessage("alert-danger", "Vui lòng quét hoặc nhập mã phiếu.");
      doInput.focus();
      return;
    }

    doInput.value = doNo;
    showMessage("alert-info", "Đang tìm phiếu đóng hàng...");

    try {
      const res = await fetch("/api/pack/do/" + encodeURIComponent(doNo));
      const data = await res.json();

      if (!data.ok) {
        showMessage("alert-danger", data.error || data.message || "Không tìm thấy phiếu.");
        doInput.focus();
        if (doInput.select) doInput.select();
        return;
      }

      currentPack = data.data;

      document.getElementById("infoPickingNo").innerText = currentPack.picking_no;
      document.getElementById("infoDoNo").innerText = (currentPack.do_nos || []).join(", ") || currentPack.do_no || "";
      document.getElementById("infoTotalDo").innerText = currentPack.total_do || 0;
      document.getElementById("infoTrip").innerText = currentPack.trip_no || "-";
      document.getElementById("infoWave").innerText = currentPack.wave || "-";
      document.getElementById("infoSlot").innerText = currentPack.khung_gio || "-";
      document.getElementById("infoDeliveryType").innerText = currentPack.loai_giao || "-";
      document.getElementById("infoStore").innerText = currentPack.store_id + " - " + currentPack.store_name;
      document.getElementById("infoType").innerText = currentPack.pack_type_name;
      document.getElementById("infoSkuLine").innerText = currentPack.sku_line_count;
      document.getElementById("infoTotalQty").innerText = currentPack.total_qty;
      const infoStatus = document.getElementById("infoStatus");

      switch (currentPack.status) {
        case "DONE":
          infoStatus.innerHTML = '<span class="badge bg-success">Đã đóng hàng</span>';
          break;
        case "PARTIAL":
          infoStatus.innerHTML = '<span class="badge bg-info">Đóng hàng một phần</span>';
          break;
        default:
          infoStatus.innerHTML = '<span class="badge bg-warning text-dark">Chờ đóng hàng</span>';
      }

      actualPackageQty.value = currentPack.actual_package_qty || "";
      if (pickerNameInput) pickerNameInput.value = currentPack.picked_by || "";

      renderSkuTable(currentPack.rows || []);

      clearMessage();
      packBox.classList.remove("d-none");
      window.scrollTo({ top: packBox.offsetTop - 80, behavior: "smooth" });
      if (pickerNameInput && !pickerNameInput.value.trim()) {
        pickerNameInput.focus();
      } else {
        actualPackageQty.focus();
      }

    } catch (err) {
      showMessage("alert-danger", err.message || "Lỗi kết nối server.");
    }
  }

  async function confirmPack() {
    if (!currentPack) {
      showMessage("alert-danger", "Chưa load phiếu đóng hàng.");
      return;
    }

    const pickerName = (pickerNameInput ? pickerNameInput.value.trim() : "");

    if (!pickerName) {
      showMessage("alert-danger", "Vui lòng nhập người lấy hàng / picker trước khi xác nhận đóng hàng.");
      if (pickerNameInput) pickerNameInput.focus();
      return;
    }

    const packageQty = actualPackageQty.value.trim();

    if (packageQty === "" || Number(packageQty) <= 0) {
      showMessage("alert-danger", "Số kiện thực tế không hợp lệ.");
      actualPackageQty.focus();
      return;
    }

    const formData = new FormData();
    formData.append("do_no", currentPack.picking_no);
    formData.append("actual_package_qty", packageQty);
    formData.append("picker_name", pickerName);

    try {
      confirmPackBtn.disabled = true;
      confirmPackBtn.innerText = "ĐANG LƯU...";

      const res = await fetch("/api/pack/confirm", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!data.ok) {
        showMessage("alert-danger", data.error || data.message || "Đóng hàng lỗi.");
        confirmPackBtn.disabled = false;
        confirmPackBtn.innerText = "✅ Xác nhận đóng hàng";
        return;
      }

      const savedPack = data.data || {};
      const deductQty = Number(savedPack.total_deduct_qty || 0);
      const deductLine = Number(savedPack.deduct_line_count || 0);
      const successMessage = deductQty > 0
        ? `✅ Đóng hàng thành công. Đã trừ tồn ${deductQty} sản phẩm / ${deductLine} dòng vị trí.`
        : "✅ Đóng hàng thành công.";
      showMessage("alert-success", successMessage);

      const beep = document.getElementById("successBeep");
      if (beep) {
        beep.currentTime = 0;
        beep.play().catch(() => {});
      }

      confirmPackBtn.disabled = false;
      confirmPackBtn.innerText = "✅ Xác nhận đóng hàng";

      doInput.value = "";
      actualPackageQty.value = "";
      if (pickerNameInput) pickerNameInput.value = "";
      skuTableBody.innerHTML = "";
      packBox.classList.add("d-none");
      currentPack = null;

      setTimeout(() => { clearMessage(); }, 2000);
      doInput.focus();

    } catch (err) {
      showMessage("alert-danger", err.message || "Lỗi kết nối server.");
      confirmPackBtn.disabled = false;
      confirmPackBtn.innerText = "✅ Xác nhận đóng hàng";
    }
  }

  document.querySelectorAll(".load-pending-pack").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const pickingNo = (btn.getAttribute("data-picking-no") || "").trim().toUpperCase();
      if (!pickingNo) return;
      doInput.value = pickingNo;
      loadPack();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });

  if (loadPackBtn) loadPackBtn.addEventListener("click", loadPack);
  if (confirmPackBtn) confirmPackBtn.addEventListener("click", confirmPack);

  if (doInput) {
    doInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        loadPack();
      }
    });
    doInput.addEventListener("click", function () {
      if (Date.now() < suppressAutoScanUntil) return;
      if (scannerBox && !scannerBox.classList.contains("d-none")) return;
      startScanner();
    });
  }

  if (scanDoBtn) scanDoBtn.addEventListener("click", startScanner);
  if (closeScannerBtn) closeScannerBtn.addEventListener("click", function () { stopScanner(true); });

  if (pickerNameInput) {
    pickerNameInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        actualPackageQty.focus();
      }
    });
  }

  if (actualPackageQty) {
    actualPackageQty.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        if (!confirmPackBtn.disabled) confirmPack();
      }
    });
  }
});
