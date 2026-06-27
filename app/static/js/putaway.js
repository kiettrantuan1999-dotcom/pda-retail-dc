document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("putawayForm");
  const locationInput = document.getElementById("location_id");
  const qtyInput = document.getElementById("qty_putaway");

  const resultBox = document.getElementById("resultBox");
  const successBox = document.getElementById("successBox");

  const scannerBox = document.getElementById("scannerBox");
  const scanLocationBtn = document.getElementById("scanLocationBtn");
  const closeScannerBtn = document.getElementById("closeScannerBtn");

  const successLocation = document.getElementById("successLocation");
  const successQty = document.getElementById("successQty");

  let html5QrCode = null;
  let isScannerRunning = false;

  if (locationInput) {
    locationInput.focus();
  }

  function showMessage(type, message) {
    if (!resultBox) return;

    resultBox.classList.remove(
      "d-none",
      "alert-success",
      "alert-danger",
      "alert-info"
    );

    resultBox.classList.add(type);
    resultBox.innerText = message;
  }

  async function stopScanner() {
    if (html5QrCode && isScannerRunning) {
      await html5QrCode.stop();
      isScannerRunning = false;
    }

    if (scannerBox) {
      scannerBox.classList.add("d-none");
    }
  }

  if (scanLocationBtn) {
    scanLocationBtn.addEventListener("click", async function () {
      if (!scannerBox) return;

      scannerBox.classList.remove("d-none");

      html5QrCode = new Html5Qrcode("reader");

      try {
        await html5QrCode.start(
          { facingMode: "environment" },
          {
            fps: 10,
            qrbox: { width: 250, height: 250 },
          },
          async function (decodedText) {
            locationInput.value = decodedText.trim();
            await stopScanner();

            if (qtyInput) {
              qtyInput.focus();
            }
          }
        );

        isScannerRunning = true;
      } catch (err) {
        showMessage("alert-danger", "Không mở được camera.");
      }
    });
  }

  if (closeScannerBtn) {
    closeScannerBtn.addEventListener("click", async function () {
      await stopScanner();
    });
  }

  if (!form) return;

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const locationValue = locationInput.value.trim();
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

    showMessage("alert-info", "Đang xử lý cất hàng...");

    const formData = new FormData(form);

    try {
      const response = await fetch("/api/putaway/confirm", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.ok) {
        resultBox.classList.add("d-none");
        form.classList.add("d-none");

        if (successLocation) {
          successLocation.innerText = locationValue;
        }

        if (successQty) {
          successQty.innerText = qtyValue;
        }

        if (successBox) {
          successBox.classList.remove("d-none");
        }
      } else {
        showMessage("alert-danger", data.error || "Cất hàng thất bại.");
      }
    } catch (err) {
      showMessage("alert-danger", "Lỗi kết nối server.");
    }
  });
});