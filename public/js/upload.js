import * as ui from './ui.js?v=6.6';
import { state } from './app.js?v=6.6';

export async function initUploadPhase() {
    // Show download links and instructions
    ui.printOptHeader();
    ui.printLine('> 权限校验完毕', 'ok');
    ui.printLine('please download CloudflareSpeedTest native scanner:', 'dim');

    ui.printDownloadButton('Windows (amd64) .zip', '/optimize/downloads/cfst_windows_amd64.zip');
    ui.printDownloadButton('Linux (amd64) .tar.gz', '/optimize/downloads/cfst_linux_amd64.tar.gz');
    ui.printDownloadButton('Linux (arm64) .tar.gz', '/optimize/downloads/cfst_linux_arm64.tar.gz');

    ui.printLine('');
    ui.printLine('run the scanner in your terminal. it will generate a result.csv.', 'dim');
    ui.printLine('');

    // Setup drag and drop area
    ui.renderUploadArea();

    const dropZone = document.getElementById('drop-zone');

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop zone
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('highlight');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('highlight');
        }, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', handleDrop, false);
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

async function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files.length === 0) return;

    const file = files[0];
    if (!file.name.endsWith('.csv')) {
        ui.showError('please drop a .csv file');
        return;
    }

    ui.printLine(`> uploading ${file.name}...`, 'warn');
    await uploadFile(file);
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/results', {
            method: 'POST',
            headers: {
                'X-Session-Token': state.sessionToken
            },
            body: formData
        });

        if (res.ok) {
            const data = await res.json();
            if (data.results && data.results.length > 0) {
                ui.updateResultsTable(data.results);
            }
            ui.showSubscriptionResult(data);
        } else {
            let errDetail = 'Failed to submit file';
            try {
                const errJson = await res.json();
                if (errJson.detail) errDetail = errJson.detail;
            } catch (e) { }
            ui.showError(errDetail);
        }
    } catch (e) {
        ui.showError('network error: ' + e.message);
    }
}
