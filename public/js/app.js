/**
 * app.js — Application entry point and shared state.
 */

import { initTrigger, checkSavedSession } from './auth.js?v=6.6';

// ─── Global State ────────────────────────────────────────

export const state = {
    /** @type {string|null} Current session token */
    sessionToken: null,
};

// ─── Bootstrap ───────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Try to restore existing session first
    checkSavedSession();

    // Initialize the hidden trigger (triple-click on gear icon)
    initTrigger();
});
