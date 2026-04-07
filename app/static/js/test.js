const API_BASE = '/api';

// On Load
document.addEventListener('DOMContentLoaded', () => {
    fetchLogs();
});

// AI Debugger
async function testAIRaw() {
    const q = document.getElementById('ai-query').value || 'Zubní klinika';
    const loc = document.getElementById('ai-loc').value || 'Praha';
    
    document.getElementById('ai-loading').style.display = 'block';
    const promptOut = document.getElementById('ai-prompt-out');
    const rawOut = document.getElementById('ai-raw-out');
    
    promptOut.innerText = "Načítám...";
    rawOut.innerText = "Načítám...";
    
    try {
        const res = await fetch(`${API_BASE}/search/ai_raw?query=${encodeURIComponent(q)}&location=${encodeURIComponent(loc)}`);
        const data = await res.json();
        
        promptOut.innerText = data.prompt || "Chyba API";
        rawOut.innerText = data.raw_response ? data.raw_response.trim() : JSON.stringify(data, null, 2);
    } catch(err) {
        rawOut.innerText = `Síťová chyba: ${err.message}`;
    } finally {
        document.getElementById('ai-loading').style.display = 'none';
        fetchLogs(); // auto-refresh system logs after call
    }
}

// Scraper Test
async function testScraper() {
    const url = document.getElementById('scraper-url').value;
    if(!url) return alert('Zadejte URL pro test');
    
    document.getElementById('scraper-loading').style.display = 'block';
    const logsContainer = document.getElementById('scraper-logs');
    const emailsUl = document.getElementById('scraper-emails');
    
    logsContainer.innerHTML = '';
    emailsUl.innerHTML = '<li style="color: var(--text-secondary);">Načítám...</li>';
    
    try {
        const res = await fetch(`${API_BASE}/scraper/test?url=${encodeURIComponent(url)}`);
        const data = await res.json();
        
        logsContainer.innerHTML = (data.logs || []).map(l => `<div style="margin-bottom: 4px;">${l}</div>`).join('');
        
        if (data.emails && data.emails.length > 0) {
            emailsUl.innerHTML = data.emails.map(e => `<li>${e}</li>`).join('');
        } else {
            emailsUl.innerHTML = '<li style="color: red;">Žádné emaily nenalezeny.</li>';
        }
    } catch(err) {
        logsContainer.innerHTML = `<span style="color:red">Chyba API/Scraperu: ${err.message}</span>`;
        emailsUl.innerHTML = '';
    } finally {
        document.getElementById('scraper-loading').style.display = 'none';
        fetchLogs();
    }
}

// Global Logs
async function fetchLogs() {
    const el = document.getElementById('system-logs');
    try {
        const res = await fetch(`${API_BASE}/debug/logs?lines=100`);
        const data = await res.json();
        
        if(data.logs) {
            el.innerHTML = data.logs.join('<br>');
            el.scrollTop = el.scrollHeight; // auto scroll to bottom
        } else {
            el.innerHTML = "Logy prázdné.";
        }
    } catch(err) {
        console.error(err);
        el.innerHTML = "Chyba načtení logů ze serveru.";
    }
}
