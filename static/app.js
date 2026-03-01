/* FireBird Viewer - client-side utilities */

/* Auto-dismiss toast notifications after 4 seconds */
document.addEventListener('htmx:afterSwap', function() {
    const container = document.getElementById('toast-container');
    if (container && container.children.length > 0) {
        const alerts = container.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            setTimeout(function() {
                alert.parentElement?.remove();
            }, 4000);
        });
    }
});

/* ------------------------------------------------------------------ */
/* Custom DaisyUI confirm dialog instead of native window.confirm()   */
/* ------------------------------------------------------------------ */

(function() {
    // Ensure modal element exists in the DOM
    function ensureModal() {
        if (document.getElementById('confirm-modal')) return;
        document.body.insertAdjacentHTML('beforeend', `
            <dialog id="confirm-modal" class="modal">
              <div class="modal-box">
                <h3 class="font-bold text-lg" id="confirm-modal-title">Confirm</h3>
                <p class="py-4" id="confirm-modal-message"></p>
                <div class="modal-action">
                  <button class="btn btn-ghost" id="confirm-modal-cancel">Cancel</button>
                  <button class="btn btn-error" id="confirm-modal-ok">Delete</button>
                </div>
              </div>
              <form method="dialog" class="modal-backdrop"><button>close</button></form>
            </dialog>
        `);
    }

    // Intercept htmx:confirm to show DaisyUI modal
    document.addEventListener('htmx:confirm', function(e) {
        // Only intercept elements that have hx-confirm
        if (!e.detail.question) return;

        e.preventDefault();
        ensureModal();

        const modal = document.getElementById('confirm-modal');
        const msgEl = document.getElementById('confirm-modal-message');
        const okBtn = document.getElementById('confirm-modal-ok');
        const cancelBtn = document.getElementById('confirm-modal-cancel');

        msgEl.textContent = e.detail.question;
        modal.showModal();

        // Clean up previous listeners
        const newOk = okBtn.cloneNode(true);
        const newCancel = cancelBtn.cloneNode(true);
        okBtn.parentNode.replaceChild(newOk, okBtn);
        cancelBtn.parentNode.replaceChild(newCancel, cancelBtn);

        newOk.addEventListener('click', function() {
            modal.close();
            e.detail.issueRequest(true);
        }, { once: true });

        newCancel.addEventListener('click', function() {
            modal.close();
        }, { once: true });
    });
})();
