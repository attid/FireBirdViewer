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

/* ------------------------------------------------------------------ */
/* Recent connections (localStorage)                                  */
/* Save database+user on successful connect, show list on form load   */
/* ------------------------------------------------------------------ */

(function() {
    var STORAGE_KEY = 'fbviewer_recent';
    var MAX_RECENT = 10;

    function getRecent() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
        } catch (e) {
            return [];
        }
    }

    function saveRecent(database, user) {
        var list = getRecent();
        // Remove duplicate
        list = list.filter(function(item) {
            return !(item.database === database && item.user === user);
        });
        // Add to front
        list.unshift({ database: database, user: user });
        // Trim
        if (list.length > MAX_RECENT) list = list.slice(0, MAX_RECENT);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    }

    function removeRecent(database, user) {
        var list = getRecent();
        list = list.filter(function(item) {
            return !(item.database === database && item.user === user);
        });
        localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    }

    function renderRecent() {
        var container = document.getElementById('recent-connections');
        if (!container) return;
        var list = getRecent();
        if (list.length === 0) return;

        var html = '<div class="divider text-xs text-base-content/40">Recent</div>';
        html += '<div class="flex flex-col gap-1">';
        list.forEach(function(item, idx) {
            html += '<div class="flex items-center gap-2 group">'
                + '<a href="#" class="recent-conn-item flex-1 text-sm'
                + ' link link-hover truncate" data-idx="' + idx + '">'
                + escapeHtml(item.database)
                + ' <span class="text-base-content/40">(' + escapeHtml(item.user) + ')</span>'
                + '</a>'
                + '<button class="recent-conn-del btn btn-ghost btn-xs'
                + ' opacity-0 group-hover:opacity-100" data-idx="' + idx
                + '" title="Remove">\u00d7</button>'
                + '</div>';
        });
        html += '</div>';
        container.innerHTML = html;
    }

    function escapeHtml(s) {
        var d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    // Fill form when clicking a recent connection
    document.addEventListener('click', function(e) {
        var item = e.target.closest('.recent-conn-item');
        if (item) {
            e.preventDefault();
            var idx = parseInt(item.dataset.idx, 10);
            var list = getRecent();
            if (list[idx]) {
                var dbInput = document.querySelector('input[name="database"]');
                var userInput = document.querySelector('input[name="user"]');
                var pwInput = document.querySelector('input[name="password"]');
                if (dbInput) dbInput.value = list[idx].database;
                if (userInput) userInput.value = list[idx].user;
                if (pwInput) { pwInput.value = ''; pwInput.focus(); }
            }
            return;
        }

        var del = e.target.closest('.recent-conn-del');
        if (del) {
            e.preventDefault();
            var didx = parseInt(del.dataset.idx, 10);
            var dlist = getRecent();
            if (dlist[didx]) {
                removeRecent(dlist[didx].database, dlist[didx].user);
                renderRecent();
            }
        }
    });

    // Save on successful connect (HTMX redirects to /dashboard)
    document.addEventListener('htmx:beforeSwap', function(e) {
        // If the connect form triggered a redirect to dashboard, save the connection
        if (e.detail.xhr && e.detail.xhr.responseURL &&
            e.detail.xhr.responseURL.indexOf('/dashboard') !== -1) {
            var dbInput = document.querySelector('input[name="database"]');
            var userInput = document.querySelector('input[name="user"]');
            if (dbInput && userInput && dbInput.value) {
                saveRecent(dbInput.value, userInput.value);
            }
        }
    });

    // Render on page load and after HTMX swaps
    document.addEventListener('DOMContentLoaded', renderRecent);
    document.addEventListener('htmx:afterSwap', renderRecent);
})();

/* ------------------------------------------------------------------ */
/* AI Assistant: settings in localStorage + form interception          */
/* ------------------------------------------------------------------ */

