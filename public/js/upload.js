/**
 * upload.js — Optimizer UI and CSV upload flow.
 */

import * as ui from './ui.js?v=6.9';

const RESULTS_ENDPOINT = '/api/results';
const DOWNLOAD_OPTIONS = [
    ['Windows (amd64) .zip', '/optimize/downloads/cfst_windows_amd64.zip'],
    ['Linux (amd64) .tar.gz', '/optimize/downloads/cfst_linux_amd64.tar.gz'],
    ['Linux (arm64) .tar.gz', '/optimize/downloads/cfst_linux_arm64.tar.gz'],
];
const DROP_EVENTS = ['dragenter', 'dragover', 'dragleave', 'drop'];
const HIGHLIGHT_ON_EVENTS = ['dragenter', 'dragover'];
const HIGHLIGHT_OFF_EVENTS = ['dragleave', 'drop'];

let hasBoundGlobalDropListeners = false;

/**
 * @typedef {{
 *   ip: string,
 *   avg_latency: number,
 *   loss_rate: number,
 *   speed_kbps: number,
 *   score: number,
 *   colo: string
 * }} IPResult
 *
 * @typedef {{
 *   key: string,
 *   expires_at: number,
 *   is_cached: boolean,
 *   sub_url: string,
 *   results: IPResult[]
 * }} SubscriptionResponse
 */

/**
 * Initialize the optimizer output once per page lifecycle.
 * @returns {Promise<void>}
 */
export async function initUploadPhase() {
    if (document.getElementById('drop-zone')) {
        return;
    }

    ui.printOptHeader();
    ui.printLine('> Access confirmed', 'ok');
    ui.printLine('download CloudflareSpeedTest:', 'dim');

    DOWNLOAD_OPTIONS.forEach(([label, url]) => {
        ui.printDownloadButton(label, url);
    });

    ui.printLine('');
    ui.printLine('run it locally. it will generate result.csv.', 'dim');
    ui.printLine('');

    const dropZone = ui.renderUploadArea();
    bindDropZone(dropZone);
}

/**
 * Bind all drop handlers to the upload zone.
 * @param {HTMLElement} dropZone
 * @returns {void}
 */
function bindDropZone(dropZone) {
    DROP_EVENTS.forEach((eventName) => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    if (!hasBoundGlobalDropListeners) {
        DROP_EVENTS.forEach((eventName) => {
            document.body.addEventListener(eventName, preventDefaults, false);
        });
        hasBoundGlobalDropListeners = true;
    }

    HIGHLIGHT_ON_EVENTS.forEach((eventName) => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('highlight');
        }, false);
    });

    HIGHLIGHT_OFF_EVENTS.forEach((eventName) => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('highlight');
        }, false);
    });

    dropZone.addEventListener('drop', (event) => {
        void handleDrop(event);
    }, false);
}

/**
 * Suppress the browser's default file-drop behavior.
 * @param {Event} event
 * @returns {void}
 */
function preventDefaults(event) {
    event.preventDefault();
    event.stopPropagation();
}

/**
 * Handle a file-drop event.
 * @param {DragEvent} event
 * @returns {Promise<void>}
 */
async function handleDrop(event) {
    const files = event.dataTransfer?.files;
    if (!files || files.length === 0) {
        return;
    }

    const [file] = files;
    if (!file.name.endsWith('.csv')) {
        ui.showError('please drop a .csv file');
        return;
    }

    ui.printLine(`> uploading ${file.name}...`, 'warn');
    await uploadFile(file);
}

/**
 * Upload the CSV and render the resulting subscription info.
 * @param {File} file
 * @returns {Promise<void>}
 */
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const uploadResponse = await fetch(RESULTS_ENDPOINT, {
            method: 'POST',
            credentials: 'same-origin',
            body: formData,
        });

        if (!uploadResponse.ok) {
            const errorResponse = await safeReadJson(uploadResponse);
            if (uploadResponse.status === 401) {
                ui.showError('session expired, please refresh and login again');
                return;
            }
            ui.showError(errorResponse.detail || 'Failed to submit file');
            return;
        }

        /** @type {SubscriptionResponse} */
        const subscriptionResponse = await uploadResponse.json();
        if (subscriptionResponse.results.length > 0) {
            ui.updateResultsTable(subscriptionResponse.results);
        }
        ui.showSubscriptionResult(subscriptionResponse);
    } catch (error) {
        const message = error instanceof Error ? error.message : 'unknown error';
        ui.showError(`network error: ${message}`);
    }
}

/**
 * Parse an error response safely.
 * @param {Response} response
 * @returns {Promise<{detail?: string}>}
 */
async function safeReadJson(response) {
    try {
        return await response.json();
    } catch {
        return {};
    }
}
