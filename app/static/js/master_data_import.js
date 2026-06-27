document.addEventListener("DOMContentLoaded", function () {
  const resultBox = document.getElementById("resultBox");

  function showResult(ok, msg) {
    if (!resultBox) return;

    resultBox.classList.remove("d-none", "alert-success", "alert-danger");
    resultBox.classList.add(ok ? "alert-success" : "alert-danger");
    resultBox.innerText = msg;
  }

  async function uploadFile(url, fileInput) {
    const file = fileInput.files[0];

    if (!file) {
      showResult(false, "Vui lòng chọn file Excel.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(url, {
      method: "POST",
      body: formData
    });

    const data = await res.json();

    if (data.ok) {
      const d = data.data || {};
      showResult(
        true,
        `Import thành công: ${d.imported_rows || 0} dòng | Thêm mới: ${d.inserted_rows || 0} | Cập nhật: ${d.updated_rows || 0} | Bỏ qua: ${d.skipped_rows || 0}`
      );
    } else {
      showResult(false, data.error || "Import lỗi.");
    }
  }

  const importProductBtn = document.getElementById("importProductBtn");
  if (importProductBtn) {
    importProductBtn.addEventListener("click", function () {
      uploadFile(
        "/api/master-data/import/product-master",
        document.getElementById("productFile")
      );
    });
  }

  const importSkuBtn = document.getElementById("importSkuBtn");
  if (importSkuBtn) {
    importSkuBtn.addEventListener("click", function () {
      uploadFile(
        "/api/master-data/import/sku-master",
        document.getElementById("skuFile")
      );
    });
  }

  const importCategoryBtn = document.getElementById("importCategoryBtn");
  if (importCategoryBtn) {
    importCategoryBtn.addEventListener("click", function () {
      const mode = document.getElementById("categoryMode").value;

      if (mode === "replace") {
        const ok = confirm("Replace sẽ xóa toàn bộ Category Aisle hiện tại. Tiếp tục?");
        if (!ok) return;
      }

      uploadFile(
        `/api/master-data/import/category-aisle?mode=${mode}`,
        document.getElementById("categoryFile")
      );
    });
  }

  const importPoBtn = document.getElementById("importPoBtn");
  if (importPoBtn) {
    importPoBtn.addEventListener("click", function () {
      uploadFile(
        "/api/master-data/import/po-detail",
        document.getElementById("poFile")
      );
    });
  }
});