(function() {
    var AI_STORAGE_KEY = 'fbviewer_ai_settings';

    function getAiSettings() {
        try {
            return JSON.parse(localStorage.getItem(AI_STORAGE_KEY)) || {};
        } catch (e) {
            return {};
        }
    }

    // Load non-secret defaults from server env vars (AI_BASE_URL, AI_MODEL)
    // if localStorage is empty. API key is NEVER sent from the server —
    // it stays server-side and is used as a fallback in /ai/ask.
    function loadDefaultsIfEmpty() {
        var existing = getAiSettings();
        if (existing.base_url) return; // already configured
        fetch('/ai/defaults')
            .then(function(r) { return r.json(); })
            .then(function(defaults) {
                if (defaults.base_url) {
                    var settings = {
                        base_url: defaults.base_url,
                        api_key: '',  // never from server
                        model: defaults.model || '',
                        api_key_on_server: defaults.api_key_set || false
                    };
                    localStorage.setItem(AI_STORAGE_KEY, JSON.stringify(settings));
                    populateAiSettingsModal();
                }
            })
            .catch(function() { /* ignore */ });
    }

    // Called by the Settings modal "Save" button (window-scoped)
    window.__saveAiSettings = function() {
        var baseUrl = document.getElementById('ai-base-url');
        var apiKey = document.getElementById('ai-api-key');
        var model = document.getElementById('ai-model');
        var settings = {
            base_url: baseUrl ? baseUrl.value : '',
            api_key: apiKey ? apiKey.value : '',
            model: model ? model.value : ''
        };
        localStorage.setItem(AI_STORAGE_KEY, JSON.stringify(settings));
    };

    // Pre-fill settings modal inputs when it appears
    function populateAiSettingsModal() {
        var settings = getAiSettings();
        var baseUrl = document.getElementById('ai-base-url');
        var apiKey = document.getElementById('ai-api-key');
        var model = document.getElementById('ai-model');
        if (baseUrl && settings.base_url) baseUrl.value = settings.base_url;
        if (apiKey && settings.api_key) apiKey.value = settings.api_key;
        if (apiKey && !settings.api_key && settings.api_key_on_server) {
            apiKey.placeholder = '(set on server via AI_API_KEY)';
        }
        if (model && settings.model) model.value = settings.model;
    }

    // Inject AI settings + conversation history before HTMX sends the request
    document.addEventListener('htmx:configRequest', function(e) {
        var elt = e.detail.elt;
        var form = elt.closest('#ai-ask-form');
        if (!form) return;

        var settings = getAiSettings();
        e.detail.parameters['ai_base_url'] = settings.base_url || '';
        e.detail.parameters['ai_api_key'] = settings.api_key || '';
        e.detail.parameters['ai_model'] = settings.model || '';

        // Include conversation history (base64-encoded, stored in a hidden div)
        var historyEl = document.getElementById('ai-history-data');
        if (historyEl && historyEl.textContent.trim()) {
            e.detail.parameters['ai_history'] = historyEl.textContent.trim();
        }
    });

    // Clear input after successful submission and scroll chat to bottom
    document.addEventListener('htmx:afterSwap', function(e) {
        // Populate settings modal on any swap (in case it just appeared)
        populateAiSettingsModal();
        // Load env defaults when AI page first appears
        if (document.getElementById('ai-ask-form')) {
            loadDefaultsIfEmpty();
        }

        // Clear the question input after successful AI ask
        var input = document.getElementById('ai-question-input');
        if (input && e.detail.target && e.detail.target.id === 'ai-chat-messages') {
            input.value = '';
            // Scroll chat to bottom
            var chat = document.getElementById('ai-chat-messages');
            if (chat) {
                chat.scrollTop = chat.scrollHeight;
            }
        }
    });

    // Clear chat: reset messages and conversation history
    window.__clearAiChat = function() {
        var chat = document.getElementById('ai-chat-messages');
        if (chat) {
            chat.innerHTML =
                '<div class="p-4">'
                + '<p class="text-base-content/60 text-sm text-center">'
                + 'Ask questions about your database in natural language. '
                + 'I can query data, explain schemas, and suggest SQL.'
                + '</p></div>';
        }
        var history = document.getElementById('ai-history-data');
        if (history) {
            history.textContent = '';
        }
    };

    // Also populate on page load
    document.addEventListener('DOMContentLoaded', populateAiSettingsModal);
})();
