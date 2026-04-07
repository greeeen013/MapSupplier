const API_BASE = '/api';

// State
let currentSearchresults = [];
let currentAISearchresults = [];
let suppliers = [];
let currentSupplier = null;
let presets = [];
let activeTagFilter = null;

let currentSettingsTab = 'template';
let editingPresetId = null;

// Init
document.addEventListener('DOMContentLoaded', () => {
    loadPresets();
    loadSuppliers();

    // Setup tooltip
    const tooltipIcon = document.getElementById('ai-prompt-tooltip');
    if (tooltipIcon) {
        tooltipIcon.addEventListener('mouseenter', updateAIPromptTooltip);
    }
});

// Navigation
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('nav button').forEach(el => el.classList.remove('active'));

    document.getElementById(`view-${viewName}`).classList.add('active');
    document.getElementById(`nav-${viewName}`).classList.add('active');

    if (viewName === 'email') {
        loadSuppliers(); // Refresh list
    }
}

// --- Search Logic ---

async function searchPlaces() {
    const query = document.getElementById('keywords').value;
    const location = document.getElementById('location').value;
    const autoConfirm = document.getElementById('auto-confirm').checked;

    if (!query) return alert('Zadejte klíčová slova');

    const resultsContainer = document.getElementById('search-results');
    resultsContainer.innerHTML = '';
    document.getElementById('search-loading').style.display = 'block';

    try {
        const response = await fetch(`${API_BASE}/search/places?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`);
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();

        currentSearchresults = data;
        renderSearchResults(data);

        if (autoConfirm) {
            await autoConfirmAll(data);
        }

    } catch (err) {
        alert('Chyba hledání: ' + err.message);
    } finally {
        document.getElementById('search-loading').style.display = 'none';
    }
}

async function searchAIPlaces() {
    const query = document.getElementById('ai-keywords').value;
    const location = document.getElementById('ai-location').value;

    if (!query) return alert('Zadejte klíčová slova');

    const resultsContainer = document.getElementById('ai-search-results');
    resultsContainer.innerHTML = '';
    document.getElementById('ai-search-loading').style.display = 'block';

    try {
        const response = await fetch(`${API_BASE}/search/ai_places?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`);
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();

        currentAISearchresults = data;
        renderAISearchResults(data);

    } catch (err) {
        alert('Chyba AI hledání: ' + err.message);
    } finally {
        document.getElementById('ai-search-loading').style.display = 'none';
    }
}

async function updateAIPromptTooltip() {
    const q = document.getElementById('ai-keywords').value || "Tvé slovo";
    const loc = document.getElementById('ai-location').value || "Tvá oblast";
    const disp = document.getElementById('ai-prompt-text-display');
    if (!disp) return;
    
    disp.innerText = "Načítám prompt...";
    try {
        const res = await fetch(`${API_BASE}/search/ai_prompt_text?query=${encodeURIComponent(q)}&location=${encodeURIComponent(loc)}`);
        const data = await res.json();
        disp.innerText = data.prompt;
    } catch(e) {
        disp.innerText = 'Nelze načíst prompt.';
    }
}

function renderSearchResults(results) {
    const container = document.getElementById('search-results');
    container.innerHTML = results.map(place => `
        <div class="card" id="card-${place.google_id}">
             <div class="card-img" style="background-image: url('${place.images[0] || ''}')">
                 ${place.is_street_view ? '<span class="street-view-label">Street View</span>' : ''}
             </div>
             <div class="card-content">
                 <h3>${place.name}</h3>
                 <div class="rating">★ ${place.rating || 'N/A'}</div>
                 <p>${place.address}</p>
                 <span class="status-badge status-${place.status}">${place.status}</span>
             </div>
             <div class="card-actions">
                 <button class="btn-approve" onclick="approveSupplier('${place.google_id}')">Potvrdit</button>
                 <button class="btn-reject" onclick="rejectSupplier('${place.google_id}')">Zamítnout</button>
             </div>
        </div>
    `).join('');
}

