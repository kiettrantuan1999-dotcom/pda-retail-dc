document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("grForm");

  const poInput = document.getElementById("po_no");
  const palletInput = document.getElementById("pallet_id");
  const barcodeInput = document.getElementById("barcode");
  const pcbInput = document.getElementById("pcb");
  const cartonQtyInput = document.getElementById("carton_qty");
  const looseQtyInput = document.getElementById("loose_qty");
  const qtyPromoInput = document.getElementById("qty_promo");
  const qtyTotalPreview = document.getElementById("qty_total_preview");

  const productInfoBox = document.getElementById("productInfoBox");
  const productName = document.getElementById("productName");
  const productSku = document.getElementById("productSku");
  const productBarcode = document.getElementById("productBarcode");
  const masterPcb = document.getElementById("masterPcb");

  const resultBox = document.getElementById("resultBox");
  const resultTitle = document.getElementById("resultTitle");
  const resultText = document.getElementById("resultText");

  const historySubtitle = document.getElementById("historySubtitle");
  const historyBody = document.getElementById("grHistoryBody");
  const reloadHistoryBtn = document.getElementById("reloadHistoryBtn");

  const editGrBox = document.getElementById("editGrBox");
  const editGrForm = document.getElementById("editGrForm");
  const cancelEditGrBtn = document.getElementById("cancelEditGrBtn");
  const editPalletIdInput = document.getElementById("edit_pallet_id");
  const editPalletText = document.getElementById("editPalletText");
  const editSkuText = document.getElementById("editSkuText");
  const editProductNameText = document.getElementById("editProductNameText");
  const editBarcodeText = document.getElementById("editBarcodeText");
  const editMasterPcbText = document.getElementById("editMasterPcbText");
  const editCurrentQtyText = document.getElementById("editCurrentQtyText");
  const editPcbInput = document.getElementById("edit_pcb");
  const editCartonQtyInput = document.getElementById("edit_carton_qty");
  const editLooseQtyInput = document.getElementById("edit_loose_qty");
  const editQtyPromoInput = document.getElementById("edit_qty_promo");
  const editQtyTotalPreview = document.getElementById("edit_qty_total_preview");

  const scannerBox = document.getElementById("scannerBox");
  const closeScannerBtn = document.getElementById("closeScannerBtn");
  const scannerTargetLabel = document.getElementById("scannerTargetLabel");

  let html5QrCode = null;
  let activeTargetInput = null;
  let isStartingScanner = false;
  let lastDecodedText = "";
  let lastDecodedAt = 0;
  let currentProduct = null;
  let grHistoryRows = {};

  poInput.focus();
  recalcQtyPreview();

  function numberValue(input) {
    return Number(input.value || 0);
  }

  function recalcQtyPreview() {
    const pcb = Math.max(numberValue(pcbInput), 0);
    const cartonQty = Math.max(numberValue(cartonQtyInput), 0);
    const looseQty = Math.max(numberValue(looseQtyInput), 0);
    const qtyPromo = Math.max(numberValue(qtyPromoInput), 0);
    const qtyGr = pcb * cartonQty + looseQty;
    const qtyTotal = qtyGr + qtyPromo;

    qtyTotalPreview.value = String(qtyTotal);
    return { pcb, cartonQty, looseQty, qtyPromo, qtyGr, qtyTotal };
  }

  [pcbInput, cartonQtyInput, looseQtyInput, qtyPromoInput].forEach(function (input) {
    input.addEventListener("input", recalcQtyPreview);
  });

  if (editPcbInput) {
    [editPcbInput, editCartonQtyInput, editLooseQtyInput, editQtyPromoInput].forEach(function (input) {
      input.addEventListener("input", recalcEditQtyPreview);
    });
  }

  if (cancelEditGrBtn) {
    cancelEditGrBtn.addEventListener("click", function () {
      editGrBox.classList.add("d-none");
    });
  }

  function moveNextOnEnter(current, next) {
    current.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        if (next) {
          next.focus();
          if (next.select) next.select();
        }
      }
    });
  }

  moveNextOnEnter(poInput, palletInput);
  moveNextOnEnter(palletInput, barcodeInput);
  moveNextOnEnter(barcodeInput, cartonQtyInput);
  moveNextOnEnter(cartonQtyInput, looseQtyInput);
  moveNextOnEnter(looseQtyInput, qtyPromoInput);

  qtyPromoInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  poInput.addEventListener("change", loadHistory);
  poInput.addEventListener("blur", loadHistory);
  barcodeInput.addEventListener("change", loadProductInfo);
  barcodeInput.addEventListener("blur", loadProductInfo);
  reloadHistoryBtn.addEventListener("click", loadHistory);

  function getNextInput(targetInput) {
    if (targetInput.id === "po_no") return palletInput;
    if (targetInput.id === "pallet_id") return barcodeInput;
    if (targetInput.id === "barcode") return cartonQtyInput;
    if (targetInput.id === "carton_qty") return looseQtyInput;
    if (targetInput.id === "loose_qty") return qtyPromoInput;
    return null;
  }

  function beep() {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      oscillator.frequency.value = 880;
      oscillator.type = "sine";
      gainNode.gain.setValueAtTime(0.2, audioCtx.currentTime);
      oscillator.start();
      oscillator.stop(audioCtx.currentTime + 0.08);
    } catch (e) {
      console.log("Beep not supported");
    }
  }

  function showError(message) {
    resultBox.classList.remove("d-none");
    resultTitle.innerText = "❌ Lỗi";
    resultTitle.className = "fw-bold mb-2 text-danger";
    resultText.innerText = message;
  }

  function clearProductInfo() {
    currentProduct = null;
    productInfoBox.classList.add("d-none");
    productName.innerText = "-";
    productSku.innerText = "-";
    productBarcode.innerText = "-";
    masterPcb.innerText = "-";
    pcbInput.value = "1";
    recalcQtyPreview();
  }

  async function loadProductInfo() {
    const barcode = barcodeInput.value.trim();

    if (!barcode) {
      clearProductInfo();
      return;
    }

    try {
      const res = await fetch(`/api/gr/product/${encodeURIComponent(barcode)}`);
      const data = await res.json();

      if (!data.ok) {
        clearProductInfo();
        showError(data.error || "Không tìm thấy barcode trong master data");
        return;
      }

      currentProduct = data.data;
      productInfoBox.classList.remove("d-none");
      productName.innerText = currentProduct.product_name || "Không có tên sản phẩm";
      productSku.innerText = currentProduct.sku || "-";
      productBarcode.innerText = currentProduct.barcode || barcode;
      masterPcb.innerText = String(currentProduct.pcb || 1);
      pcbInput.value = String(currentProduct.pcb || 1);
      recalcQtyPreview();
    } catch (err) {
      showError(err.message);
    }
  }


  function recalcEditQtyPreview() {
  if (!editPcbInput) return 0;

  const pcb = Math.max(Number(editPcbInput.value || 0), 0);
  const cartonQty = Math.max(Number(editCartonQtyInput.value || 0), 0);
  const looseQty = Math.max(Number(editLooseQtyInput.value || 0), 0);
  const qtyPromo = Math.max(Number(editQtyPromoInput.value || 0), 0);

  const total = pcb * cartonQty + looseQty + qtyPromo;

  editQtyTotalPreview.value = String(total);
  return total;
}

  function openEditGr(row) {
    if (!editGrBox || !row) return;

    editPalletIdInput.value = row.pallet_id || "";
    editPalletText.innerText = row.pallet_id || "-";
    editSkuText.innerText = row.sku || "-";
    if (editProductNameText) editProductNameText.innerText = row.product_name || "-";
    if (editBarcodeText) editBarcodeText.innerText = row.barcode || "-";
    if (editMasterPcbText) editMasterPcbText.innerText = String(row.pcb || 1);
    editCurrentQtyText.innerText = String(row.qty_total || row.qty_gr || 0);

    editPcbInput.value = String(row.pcb || 1);
    editCartonQtyInput.value = "0";
    editLooseQtyInput.value = String(row.qty_total || row.qty_gr || 0);
    editQtyPromoInput.value = "0";
    recalcEditQtyPreview();

    editGrBox.classList.remove("d-none");
    editGrBox.scrollIntoView({ behavior: "smooth", block: "start" });
    setTimeout(function () {
      editCartonQtyInput.focus();
      editCartonQtyInput.select();
    }, 120);
  }

  async function enrichHistoryRow(row) {
    if (!row || !row.barcode) return row;

    try {
      const res = await fetch(`/api/gr/product/${encodeURIComponent(row.barcode)}`);
      const data = await res.json();
      if (data.ok && data.data) {
        row.product_name = data.data.product_name || "";
        row.pcb = Number(data.data.pcb || 1);
      }
    } catch (err) {
      row.pcb = row.pcb || 1;
    }

    return row;
  }

