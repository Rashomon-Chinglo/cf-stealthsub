/**
 * auth.js — Authentication logic loaded on demand.
 */

import * as ui from './ui.js?v=7.0';

const API_BASE = '/api';
const VERIFY_SESSION_ENDPOINT = `${API_BASE}/auth/verify`;
const LOGIN_ENDPOINT = `${API_BASE}/auth/login`;
const UPLOAD_MODULE_PATH = './upload.js?v=7.0';

let uploadModuleLoader = null;
let hasBoundCodeInput = false;

/**
 * @typedef {{ valid: boolean }} VerifyResponse
 * @typedef {{ expires_in: number, expires_at: number }} LoginSuccessResponse
 * @typedef {{ error?: string, remaining?: number, retry_after?: number }} AuthErrorDetail
 * @typedef {{ detail?: AuthErrorDetail | string }} AuthErrorResponse
 */

/**
 * Restore a valid cookie-backed session and jump straight into the optimizer.
 * @param {boolean} [alreadyVerified=false]
 * @returns {Promise<boolean>}
 */
export async function checkSavedSession(alreadyVerified = false) {
    try {
        if (!alreadyVerified) {
            const verifyResponse = await fetch(VERIFY_SESSION_ENDPOINT, {
                credentials: 'same-origin',
            });
            if (!verifyResponse.ok) {
                return false;
            }

            /** @type {VerifyResponse} */
            const verifyPayload = await verifyResponse.json();
            if (!verifyPayload.valid) {
                return false;
            }
        }

        ui.transitionTo('terminal');
        ui.clearTerminalOutput();
        ui.hideCodeInput();
        ui.printConsoleBanner();
        ui.printLine('> Existing session restored', 'ok');
        ui.printLine('> Loading workspace...');
        ui.printLine('');
        await openOptimizer();
        return true;
    } catch {
        return false;
    }
}

/**
 * Start the terminal-based login flow.
 * @returns {Promise<void>}
 */
export async function startLoginFlow() {
    ui.transitionTo('terminal');
    await showTerminalIntro();
}

/**
 * Load the upload module only after auth has succeeded.
 * @returns {Promise<typeof import('./upload.js')>}
 */
async function loadUploadModule() {
    if (!uploadModuleLoader) {
        uploadModuleLoader = import(UPLOAD_MODULE_PATH);
    }
    return uploadModuleLoader;
}

/**
 * Open the optimizer UI after session validation.
 * @returns {Promise<void>}
 */
async function openOptimizer() {
    ui.transitionTo('terminal');
    ui.hideCodeInput();
    const uploadModule = await loadUploadModule();
    await uploadModule.initUploadPhase();
}

/**
 * Render the terminal intro and bind the code input once.
 * @returns {Promise<void>}
 */
async function showTerminalIntro() {
    const introLines = [
        ui.CONSOLE_TITLE,
        ui.CONSOLE_DIVIDER,
        '',
        '> Establishing secure session...',
        '> Loading auth layer on demand...',
        '> Waiting for one-time verification code...',
        '',
    ];

    await ui.typeLines(introLines, 30);

    ui.showCodeInput();
    bindCodeInput();
}

/**
 * Bind the enter-to-submit handler once for the terminal input.
 * @returns {void}
 */
function bindCodeInput() {
    if (hasBoundCodeInput) {
        return;
    }

    const input = document.getElementById('code-input');
    if (!(input instanceof HTMLInputElement)) {
        return;
    }

    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && input.value.length === 6) {
            void submitCode(input.value);
        }
    });

    hasBoundCodeInput = true;
}

/**
 * Submit a TOTP code for authentication.
 * @param {string} code
 * @returns {Promise<void>}
 */
async function submitCode(code) {
    ui.setInputState(false);
    await ui.typeLine('> Verifying...');

    try {
        const loginResponse = await fetch(LOGIN_ENDPOINT, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ totp_code: code }),
        });

        if (loginResponse.ok) {
            /** @type {LoginSuccessResponse} */
            const loginPayload = await loginResponse.json();

            await ui.typeLines([
                '',
                '╔══════════════════════════════╗',
                '║      ✓ ACCESS GRANTED        ║',
                '╚══════════════════════════════╝',
                '',
                `> Session valid for: ${Math.floor(loginPayload.expires_in / 3600)}h`,
                '> Loading workspace...',
            ], 25);

            await ui.sleep(800);
            await openOptimizer();
            return;
        }

        /** @type {AuthErrorResponse} */
        const errorResponse = await safeReadJson(loginResponse);
        handleAuthFailure(errorResponse.detail);
    } catch (error) {
        console.error('Login request failed.', error);
        ui.addTerminalLine('> ✗ Network error. Please check your connection.', 'err');
        ui.setInputState(true);
    }
}

/**
 * Handle an auth failure response in a single place.
 * @param {AuthErrorDetail | string | undefined} detail
 * @returns {void}
 */
function handleAuthFailure(detail) {
    const errorDetail = typeof detail === 'string' ? { error: detail } : detail ?? {};

    if (errorDetail.error === 'TOO_MANY_ATTEMPTS') {
        ui.addTerminalLine(
            `> ⛔ Access restricted. Retry in ${errorDetail.retry_after ?? '?'}s.`,
            'err'
        );
        return;
    }

    ui.addTerminalLine(
        `> ✗ Verification failed. Remaining attempts: ${errorDetail.remaining ?? '?'}`,
        'err'
    );
    ui.setInputState(true);
}

/**
 * Parse a JSON response safely, falling back to an empty object.
 * @param {Response} response
 * @returns {Promise<AuthErrorResponse>}
 */
async function safeReadJson(response) {
    try {
        return await response.json();
    } catch {
        return {};
    }
}
