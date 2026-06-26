document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("grForm");

  const poInput = document.getElementById("po_no");
  const barcodeInput = document.getElementById("barcode");
  const palletInput = document.getElementById("pallet_id");
  const qtyInput = document.getElementById("qty_gr");

  const resultBox = document.getElementById("resultBox");
  const resultTitle = document.getElementById("resultTitle");
  const resultText = document.getElementById("resultText");

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