function renderAISearchResults(results) {
    const container = document.getElementById('ai-search-results');
    container.innerHTML = results.map(place => {
        let emailHtml = `<p><strong>Email:</strong> Nenalezen</p>`;
        
        if (place.emails_rich && place.emails_rich.length > 0) {
            const isVerified = place.emails_rich[0].verified;
            const icon = isVerified ? '✅' : '🔴';
            const tooltipText = isVerified 
                ? 'Ověřeno přes web-scraper' 
                : 'Neověřeno (pouze AI)';
            const colorClass = isVerified ? 'green' : 'red';
            const editPencil = !isVerified ? `<span id="pencil-${place.google_id}" style="cursor: pointer; margin-left: 5px;" onclick="editEmailDropdown('${place.google_id}')">✏️</span>` : '';

            if (place.emails_rich.length > 1) {
                emailHtml = `
                <div style="margin: 0.5rem 0;" id="email-container-${place.google_id}">
                    <div style="margin-bottom: 0.3rem;">
                        <strong>Emaily:</strong> ${icon} <span style="font-size: 0.8rem; font-style: italic; color: var(--text-secondary);">${tooltipText}</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <select id="email-select-${place.google_id}" style="width: 150px; font-size:0.9rem; padding: 2px;">
                            ${place.emails_rich.map(e => `<option value="${e.address}">${e.address}</option>`).join('')}
                        </select>
                        ${editPencil}
                    </div>
                </div>`;
            } else {
                emailHtml = `
                <div style="margin: 0.5rem 0;" id="email-container-${place.google_id}">
                    <div style="margin-bottom: 0.3rem;">
                        <strong>Email:</strong> <span style="font-size: 0.8rem; font-style: italic; color: var(--text-secondary);">${tooltipText}</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <span id="email-select-${place.google_id}" data-val="${place.emails_rich[0].address}" style="color: ${colorClass}; font-weight: bold;">${place.emails_rich[0].address}</span>
                        ${editPencil}
                    </div>
                </div>`;
            }
        }

        return `
        <div class="card" id="card-${place.google_id}">
             <div class="card-content">
                 <h3>${place.name}</h3>
                 ${emailHtml}
                 <p><strong>Tel:</strong> ${place.phone || 'N/A'}</p>
                 <p><strong>Adresa:</strong> ${place.address || 'N/A'}</p>
                 <p><strong>Web:</strong> ${place.website ? `<a href="${place.website}" target="_blank">Odkaz</a>` : 'N/A'}</p>
                 <span class="status-badge status-${place.status}">${place.status}</span>
             </div>
             <div class="card-actions">
                 <button class="btn-approve" onclick="approveSupplier('${place.google_id}')">Potvrdit</button>
                 <button class="btn-reject" onclick="rejectSupplier('${place.google_id}')">Zamítnout</button>
             </div>
        </div>
        `;
    }).join('');
}

function editEmailDropdown(googleId) {
    const el = document.getElementById(`email-select-${googleId}`);
    if (!el) return;
    
    let currentVal = el.tagName === 'SELECT' ? el.value : (el.getAttribute('data-val') || el.innerText);
    
    const input = document.createElement('input');
    input.type = 'text';
    input.id = `email-input-${googleId}`;
    input.value = currentVal;
    input.style.width = '150px';
    input.style.fontSize = '0.9rem';
    input.style.padding = '2px';
    
    el.parentNode.replaceChild(input, el);
    
    const pencil = document.getElementById(`pencil-${googleId}`);
    if (pencil) pencil.remove();
}

// Orphan functions removed

