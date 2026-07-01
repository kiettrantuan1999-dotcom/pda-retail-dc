document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("stagingScanForm");
  const doInput = document.getElementById("staging_do_no");
  const scanBtn = document.getElementById("scanStagingBtn");
  const closeBtn = document.getElementById("closeStagingScannerBtn");
  const scannerBox = document.getElementById("stagingScannerBox");
  const scannerVideo = document.getElementById("stagingScannerVideo");
  const resultBox = document.getElementById("stagingResultBox");

  if (doInput) {
    doInput.focus();
    doInput.addEventListener("input", function () {
      doInput.value = doInput.value.trim().toUpperCase();
    });
    doInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        submitScan();
      }
    });
  }

  function showMessage(type, message) {
    if (!resultBox) return;
    resultBox.classList.remove("d-none", "alert-success", "alert-danger", "alert-info");
    resultBox.classList.add(type);
    resultBox.innerText = message;
  }

  function submitScan() {
    if (!form || !doInput) return;
    const code = doInput.value.trim().toUpperCase();
    if (!code) {
      showMessage("alert-danger", "Vui lòng quét hoặc nhập mã phiếu.");
      doInput.focus();
      return;
    }
    doInput.value = code;
    showMessage("alert-info", "Đang tải thông tin tập kết...");
    form.submit();
  }

  if (scanBtn) {
    scanBtn.addEventListener("click", function () {
      openZxingScanner({
        targetInput: doInput,
        scannerBox: scannerBox,
        videoElement: scannerVideo,
        resultBox: resultBox,
        afterScan: function (text) {
          doInput.value = text.trim().toUpperCase();
          submitScan();
        },
      });
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", function () {
      closeZxingScanner(true);
    });
  }
});
