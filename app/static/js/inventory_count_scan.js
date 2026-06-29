document.addEventListener("DOMContentLoaded", function () {
  const countNo = document.getElementById("countNo").value;
  const locationInput = document.getElementById("locationId");
  const barcodeInput = document.getElementById("barcode");
  const loadTaskBtn = document.getElementById("loadTaskBtn");
  const taskBox = document.getElementById("taskBox");
  const saveCountBtn = document.getElementById("saveCountBtn");
  const saveResult = document.getElementById("saveResult");
  const scannerBox = document.getElementById("scannerBox");
  const closeScannerBtn = document.getElementById("closeScannerBtn");

  let html5QrCode = null;
  let activeTarget = null;
  let suppressAutoScanUntil = 0;

  locationInput.focus();

  function setTask(d) {
    document.getElementById("detailId").value = d.detail_id;
    document.getElementById("tLocation").innerText = d.location_id;
    document.getElementById("tSku").innerText = d.sku;
    document.getElementById("tBarcode").innerText = d.barcode;
    document.getElementById("tName").innerText = d.product_name || "";
    document.getElementById("tExpected").innerText = d.expected_qty;
    document.getElementById("countQty").value = d.count_qty ?? "";
    document.getElementById("note").value = "";
    saveResult.className = "alert d-none";
    taskBox.classList.remove("d-none");
    document.getElementById("countQty").focus();
  }

  async function loadTask() {
    const locationId = locationInput.value.trim();
    const barcode = barcodeInput.value.trim();

    const url = `/api/inventory/counts/${encodeURIComponent(countNo)}/scan?location_id=${encodeURIComponent(locationId)}&barcode=${encodeURIComponent(barcode)}`;
    const res = await fetch(url);
    const data = await res.json();

    if (!data.ok) {
      showToast(data.error || "Không tìm thấy dòng kiểm kê", false);
      taskBox.classList.add("d-none");
      return;
    }

    setTask(data.data);
  }

  async function saveCount() {
    const detailId = document.getElementById("detailId").value;
    const countQty = document.getElementById("countQty").value;
    const note = document.getElementById("note").value;

    const form = new FormData();
    form.append("detail_id", detailId);
    form.append("count_qty", countQty);
    form.append("note", note);

    const res = await fetch("/api/inventory/counts/save", {
      method: "POST",
      body: form,
    });
    const data = await res.json();

    if (!data.ok) {
      showToast(data.error || "Lỗi lưu kiểm kê", false);
      return;
    }

    const d = data.data;
    const diff = Number(d.variance_qty || 0);
    saveResult.className = diff === 0 ? "alert alert-success" : "alert alert-warning";
    saveResult.innerHTML = diff === 0
      ? "✅ Đã lưu. Không lệch tồn."
      : `⚠️ Đã lưu. Lệch tồn: <b>${diff}</b>`;

    barcodeInput.value = "";
    document.getElementById("countQty").value = "";
    barcodeInput.focus();
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
    const targetToRestore = activeTarget;

    if (html5QrCode) {
      await html5QrCode.stop().catch(() => {});
      try { await html5QrCode.clear(); } catch (e) {}
      html5QrCode = null;
    }
    scannerBox.classList.add("d-none");

    if (restoreFocus) restoreManualInput(targetToRestore);
  }

  async function startScanner(targetId) {
    if (Date.now() < suppressAutoScanUntil) return;

    activeTarget = document.getElementById(targetId);
    scannerBox.classList.remove("d-none");
    html5QrCode = new Html5Qrcode("reader");

    await html5QrCode.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: 250 },
      async function (decodedText) {
        activeTarget.value = decodedText;
        await stopScanner();
        if (targetId === "locationId") {
          barcodeInput.focus();
        } else {
          loadTask();
        }
      }
    );
  }

  document.querySelectorAll(".scan-btn").forEach(btn => {
    btn.addEventListener("click", () => startScanner(btn.dataset.target));
  });

  closeScannerBtn.addEventListener("click", function () { stopScanner(true); });
  loadTaskBtn.addEventListener("click", loadTask);
  saveCountBtn.addEventListener("click", saveCount);

  locationInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      barcodeInput.focus();
    }
  });

  barcodeInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      loadTask();
    }
  });
});
