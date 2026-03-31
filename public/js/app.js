/**
 * app.js — Minimal bootstrap that lazy-loads the secure flow on demand.
 */

const AUTH_MODULE_PATH = './auth.js?v=6.8';
const VERIFY_ENDPOINT = '/api/auth/verify';
const TRIGGER_CLICK_COUNT = 3;
const TRIGGER_WINDOW_MS = 2000;

let authModuleLoader = null;
let triggerClickCount = 0;
let triggerResetTimerId = null;
let hasStartedAuthFlow = false;

/**
 * Load the secure auth module only when it is actually needed.
 * @returns {Promise<typeof import('./auth.js')>}
 */
function loadAuthModule() {
    if (!authModuleLoader) {
        authModuleLoader = import(AUTH_MODULE_PATH);
    }
    return authModuleLoader;
}

/**
 * Initialize the hidden trigger on the article page.
 * The secure code path is fetched only after the trigger fires.
 * @returns {void}
 */
function initTrigger() {
    const icon = document.getElementById('cpu-icon');
    if (!icon) {
        return;
    }

    icon.addEventListener('click', () => {
        if (hasStartedAuthFlow) {
            return;
        }

        triggerClickCount += 1;
        clearTriggerTimer();
        triggerResetTimerId = window.setTimeout(resetTrigger, TRIGGER_WINDOW_MS);

        if (triggerClickCount >= TRIGGER_CLICK_COUNT) {
            void startSecureFlow();
        }
    });
}

/**
 * Restore an existing cookie-based session if one is still valid.
 * @returns {Promise<void>}
 */
async function tryRestoreSession() {
    try {
        const verifyResponse = await fetch(VERIFY_ENDPOINT, {
            credentials: 'same-origin',
        });
        if (!verifyResponse.ok) {
            return;
        }

        const auth = await loadAuthModule();
        const restored = await auth.checkSavedSession(true);
        if (restored) {
            hasStartedAuthFlow = true;
        }
    } catch (error) {
        console.error('Failed to restore saved session.', error);
    }
}

/**
 * Enter the secure auth flow after the hidden trigger fires.
 * @returns {Promise<void>}
 */
async function startSecureFlow() {
    resetTrigger();
    hasStartedAuthFlow = true;

    try {
        const auth = await loadAuthModule();
        await auth.startLoginFlow();
    } catch (error) {
        hasStartedAuthFlow = false;
        console.error('Failed to initialize secure flow.', error);
    }
}

/**
 * Reset the hidden trigger click state.
 * @returns {void}
 */
function resetTrigger() {
    triggerClickCount = 0;
    clearTriggerTimer();
}

/**
 * Clear the outstanding trigger timer if one exists.
 * @returns {void}
 */
function clearTriggerTimer() {
    if (triggerResetTimerId !== null) {
        window.clearTimeout(triggerResetTimerId);
        triggerResetTimerId = null;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initTrigger();
    void tryRestoreSession();
});
