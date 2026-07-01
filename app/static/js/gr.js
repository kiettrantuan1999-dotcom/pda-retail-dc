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
  const grPutawayType = document.getElementById("grPutawayType");
  const productWarning = document.getElementById("productWarning");

  const resultBox = document.getElementById("resultBox");
  const resultTitle = document.getElementById("resultTitle");
  const resultText = document.getElementById("resultText");

  const historySubtitle = document.getElementById("historySubtitle");
  const historyBody = document.getElementById("grHistoryBody");
  const reloadHistoryBtn = document.getElementById("reloadHistoryBtn");
  const openHistorySheetBtn = document.getElementById("openHistorySheetBtn");
  const openPoDetailSheetBtn = document.getElementById("openPoDetailSheetBtn");
  const historySheet = document.getElementById("historySheet");
  const poDetailSheet = document.getElementById("poDetailSheet");
  const completePaBtn = document.getElementById("completePaBtn");
  const poDetailSubtitle = document.getElementById("poDetailSubtitle");
  const poDetailBody = document.getElementById("poDetailBody");
  const reloadPoDetailBtn = document.getElementById("reloadPoDetailBtn");
  const poSummaryCards = document.getElementById("poSummaryCards");
  const poTotalSkuCard = document.getElementById("poTotalSkuCard");
  const poTotalOrderCard = document.getElementById("poTotalOrderCard");
  const poTotalReceivedCard = document.getElementById("poTotalReceivedCard");
  const completePaTopBtn = document.getElementById("completePaTopBtn");
  const confirmPoTopBtn = document.getElementById("confirmPoTopBtn");
  const confirmPoBtn = document.getElementById("confirmPoBtn");
  const clearGrBtn = document.getElementById("clearGrBtn");
  const completePaModal = document.getElementById("completePaModal");
  const completeModalTotalSku = document.getElementById("completeModalTotalSku");
  const completeModalTotalQty = document.getElementById("completeModalTotalQty");
  const cancelCompletePaModalBtn = document.getElementById("cancelCompletePaModalBtn");
  const confirmCompletePaModalBtn = document.getElementById("confirmCompletePaModalBtn");

  const assignSkuModal = document.getElementById("assignSkuModal");
  const assignSkuModalDetail = document.getElementById("assignSkuModalDetail");
  const assignModalTotalSku = document.getElementById("assignModalTotalSku");
  const assignModalTotalQty = document.getElementById("assignModalTotalQty");
  const closeAssignSkuModalBtn = document.getElementById("closeAssignSkuModalBtn");

  const confirmPoModal = document.getElementById("confirmPoModal");
  const confirmPoModalDetail = document.getElementById("confirmPoModalDetail");
  const confirmPoModalTotalSku = document.getElementById("confirmPoModalTotalSku");
  const confirmPoModalTotalReceived = document.getElementById("confirmPoModalTotalReceived");
  const cancelConfirmPoModalBtn = document.getElementById("cancelConfirmPoModalBtn");
  const confirmConfirmPoModalBtn = document.getElementById("confirmConfirmPoModalBtn");

  const editGrBox = document.getElementById("editGrBox");
  const editGrForm = document.getElementById("editGrForm");
  const cancelEditGrBtn = document.getElementById("cancelEditGrBtn");
  const cancelEditGrTopBtn = document.getElementById("cancelEditGrTopBtn");
  const editPalletIdInput = document.getElementById("edit_pallet_id");
  const editQueueIdInput = document.getElementById("edit_queue_id");
  const editSkuInput = document.getElementById("edit_sku");
  const editBarcodeInput = document.getElementById("edit_barcode");
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
  let latestPoSummary = null;
  let pendingCompletePa = null;
  let pendingConfirmPo = null;
  let suppressAutoScanUntil = 0;
  let isSubmittingGr = false;

  function openSheet(sheet) {
    if (!sheet) return;
    sheet.classList.remove("d-none");
    if (sheet.id === "editGrBox") {
      sheet.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function closeSheet(sheet) {
    if (!sheet) return;
    sheet.classList.add("d-none");
  }

  document.querySelectorAll(".gr-sheet-close").forEach(function (btn) {
    btn.addEventListener("click", function () {
      closeSheet(document.getElementById(btn.getAttribute("data-sheet-close")));
    });
  });

  [historySheet, poDetailSheet, editGrBox].forEach(function (sheet) {
    if (!sheet) return;
    sheet.addEventListener("click", function (e) {
      if (e.target === sheet) closeSheet(sheet);
    });
  });

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

  function closeEditGrSheet() {
    closeSheet(editGrBox);
  }

  if (cancelEditGrBtn) {
    cancelEditGrBtn.addEventListener("click", closeEditGrSheet);
  }
  if (cancelEditGrTopBtn) {
    cancelEditGrTopBtn.addEventListener("click", closeEditGrSheet);
  }

  function moveNextOnEnter(current, next, beforeMove) {
    current.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        if (typeof beforeMove === "function") {
          beforeMove();
        }
        if (next) {
          next.focus();
          if (next.select) next.select();
        }
      }
    });
  }

  moveNextOnEnter(poInput, palletInput, function () { loadHistory(); loadPoDetail(); });
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

  let poLoadTimer = null;
  function schedulePoLoad() {
    clearTimeout(poLoadTimer);
    poLoadTimer = setTimeout(function () {
      loadHistory();
      loadPoDetail();
    }, 250);
  }

  poInput.addEventListener("input", schedulePoLoad);
  poInput.addEventListener("change", function () { loadHistory(); loadPoDetail(); });
  poInput.addEventListener("blur", function () { loadHistory(); loadPoDetail(); });
  barcodeInput.addEventListener("change", loadProductInfo);
  barcodeInput.addEventListener("blur", loadProductInfo);
  if (reloadHistoryBtn) reloadHistoryBtn.addEventListener("click", loadHistory);
  if (reloadPoDetailBtn) reloadPoDetailBtn.addEventListener("click", loadPoDetail);
  if (openHistorySheetBtn) {
    openHistorySheetBtn.addEventListener("click", async function () {
      await loadHistory();
      openSheet(historySheet);
    });
  }
  if (openPoDetailSheetBtn) {
    openPoDetailSheetBtn.addEventListener("click", async function () {
      await loadPoDetail();
      openSheet(poDetailSheet);
    });
  }
  if (completePaTopBtn && completePaBtn) {
    completePaTopBtn.addEventListener("click", function () { completePaBtn.click(); });
  }
  if (confirmPoTopBtn && confirmPoBtn) {
    confirmPoTopBtn.addEventListener("click", function () { confirmPoBtn.click(); });
  }
  if (clearGrBtn) {
    clearGrBtn.addEventListener("click", function () {
      poInput.value = "";
      palletInput.value = "";
      barcodeInput.value = "";
      cartonQtyInput.value = "0";
      looseQtyInput.value = "0";
      qtyPromoInput.value = "0";
      clearProductInfo();
      renderPoDetail(null);
      renderHistory([]);
      resultBox.classList.add("d-none");
      poInput.focus();
    });
  }

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
    if (grPutawayType) grPutawayType.innerText = "-";
    if (productWarning) {
      productWarning.innerText = "";
      productWarning.classList.add("d-none");
    }
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
      const poNo = poInput.value.trim();
      const url = poNo
        ? `/api/gr/product/${encodeURIComponent(barcode)}?po_no=${encodeURIComponent(poNo)}`
        : `/api/gr/product/${encodeURIComponent(barcode)}`;
      const res = await fetch(url);
      const data = await res.json();

      if (!data.ok) {
        clearProductInfo();
        showError(data.error || "Không tải được thông tin barcode");
        return;
      }

      currentProduct = data.data;
      productInfoBox.classList.remove("d-none");
      productInfoBox.className = currentProduct.is_unknown_master
        ? "alert alert-warning py-2 mb-3"
        : "alert alert-secondary py-2 mb-3";
      productName.innerText = currentProduct.product_name || "Không có tên sản phẩm";
      productSku.innerText = currentProduct.sku || "-";
      productBarcode.innerText = currentProduct.barcode || barcode;
      masterPcb.innerText = String(currentProduct.pcb || 1);
      if (grPutawayType) grPutawayType.innerText = currentProduct.putaway_type_label || "-";
      if (productWarning) {
        const warning = currentProduct.warning || "";
        productWarning.innerText = warning;
        productWarning.classList.toggle("d-none", !warning);
      }
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
    if (editQueueIdInput) editQueueIdInput.value = row.queue_id || "";
    if (editSkuInput) editSkuInput.value = row.sku || "";
    if (editBarcodeInput) editBarcodeInput.value = row.barcode || "";
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

    openSheet(editGrBox);
    setTimeout(function () {
      if (editCartonQtyInput) {
        editCartonQtyInput.focus();
        editCartonQtyInput.select();
      }
    }, 80);
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

  function formatNumber(value) {
    return Number(value || 0).toLocaleString("vi-VN");
  }

  function getCurrentPaSummary(poNo, palletId) {
    const rows = Object.values(grHistoryRows || {}).filter(function (r, idx, arr) {
      return r
        && String(r.po_no || poNo || "") === String(poNo || "")
        && String(r.pallet_id || "").toUpperCase() === String(palletId || "").toUpperCase()
        && arr.findIndex(function (x) { return String(x.queue_id) === String(r.queue_id); }) === idx;
    });

    return {
      totalSku: rows.length,
      totalQty: rows.reduce(function (sum, r) { return sum + Number(r.qty_total || r.qty_gr || 0); }, 0)
    };
  }

  function openCompleteModal(poNo, palletId) {
    if (!completePaModal) return false;

    const summary = getCurrentPaSummary(poNo, palletId);
    pendingCompletePa = { poNo: poNo, palletId: palletId, totalSku: summary.totalSku, totalQty: summary.totalQty };

    if (completeModalTotalSku) completeModalTotalSku.innerText = formatNumber(summary.totalSku);
    if (completeModalTotalQty) completeModalTotalQty.innerText = formatNumber(summary.totalQty);
    completePaModal.classList.remove("d-none");
    document.body.style.overflow = "hidden";
    return true;
  }

  function closeCompleteModal() {
    pendingCompletePa = null;
    if (completePaModal) completePaModal.classList.add("d-none");
    if (!document.querySelector(".gr-sheet-backdrop:not(.d-none), .gr-complete-modal-backdrop:not(.d-none), .scanner-modal:not(.d-none)")) {
      document.body.style.overflow = "";
    }
  }


  function openAssignSkuModal(data) {
    if (!assignSkuModal || !data) return false;

    if (assignSkuModalDetail) {
      assignSkuModalDetail.innerHTML = `
        <div><b>PO:</b> ${escapeHtml(data.po_no || "")}</div>
        <div><b>PA:</b> ${escapeHtml(data.pallet_id || "")}</div>
        <div><b>SKU:</b> ${escapeHtml(data.sku || "")}</div>
        <div><b>Tên hàng:</b> ${escapeHtml(data.product_name || "")}</div>
        <div><b>Barcode:</b> ${escapeHtml(data.barcode || "")}</div>
        <div><b>Tổng nhập dòng này:</b> ${formatNumber(data.qty_total || data.qty_gr || 0)}</div>
      `;
    }
    if (assignModalTotalSku) assignModalTotalSku.innerText = formatNumber(data.pallet_total_sku || 1);
    if (assignModalTotalQty) assignModalTotalQty.innerText = formatNumber(data.pallet_total_qty || data.qty_total || data.qty_gr || 0);

    assignSkuModal.classList.remove("d-none");
    document.body.style.overflow = "hidden";
    return true;
  }

  function closeAssignSkuModal() {
    if (assignSkuModal) assignSkuModal.classList.add("d-none");
    if (!document.querySelector(".gr-sheet-backdrop:not(.d-none), .gr-complete-modal-backdrop:not(.d-none), .scanner-modal:not(.d-none)")) {
      document.body.style.overflow = "";
    }
    setTimeout(function () {
      barcodeInput.focus();
      if (barcodeInput.select) barcodeInput.select();
    }, 50);
  }

  function openConfirmPoModal(poNo) {
    if (!confirmPoModal) return false;
    const summary = latestPoSummary || {};
    pendingConfirmPo = { poNo: poNo };

    if (confirmPoModalDetail) {
      confirmPoModalDetail.innerHTML = `
        <div><b>PO:</b> ${escapeHtml(poNo)}</div>
        <div><b>Trạng thái hiện tại:</b> ${escapeHtml(summary.po_status || summary.status || "-")}</div>
        <div><b>Tổng SL đặt:</b> ${formatNumber(summary.total_order || 0)}</div>
      `;
    }
    if (confirmPoModalTotalSku) confirmPoModalTotalSku.innerText = formatNumber(summary.total_sku || 0);
    if (confirmPoModalTotalReceived) confirmPoModalTotalReceived.innerText = formatNumber(summary.total_received || 0);

    confirmPoModal.classList.remove("d-none");
    document.body.style.overflow = "hidden";
    return true;
  }

  function closeConfirmPoModal() {
    pendingConfirmPo = null;
    if (confirmPoModal) confirmPoModal.classList.add("d-none");
    if (!document.querySelector(".gr-sheet-backdrop:not(.d-none), .gr-complete-modal-backdrop:not(.d-none), .scanner-modal:not(.d-none)")) {
      document.body.style.overflow = "";
    }
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
      const status = String(r.flow_status || "").toUpperCase();
      const canEdit = ["DRAFT", "WAIT_PUTAWAY", "PARTIAL"].includes(status);
      const pcb = Number(r.pcb || 1);

      return `
        <tr>
          <td class="gr-primary-cell" data-label="PA">
            <div class="sku-main">${escapeHtml(r.pallet_id || "")}</div>
            <div class="muted-line">SKU: ${escapeHtml(r.sku || "-")} · Barcode: ${escapeHtml(r.barcode || "-")}</div>
          </td>
          <td data-label="SKU">${escapeHtml(r.sku || "")}</td>
          <td data-label="Tên hàng">${escapeHtml(r.product_name || "-")}</td>
          <td data-label="Barcode">${escapeHtml(r.barcode || "-")}</td>
          <td data-label="PCB" class="text-end fw-semibold">${pcb}</td>
          <td data-label="SL nhập" class="text-end fw-semibold">${formatNumber(r.qty_total || r.qty_gr || 0)}</td>
          <td data-label="Trạng thái"><span class="badge text-bg-secondary">${escapeHtml(r.flow_status || "")}</span></td>
          <td data-label="Sửa" class="text-end">
            ${
              canEdit
                ? `<button
                     type="button"
                     class="btn btn-sm btn-outline-primary edit-gr-btn"
                     data-pallet-id="${escapeHtml(r.pallet_id || "")}"
                     data-queue-id="${escapeHtml(r.queue_id || "")}">
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
        const queueId = btn.getAttribute("data-queue-id");
        const palletId = btn.getAttribute("data-pallet-id");
        const row = grHistoryRows[queueId] || grHistoryRows[palletId];

        if (!row) {
          return showError("Không tìm thấy dữ liệu dòng SKU cần sửa");
        }

        openEditGr(row);
      });
    });
  }

  function setPoLockedState(isLocked) {
    [barcodeInput, pcbInput, cartonQtyInput, looseQtyInput, qtyPromoInput, palletInput].forEach(function (input) {
      if (input) input.disabled = Boolean(isLocked);
    });
    if (completePaBtn) completePaBtn.disabled = Boolean(isLocked);
    if (completePaTopBtn) completePaTopBtn.disabled = Boolean(isLocked);
    if (confirmPoBtn) confirmPoBtn.disabled = Boolean(isLocked);
    if (confirmPoTopBtn) confirmPoTopBtn.disabled = Boolean(isLocked);
  }

  function statusBadge(status) {
    const clean = String(status || "").toUpperCase();
    if (clean === "ĐỦ") return "text-bg-success";
    if (clean === "DƯ") return "text-bg-danger";
    return "text-bg-warning";
  }

  function renderPoDetail(summary) {
    if (!poDetailBody || !poDetailSubtitle) return;

    if (!summary || !summary.rows || !summary.rows.length) {
      latestPoSummary = null;
      setPoLockedState(false);
      if (poSummaryCards) poSummaryCards.classList.add("d-none");
      poDetailSubtitle.innerText = "Scan PO để xem SKU cần nhập.";
      poDetailBody.innerHTML = `
        <tr><td colspan="9" class="text-muted small">Chưa có dữ liệu PO detail.</td></tr>
      `;
      return;
    }

    latestPoSummary = summary;
    if (poSummaryCards) poSummaryCards.classList.remove("d-none");
    if (poTotalSkuCard) poTotalSkuCard.innerText = formatNumber(summary.total_sku);
    if (poTotalOrderCard) poTotalOrderCard.innerText = formatNumber(summary.total_order);
    if (poTotalReceivedCard) poTotalReceivedCard.innerText = formatNumber(summary.total_received);

    const poStatusText = summary.po_status ? ` · PO: ${summary.po_status}` : "";
    poDetailSubtitle.innerText = `PO: ${summary.po_no} · SKU: ${summary.total_sku} · Đặt: ${summary.total_order} · Đã nhập: ${summary.total_received} · ${summary.status}${poStatusText}`;
    setPoLockedState(Boolean(summary.is_po_confirmed));

    poDetailBody.innerHTML = summary.rows.map(function (r) {
      return `
        <tr>
          <td class="gr-primary-cell" data-label="SKU">
            <div class="sku-main">${escapeHtml(r.sku || "")}</div>
            <div class="muted-line">Barcode: ${escapeHtml(r.barcode || "-")}</div>
          </td>
          <td data-label="Barcode">${escapeHtml(r.barcode || "")}</td>
          <td data-label="SL đặt" class="text-end">${formatNumber(r.qty_order || 0)}</td>
          <td data-label="Thùng chẵn" class="text-end">${formatNumber(r.carton_qty || 0)}</td>
          <td data-label="Kiện lẻ" class="text-end">${formatNumber(r.loose_qty || 0)}</td>
          <td data-label="Tổng SL" class="text-end fw-semibold">${formatNumber(r.qty_total || 0)}</td>
          <td data-label="Trạng thái"><span class="badge ${statusBadge(r.status)}">${escapeHtml(r.status || "")}</span></td>
          <td data-label="Ghi chú" class="small">${escapeHtml(r.note || "")}</td>
          <td data-label="Đã nhập" class="text-end fw-semibold">${formatNumber(r.qty_received || r.received_qty || 0)}</td>
        </tr>
      `;
    }).join("");
  }

  async function loadPoDetail() {
    if (!poDetailBody || !poDetailSubtitle) return;

    const po = poInput.value.trim();
    if (!po) {
      renderPoDetail(null);
      return;
    }

    try {
      const res = await fetch(`/api/gr/po/${encodeURIComponent(po)}`);
      const data = await res.json();

      if (!data.ok) {
        poDetailSubtitle.innerText = `PO: ${po}`;
        poDetailBody.innerHTML = `
          <tr><td colspan="9" class="text-danger small">${escapeHtml(data.error || "Không tải được PO detail")}</td></tr>
        `;
        return;
      }

      renderPoDetail(data.data);
    } catch (err) {
      poDetailBody.innerHTML = `
        <tr><td colspan="9" class="text-danger small">${escapeHtml(err.message)}</td></tr>
      `;
    }
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
        grHistoryRows[String(r.queue_id)] = r;
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

function restoreManualInput(targetInput) {
    if (!targetInput) return;

    suppressAutoScanUntil = Date.now() + 1500;

    setTimeout(function () {
      targetInput.focus();
      if (targetInput.select) targetInput.select();
    }, 80);
  }

  async function stopScanner(restoreFocus) {
    const targetToRestore = activeTargetInput;

    if (html5QrCode) {
      try {
        await html5QrCode.stop();
      } catch (e) {
        console.log("Scanner stop ignored:", e);
      }

      try {
        await html5QrCode.clear();
      } catch (e) {
        console.log("Scanner clear ignored:", e);
      }

      html5QrCode = null;
    }

    if (scannerBox) scannerBox.classList.add("d-none");

    activeTargetInput = null;
    isStartingScanner = false;

    if (restoreFocus) {
      restoreManualInput(targetToRestore);
    }
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
        loadPoDetail();
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
      if (Date.now() < suppressAutoScanUntil) return;
      if (scannerBox && !scannerBox.classList.contains("d-none")) return;
      startScanner(input.id);
    });
  });

  closeScannerBtn.addEventListener("click", function () {
    stopScanner(true);
  });


  async function saveCurrentGrLineIfNeeded() {
    const poNo = poInput.value.trim();
    const palletId = palletInput.value.trim();
    const barcode = barcodeInput.value.trim();
    const qty = recalcQtyPreview();

    // Nếu màn hình không còn barcode/SL đang nhập thì không cần lưu thêm.
    // Case này xảy ra khi user đã Enter để lưu SKU trước đó, JS đã clear barcode + qty.
    if (!barcode && qty.qtyTotal <= 0) {
      return { ok: true, skipped: true };
    }

    // Nếu có barcode nhưng chưa nhập SL thì vẫn phải chặn rõ, không để Confirm PA báo PA rỗng gây hiểu nhầm.
    if (!poNo) return { ok: false, error: "Vui lòng scan/nhập PO" };
    if (!palletId) return { ok: false, error: "Vui lòng scan PA" };
    if (!barcode) return { ok: true, skipped: true };
    if (qty.pcb <= 0) return { ok: false, error: "PCB phải lớn hơn 0" };
    if (qty.cartonQty < 0 || qty.looseQty < 0 || qty.qtyPromo < 0) return { ok: false, error: "Số lượng không được âm" };
    if (qty.qtyTotal <= 0) return { ok: false, error: "Bạn đã scan barcode nhưng chưa nhập số lượng. Vui lòng nhập SL trước khi Confirm PA." };

    if (isSubmittingGr) return { ok: false, error: "Hệ thống đang lưu SKU, vui lòng thao tác lại sau vài giây." };
    isSubmittingGr = true;

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

      if (!data.ok) {
        return { ok: false, error: data.error || "Không tự lưu được SKU vào PA trước khi Confirm PA" };
      }

      // Lưu thành công: clear dòng đang nhập để tránh bấm Confirm PA nhiều lần bị cộng trùng số lượng.
      barcodeInput.value = "";
      cartonQtyInput.value = "0";
      looseQtyInput.value = "0";
      qtyPromoInput.value = "0";
      clearProductInfo();
      recalcQtyPreview();

      return { ok: true, skipped: false, data: data.data };
    } catch (err) {
      return { ok: false, error: err.message || "Lỗi kết nối khi tự lưu SKU vào PA" };
    } finally {
      isSubmittingGr = false;
    }
  }


  async function submitCompletePa(poNo, palletId) {
    const formData = new FormData();
    formData.append("po_no", poNo);
    formData.append("pallet_id", palletId);

    try {
      completePaBtn.disabled = true;
      if (completePaTopBtn) completePaTopBtn.disabled = true;
      completePaBtn.innerText = "ĐANG CONFIRM PA...";
      if (completePaTopBtn) completePaTopBtn.innerText = "Đang confirm...";

      const res = await fetch("/api/gr/complete-pa", {
        method: "POST",
        body: formData
      });

      const data = await res.json();

      if (!data.ok) {
        return showError(data.error || "Không hoàn tất được PA");
      }

      resultBox.classList.remove("d-none");
      resultBox.classList.add("gr-result-success");
      resultTitle.innerText = "✅ Đã Confirm PA";
      resultTitle.className = "fw-bold mb-2 text-success";
      resultText.innerHTML = `
        <div><b>PO:</b> ${escapeHtml(data.data.po_no)}</div>
        <div><b>PA:</b> ${escapeHtml(data.data.pallet_id)}</div>
        <div><b>Tổng số lượng SKU GR:</b> ${formatNumber(data.data.total_sku)}</div>
        <div><b>Tổng số lượng GR:</b> ${formatNumber(data.data.total_qty)}</div>
        <div><b>Status:</b> ${escapeHtml(data.data.flow_status)}</div>
        <div class="text-muted mt-1">PA đã chuyển sang danh sách Put Away. Scan PA mới để tiếp tục nhập cùng PO.</div>
      `;

      await loadHistory();
      await loadPoDetail();

      palletInput.value = "";
      barcodeInput.value = "";
      cartonQtyInput.value = "0";
      looseQtyInput.value = "0";
      qtyPromoInput.value = "0";
      clearProductInfo();
      recalcQtyPreview();

      setTimeout(function () {
        // Sau khi hoàn tất PA, giữ nguyên PO và đưa focus về PA để scan PA tiếp theo của cùng PO.
        palletInput.focus();
        if (palletInput.select) palletInput.select();
      }, 100);
    } catch (err) {
      showError(err.message);
    } finally {
      completePaBtn.disabled = false;
      if (completePaTopBtn) completePaTopBtn.disabled = false;
      completePaBtn.innerText = "✅ CONFIRM PA";
      if (completePaTopBtn) completePaTopBtn.innerText = "✓ Confirm PA";
    }
  }

  if (completePaBtn) {
    completePaBtn.addEventListener("click", async function () {
      const poNo = poInput.value.trim();
      const palletId = palletInput.value.trim();

      if (!poNo) return showError("Vui lòng nhập/scan PO trước khi Confirm PA");
      if (!palletId) return showError("Vui lòng nhập/scan PA trước khi Confirm PA");

      // Fix flow mới: nếu user vừa scan barcode + nhập SL rồi bấm Confirm PA ngay,
      // tự lưu dòng SKU đang nhập trước, không bắt user phải Enter/nút lưu riêng.
      const saveResult = await saveCurrentGrLineIfNeeded();
      if (!saveResult.ok) {
        return showError(saveResult.error || "Không tự lưu được SKU vào PA trước khi Confirm PA");
      }

      await loadHistory();
      await loadPoDetail();
      const currentSummary = getCurrentPaSummary(poNo, palletId);
      if (currentSummary.totalSku <= 0 || currentSummary.totalQty <= 0) {
        return showError("PA chưa có SKU hoặc số lượng GR. Hãy scan barcode và nhập số lượng trước khi Confirm PA.");
      }

      openCompleteModal(poNo, palletId);
    });
  }

  if (cancelCompletePaModalBtn) {
    cancelCompletePaModalBtn.addEventListener("click", closeCompleteModal);
  }

  if (completePaModal) {
    completePaModal.addEventListener("click", function (e) {
      if (e.target === completePaModal) closeCompleteModal();
    });
  }

  if (confirmCompletePaModalBtn) {
    confirmCompletePaModalBtn.addEventListener("click", async function () {
      if (!pendingCompletePa) return closeCompleteModal();
      const poNo = pendingCompletePa.poNo;
      const palletId = pendingCompletePa.palletId;
      closeCompleteModal();
      await submitCompletePa(poNo, palletId);
    });
  }


  if (closeAssignSkuModalBtn) {
    closeAssignSkuModalBtn.addEventListener("click", closeAssignSkuModal);
  }

  if (assignSkuModal) {
    assignSkuModal.addEventListener("click", function (e) {
      if (e.target === assignSkuModal) closeAssignSkuModal();
    });
  }

  if (cancelConfirmPoModalBtn) {
    cancelConfirmPoModalBtn.addEventListener("click", closeConfirmPoModal);
  }

  if (confirmPoModal) {
    confirmPoModal.addEventListener("click", function (e) {
      if (e.target === confirmPoModal) closeConfirmPoModal();
    });
  }

  if (confirmConfirmPoModalBtn) {
    confirmConfirmPoModalBtn.addEventListener("click", async function () {
      if (!pendingConfirmPo) return closeConfirmPoModal();
      const poNo = pendingConfirmPo.poNo;
      closeConfirmPoModal();
      await executeConfirmPo(poNo);
    });
  }


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
      if (editQueueIdInput) formData.append("queue_id", editQueueIdInput.value || "");
      if (editSkuInput) formData.append("sku", editSkuInput.value || "");
      if (editBarcodeInput) formData.append("barcode", editBarcodeInput.value || "");
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

        closeSheet(editGrBox);
        await loadHistory();
        await loadPoDetail();
      } catch (err) {
        showError(err.message);
      }
    });
  }

  async function executeConfirmPo(poNo) {
    const formData = new FormData();
    formData.append("po_no", poNo);

    let confirmedOk = false;
    try {
      if (confirmPoBtn) { confirmPoBtn.disabled = true; confirmPoBtn.innerText = "ĐANG XÁC NHẬN PO..."; }
      if (confirmPoTopBtn) { confirmPoTopBtn.disabled = true; confirmPoTopBtn.innerText = "Đang xác nhận..."; }
      if (confirmConfirmPoModalBtn) { confirmConfirmPoModalBtn.disabled = true; confirmConfirmPoModalBtn.innerText = "Đang xác nhận..."; }

      const res = await fetch("/api/gr/confirm-po", { method: "POST", body: formData });
      const data = await res.json();

      if (!data.ok) return showError(data.error || "Không xác nhận được PO");

      resultBox.classList.remove("d-none");
      resultBox.classList.add("gr-result-success");
      resultTitle.innerText = "✅ Đã xác nhận PO";
      resultTitle.className = "fw-bold mb-2 text-success";
      resultText.innerHTML = `
        <div><b>PO:</b> ${escapeHtml(data.data.po_no)}</div>
        <div><b>Trạng thái:</b> ${escapeHtml(data.data.po_status)}</div>
        <div><b>Tổng PA:</b> ${formatNumber(data.data.total_pa)}</div>
        <div><b>Tổng SKU:</b> ${formatNumber(data.data.total_sku)}</div>
        <div><b>Tổng SL GR:</b> ${formatNumber(data.data.total_qty)}</div>
        <div class="text-muted mt-1">PO đã đóng. Hệ thống đã khóa GR thêm và khóa sửa SL.</div>
      `;

      await loadHistory();
      await loadPoDetail();
      confirmedOk = true;
      setPoLockedState(true);
    } catch (err) {
      showError(err.message);
    } finally {
      if (confirmConfirmPoModalBtn) { confirmConfirmPoModalBtn.disabled = false; confirmConfirmPoModalBtn.innerText = "Xác nhận đóng PO"; }
      if (!confirmedOk) {
        if (confirmPoBtn) { confirmPoBtn.disabled = false; confirmPoBtn.innerText = "✅ XÁC NHẬN PO"; }
        if (confirmPoTopBtn) { confirmPoTopBtn.disabled = false; confirmPoTopBtn.innerText = "✓ Confirm PO"; }
      }
    }
  }

  async function submitConfirmPo() {
    const poNo = poInput.value.trim();
    if (!poNo) return showError("Vui lòng nhập/scan PO trước khi xác nhận PO");

    await loadHistory();
    await loadPoDetail();
    openConfirmPoModal(poNo);
  }

  if (confirmPoBtn) {
    confirmPoBtn.addEventListener("click", submitConfirmPo);
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    if (isSubmittingGr) return;

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

    isSubmittingGr = true;

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
          <div><b>Còn Put Away dòng SKU:</b> ${data.data.qty_remain_putaway}</div>
          <div><b>Tổng SKU trên PA:</b> ${data.data.pallet_total_sku || 1}</div>
          <div><b>Tổng SL trên PA:</b> ${data.data.pallet_total_qty || data.data.qty_total}</div>
          <div><b>Status:</b> ${data.data.flow_status}</div>
          <div class="text-muted mt-1">Đã tự lưu SKU vào PA. Scan SKU tiếp theo trên cùng PA, hoặc bấm <b>Confirm PA</b> để qua PA mới.</div>
        `;

        // Giữ nguyên PA để nhân sự có thể scan nhiều SKU vào cùng pallet.
        barcodeInput.value = "";
        cartonQtyInput.value = "0";
        looseQtyInput.value = "0";
        qtyPromoInput.value = "0";
        clearProductInfo();

        await loadHistory();
        await loadPoDetail();

        // Hiện popup xác nhận SKU đã được assign vào PA để nhân sự nhìn rõ trạng thái lưu.
        openAssignSkuModal(data.data);

        setTimeout(function () {
          if (!assignSkuModal || assignSkuModal.classList.contains("d-none")) {
            barcodeInput.focus();
            if (barcodeInput.select) barcodeInput.select();
          }
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
    } finally {
      isSubmittingGr = false;
    }
  });
});