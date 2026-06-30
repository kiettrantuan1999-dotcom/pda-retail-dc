document.addEventListener("DOMContentLoaded", function () {
  const taskList = document.getElementById("taskList");
  const emptyBox = document.getElementById("emptyBox");
  const summaryBox = document.getElementById("summaryBox");
  const searchInput = document.getElementById("searchInput");
  const refreshBtn = document.getElementById("refreshBtn");

  let allTasks = [];

  loadTasks();

  refreshBtn.addEventListener("click", loadTasks);

  searchInput.addEventListener("input", function () {
    renderTasks();
  });

  async function loadTasks() {
    taskList.innerHTML = "";
    emptyBox.classList.add("d-none");
    summaryBox.classList.add("d-none");

    try {
      const res = await fetch("/api/putaway/tasks");
      const data = await res.json();

      if (!data.ok) {
        emptyBox.classList.remove("d-none");
        emptyBox.innerText = data.error || "Không tải được task.";
        return;
      }

      allTasks = data.data.rows || [];
      renderTasks();

    } catch (err) {
      emptyBox.classList.remove("d-none");
      emptyBox.innerText = err.message;
    }
  }

  function renderTasks() {
    const q = searchInput.value.trim().toUpperCase();

    const rows = allTasks.filter(function (x) {
      const text = [
        x.pallet_id,
        x.po_no,
        x.sku,
        x.barcode,
        x.flow_status
      ].join(" ").toUpperCase();

      return text.includes(q);
    });

    taskList.innerHTML = "";

    if (rows.length === 0) {
      emptyBox.classList.remove("d-none");
    } else {
      emptyBox.classList.add("d-none");
    }

    const totalQty = rows.reduce(function (sum, x) {
      return sum + Number(x.qty_remain_putaway || 0);
    }, 0);

    const waitCount = rows.filter(x => x.flow_status === "WAIT_PUTAWAY").length;
    const partialCount = rows.filter(x => x.flow_status === "PARTIAL").length;

    summaryBox.classList.remove("d-none");
    summaryBox.innerHTML = `
      <b>Tổng task:</b> ${rows.length}
      &nbsp; | &nbsp;
      <b>WAIT:</b> ${waitCount}
      &nbsp; | &nbsp;
      <b>PARTIAL:</b> ${partialCount}
      &nbsp; | &nbsp;
      <b>Qty còn:</b> ${totalQty}
    `;

    rows.forEach(function (x) {
      const badgeClass = x.flow_status === "PARTIAL"
        ? "bg-warning text-dark"
        : "bg-primary";

      const statusText = x.flow_status === "PARTIAL"
        ? "PARTIAL"
        : "WAIT";

      const card = document.createElement("div");
      card.className = "card shadow-sm mb-3";

      card.innerHTML = `
        <div class="card-body">

          <div class="d-flex justify-content-between align-items-start mb-2">
            <div>
              <div class="fw-bold fs-5">${x.pallet_id}</div>
              <div class="text-muted small">PO: ${x.po_no || ""}</div>
            </div>

            <span class="badge ${badgeClass}">
              ${statusText}
            </span>
          </div>

          <div class="row small mb-3">
            <div class="col-6">
              <b>SKU</b><br>
              ${x.sku || ""}
            </div>

            <div class="col-6">
              <b>Barcode</b><br>
              ${x.barcode || ""}
            </div>

            <div class="col-4 mt-2">
              <b>GR</b><br>
              ${x.qty_gr ?? 0}
            </div>

            <div class="col-4 mt-2">
              <b>Đã PA</b><br>
              ${x.qty_putaway ?? 0}
            </div>

            <div class="col-4 mt-2">
              <b>Còn</b><br>
              ${x.qty_remain_putaway ?? 0}
            </div>
          </div>

          <button
            class="btn btn-success w-100 open-task-btn"
            data-pallet="${x.pallet_id}">
            MỞ TASK
          </button>

        </div>
      `;

      taskList.appendChild(card);
    });

    document.querySelectorAll(".open-task-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const pallet = btn.getAttribute("data-pallet");
        window.location.href = "/putaway/" + encodeURIComponent(pallet);
      });
    });
  }
});