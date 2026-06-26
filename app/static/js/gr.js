document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("grForm");

  const poInput = document.getElementById("po_no");
  const barcodeInput = document.getElementById("barcode");
  const palletInput = document.getElementById("pallet_id");
  const qtyInput = document.getElementById("qty_gr");

  const resultBox = document.getElementById("resultBox");
  const resultTitle = document.getElementById("resultTitle");
  const resultText = document.getElementById("resultText");

  const scannerBox = document.getElementById("scannerBox");
  const closeScannerBtn = document.getElementById("closeScannerBtn");

  let html5QrCode = null;
  let activeTargetInput = null;
  let isStartingScanner = false;

  poInput.focus();

  function moveNextOnEnter(current, next) {
    current.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        next.focus();
      }
    });
  }

  moveNextOnEnter(poInput, barcodeInput);
  moveNextOnEnter(barcodeInput, palletInput);
  moveNextOnEnter(palletInput, qtyInput);

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
      oscillator.stop(audioCtx.currentTime + 0.12);
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

  async function stopScanner() {
    if (html5QrCode) {
      try {
        const state = html5QrCode.getState();

        // 2 = SCANNING in html5-qrcode
        if (state === 2) {
          await html5QrCode.stop();
        }

        await html5QrCode.clear();
      } catch (e) {
        console.log("Stop scanner warning:", e);
      }

      html5QrCode = null;
    }

    scannerBox.classList.add("d-none");
    activeTargetInput = null;
    isStartingScanner = false;
  }

  function getNextInput(targetInput) {
  if (targetInput.id === "po_no") return barcodeInput;
  if (targetInput.id === "barcode") return palletInput;
  if (targetInput.id === "pallet_id") return qtyInput;
  return null;
  }

  async function getBestCameraId() {
    const cameras = await Html5Qrcode.getCameras();

    if (!cameras || cameras.length === 0) {
      throw new Error("Không tìm thấy camera trên thiết bị");
    }

    // Ưu tiên camera sau nếu tên có các keyword phổ biến
    const backCamera = cameras.find(function (camera) {
      const label = (camera.label || "").toLowerCase();
      return (
        label.includes("back") ||
        label.includes("rear") ||
        label.includes("environment") ||
        label.includes("camera 0")
      );
    });

    return backCamera ? backCamera.id : cameras[cameras.length - 1].id;
  }

  async function startScanner(targetInputId) {
    if (isStartingScanner) return;

    isStartingScanner = true;
    activeTargetInput = document.getElementById(targetInputId);

    scannerBox.classList.remove("d-none");
    resultBox.classList.add("d-none");

    if (html5QrCode) {
      await stopScanner();
      scannerBox.classList.remove("d-none");
    }

    html5QrCode = new Html5Qrcode("reader", {
      verbose: false
    });

    const config = {
      fps: 10,
      qrbox: function (viewfinderWidth, viewfinderHeight) {
        const minEdge = Math.min(viewfinderWidth, viewfinderHeight);
        const qrboxSize = Math.floor(minEdge * 0.75);
        return {
          width: qrboxSize,
          height: qrboxSize
        };
      },
      aspectRatio: 1.777778
    };

    try {
      const cameraId = await getBestCameraId();

      await html5QrCode.start(
        cameraId,
        config,
        async function onScanSuccess(decodedText) {
          if (!activeTargetInput) return;

          activeTargetInput.value = decodedText;
          beep();

          const nextInput = getNextInput(activeTargetInput);

          await stopScanner();

          if (nextInput) {
            setTimeout(function () {
              nextInput.focus();
            }, 200);
          }
        },
        function onScanFailure() {
          // ignore scan failure
        }
      );

      isStartingScanner = false;

    } catch (err) {
      console.error("Camera error:", err);

      await stopScanner();

      showError(
        "Không mở được camera. Hãy mở bằng Safari/Chrome thật, cấp quyền Camera, và đảm bảo đang dùng HTTPS."
      );
    }
  }

  document.querySelectorAll(".scan-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const target = btn.getAttribute("data-target");
      startScanner(target);
    });
  });

  closeScannerBtn.addEventListener("click", function () {
    stopScanner();
  });

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const formData = new FormData();
    formData.append("po_no", poInput.value.trim());
    formData.append("barcode", barcodeInput.value.trim());
    formData.append("pallet_id", palletInput.value.trim());
    formData.append("qty_gr", qtyInput.value.trim());

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
          <div><b>Barcode:</b> ${data.data.barcode}</div>
          <div><b>Qty:</b> ${data.data.qty_gr}</div>
          <div><b>Status:</b> ${data.data.flow_status}</div>
        `;

        barcodeInput.value = "";
        palletInput.value = "";
        qtyInput.value = "";
        barcodeInput.focus();

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