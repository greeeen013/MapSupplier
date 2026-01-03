const API_BASE = '/api';

// State
let currentSearchresults = [];
let suppliers = [];
let currentSupplier = null;
let presets = [];

// Init
document.addEventListener('DOMContentLoaded', () => {
    loadPresets();
    loadSuppliers();
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

function renderSearchResults(results) {
    const container = document.getElementById('search-results');
    container.innerHTML = results.map(place => `
        <div class="card" id="card-${place.google_id}">
             <div class="card-img" style="background-image: url('${place.images[0] || ''}')"></div>
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

async function approveSupplier(googleId) {
    const place = currentSearchresults.find(p => p.google_id === googleId);
    if (!place) return;

    const payload = {
        ...place,
        keyword: document.getElementById('keywords').value,
        status: 'accepted'
    };

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
    const place = currentSearchresults.find(p => p.google_id === googleId);
    if (!place) return;

    const payload = {
        ...place,
        keyword: document.getElementById('keywords').value,
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
        badge.className = `status-badge status-${status}`;
        badge.innerText = status;
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
    renderSupplierList();
}

function renderSupplierList() {
    const list = document.getElementById('supplier-list');
    list.innerHTML = suppliers.map(s => `
        <div class="supplier-list-item" onclick="selectSupplier(${s.id})">
            <h4>${s.name}</h4>
            <span>${s.keyword || 'N/A'}</span>
            ${s.status === 'contacted' ? '✅' : ''}
        </div>
    `).join('');
}

async function selectSupplier(id) {
    currentSupplier = suppliers.find(s => s.id === id);
    if (!currentSupplier) return;

    // Fetch fresh details just in case

    const panel = document.getElementById('supplier-detail-panel');
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
                    <option value="">-- Vyberte Preset --</option>
                    ${presets.map(p => `<option value="${p.id}">${p.name}</option>`).join('')}
                </select>
            </div>
            
            <div id="tab-ai" class="tab-content" style="display:none;">
                <div style="display:flex; gap:0.5rem; margin-bottom:1rem;">
                    <input type="text" id="ai-prompt" placeholder="Např. Nabídka prodeje luxusních hodinek" style="flex:1">
                    <button class="action-btn" onclick="generateAI()">Generovat</button>
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
                 <label style="margin-left: auto; display: flex; align-items: center; gap: 0.5rem;">
                        <input type="checkbox" id="auto-email"> Auto-Send
                </label>
            </div>
        </div>
    `;
}

function setTab(tab) {
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
    const id = parseInt(document.getElementById('preset-select').value);
    const preset = presets.find(p => p.id === id);
    if (preset) {
        document.getElementById('email-subject').value = preset.subject;
        document.getElementById('email-body').value = preset.body;
    }
}

async function generateAI() {
    const prompt = document.getElementById('ai-prompt').value;
    if (!prompt) return alert('Zadejte prompt');

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

        // Try to parse subject if line 1 starts with 'Předmět:'
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
            alert('Odesláno!');
            loadSuppliers(); // refresh status
            // Auto advance?
            // find next index
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
        // Mark as skipped_forever via API (reuse reject endpoint or update status)
        // For now reuse reject endpoint logic but keep meaningful status
        // We can just set status to 'skipped_forever'
        // Need endpoint support. Suppliers update endpoint supports any fields.

        await fetch(`${API_BASE}/suppliers/${currentSupplier.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...currentSupplier,
                status: 'skipped_forever'
            })
        });
        loadSuppliers();
    } else {
        // Just clear selection or move to next
        document.getElementById('supplier-detail-panel').innerHTML = '<p style="text-align:center;margin-top:5rem;">Vyberte dalšího...</p>';
        currentSupplier = null;
    }
}
