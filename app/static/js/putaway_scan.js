document.addEventListener("DOMContentLoaded", function () {

    const palletInput = document.getElementById("pallet_id");
    const locationInput = document.getElementById("location_id");
    const qtyInput = document.getElementById("qty_putaway");

    const taskBox = document.getElementById("taskBox");
    const suggestBox = document.getElementById("locationSuggest");
    const locationStatus = document.getElementById("locationStatus");

    const loadBtn = document.getElementById("loadBtn");

    let currentTask = null;
    let suggestedLocations = [];

    loadBtn.addEventListener("click", loadTask);

    palletInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            loadTask();
        }
    });

    locationInput.addEventListener("blur", validateLocation);

    async function loadTask() {

        const pallet = palletInput.value.trim();

        if (!pallet) {
            alert("Vui lòng scan PA");
            return;
        }

        try {

            const res = await fetch(
                "/api/putaway/pallet/" + encodeURIComponent(pallet)
            );

            const data = await res.json();

            if (!data.ok) {
                alert(data.error);
                return;
            }

            currentTask = data.data;

            document.getElementById("po_no").innerText = currentTask.po_no;
            document.getElementById("pa").innerText = currentTask.pallet_id;
            document.getElementById("sku").innerText = currentTask.sku;
            document.getElementById("barcode").innerText = currentTask.barcode;
            document.getElementById("qty").innerText = currentTask.qty_remain_putaway;

            qtyInput.value = currentTask.qty_remain_putaway;

            suggestedLocations = [];

            suggestBox.innerHTML = "";

            if (currentTask.suggested_locations.length === 0) {

                suggestBox.innerHTML = `
                    <div class="alert alert-warning">
                        ⚠ SKU chưa có vị trí gợi ý.<br>
                        Vui lòng scan vị trí thực tế.
                    </div>
                `;

            } else {

                currentTask.suggested_locations.forEach(function (x) {

                    suggestedLocations.push(
                        x.location_id.toUpperCase()
                    );

                    suggestBox.innerHTML += `
                        <div class="alert alert-success mb-2">
                            📍 ${x.location_id}
                        </div>
                    `;

                });

            }

            taskBox.classList.remove("d-none");

            locationInput.focus();

        }

        catch (err) {

            alert(err);

        }

    }

    function validateLocation() {

        const location = locationInput.value.trim().toUpperCase();

        if (location === "")
            return;

        locationStatus.classList.remove(
            "d-none",
            "alert-success",
            "alert-warning",
            "alert-danger"
        );

        if (suggestedLocations.includes(location)) {

            locationStatus.classList.add("alert-success");

            locationStatus.innerHTML =
                "🟢 Vị trí gợi ý";

        }

        else {

            locationStatus.classList.add("alert-warning");

            locationStatus.innerHTML =
                "🟡 Vị trí ngoài gợi ý<br>Hệ thống sẽ kiểm tra khi xác nhận.";

        }

    }
const confirmBtn = document.getElementById("confirmBtn");

confirmBtn.addEventListener("click", confirmPutaway);

async function confirmPutaway() {
    if (!currentTask) {
        alert("Chưa load PA");
        return;
    }

    const locationId = locationInput.value.trim();
    const qtyPutaway = qtyInput.value.trim();

    if (!locationId) {
        alert("Vui lòng scan vị trí");
        return;
    }

    if (!qtyPutaway || Number(qtyPutaway) <= 0) {
        alert("Số lượng Put Away không hợp lệ");
        return;
    }

    const formData = new FormData();
    formData.append("queue_id", currentTask.queue_id);
    formData.append("location_id", locationId);
    formData.append("qty_putaway", qtyPutaway);

    try {
        confirmBtn.disabled = true;
        confirmBtn.innerText = "ĐANG LƯU...";

        const res = await fetch("/api/putaway/confirm", {
            method: "POST",
            body: formData
        });

        const data = await res.json();

        if (!data.ok) {
            alert(data.error || "Put Away lỗi");
            confirmBtn.disabled = false;
            confirmBtn.innerText = "XÁC NHẬN PUT AWAY";
            return;
        }

        alert("Put Away thành công");

        // Reset về màn scan PA
        currentTask = null;
        suggestedLocations = [];

        palletInput.value = "";
        locationInput.value = "";
        qtyInput.value = "";

        taskBox.classList.add("d-none");
        locationStatus.classList.add("d-none");

        confirmBtn.disabled = false;
        confirmBtn.innerText = "XÁC NHẬN PUT AWAY";

        palletInput.focus();

    } catch (err) {
        alert(err.message);
        confirmBtn.disabled = false;
        confirmBtn.innerText = "XÁC NHẬN PUT AWAY";
    }
}
});