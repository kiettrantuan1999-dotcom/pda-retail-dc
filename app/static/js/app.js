function showToast(msg, ok=true){
  const el = document.getElementById("appToast");
  const body = document.getElementById("toastBody");
  if(!el || !body) return;
  body.innerText = msg;
  el.className = "toast " + (ok ? "text-bg-success" : "text-bg-danger");
  new bootstrap.Toast(el).show();
}
function focusFirst(){
  const x = document.querySelector("input[autofocus], .scan-input");
  if(x){ setTimeout(()=>x.focus(), 100); }
}
window.addEventListener("load", focusFirst);