async function approveSupplier(googleId) {
    let place = currentSearchresults.find(p => p.google_id === googleId);
    let isAI = false;
    if (!place) {
        place = currentAISearchresults.find(p => p.google_id === googleId);
        isAI = !!place;
    }
    if (!place) return;

    let selectedEmail = place.email; // Fallback
    const inputEl = document.getElementById(`email-input-${googleId}`);
    const selectEl = document.getElementById(`email-select-${googleId}`);
    
    if (inputEl) {
        selectedEmail = inputEl.value;
    } else if (selectEl) {
        if (selectEl.tagName === 'SELECT') {
            selectedEmail = selectEl.value;
        } else {
            selectedEmail = selectEl.getAttribute('data-val') || selectEl.innerText;
        }
    }

    const payload = {
        ...place,
        email: selectedEmail,
        keyword: isAI ? document.getElementById('ai-keywords').value : document.getElementById('keywords').value,
        status: 'accepted'
    };

    if (isAI) {
        const query = document.getElementById('ai-keywords').value;
        const location = document.getElementById('ai-location').value;
        payload.tags = [query, location, 'AI SEARCH']
            .filter(Boolean)
            .map(t => t.toUpperCase());
    }

    try {
        const res = await fetch(`${API_BASE}/suppliers/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Failed');

        updateCardStatus(googleId, 'accepted');
    } catch (e) {
        console.error(e);
        alert('Chyba uložení');
    }
}

async function rejectSupplier(googleId) {
    let place = currentSearchresults.find(p => p.google_id === googleId);
    let isAI = false;
    if (!place) {
        place = currentAISearchresults.find(p => p.google_id === googleId);
        isAI = !!place;
    }
    if (!place) return;

    const payload = {
        ...place,
        keyword: isAI ? document.getElementById('ai-keywords').value : document.getElementById('keywords').value,
        status: 'rejected'
    };

    try {
        const res = await fetch(`${API_BASE}/suppliers/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        // Remove card or gray it out
        const card = document.getElementById(`card-${googleId}`);
        if (card) card.style.opacity = '0.5';
        updateCardStatus(googleId, 'rejected');
    } catch (e) {
        console.error(e);
    }
}

function updateCardStatus(googleId, status) {
    const card = document.getElementById(`card-${googleId}`);
    if (card) {
        const badge = card.querySelector('.status-badge');
        if (badge) {
            badge.className = `status-badge status-${status}`;
            badge.innerText = status;
        }
    }
}

async function autoConfirmAll(results) {
    for (const place of results) {
        if (place.status === 'new') {
            await approveSupplier(place.google_id);
            // Small delay to not spam UI
            await new Promise(r => setTimeout(r, 100));
        }
    }
}

// --- Email Logic ---

async function loadSuppliers() {
    const res = await fetch(`${API_BASE}/suppliers/?status=accepted`);
    suppliers = await res.json();
    renderTagFilter();
    renderSupplierList();
}

function renderTagFilter() {
    const bar = document.getElementById('tag-filter-bar');
    if (!bar) return;

    const allTags = new Set();
    suppliers.forEach(s => {
        if (Array.isArray(s.tags)) {
            s.tags.forEach(t => allTags.add(t.toUpperCase()));
        }
    });

    if (allTags.size === 0) {
        bar.innerHTML = '';
        return;
    }

    const chips = ['VŠE', ...allTags].map(tag => {
        const isActive = tag === 'VŠE' ? !activeTagFilter : activeTagFilter === tag;
        const onclick = tag === 'VŠE' ? 'setTagFilter(null)' : `setTagFilter('${tag.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')`;
        return `<button class="tag-chip${isActive ? ' active' : ''}" onclick="${onclick}">${tag}</button>`;
    }).join('');

    bar.innerHTML = chips;
}

function setTagFilter(tag) {
    activeTagFilter = tag;
    renderTagFilter();
    renderSupplierList();
}

function renderSupplierList() {
    const list = document.getElementById('supplier-list');
    let filtered = suppliers;
    if (activeTagFilter) {
        filtered = suppliers.filter(s =>
            Array.isArray(s.tags) &&
            s.tags.some(t => t.toUpperCase() === activeTagFilter)
        );
    }
    list.innerHTML = filtered.map(s => {
        let tagsHtml = '';
        if (Array.isArray(s.tags) && s.tags.length > 0) {
            tagsHtml = s.tags.map(t => `<span>${t}</span>`).join('');
        } else {
            tagsHtml = `<span>${s.keyword || 'N/A'}</span>`;
        }
        return `
        <div class="supplier-list-item" onclick="selectSupplier(${s.id})">
            <h4>${s.name}</h4>
            <div style="margin-top: 0.3rem; display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center;">
                ${tagsHtml}
                ${s.status === 'contacted' ? '<div style="margin-left: auto;">✅</div>' : ''}
            </div>
        </div>
        `;
    }).join('');
}

async function selectSupplier(id) {
    currentSupplier = suppliers.find(s => s.id === id);
    if (!currentSupplier) return;

    const panel = document.getElementById('supplier-detail-panel');
    const autoSendState = document.getElementById('auto-email') ? document.getElementById('auto-email').checked : false;

    // Filter presets
    const templates = presets.filter(p => !p.preset_type || p.preset_type === 'template');
    const prompts = presets.filter(p => p.preset_type === 'ai_prompt');

    panel.innerHTML = `
        <h2>${currentSupplier.name}</h2>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1rem 0;">
            <div>
                <strong>Email:</strong> ${currentSupplier.email || 'Není (Možná zkusit Detail Search)'} <br>
                <strong>Tel:</strong> ${currentSupplier.phone || 'N/A'} <br>
                <strong>Web:</strong> <a href="${currentSupplier.website}" target="_blank">${currentSupplier.website || 'N/A'}</a>
            </div>
            <div>
                <strong>Rating:</strong> ${currentSupplier.rating} <br>
                <strong>Adresa:</strong> ${currentSupplier.address}
            </div>
        </div>
        
        <div class="email-section">
            <div class="tabs">
                <button class="tab-btn active" onclick="setTab('preset')">Presety</button>
                <button class="tab-btn" onclick="setTab('ai')">Gemini AI</button>
            </div>
            
            <div id="tab-preset" class="tab-content">
                <select id="preset-select" onchange="applyPreset()" style="width: 100%; margin-bottom: 1rem;">
                    <option value="">-- Vlastní zpráva --</option>
                    ${templates.map(p => `<option value="${p.id}">${p.name}</option>`).join('')}
                </select>
            </div>
            
            <div id="tab-ai" class="tab-content" style="display:none;">
                 <div style="display:flex; flex-direction:column; margin-bottom: 1rem;">
                     <select id="prompt-select" onchange="applyPrompt()" style="width: 100%; margin-bottom: 0.5rem;">
                        <option value="">-- Vlastní prompt --</option>
                        ${prompts.map(p => `<option value="${p.id}">${p.name}</option>`).join('')}
                    </select>
                    <div style="display:flex; gap:0.5rem;">
                        <input type="text" id="ai-prompt" placeholder="Např. Nabídka prodeje luxusních hodinek ({name}, {address})" style="flex:1">
                        <div class="info-tooltip" style="position:relative; top:0; right:0; margin-left:5px;">
                            ℹ️ 
                            <span class="tooltiptext">
                                Proměnné: {name}, {address}, {rating}, {keyword}, {phone}, {website}, {email}
                            </span>
                        </div>
                        <button class="action-btn" onclick="generateAI()">Generovat</button>
                    </div>
                </div>
            </div>
            
            <div class="email-compose">
                <input type="text" id="email-subject" placeholder="Předmět" style="width: 100%; margin-bottom: 0.5rem;">
                <textarea id="email-body" placeholder="Text emailu..."></textarea>
            </div>
            
            <div style="display:flex; gap: 1rem; margin-top: 1rem;">
                <button class="primary" onclick="sendEmail()">Odeslat</button>
                <button class="action-btn" style="background:#444" onclick="skipSupplier(false)">Přeskočit (Dočasně)</button>
                <button class="danger" onclick="skipSupplier(true)">Přeskočit (Navždy)</button>
                 <label style="margin-left: auto; display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                        <input type="checkbox" id="auto-email" ${autoSendState ? 'checked' : ''}> Auto-Send
                </label>
            </div>
        </div>
    `;

    // Restore last used prompt or preset if auto-sending is active?
    // Actually, handling auto-send logic:
    if (autoSendState) {
        // Simple logic: If we have a prompt or preset selected in memory (variable?), apply it.
        // But since we just rendered, DOM is empty.
        // We should ideally persist "Last Selected Preset/Prompt ID" in a global var.

        if (lastSelectedTab === 'preset' && lastSelectedPresetId) {
            document.getElementById('preset-select').value = lastSelectedPresetId;
            applyPreset();
            // Since logic is async (sendEmail), we should wait a bit then send
            setTimeout(sendEmail, 500);
        } else if (lastSelectedTab === 'ai' && lastSelectedPromptId) {
            setTab('ai');
            document.getElementById('prompt-select').value = lastSelectedPromptId;
            applyPrompt(); // Fills input
            // Generate then send
            await generateAI();
            setTimeout(sendEmail, 1500); // Wait for generation to propagate? generateAI awaits, so we are good.
        }
    }
}

// Global state to track auto-send choices
let lastSelectedTab = 'preset';
let lastSelectedPresetId = '';
let lastSelectedPromptId = '';

function setTab(tab) {
    lastSelectedTab = tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');

    if (tab === 'preset') {
        document.querySelector('[onclick="setTab(\'preset\')"]').classList.add('active');
        document.getElementById('tab-preset').style.display = 'block';
    } else {
        document.querySelector('[onclick="setTab(\'ai\')"]').classList.add('active');
        document.getElementById('tab-ai').style.display = 'block';
    }
}

async function loadPresets() {
    try {
        const res = await fetch(`${API_BASE}/email/presets`);
        presets = await res.json();
    } catch (e) { console.error(e); }
}

function applyPreset() {
    const idStr = document.getElementById('preset-select').value;
    lastSelectedPresetId = idStr;

    if (!idStr) {
        // Clear
        document.getElementById('email-subject').value = "";
        document.getElementById('email-body').value = "";
        return;
    }

    const id = parseInt(idStr);
    const preset = presets.find(p => p.id === id);
    if (preset) {
        document.getElementById('email-subject').value = preset.subject;
        document.getElementById('email-body').value = preset.body;
    }
}

function applyPrompt() {
    const idStr = document.getElementById('prompt-select').value;
    lastSelectedPromptId = idStr;

    if (!idStr) return; // Don't clear manual input if they just switch back to empty

    const id = parseInt(idStr);
    const preset = presets.find(p => p.id === id);
    if (preset) {
        document.getElementById('ai-prompt').value = preset.body; // Using body as prompt content
    }
}

function replacePlaceholders(text, supplier) {
    if (!text || !supplier) return text;
    let out = text;
    out = out.replace(/{name}/g, supplier.name || '');
    out = out.replace(/{address}/g, supplier.address || '');
    out = out.replace(/{rating}/g, supplier.rating || '');
    out = out.replace(/{keyword}/g, supplier.keyword || '');
    out = out.replace(/{phone}/g, supplier.phone || '');
    out = out.replace(/{website}/g, supplier.website || '');
    out = out.replace(/{email}/g, supplier.email || '');
    return out;
}

async function generateAI() {
    let prompt = document.getElementById('ai-prompt').value;
    if (!prompt) return alert('Zadejte prompt');

    // Replace placeholders before sending
    prompt = replacePlaceholders(prompt, currentSupplier);

    document.getElementById('email-body').value = 'Generuji...';

    try {
        const res = await fetch(`${API_BASE}/email/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                supplier_info: currentSupplier
            })
        });
        const data = await res.json();
        const text = data.generated_text;

        const lines = text.split('\n');
        if (lines[0].toLowerCase().startsWith('předmět:')) {
            document.getElementById('email-subject').value = lines[0].replace(/předmět:\s*/i, '');
            document.getElementById('email-body').value = lines.slice(1).join('\n').trim();
        } else {
            document.getElementById('email-body').value = text;
        }

    } catch (e) {
        alert('Chyba AI: ' + e.message);
    }
}

async function sendEmail() {
    const subject = document.getElementById('email-subject').value;
    const body = document.getElementById('email-body').value;

    if (!currentSupplier) return;

    try {
        const res = await fetch(`${API_BASE}/email/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                supplier_id: currentSupplier.id,
                subject,
                body
            })
        });
        const data = await res.json();

        if (data.status === 'success') {
            // Find next supplier index
            const currentIndex = suppliers.findIndex(s => s.id === currentSupplier.id);
            if (currentIndex >= 0 && currentIndex < suppliers.length - 1) {
                const nextId = suppliers[currentIndex + 1].id;
                selectSupplier(nextId);
            } else {
                alert('Vše odesláno! (Konec seznamu)');
            }
        } else {
            alert('Chyba: ' + data.message);
        }
    } catch (e) {
        alert('Chyba odeslání: ' + e);
    }
}

