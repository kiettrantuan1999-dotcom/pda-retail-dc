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
  const scannerVideo = document.getElementById("scannerVideo");

  let currentPack = null;

  if (doInput) doInput.focus();

  function showMessage(type, message) {
    resultBox.classList.remove(
      "d-none",
      "alert-success",
      "alert-danger",
      "alert-info"
    );

    resultBox.classList.add(type);
    resultBox.innerText = message;
  }

  function clearMessage() {
    resultBox.classList.add("d-none");
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

    showMessage("alert-info", "Đang tìm phiếu đóng hàng...");

    try {
      const res = await fetch("/api/pack/do/" + encodeURIComponent(doNo));
      const data = await res.json();

      if (!data.ok) {
        showMessage("alert-danger", data.error || data.message || "Không tìm thấy phiếu.");
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
      document.getElementById("infoStore").innerText =
        currentPack.store_id + " - " + currentPack.store_name;
      document.getElementById("infoType").innerText = currentPack.pack_type_name;
      document.getElementById("infoSkuLine").innerText = currentPack.sku_line_count;
      document.getElementById("infoTotalQty").innerText = currentPack.total_qty;
      const infoStatus = document.getElementById("infoStatus");

    switch (currentPack.status) {
      case "DONE":
        infoStatus.innerHTML =
          '<span class="badge bg-success">Đã đóng hàng</span>';
        break;

      case "PARTIAL":
        infoStatus.innerHTML =
          '<span class="badge bg-info">Đóng hàng một phần</span>';
        break;

      default:
        infoStatus.innerHTML =
          '<span class="badge bg-warning text-dark">Chờ đóng hàng</span>';
    }

      actualPackageQty.value = currentPack.actual_package_qty || "";
      if (pickerNameInput) pickerNameInput.value = currentPack.picked_by || "";

      renderSkuTable(currentPack.rows || []);

      clearMessage();
      packBox.classList.remove("d-none");
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

    if (packageQty === "" || Number(packageQty) < 0) {
      showMessage("alert-danger", "Số kiện thực tế không hợp lệ.");
      if (pickerNameInput && !pickerNameInput.value.trim()) {
        pickerNameInput.focus();
      } else {
        actualPackageQty.focus();
      }
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

      showMessage("alert-success", "✅ Đóng hàng thành công.");

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

      setTimeout(() => {
        clearMessage();
      }, 2000);

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

  if (loadPackBtn) {
    loadPackBtn.addEventListener("click", loadPack);
  }

  if (confirmPackBtn) {
    confirmPackBtn.addEventListener("click", confirmPack);
  }

  if (doInput) {
      doInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        loadPack();
      }
    });
  }

  if (scanDoBtn) {
    scanDoBtn.addEventListener("click", function () {
      openZxingScanner({
        targetInput: doInput,
        scannerBox: scannerBox,
        videoElement: scannerVideo,
        resultBox: resultBox,
        afterScan: function (text) {
          doInput.value = text.trim().toUpperCase();
          loadPack();
        },
      });
    });
  }

  if (closeScannerBtn) {
    closeScannerBtn.addEventListener("click", function () {
      closeZxingScanner(true);
    });
  }

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

      if (!confirmPackBtn.disabled) {
        confirmPack();
      }
    }
  });
}
});
