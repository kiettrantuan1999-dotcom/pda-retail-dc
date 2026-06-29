document.addEventListener("DOMContentLoaded", function () {
  const qInput = document.getElementById("invQ");
  const searchBtn = document.getElementById("searchBtn");
  const resultBox = document.getElementById("invResult");
  const summaryBox = document.getElementById("invSummary");
  const scannerBox = document.getElementById("scannerBox");
  const scanBtn = document.getElementById("scanBtn");
  const closeScannerBtn = document.getElementById("closeScannerBtn");

  let html5QrCode = null;
  let suppressAutoScanUntil = 0;

  qInput.focus();

  async function searchInventory() {
    const q = qInput.value.trim();

    const res = await fetch("/api/inventory/search?q=" + encodeURIComponent(q));
    const data = await res.json();

    if (!data.ok) {
      showToast(data.error || "Lỗi tra cứu tồn", false);
      return;
    }

    const rows = data.data.rows || [];
    const totalQty = rows.reduce((sum, r) => sum + Number(r.qty_onhand || 0), 0);

    summaryBox.classList.remove("d-none");
    summaryBox.innerHTML = `Tìm thấy <b>${rows.length}</b> dòng tồn. Tổng Qty: <b>${totalQty}</b>`;

    if (rows.length === 0) {
      resultBox.innerHTML = `<div class="alert alert-secondary">Không có tồn phù hợp.</div>`;
      return;
    }

    let html = "";
    for (const r of rows) {
      html += `
        <div class="card shadow-sm mb-2">
          <div class="card-body">
            <div class="d-flex justify-content-between mb-2">
              <div class="fw-bold">${r.location_id}</div>
              <span class="badge text-bg-primary">Qty ${r.qty_onhand}</span>
            </div>
            <div><b>SKU:</b> ${r.sku}</div>
            <div><b>Barcode:</b> ${r.barcode}</div>
            <div><b>Tên hàng:</b> ${r.product_name || ""}</div>
            <div class="text-muted small mt-1">Update: ${r.last_update || ""}</div>
          </div>
        </div>
      `;
    }

    resultBox.innerHTML = html;
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
      await html5QrCode.stop().catch(() => {});
      try { await html5QrCode.clear(); } catch (e) {}
      html5QrCode = null;
    }
    scannerBox.classList.add("d-none");

    if (restoreFocus) restoreManualInput(qInput);
  }

  async function startScanner() {
    if (Date.now() < suppressAutoScanUntil) return;

    scannerBox.classList.remove("d-none");
    html5QrCode = new Html5Qrcode("reader");

    await html5QrCode.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: 250 },
      async function (decodedText) {
        qInput.value = decodedText;
        await stopScanner();
        searchInventory();
      }
    );
  }

  searchBtn.addEventListener("click", searchInventory);
  qInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      searchInventory();
    }
  });

  scanBtn.addEventListener("click", startScanner);
  closeScannerBtn.addEventListener("click", function () { stopScanner(true); });
});