async function skipSupplier(forever) {
    if (!currentSupplier) return;

    if (forever) {
        await fetch(`${API_BASE}/suppliers/${currentSupplier.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...currentSupplier,
                status: 'skipped_forever'
            })
        });
        loadSuppliers(); // Reload
    } else {
        const currentIndex = suppliers.findIndex(s => s.id === currentSupplier.id);
        if (currentIndex >= 0 && currentIndex < suppliers.length - 1) {
            selectSupplier(suppliers[currentIndex + 1].id);
        } else {
            document.getElementById('supplier-detail-panel').innerHTML = '<p style="text-align:center;margin-top:5rem;">Konec seznamu.</p>';
            currentSupplier = null;
        }
    }
}


// --- Settings Modal Logic ---

function openSettings() {
    document.getElementById('settings-modal').style.display = 'block';
    setSettingsTab('template');
}

function closeSettings() {
    document.getElementById('settings-modal').style.display = 'none';
    loadPresets(); // Refresh main UI
}

function setSettingsTab(type) {
    currentSettingsTab = type;
    document.querySelectorAll('#settings-modal .tab-btn').forEach(b => b.classList.remove('active'));
    // Simple toggle logic based on text content or index? using onclick mapping
    if (type === 'template') {
        document.querySelector('#settings-modal button[onclick="setSettingsTab(\'template\')"]').classList.add('active');
        document.getElementById('edit-subject').placeholder = "Předmět e-mailu";
        document.getElementById('ai-variables-panel').style.display = 'none';
    } else {
        document.querySelector('#settings-modal button[onclick="setSettingsTab(\'ai_prompt\')"]').classList.add('active');
        document.getElementById('edit-subject').placeholder = "Poznámka / Popis";
        document.getElementById('ai-variables-panel').style.display = 'block';
    }

    renderSettingsList();
    cancelEdit();
}

function renderSettingsList() {
    const list = document.getElementById('settings-list');
    const filtered = presets.filter(p => {
        if (currentSettingsTab === 'template') return !p.preset_type || p.preset_type === 'template';
        return p.preset_type === 'ai_prompt';
    });

    list.innerHTML = filtered.map(p => `
        <div class="settings-item" onclick="editPreset(${p.id})">
            <span>${p.name}</span>
            <span>✏️</span>
        </div>
    `).join('');
}

function createNewPreset() {
    editingPresetId = null;
    document.getElementById('preset-editor').style.display = 'block';
    document.getElementById('edit-name').value = '';
    document.getElementById('edit-subject').value = '';
    document.getElementById('edit-body').value = '';
}

function editPreset(id) {
    const preset = presets.find(p => p.id === id);
    if (!preset) return;

    editingPresetId = id;
    document.getElementById('preset-editor').style.display = 'block';
    document.getElementById('edit-name').value = preset.name;
    document.getElementById('edit-subject').value = preset.subject;
    document.getElementById('edit-body').value = preset.body;
}

function cancelEdit() {
    document.getElementById('preset-editor').style.display = 'none';
    editingPresetId = null;
}

async function savePreset() {
    const name = document.getElementById('edit-name').value;
    const subject = document.getElementById('edit-subject').value;
    const body = document.getElementById('edit-body').value;

    if (!name) return alert('Zadejte název');

    const payload = {
        name,
        subject,
        body,
        preset_type: currentSettingsTab
    };

    // Check local duplicate names? Server handles unique constraint.

    try {
        let res;
        if (editingPresetId) {
            res = await fetch(`${API_BASE}/email/presets/${editingPresetId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            res = await fetch(`${API_BASE}/email/presets`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        if (!res.ok) throw new Error('Uložení selhalo');

        // Refresh
        const updated = await fetch(`${API_BASE}/email/presets`).then(r => r.json());
        presets = updated;
        renderSettingsList();
        cancelEdit();

    } catch (e) {
        alert(e.message);
    }
}

async function deletePreset() {
    if (!editingPresetId) return;
    if (!confirm('Opravdu smazat?')) return;

    try {
        await fetch(`${API_BASE}/email/presets/${editingPresetId}`, { method: 'DELETE' });
        const updated = await fetch(`${API_BASE}/email/presets`).then(r => r.json());
        presets = updated;
        renderSettingsList();
        cancelEdit();
    } catch (e) {
        alert('Chyba mazání');
    }
}

// Window click to close modal
window.onclick = function (event) {
    const modal = document.getElementById('settings-modal');
    if (event.target == modal) {
        closeSettings();
    }
}

function insertPlaceholder(placeholder) {
    const textarea = document.getElementById('edit-body');
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;

    const before = text.substring(0, start);
    const after = text.substring(end);

    textarea.value = before + placeholder + after;
    textarea.selectionStart = textarea.selectionEnd = start + placeholder.length;
    textarea.focus();
}
