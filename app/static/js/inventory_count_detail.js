document.addEventListener("DOMContentLoaded", function () {
  const approveBtn = document.getElementById("approveBtn");

  if (!approveBtn) return;

  approveBtn.addEventListener("click", async function () {
    const countNo = approveBtn.dataset.countNo;
    const okConfirm = confirm("Duyệt kiểm kê sẽ cập nhật tồn hệ thống theo số lượng thực tế. Tiếp tục?");

    if (!okConfirm) return;

    const res = await fetch(`/api/inventory/counts/${encodeURIComponent(countNo)}/approve`, {
      method: "POST",
    });
    const data = await res.json();

    if (!data.ok) {
      showToast(data.error || "Không duyệt được kiểm kê", false);
      return;
    }

    showToast("Đã duyệt kiểm kê và cập nhật tồn", true);
    setTimeout(() => window.location.reload(), 800);
  });
});
