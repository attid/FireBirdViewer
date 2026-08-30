/* FireBird Viewer - client-side utilities */

function appUrl(path) {
    var rootMeta = document.querySelector('meta[name="app-root-path"]');
    var root = rootMeta ? rootMeta.getAttribute('content') || '' : '';
    if (!path.startsWith('/')) path = '/' + path;
    if (!root || root === '/') return path;
    return root.replace(/\/+$/, '') + path;
}

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
        if (!cell || cell.querySelector('.inline-cell-editor')) return;

        const dbKey = cell.dataset.dbKey;
        const column = cell.dataset.column;
        const columnType = cell.dataset.type || '';
        const tableName = cell.dataset.table;
        const rawValue = cell.dataset.value || '';
        const isBoolean = columnType.toUpperCase() === 'BOOLEAN';

        // Remember original display text
        const originalText = cell.textContent;
        const originalStyle = {
            backgroundColor: cell.style.backgroundColor,
            boxShadow: cell.style.boxShadow,
            position: cell.style.position,
        };

        let control;
        if (isBoolean) {
            control = document.createElement('select');
            control.className = 'select select-bordered select-xs w-full';
            ['TRUE', 'FALSE'].forEach(function(value) {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = value;
                control.appendChild(option);
            });
            control.value = rawValue.toLowerCase() === 'false' ? 'FALSE' : 'TRUE';
        } else {
            control = document.createElement('input');
            control.type = 'text';
            control.value = rawValue;
            control.className = 'input input-bordered input-xs w-full';
        }
        control.setAttribute('aria-label', `Edit ${column}`);
        control.style.fontFamily = 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';
        control.style.fontSize = '16px';
        control.style.minWidth = '0';
        control.style.width = '100%';

        const hint = document.createElement('div');
        hint.textContent = 'Enter save / Esc cancel';
        hint.style.fontSize = '10px';
        hint.style.lineHeight = '1';
        hint.style.marginTop = '3px';
        hint.style.opacity = '0.65';
        hint.style.whiteSpace = 'nowrap';

        const editor = document.createElement('div');
        const editorChars = Math.max(32, Math.min(String(rawValue).length + 4, 80));
        editor.className = 'inline-cell-editor';
        editor.style.fontFamily = control.style.fontFamily;
        editor.style.fontSize = control.style.fontSize;
        editor.style.width = `${editorChars}ch`;
        editor.style.maxWidth = 'min(80ch, 70vw)';
        editor.style.boxSizing = 'border-box';
        editor.style.padding = '2px';
        editor.style.border = '2px solid rgba(59, 130, 246, 0.65)';
        editor.style.boxShadow = 'inset 0 0 0 1px rgba(59, 130, 246, 0.35)';
        editor.appendChild(control);
        editor.appendChild(hint);

        // Replace cell content
        cell.textContent = '';
        cell.appendChild(editor);
        cell.style.position = 'relative';
        cell.style.backgroundColor = 'rgba(59, 130, 246, 0.08)';
        control.focus();
        if (control.tagName === 'INPUT') {
            control.setSelectionRange(0, 0);
        }

        let settled = false;

        function restoreEditStyle() {
            cell.style.backgroundColor = originalStyle.backgroundColor;
            cell.style.boxShadow = originalStyle.boxShadow;
            cell.style.position = originalStyle.position;
        }

        function cancel() {
            if (settled) return;
            settled = true;
            restoreEditStyle();
            cell.textContent = originalText;
        }

        function save() {
            if (settled) return;
            settled = true;

            const newValue = control.value;
            // Show saving state
            restoreEditStyle();
            cell.textContent = '...';
            cell.classList.add('opacity-50');

            fetch(appUrl(`/object/table/${encodeURIComponent(tableName)}/row/${encodeURIComponent(dbKey)}`), {
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

        control.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                save();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancel();
            }
        });

        if (isBoolean) {
            control.addEventListener('change', save);
        }

        control.addEventListener('blur', function() {
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
/* Sidebar object tree filter                                         */
/* ------------------------------------------------------------------ */

(function() {
    function applySidebarFilter() {
        var input = document.getElementById('sidebar-filter');
        if (!input) return;

        var query = input.value.trim().toLowerCase();
        var sections = document.querySelectorAll('[data-sidebar-section="true"]');

        sections.forEach(function(section) {
            var visibleCount = 0;
            var items = section.querySelectorAll('[data-sidebar-item="true"][data-filter-name]');

            items.forEach(function(item) {
                var name = item.dataset.filterName || '';
                var visible = !query || name.indexOf(query) !== -1;
                item.classList.toggle('hidden', !visible);
                if (visible) visibleCount += 1;
            });

            var summary = section.querySelector('[data-section-summary="true"]');
            var title = section.dataset.sectionTitle || '';
            var total = parseInt(section.dataset.sectionTotal || '0', 10);
            if (summary && title) {
                var count = query ? visibleCount : total;
                summary.textContent = title + ' (' + count + ')';
                summary.setAttribute('data-section-visible-count', String(count));
            }

            section.classList.toggle('hidden', Boolean(query) && visibleCount === 0);
        });
    }

    document.addEventListener('input', function(e) {
        if (e.target && e.target.id === 'sidebar-filter') {
            applySidebarFilter();
        }
    });

    document.addEventListener('DOMContentLoaded', applySidebarFilter);
    document.addEventListener('htmx:afterSwap', applySidebarFilter);
})();

/* ------------------------------------------------------------------ */
/* AI Assistant: server-managed and browser-relayed provider modes     */
/* ------------------------------------------------------------------ */

(function() {
    var AI_STORAGE_KEY = 'fbviewer_ai_settings';
    var sessionAiKey = '';

    function getAiSettings() {
        try {
            var settings = JSON.parse(localStorage.getItem(AI_STORAGE_KEY)) || {};
            if (!sessionAiKey && settings.remember_key && settings.api_key) {
                sessionAiKey = settings.api_key;
            }
            return settings;
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
        fetch(appUrl('/ai/defaults'))
            .then(function(r) { return r.json(); })
            .then(function(defaults) {
                if (defaults.base_url) {
                    var settings = {
                        base_url: defaults.base_url,
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
        var rememberKey = document.getElementById('ai-remember-key');
        sessionAiKey = apiKey ? apiKey.value.trim() : '';
        var settings = {
            base_url: baseUrl ? baseUrl.value.trim() : '',
            model: model ? model.value.trim() : '',
            remember_key: Boolean(rememberKey && rememberKey.checked)
        };
        if (settings.remember_key && sessionAiKey) settings.api_key = sessionAiKey;
        localStorage.setItem(AI_STORAGE_KEY, JSON.stringify(settings));
    };

    document.addEventListener('click', function(e) {
        if (!e.target || e.target.id !== 'ai-settings-save') return;
        window.__saveAiSettings();
        document.getElementById('ai-settings-modal').close();
    });

    // Pre-fill settings modal inputs when it appears
    function populateAiSettingsModal() {
        var settings = getAiSettings();
        var baseUrl = document.getElementById('ai-base-url');
        var apiKey = document.getElementById('ai-api-key');
        var model = document.getElementById('ai-model');
        var rememberKey = document.getElementById('ai-remember-key');
        if (baseUrl && settings.base_url) baseUrl.value = settings.base_url;
        if (apiKey && sessionAiKey) apiKey.value = sessionAiKey;
        if (apiKey && !sessionAiKey && settings.api_key_on_server) {
            apiKey.placeholder = '(set on server via AI_API_KEY)';
        }
        if (model && settings.model) model.value = settings.model;
        if (rememberKey) rememberKey.checked = Boolean(settings.remember_key);
    }

    // Server-managed mode receives only conversation state and execution context.
    document.addEventListener('htmx:configRequest', function(e) {
        var elt = e.detail.elt;
        var form = elt.closest('#ai-ask-form');
        if (!form) return;

        var historyEl = document.getElementById('ai-history-data');
        if (historyEl && historyEl.textContent.trim()) {
            e.detail.parameters['ai_history'] = historyEl.textContent.trim();
        }

        var contextEl = document.getElementById('ai-context-data');
        if (contextEl && contextEl.textContent.trim()) {
            e.detail.parameters['ai_context'] = contextEl.textContent.trim();
        }
    });

    function providerRequestBody(request) {
        var messages = request.messages.map(function(message) {
            var item = { role: message.role, content: message.content || '' };
            if (message.tool_calls && message.tool_calls.length) {
                item.tool_calls = message.tool_calls.map(function(call) {
                    return {
                        id: call.id,
                        type: 'function',
                        function: { name: call.name, arguments: call.arguments }
                    };
                });
            }
            if (message.tool_call_id) item.tool_call_id = message.tool_call_id;
            return item;
        });
        var body = { model: request.model, messages: messages };
        if (request.tools && request.tools.length) {
            body.tools = request.tools.map(function(tool) {
                return {
                    type: 'function',
                    function: {
                        name: tool.name,
                        description: tool.description,
                        parameters: tool.parameters
                    }
                };
            });
            body.tool_choice = 'auto';
        }
        return body;
    }

    async function appJson(path, payload) {
        var response = await fetch(appUrl(path), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        var data = await response.json();
        if (!response.ok || data.error) throw new Error(data.error || `HTTP ${response.status}`);
        return data;
    }

    async function providerJson(request, apiKey) {
        var url = request.base_url.replace(/\/+$/, '') + '/chat/completions';
        var response;
        try {
            response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + apiKey,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(providerRequestBody(request))
            });
        } catch (error) {
            throw new Error(
                'The browser could not reach the AI provider. Check HTTPS, CORS, and the URL. '
                + error.message
            );
        }
        if (!response.ok) {
            var detail = await response.text();
            throw new Error(`AI provider returned HTTP ${response.status}: ${detail.slice(0, 500)}`);
        }
        return response.json();
    }

    function setAiBusy(busy) {
        var button = document.getElementById('ai-ask-btn');
        var loading = document.getElementById('ai-loading');
        if (button) button.disabled = busy;
        if (loading) loading.classList.toggle('htmx-request', busy);
    }

    function appendAiHtml(html) {
        var chat = document.getElementById('ai-chat-messages');
        if (!chat) return;
        chat.insertAdjacentHTML('beforeend', html);
        chat.scrollTop = chat.scrollHeight;
    }

    function appendAiError(message) {
        var wrapper = document.createElement('div');
        wrapper.className = 'chat chat-start';
        var bubble = document.createElement('div');
        bubble.className = 'chat-bubble chat-bubble-error';
        bubble.textContent = 'Error: ' + message;
        wrapper.appendChild(bubble);
        var chat = document.getElementById('ai-chat-messages');
        if (chat) chat.appendChild(wrapper);
    }

    async function runBrowserRelay(question, settings, apiKey) {
        var history = document.getElementById('ai-history-data');
        var context = document.getElementById('ai-context-data');
        var step = await appJson('/ai/relay/start', {
            question: question,
            base_url: settings.base_url || '',
            model: settings.model || 'gpt-4o-mini',
            history: history ? history.textContent.trim() : '',
            context: context ? context.textContent.trim() : ''
        });
        appendAiHtml(step.user_html);

        while (step.status === 'needs_model') {
            var providerResponse = await providerJson(step.request, apiKey);
            step = await appJson('/ai/relay/continue', {
                state: step.state,
                provider_response: providerResponse
            });
        }
        if (step.html) appendAiHtml(step.html);
        if (history) history.textContent = step.state || '';
        if (context) context.textContent = '';
    }

    function startBrowserRelayFromForm(e) {
        var settings = getAiSettings();
        var apiKey = sessionAiKey || (settings.remember_key ? settings.api_key || '' : '');
        if (!apiKey) return false;

        e.preventDefault();
        e.stopImmediatePropagation();
        var input = document.getElementById('ai-question-input');
        var question = input ? input.value.trim() : '';
        if (!question) return true;
        setAiBusy(true);
        runBrowserRelay(question, settings, apiKey)
            .then(function() { if (input) input.value = ''; })
            .catch(function(error) { appendAiError(error.message); })
            .finally(function() { setAiBusy(false); });
        return true;
    }

    // Intercept before HTMX creates a submit request. Without a personal key,
    // the normal form submit continues to the server-managed route.
    document.addEventListener('click', function(e) {
        if (e.target && e.target.closest('#ai-ask-btn')) startBrowserRelayFromForm(e);
    }, true);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.target && e.target.id === 'ai-question-input') {
            startBrowserRelayFromForm(e);
        }
    }, true);

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
        var context = document.getElementById('ai-context-data');
        if (context) {
            context.textContent = '';
        }
    };

    // Also populate on page load
    document.addEventListener('DOMContentLoaded', populateAiSettingsModal);
})();
