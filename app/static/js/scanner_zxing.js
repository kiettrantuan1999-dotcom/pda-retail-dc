let zxingReader = null;
let zxingControls = null;
let zxingTargetInput = null;
let zxingAfterScan = null;
let zxingSuppressAutoOpenUntil = 0;

async function openZxingScanner(options) {
  if (Date.now() < zxingSuppressAutoOpenUntil) return;

  const targetInput = options.targetInput;
  const scannerBox = options.scannerBox;
  const videoElement = options.videoElement;
  const resultBox = options.resultBox || null;
  const afterScan = options.afterScan || null;

  zxingTargetInput = targetInput;
  zxingAfterScan = afterScan;

  if (!targetInput || !scannerBox || !videoElement) {
    alert("Thiếu cấu hình máy quét.");
    return;
  }

  scannerBox.classList.remove("d-none");

  if (!zxingReader) {
    zxingReader = new ZXingBrowser.BrowserMultiFormatReader();
  }

  try {
    zxingControls = await zxingReader.decodeFromVideoDevice(
      undefined,
      videoElement,
      function (result, error, controls) {
        if (result) {
          const text = result.getText().trim();

          zxingTargetInput.value = text;

          closeZxingScanner();

          if (typeof zxingAfterScan === "function") {
            zxingAfterScan(text);
          }
        }
      }
    );
  } catch (err) {
    if (resultBox) {
      resultBox.classList.remove("d-none", "alert-success", "alert-info");
      resultBox.classList.add("alert-danger");
      resultBox.innerText = "Không mở được camera.";
    } else {
      alert("Không mở được camera.");
    }
  }
}

function closeZxingScanner(restoreFocus) {
  const targetToRestore = zxingTargetInput;

  if (zxingControls) {
    zxingControls.stop();
    zxingControls = null;
  }

  const scannerBoxes = document.querySelectorAll(".scanner-box");
  scannerBoxes.forEach(function (box) {
    box.classList.add("d-none");
  });

  if (restoreFocus && targetToRestore) {
    zxingSuppressAutoOpenUntil = Date.now() + 1500;
    setTimeout(function () {
      targetToRestore.focus();
      if (targetToRestore.select) targetToRestore.select();
    }, 80);
  }

  zxingTargetInput = null;
  zxingAfterScan = null;
}