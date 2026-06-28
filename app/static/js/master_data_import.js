document.addEventListener("DOMContentLoaded", function () {
  const resultBox = document.getElementById("resultBox");

  function showResult(ok, msg) {
    if (!resultBox) {
      alert(msg);
      return;
    }

    resultBox.classList.remove("d-none", "alert-success", "alert-danger", "alert-info");
    resultBox.classList.add(ok ? "alert-success" : "alert-danger");
    resultBox.innerText = msg;
  }

  async function uploadFile(url, fileInputId) {
    const fileInput = document.getElementById(fileInputId);

    if (!fileInput) {
      showResult(false, `Không tìm thấy input file: ${fileInputId}`);
      return;
    }

    const file = fileInput.files[0];

    if (!file) {
      showResult(false, "Vui lòng chọn file Excel.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    showResult(true, "Đang nhập dữ liệu...");

    try {
      const res = await fetch(url, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!data.ok) {
        showResult(false, data.error || "Nhập dữ liệu lỗi.");
        return;
      }

      const d = data.data || {};
      showResult(
        true,
        `Nhập thành công: ${d.imported_rows || 0} dòng | Thêm mới: ${d.inserted_rows || 0} | Cập nhật: ${d.updated_rows || 0} | Bỏ qua: ${d.skipped_rows || 0} | Số DO: ${d.so_do || 0} | Số phiếu: ${d.so_phieu_lay_hang || 0}`
      );
    } catch (err) {
      showResult(false, err.message || "Lỗi kết nối server.");
    }
  }

  function bindClick(buttonId, handler) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    btn.addEventListener("click", handler);
  }

  bindClick("importProductBtn", function () {
    uploadFile("/api/master-data/import/product-master", "productFile");
  });

  bindClick("importSkuBtn", function () {
    uploadFile("/api/master-data/import/sku-master", "skuFile");
  });

  bindClick("importLocationBtn", function () {
    uploadFile("/api/master-data/import/location-master", "locationFile");
  });

  bindClick("importCategoryBtn", function () {
    const modeEl = document.getElementById("categoryMode");
    const mode = modeEl ? modeEl.value : "upsert";

    if (mode === "replace") {
      const ok = confirm("Replace sẽ xóa dữ liệu cũ. Tiếp tục?");
      if (!ok) return;
    }

    uploadFile(`/api/master-data/import/category-aisle?mode=${mode}`, "categoryFile");
  });

  bindClick("importPoBtn", function () {
    uploadFile("/api/master-data/import/po-detail", "poFile");
  });

  bindClick("importDoBtn", function () {
    uploadFile("/api/master-data/import/do-detail", "doFile");
  });
});