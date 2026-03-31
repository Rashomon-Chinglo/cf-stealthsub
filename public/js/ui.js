/**
 * ui.js — Pure terminal text output. No fancy DOM elements.
 */

/**
 * @typedef {'article' | 'terminal'} ViewName
 * @typedef {{
 *   ip: string,
 *   avg_latency: number,
 *   loss_rate: number,
 *   speed_kbps: number,
 *   colo: string
 * }} ResultRow
 * @typedef {{
 *   is_cached: boolean,
 *   sub_url: string
 * }} SubscriptionViewModel
 */

/**
 * Query a single element.
 * @template {Element} T
 * @param {string} selector
 * @returns {T | null}
 */
const $ = (selector) => document.querySelector(selector);

/**
 * Require an element to exist.
 * @template {Element} T
 * @param {string} selector
 * @returns {T}
 */
function requireElement(selector) {
    const element = $(selector);
    if (!element) {
        throw new Error(`Missing required element: ${selector}`);
    }
    return /** @type {T} */ (element);
}

/**
 * Append a node to the terminal output and keep the viewport pinned to the bottom.
 * @template {Node} T
 * @param {T} node
 * @returns {T}
 */
function appendTerminalNode(node) {
    termOut().appendChild(node);
    scrollTerminalToBottom();
    return node;
}

/**
 * Build a terminal line element with an optional class name.
 * @param {string} text
 * @param {string} [className='']
 * @returns {HTMLDivElement}
 */
function createTerminalLine(text, className = '') {
    const line = document.createElement('div');
    line.className = `t-line ${className}`.trim();
    line.textContent = text;
    return line;
}

/**
 * Transition between the three application views.
 * @param {ViewName} target
 * @returns {void}
 */
export function transitionTo(target) {
    /** @type {Record<ViewName, HTMLElement>} */
    const views = {
        article: requireElement('#article-view'),
        terminal: requireElement('#terminal-view'),
    };

    Object.values(views).forEach((view) => view.classList.add('hidden'));
    if (target !== 'article') {
        document.body.classList.add('term-active');
    }
    views[target].classList.remove('hidden');
}

/**
 * Terminal output container.
 * @returns {HTMLElement}
 */
function termOut() {
    return requireElement('#terminal-output');
}

/**
 * Type a list of terminal lines sequentially.
 * @param {string[]} lines
 * @param {number} [speed=25]
 * @returns {Promise<void>}
 */
export async function typeLines(lines, speed = 25) {
    for (const line of lines) {
        await typeLine(line, speed);
        await sleep(80 + Math.random() * 120);
    }
}

/**
 * Type a single line character by character.
 * @param {string} text
 * @param {number} [speed=25]
 * @returns {Promise<void>}
 */
export async function typeLine(text, speed = 25) {
    const line = appendTerminalNode(createTerminalLine(''));

    for (const character of text) {
        line.textContent += character;
        await sleep(speed);
        scrollTerminalToBottom();
    }
}

/**
 * Append a terminal line immediately.
 * @param {string} text
 * @param {string} [cls='']
 * @returns {HTMLElement}
 */
export function addTerminalLine(text, cls = '') {
    return appendTerminalNode(createTerminalLine(text, cls));
}

/**
 * Reveal and focus the TOTP input.
 * @returns {void}
 */
export function showCodeInput() {
    const line = requireElement('#terminal-input-line');
    const input = /** @type {HTMLInputElement} */ (requireElement('#code-input'));
    line.classList.remove('hidden');
    input.focus();
}

/**
 * Hide the TOTP input line after auth is complete.
 * @returns {void}
 */
export function hideCodeInput() {
    const line = requireElement('#terminal-input-line');
    line.classList.add('hidden');
}

/**
 * Enable or disable the TOTP input.
 * @param {boolean} enabled
 * @returns {void}
 */
export function setInputState(enabled) {
    const input = /** @type {HTMLInputElement} */ (requireElement('#code-input'));
    input.disabled = !enabled;
    if (enabled) {
        input.value = '';
        input.focus();
    }
}

/**
 * Clear optimizer output before re-rendering.
 * @returns {void}
 */
export function clearTerminalOutput() {
    termOut().textContent = '';
}

/**
 * Print a plain terminal-style line in the optimizer view.
 * @param {string} text
 * @param {string} [cls='']
 * @returns {HTMLElement}
 */
export function printLine(text, cls = '') {
    return appendTerminalNode(createTerminalLine(text, cls));
}

