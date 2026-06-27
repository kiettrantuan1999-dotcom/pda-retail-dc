document.addEventListener("DOMContentLoaded", function () {
  const palletInput = document.getElementById("pallet_id");
  const findPalletBtn = document.getElementById("findPalletBtn");
  const resultBox = document.getElementById("resultBox");

  const scannerBox = document.getElementById("scannerBox");
  const scanPalletBtn = document.getElementById("scanPalletBtn");
  const closeScannerBtn = document.getElementById("closeScannerBtn");

  let html5QrCode = null;
  let isScannerRunning = false;

  if (palletInput) {
    palletInput.focus();
  }

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

  async function stopScanner() {
    if (html5QrCode && isScannerRunning) {
      await html5QrCode.stop();
      isScannerRunning = false;
    }

    scannerBox.classList.add("d-none");
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

      const queueId = data.data.queue_id;

      if (!queueId) {
        showMessage("alert-danger", "PA này chưa có nhiệm vụ cất hàng.");
        return;
      }

      window.location.href = "/putaway/" + queueId;
    } catch (err) {
      showMessage("alert-danger", "Lỗi kết nối server.");
    }
  }

  if (findPalletBtn) {
    findPalletBtn.addEventListener("click", findPallet);
  }

  if (palletInput) {
    palletInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        findPallet();
      }
    });
  }

  if (scanPalletBtn) {
    scanPalletBtn.addEventListener("click", async function () {
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
            palletInput.value = decodedText.trim().toUpperCase();
            await stopScanner();
            await findPallet();
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
});