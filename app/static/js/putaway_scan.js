document.addEventListener("DOMContentLoaded", function () {
  const palletInput = document.getElementById("pallet_id");
  const locationInput = document.getElementById("location_id");
  const qtyInput = document.getElementById("qty_putaway");

  const taskBox = document.getElementById("taskBox");
  const suggestBox = document.getElementById("locationSuggest");
  const locationStatus = document.getElementById("locationStatus");

  const loadBtn = document.getElementById("loadBtn");
  const confirmBtn = document.getElementById("confirmBtn");

  const scanPalletBtn = document.getElementById("scanPalletBtn");
  const scanLocationBtn = document.getElementById("scanLocationBtn");
  const closeScannerBtn = document.getElementById("closeScannerBtn");
  const scannerBox = document.getElementById("scannerBox");
  const scannerVideo = document.getElementById("scannerVideo");

  let currentTask = null;
  let suggestedLocations = [];
  let activeScanTarget = null;

  const urlParams = new URLSearchParams(window.location.search);
  const palletFromUrl = urlParams.get("pallet_id");

  if (palletInput) {
    palletInput.focus();
  }

  if (palletFromUrl && palletInput) {
    palletInput.value = palletFromUrl;
    setTimeout(loadTask, 300);
  }

  function showAlert(message) {
    alert(message);
  }

  function resetLocationStatus() {
    if (!locationStatus) return;

    locationStatus.classList.add("d-none");
    locationStatus.classList.remove(
      "alert-success",
      "alert-warning",
      "alert-danger"
    );
    locationStatus.innerHTML = "";
  }

  function showLocationStatus(type, message) {
    if (!locationStatus) return;

    locationStatus.classList.remove(
      "d-none",
      "alert-success",
      "alert-warning",
      "alert-danger"
    );

    locationStatus.classList.add(type);
    locationStatus.innerHTML = message;
  }

  function resetScreen() {
    currentTask = null;
    suggestedLocations = [];

    if (palletInput) palletInput.value = "";
    if (locationInput) locationInput.value = "";
    if (qtyInput) qtyInput.value = "";

    if (taskBox) taskBox.classList.add("d-none");
    if (suggestBox) suggestBox.innerHTML = "";

    resetLocationStatus();

    if (confirmBtn) {
      confirmBtn.disabled = false;
      confirmBtn.innerText = "XÁC NHẬN CẤT HÀNG";
    }

    if (palletInput) palletInput.focus();
  }

  async function loadTask() {
    const pallet = palletInput.value.trim();

    if (!pallet) {
      showAlert("Vui lòng quét hoặc nhập mã PA.");
      palletInput.focus();
      return;
    }

    try {
      if (loadBtn) {
        loadBtn.disabled = true;
        loadBtn.innerText = "ĐANG TÌM...";
      }

      const res = await fetch(
        "/api/putaway/pallet/" + encodeURIComponent(pallet)
      );

      const data = await res.json();

      if (!data.ok) {
        showAlert(data.error || "Không tìm thấy nhiệm vụ cất hàng.");
        return;
      }

      currentTask = data.data;

      document.getElementById("po_no").innerText = currentTask.po_no || "";
      document.getElementById("pa").innerText = currentTask.pallet_id || "";
      document.getElementById("sku").innerText = currentTask.sku || "";
      document.getElementById("barcode").innerText = currentTask.barcode || "";
      document.getElementById("qty").innerText =
        currentTask.qty_remain_putaway || 0;

      qtyInput.value = currentTask.qty_remain_putaway || 0;

      suggestedLocations = [];
      suggestBox.innerHTML = "";

      const suggestions =
        currentTask.suggested_locations ||
        currentTask.suggested_aisles ||
        [];

      if (!suggestions || suggestions.length === 0) {
        suggestBox.innerHTML = `
          <div class="alert alert-warning">
            ⚠ SKU chưa có vị trí gợi ý.<br>
            Vui lòng quét vị trí thực tế.
          </div>
        `;
      } else {
        suggestions.forEach(function (x) {
          const locationId = (x.location_id || x.aisle || "").toUpperCase();

          if (locationId) {
            suggestedLocations.push(locationId);
          }

          suggestBox.innerHTML += `
            <div class="alert alert-success mb-2">
              📍 ${locationId || "Vị trí gợi ý"}
            </div>
          `;
        });
      }

      taskBox.classList.remove("d-none");
      resetLocationStatus();
      locationInput.focus();
    } catch (err) {
      showAlert(err.message || "Lỗi kết nối server.");
    } finally {
      if (loadBtn) {
        loadBtn.disabled = false;
        loadBtn.innerText = "TÌM PA";
      }
    }
  }

  function validateLocation() {
    const location = locationInput.value.trim().toUpperCase();

    if (!location) return;

    if (suggestedLocations.includes(location)) {
      showLocationStatus("alert-success", "🟢 Vị trí gợi ý");
    } else {
      showLocationStatus(
        "alert-warning",
        "🟡 Vị trí ngoài gợi ý<br>Hệ thống sẽ kiểm tra khi xác nhận."
      );
    }
  }

  async function confirmPutaway() {
    if (!currentTask) {
      showAlert("Chưa load PA.");
      return;
    }

    const locationId = locationInput.value.trim();
    const qtyPutaway = qtyInput.value.trim();

    if (!locationId) {
      showAlert("Vui lòng quét hoặc nhập vị trí.");
      locationInput.focus();
      return;
    }

    if (!qtyPutaway || Number(qtyPutaway) <= 0) {
      showAlert("Số lượng cất hàng không hợp lệ.");
      qtyInput.focus();
      return;
    }

    const formData = new FormData();
    formData.append("queue_id", currentTask.queue_id);
    formData.append("location_id", locationId);
    formData.append("qty_putaway", qtyPutaway);

    try {
      confirmBtn.disabled = true;
      confirmBtn.innerText = "ĐANG LƯU...";

      const res = await fetch("/api/putaway/confirm", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!data.ok) {
        showAlert(data.error || "Cất hàng lỗi.");
        confirmBtn.disabled = false;
        confirmBtn.innerText = "XÁC NHẬN CẤT HÀNG";
        return;
      }

      showAlert("Cất hàng thành công.");
      resetScreen();
    } catch (err) {
      showAlert(err.message || "Lỗi kết nối server.");
      confirmBtn.disabled = false;
      confirmBtn.innerText = "XÁC NHẬN CẤT HÀNG";
    }
  }

  function openScannerFor(target) {
    activeScanTarget = target;

    if (typeof openZxingScanner !== "function") {
      showAlert("Chưa tải được thư viện quét mã.");
      return;
    }

    const targetInput = target === "PALLET" ? palletInput : locationInput;

    openZxingScanner({
      targetInput: targetInput,
      scannerBox: scannerBox,
      videoElement: scannerVideo,
      resultBox: null,
      afterScan: function (text) {
        if (activeScanTarget === "PALLET") {
          palletInput.value = text.trim().toUpperCase();
          loadTask();
        } else if (activeScanTarget === "LOCATION") {
          locationInput.value = text.trim().toUpperCase();
          validateLocation();
          qtyInput.focus();
        }
      },
    });
  }

  if (loadBtn) {
    loadBtn.addEventListener("click", loadTask);
  }

  if (confirmBtn) {
    confirmBtn.addEventListener("click", confirmPutaway);
  }

  if (palletInput) {
    palletInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        loadTask();
      }
    });
  }

  if (locationInput) {
    locationInput.addEventListener("blur", validateLocation);

    locationInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        qtyInput.focus();
      }
    });
  }

  if (scanPalletBtn) {
    scanPalletBtn.addEventListener("click", function () {
      openScannerFor("PALLET");
    });
  }

  if (scanLocationBtn) {
    scanLocationBtn.addEventListener("click", function () {
      openScannerFor("LOCATION");
    });
  }

  if (closeScannerBtn) {
    closeScannerBtn.addEventListener("click", function () {
      if (typeof closeZxingScanner === "function") {
        closeZxingScanner();
      }
    });
  }
});