function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function renderHistory(rows) {
    const po = poInput.value.trim();
    historySubtitle.innerText = po ? `PO: ${po} · ${rows.length} PA đã GR` : "Chưa chọn PO";

    if (!rows.length) {
      historyBody.innerHTML = `
        <tr>
          <td colspan="8" class="text-muted small">Chưa có PA nào được GR cho PO này.</td>
        </tr>
      `;
      return;
    }

    historyBody.innerHTML = rows.map(function (r) {
      const canEdit = String(r.flow_status || "").toUpperCase() === "WAIT_PUTAWAY";
      const pcb = Number(r.pcb || 1);

      return `
        <tr>
          <td class="fw-semibold text-nowrap">${escapeHtml(r.pallet_id || "")}</td>
          <td class="text-nowrap">${escapeHtml(r.sku || "")}</td>
          <td style="min-width: 180px;">${escapeHtml(r.product_name || "-")}</td>
          <td class="text-nowrap">${escapeHtml(r.barcode || "-")}</td>
          <td class="text-end fw-semibold">${pcb}</td>
          <td class="text-end fw-semibold">${Number(r.qty_total || r.qty_gr || 0)}</td>
          <td><span class="badge text-bg-secondary">${escapeHtml(r.flow_status || "")}</span></td>
          <td class="text-end">
            ${
              canEdit
                ? `<button
                     type="button"
                     class="btn btn-sm btn-outline-primary edit-gr-btn"
                     data-pallet-id="${escapeHtml(r.pallet_id || "")}">
                     Sửa
                   </button>`
                : `<span class="text-muted small">Khóa</span>`
            }
          </td>
        </tr>
      `;
    }).join("");

    document.querySelectorAll(".edit-gr-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const palletId = btn.getAttribute("data-pallet-id");
        const row = grHistoryRows[palletId];

        if (!row) {
          return showError("Không tìm thấy dữ liệu PA cần sửa");
        }

        openEditGr(row);
      });
    });
  }

  async function loadHistory() {
    const po = poInput.value.trim();

    if (!po) {
      grHistoryRows = {};
      renderHistory([]);
      return;
    }

    try {
      const res = await fetch(`/api/gr/history/${encodeURIComponent(po)}`);
      const data = await res.json();

      if (!data.ok) {
        historyBody.innerHTML = `
          <tr><td colspan="8" class="text-danger small">${data.error || "Không tải được lịch sử GR"}</td></tr>
        `;
        return;
      }

      const rows = data.data.rows || [];
      grHistoryRows = {};

      rows.forEach(function (r) {
        r.qty_total = Number(r.qty_total || r.qty_gr || 0);
        r.pcb = Number(r.pcb || 1);
        r.product_name = r.product_name || "";
        r.barcode = r.barcode || "";
        grHistoryRows[r.pallet_id] = r;
      });

      renderHistory(rows);
    } catch (err) {
      historyBody.innerHTML = `
        <tr><td colspan="8" class="text-danger small">${err.message}</td></tr>
      `;
    }
  }

  function getScannerLabel(targetInputId) {
    if (targetInputId === "po_no") return "Đang quét mã PO";
    if (targetInputId === "pallet_id") return "Đang quét mã PA / Pallet";
    if (targetInputId === "barcode") return "Đang quét Barcode sản phẩm";
    return "Đưa mã vào khung để quét";
  }

  function getFormats(targetInputId) {
    if (!window.Html5QrcodeSupportedFormats) return [];

    if (targetInputId === "barcode") {
      return [
        Html5QrcodeSupportedFormats.EAN_13,
        Html5QrcodeSupportedFormats.EAN_8,
        Html5QrcodeSupportedFormats.CODE_128,
        Html5QrcodeSupportedFormats.UPC_A,
        Html5QrcodeSupportedFormats.UPC_E,
        Html5QrcodeSupportedFormats.ITF
      ];
    }

    if (targetInputId === "pallet_id") {
      return [
        Html5QrcodeSupportedFormats.QR_CODE,
        Html5QrcodeSupportedFormats.CODE_128,
        Html5QrcodeSupportedFormats.CODE_39
      ];
    }

    return [
      Html5QrcodeSupportedFormats.CODE_128,
      Html5QrcodeSupportedFormats.CODE_39,
      Html5QrcodeSupportedFormats.QR_CODE
    ];
  }

  function buildScannerConfig(targetInputId) {
    const isProductBarcode = targetInputId === "barcode";
    const formats = getFormats(targetInputId);

    const config = {
      fps: 15,
      qrbox: function (viewfinderWidth, viewfinderHeight) {
        const widthRatio = isProductBarcode ? 0.88 : 0.72;
        const heightRatio = isProductBarcode ? 0.26 : 0.52;

        const width = Math.floor(viewfinderWidth * widthRatio);
        const height = Math.floor(viewfinderHeight * heightRatio);

        return {
          width: Math.max(240, Math.min(width, 460)),
          height: Math.max(isProductBarcode ? 100 : 200, Math.min(height, isProductBarcode ? 160 : 330))
        };
      },
      disableFlip: true,
      rememberLastUsedCamera: true,
      experimentalFeatures: {
        useBarCodeDetectorIfSupported: true
      }
    };

    if (formats.length) {
      config.formatsToSupport = formats;
    }

    return config;
  }

  function normalizeCameraError(err) {
    const rawMessage = err && err.message ? err.message : String(err || "");
    const name = err && err.name ? err.name : "";

    if (name === "NotAllowedError" || rawMessage.includes("Permission denied")) {
      return "Trình duyệt chưa được cấp quyền Camera. Vào Settings > Safari/Chrome > Camera > Allow.";
    }

    if (name === "NotFoundError" || rawMessage.includes("Requested device not found")) {
      return "Không tìm thấy camera trên thiết bị.";
    }

    if (name === "NotReadableError") {
      return "Camera đang bị app khác sử dụng. Hãy đóng app camera/Zalo/Chrome tab khác rồi thử lại.";
    }

    if (name === "OverconstrainedError" || rawMessage.includes("constraint")) {
      return "Thiết bị không hỗ trợ cấu hình camera hiện tại. Đã bỏ cấu hình nâng cao, hãy thử lại.";
    }

    if (!window.isSecureContext) {
      return "Camera chỉ chạy trên HTTPS hoặc localhost. Hãy mở app bằng link HTTPS Railway.";
    }

    return rawMessage || "Không mở được camera. Hãy kiểm tra quyền Camera và thử lại.";
  }

  async function startScanner(targetInputId) {
    if (isStartingScanner) return;

    if (!window.Html5Qrcode) {
      showError("Thiếu thư viện Html5Qrcode. Kiểm tra file base.html có import html5-qrcode chưa.");
      return;
    }

    if (!window.isSecureContext) {
      showError("Camera chỉ chạy trên HTTPS hoặc localhost. Hãy mở app bằng link HTTPS Railway.");
      return;
    }

    isStartingScanner = true;
    activeTargetInput = document.getElementById(targetInputId);

    scannerBox.classList.remove("d-none");
    if (scannerTargetLabel) scannerTargetLabel.innerText = getScannerLabel(targetInputId);
    resultBox.classList.add("d-none");

    if (html5QrCode) {
      await stopScanner();
      scannerBox.classList.remove("d-none");
    }

    html5QrCode = new Html5Qrcode("reader");

    const onScanSuccess = async function (decodedText) {
      const now = Date.now();
      const cleanText = String(decodedText || "").trim();

      if (!activeTargetInput || !cleanText) return;
      if (cleanText === lastDecodedText && now - lastDecodedAt < 900) return;

      lastDecodedText = cleanText;
      lastDecodedAt = now;

      activeTargetInput.value = cleanText;
      beep();

      const currentInput = activeTargetInput;
      const nextInput = getNextInput(currentInput);

      await stopScanner();

      if (currentInput.id === "po_no") {
        loadHistory();
      }

      if (currentInput.id === "barcode") {
        await loadProductInfo();
      }

      if (nextInput) {
        setTimeout(function () {
          nextInput.focus();
          if (nextInput.select) nextInput.select();
        }, 100);
      }
    };

    const onScanFailure = function () {
      // Ignore continuous scan miss.
    };

    try {
      await html5QrCode.start(
        { facingMode: "environment" },
        buildScannerConfig(targetInputId),
        onScanSuccess,
        onScanFailure
      );

      isStartingScanner = false;
    } catch (err) {
      console.error("Camera error:", err);
      await stopScanner();
      showError(normalizeCameraError(err));
    }
  }

  document.querySelectorAll(".scan-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const target = btn.getAttribute("data-target");
      startScanner(target);
    });
  });

  [poInput, palletInput, barcodeInput].forEach(function (input) {
    input.addEventListener("click", function () {
      if (scannerBox && !scannerBox.classList.contains("d-none")) return;
      startScanner(input.id);
    });
  });

  closeScannerBtn.addEventListener("click", function () {
    stopScanner();
  });


  if (editGrForm) {
    editGrForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const palletId = editPalletIdInput.value.trim();
      const pcb = Math.max(Number(editPcbInput.value || 0), 0);
      const cartonQty = Math.max(Number(editCartonQtyInput.value || 0), 0);
      const looseQty = Math.max(Number(editLooseQtyInput.value || 0), 0);
      const qtyPromo = Math.max(Number(editQtyPromoInput.value || 0), 0);
      const total = recalcEditQtyPreview();

      if (!palletId) return showError("Không tìm thấy PA cần sửa");
      if (pcb <= 0) return showError("PCB phải lớn hơn 0");
      if (total <= 0) return showError("Tổng số lượng mới phải lớn hơn 0");

      const formData = new FormData();
      formData.append("pallet_id", palletId);
      formData.append("pcb", String(pcb));
      formData.append("carton_qty", String(cartonQty));
      formData.append("loose_qty", String(looseQty));
      formData.append("qty_promo", String(qtyPromo));

      try {
        const res = await fetch("/api/gr/update-qty", {
          method: "POST",
          body: formData
        });

        const data = await res.json();

        if (!data.ok) {
          return showError(data.error || "Không cập nhật được số lượng GR");
        }

        resultBox.classList.remove("d-none");
        resultTitle.innerText = "✅ Đã cập nhật số lượng GR";
        resultTitle.className = "fw-bold mb-2 text-success";
        resultText.innerHTML = `
          <div><b>PA:</b> ${data.data.pallet_id}</div>
          <div><b>SKU:</b> ${data.data.sku}</div>
          <div><b>SL cũ:</b> ${data.data.old_qty}</div>
          <div><b>SL mới:</b> ${data.data.qty_total}</div>
          <div><b>Còn Put Away:</b> ${data.data.qty_remain_putaway}</div>
        `;

        editGrBox.classList.add("d-none");
        await loadHistory();
      } catch (err) {
        showError(err.message);
      }
    });
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const poNo = poInput.value.trim();
    const palletId = palletInput.value.trim();
    const barcode = barcodeInput.value.trim();
    const qty = recalcQtyPreview();

    if (!poNo) return showError("Vui lòng scan/nhập PO");
    if (!palletId) return showError("Vui lòng scan PA");
    if (!barcode) return showError("Vui lòng scan Barcode");
    if (qty.pcb <= 0) return showError("PCB phải lớn hơn 0");
    if (qty.cartonQty < 0 || qty.looseQty < 0 || qty.qtyPromo < 0) return showError("Số lượng không được âm");
    if (qty.qtyTotal <= 0) return showError("Tổng số lượng nhập phải lớn hơn 0");

    const formData = new FormData();
    formData.append("po_no", poNo);
    formData.append("pallet_id", palletId);
    formData.append("barcode", barcode);
    formData.append("pcb", String(qty.pcb));
    formData.append("carton_qty", String(qty.cartonQty));
    formData.append("loose_qty", String(qty.looseQty));
    formData.append("qty_promo", String(qty.qtyPromo));

    try {
      const res = await fetch("/api/gr/confirm", {
        method: "POST",
        body: formData
      });

      const data = await res.json();
      resultBox.classList.remove("d-none");

      if (data.ok) {
        resultTitle.innerText = "✅ GR thành công";
        resultTitle.className = "fw-bold mb-2 text-success";

        resultText.innerHTML = `
          <div><b>PO:</b> ${data.data.po_no}</div>
          <div><b>PA:</b> ${data.data.pallet_id}</div>
          <div><b>SKU:</b> ${data.data.sku}</div>
          <div><b>Tên hàng:</b> ${data.data.product_name || ""}</div>
          <div><b>Barcode:</b> ${data.data.barcode}</div>
          <div><b>PCB:</b> ${data.data.pcb}</div>
          <div><b>Thùng chẵn:</b> ${data.data.carton_qty}</div>
          <div><b>Kiện lẻ:</b> ${data.data.loose_qty}</div>
          <div><b>SL nhập:</b> ${data.data.qty_gr}</div>
          <div><b>SL khuyến mãi:</b> ${data.data.qty_promo}</div>
          <div><b>Tổng nhập:</b> ${data.data.qty_total}</div>
          <div><b>Còn Put Away:</b> ${data.data.qty_remain_putaway}</div>
          <div><b>Status:</b> ${data.data.flow_status}</div>
        `;

        palletInput.value = "";
        barcodeInput.value = "";
        cartonQtyInput.value = "0";
        looseQtyInput.value = "0";
        qtyPromoInput.value = "0";
        clearProductInfo();

        await loadHistory();

        setTimeout(function () {
          palletInput.focus();
          if (palletInput.select) palletInput.select();
        }, 100);
      } else {
        resultTitle.innerText = "❌ GR lỗi";
        resultTitle.className = "fw-bold mb-2 text-danger";
        resultText.innerText = data.error || "Có lỗi xảy ra";
      }
    } catch (err) {
      resultBox.classList.remove("d-none");
      resultTitle.innerText = "❌ Lỗi kết nối";
      resultTitle.className = "fw-bold mb-2 text-danger";
      resultText.innerText = err.message;
    }
  });
});