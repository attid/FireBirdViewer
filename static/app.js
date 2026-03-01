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

    document.addEventListener('htmx:confirm', function(e) {
        if (!e.detail.question) return;
        e.preventDefault();
        ensureModal();

        const modal = document.getElementById('confirm-modal');
        const msgEl = document.getElementById('confirm-modal-message');
        const okBtn = document.getElementById('confirm-modal-ok');
        const cancelBtn = document.getElementById('confirm-modal-cancel');

        msgEl.textContent = e.detail.question;
        modal.showModal();

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

/* ------------------------------------------------------------------ */
/* Inline cell editing                                                */
/* Click cell -> input appears -> Enter saves, Esc cancels            */
/* ------------------------------------------------------------------ */

(function() {
    // Delegate click on editable cells (works after HTMX swaps)
    document.addEventListener('click', function(e) {
        const cell = e.target.closest('.editable-cell');
        if (!cell || cell.querySelector('input')) return; // already editing

        const dbKey = cell.dataset.dbKey;
        const column = cell.dataset.column;
        const tableName = cell.dataset.table;
        const rawValue = cell.dataset.value || '';

        // Remember original display text
        const originalText = cell.textContent;

        // Create input
        const input = document.createElement('input');
        input.type = 'text';
        input.value = rawValue;
        input.className = 'input input-bordered input-xs w-full';
        input.style.minWidth = '60px';

        // Replace cell content
        cell.textContent = '';
        cell.appendChild(input);
        input.focus();
        input.select();

        let settled = false;

        function cancel() {
            if (settled) return;
            settled = true;
            cell.textContent = originalText;
        }

        function save() {
            if (settled) return;
            settled = true;

            const newValue = input.value;
            // Show saving state
            cell.textContent = '...';
            cell.classList.add('opacity-50');

            fetch(`/object/table/${encodeURIComponent(tableName)}/row/${encodeURIComponent(dbKey)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ column: column, value: newValue }),
            })
            .then(function(resp) { return resp.json(); })
            .then(function(data) {
                cell.classList.remove('opacity-50');
                if (data.ok) {
                    const display = data.value != null ? String(data.value) : 'NULL';
                    cell.textContent = display;
                    cell.dataset.value = newValue;
                    // Update null styling
                    if (data.value == null) {
                        cell.classList.add('text-base-content/40', 'italic');
                    } else {
                        cell.classList.remove('text-base-content/40', 'italic');
                    }
                    // Brief green flash
                    cell.style.transition = 'background-color 0.3s';
                    cell.style.backgroundColor = 'rgba(0, 200, 80, 0.15)';
                    setTimeout(function() { cell.style.backgroundColor = ''; }, 800);
                } else {
                    cell.textContent = originalText;
                    // Brief red flash + show error
                    cell.style.transition = 'background-color 0.3s';
                    cell.style.backgroundColor = 'rgba(255, 0, 0, 0.15)';
                    setTimeout(function() { cell.style.backgroundColor = ''; }, 1500);
                    // Show error in a small tooltip
                    cell.title = data.error || 'Update failed';
                    setTimeout(function() { cell.title = ''; }, 5000);
                }
            })
            .catch(function() {
                cell.classList.remove('opacity-50');
                cell.textContent = originalText;
                cell.style.backgroundColor = 'rgba(255, 0, 0, 0.15)';
                setTimeout(function() { cell.style.backgroundColor = ''; }, 1500);
            });
        }

        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                save();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancel();
            }
        });

        input.addEventListener('blur', function() {
            // Small delay to allow click-away to register
            setTimeout(function() { cancel(); }, 150);
        });
    });
})();
