/**
 * ui.js — Pure terminal text output. No fancy DOM elements.
 */

const $ = (sel) => document.querySelector(sel);

// ─── Phase Transitions ──────────────────────────────────

export function transitionTo(target) {
    const views = {
        article:   $('#article-view'),
        terminal:  $('#terminal-view'),
        optimizer: $('#optimizer-view'),
    };

    // Hide all
    Object.values(views).forEach(el => el.classList.add('hidden'));

    // Fade out article gracefully
    if (target !== 'article') {
        document.body.classList.add('term-active');
    }

    views[target].classList.remove('hidden');
}

// ─── Terminal (Phase 2) ──────────────────────────────────

const termOut = () => $('#terminal-output');

export async function typeLines(lines, speed = 25) {
    for (const line of lines) {
        await typeLine(line, speed);
        await sleep(80 + Math.random() * 120);
    }
}

export async function typeLine(text, speed = 25) {
    const div = document.createElement('div');
    div.className = 't-line';
    termOut().appendChild(div);
    for (const ch of text) {
        div.textContent += ch;
        await sleep(speed);
    }
}

export function addTerminalLine(text, cls = '') {
    const div = document.createElement('div');
    div.className = `t-line ${cls}`.trim();
    div.textContent = text;
    termOut().appendChild(div);
}

export function showCodeInput() {
    const line = $('#terminal-input-line');
    line.classList.remove('hidden');
    $('#code-input').focus();
}

export function setInputState(enabled) {
    const input = $('#code-input');
    input.disabled = !enabled;
    if (enabled) { input.value = ''; input.focus(); }
}

// ─── Optimizer (Phase 3) — all text ──────────────────────

const optOut = () => $('#opt-output');

export function printLine(text, cls = '') {
    const div = document.createElement('div');
    div.className = `t-line ${cls}`.trim();
    div.textContent = text;
    optOut().appendChild(div);
    return div;
}

export function printDownloadButton(text, url) {
    const div = document.createElement('div');
    div.className = 't-line';
    
    const a = document.createElement('a');
    a.href = url;
    a.download = '';
    a.className = 't-dl-btn';
    a.innerHTML = `[ <span class="dl-icon">↓</span> ${text} ]`;
    
    div.appendChild(a);
    optOut().appendChild(div);
    return div;
}

// Header
export function printOptHeader() {
    printLine('cf-stealthsub v0.2.0', 'accent');
    printLine('─'.repeat(50), 'dim');
    printLine('');
}

// ── Upload UI ──

export function renderUploadArea() {
    const box = document.createElement('div');
    box.id = 'drop-zone';
    box.className = 'upload-zone';
    box.textContent = '[ === DRAG AND DROP result.csv HERE === ]';
    optOut().appendChild(box);
    printLine('');
}

// ── Results table (plain text) ──

export function updateResultsTable(results) {
    if (!results || results.length === 0) return;
    printLine('');
    printLine('─'.repeat(70), 'dim');
    printLine(
        '#'.padEnd(4) +
        'IP'.padEnd(18) +
        'Colo'.padEnd(8) +
        'Latency'.padEnd(10) +
        'Speed'.padEnd(12) +
        'Loss',
        'dim'
    );
    printLine('─'.repeat(70), 'dim');

    results.forEach((r, i) => {
        const cls = i < 3 ? 'accent' : '';
        const star = i < 3 ? '★' : ' ';
        const line =
            `${star}${String(i + 1).padStart(2)} ` +
            r.ip.padEnd(18) +
            (r.colo || 'UNK').padEnd(8) +
            `${r.avg_latency.toFixed(0)}ms`.padEnd(10) +
            `${r.speed_kbps.toFixed(0)}K`.padEnd(12) +
            `${(r.loss_rate * 100).toFixed(0)}%`;
        printLine(line, cls);
    });
    printLine('─'.repeat(70), 'dim');
}

// ── Subscription result ──

export function showSubscriptionResult(data) {
    printLine('');
    if (data.is_cached) {
        printLine('[cached] subscription already exists', 'warn');
    } else {
        printLine('[done] subscription generated', 'ok');
    }
    printLine('');

    // URL line
    const urlDiv = document.createElement('div');
    urlDiv.className = 'sub-line';
    urlDiv.innerHTML = `<input id="sub-url" value="${data.sub_url}" readonly> <button id="copy-btn">copy</button> <button id="clash-btn">clash://</button>`;
    optOut().appendChild(urlDiv);

    // Bind copy
    document.getElementById('copy-btn').onclick = async () => {
        try {
            await navigator.clipboard.writeText(data.sub_url);
            document.getElementById('copy-btn').textContent = '✓ copied';
            setTimeout(() => { document.getElementById('copy-btn').textContent = 'copy'; }, 2000);
        } catch {
            document.getElementById('sub-url').select();
            document.execCommand('copy');
        }
    };

    // Bind clash import
    document.getElementById('clash-btn').onclick = () => {
        window.open('clash://install-config?url=' + encodeURIComponent(data.sub_url));
    };
}

export function showError(msg) {
    printLine(`error: ${msg}`, 'err');
}

// ─── Utilities ──────────────────────────────────────────

export function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
