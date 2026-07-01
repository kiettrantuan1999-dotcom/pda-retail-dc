(function () {
  function toast(message, tone) {
    const toastEl = document.getElementById('appToast');
    const body = document.getElementById('toastBody');
    if (!toastEl || !body || !window.bootstrap) return;
    body.textContent = message;
    toastEl.classList.remove('text-bg-dark', 'text-bg-success', 'text-bg-danger', 'text-bg-warning');
    toastEl.classList.add(tone === 'success' ? 'text-bg-success' : tone === 'danger' ? 'text-bg-danger' : tone === 'warning' ? 'text-bg-warning' : 'text-bg-dark');
    bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 1600 }).show();
  }

  function beep(type) {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = type === 'error' ? 220 : 880;
      gain.gain.value = type === 'error' ? 0.10 : 0.06;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      setTimeout(function () {
        osc.stop();
        ctx.close();
      }, type === 'error' ? 260 : 90);
    } catch (e) {}
  }

  window.WESUI = { toast: toast, beep: beep };

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.scan-input, input[autofocus], #do_no, #staging_do_no').forEach(function (el) {
      el.addEventListener('change', function () {
        el.classList.remove('scan-focus-pulse');
        void el.offsetWidth;
        el.classList.add('scan-focus-pulse');
      });
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') beep('success');
      });
    });

    document.querySelectorAll('tbody tr').forEach(function (tr) {
      tr.addEventListener('click', function () {
        tr.classList.remove('wes-row-flash');
        void tr.offsetWidth;
        tr.classList.add('wes-row-flash');
      });
    });
  });
})();