/**
 * Print a file download link styled as a terminal button.
 * @param {string} text
 * @param {string} url
 * @returns {HTMLElement}
 */
export function printDownloadButton(text, url) {
    const line = createTerminalLine('');

    const link = document.createElement('a');
    link.href = url;
    link.download = '';
    link.className = 't-dl-btn';
    link.innerHTML = `[ <span class="dl-icon">↓</span> ${text} ]`;

    line.appendChild(link);
    return appendTerminalNode(line);
}

/**
 * Render the optimizer header.
 * @returns {void}
 */
export function printOptHeader() {
    printLine('cf-stealthsub v0.2.0', 'accent');
    printLine('─'.repeat(50), 'dim');
    printLine('');
}

/**
 * Render the upload drop zone.
 * @returns {HTMLElement}
 */
export function renderUploadArea() {
    const existing = $('#drop-zone');
    if (existing instanceof HTMLElement) {
        return existing;
    }

    const box = document.createElement('div');
    box.id = 'drop-zone';
    box.className = 'upload-zone';
    box.textContent = '[ === DRAG AND DROP result.csv HERE === ]';
    appendTerminalNode(box);
    printLine('');
    return box;
}

/**
 * Print a text-only results table.
 * @param {ResultRow[]} results
 * @returns {void}
 */
export function updateResultsTable(results) {
    if (results.length === 0) {
        return;
    }

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

    results.forEach((result, index) => {
        const cls = index < 3 ? 'accent' : '';
        const star = index < 3 ? '★' : ' ';
        const line =
            `${star}${String(index + 1).padStart(2)} ` +
            result.ip.padEnd(18) +
            (result.colo || 'UNK').padEnd(8) +
            `${result.avg_latency.toFixed(0)}ms`.padEnd(10) +
            `${result.speed_kbps.toFixed(0)}K`.padEnd(12) +
            `${(result.loss_rate * 100).toFixed(0)}%`;

        printLine(line, cls);
    });

    printLine('─'.repeat(70), 'dim');
}

/**
 * Render the generated subscription URL and action buttons.
 * @param {SubscriptionViewModel} data
 * @returns {void}
 */
export function showSubscriptionResult(data) {
    printLine('');
    printLine(
        data.is_cached ? '[cached] subscription already exists' : '[done] subscription generated',
        data.is_cached ? 'warn' : 'ok'
    );
    printLine('');

    const subscriptionRow = document.createElement('div');
    subscriptionRow.className = 'sub-line';

    const input = document.createElement('input');
    input.id = 'sub-url';
    input.value = data.sub_url;
    input.readOnly = true;

    const copyButton = document.createElement('button');
    copyButton.id = 'copy-btn';
    copyButton.type = 'button';
    copyButton.textContent = 'copy';

    const clashButton = document.createElement('button');
    clashButton.id = 'clash-btn';
    clashButton.type = 'button';
    clashButton.textContent = 'clash://';

    subscriptionRow.appendChild(input);
    subscriptionRow.appendChild(copyButton);
    subscriptionRow.appendChild(clashButton);
    appendTerminalNode(subscriptionRow);

    copyButton.onclick = async () => {
        try {
            await navigator.clipboard.writeText(data.sub_url);
            setButtonLabelTemporarily(copyButton, '✓ copied', 'copy', 2000);
        } catch {
            input.select();
            document.execCommand('copy');
        }
    };

    clashButton.onclick = () => {
        window.open(`clash://install-config?url=${encodeURIComponent(data.sub_url)}`);
    };
}

/**
 * Show an error line in the optimizer view.
 * @param {string} msg
 * @returns {void}
 */
export function showError(msg) {
    printLine(`error: ${msg}`, 'err');
}

/**
 * Temporarily swap a button label, then restore it.
 * @param {HTMLButtonElement} button
 * @param {string} activeLabel
 * @param {string} idleLabel
 * @param {number} delayMs
 * @returns {void}
 */
function setButtonLabelTemporarily(button, activeLabel, idleLabel, delayMs) {
    button.textContent = activeLabel;
    window.setTimeout(() => {
        button.textContent = idleLabel;
    }, delayMs);
}

/**
 * Sleep helper used by the terminal typing animation.
 * @param {number} ms
 * @returns {Promise<void>}
 */
export function sleep(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
}

/**
 * Keep the terminal pinned to the latest output.
 * @returns {void}
 */
function scrollTerminalToBottom() {
    const terminal = requireElement('#terminal-view');
    terminal.scrollTop = terminal.scrollHeight;
}
