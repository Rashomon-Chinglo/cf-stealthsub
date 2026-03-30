/**
 * auth.js — Authentication logic: trigger detection, terminal login, session management.
 */

import { state } from './app.js?v=6.6';
import { initUploadPhase as initOptimizer } from './upload.js?v=6.6';
import * as ui from './ui.js?v=6.6';

const API_BASE = '/api';

// ─── Trigger: Hidden Entry Point ─────────────────────────

/**
 * Initialize the triple-click trigger on the gear icon.
 */
export function initTrigger() {
    const icon = document.getElementById('cpu-icon');
    if (!icon) return;

    let clicks = 0;
    let timer = null;

    icon.addEventListener('click', () => {
        clicks++;
        clearTimeout(timer);
        timer = setTimeout(() => { clicks = 0; }, 2000);

        if (clicks >= 3) {
            clicks = 0;
            clearTimeout(timer);
            ui.transitionTo('terminal');
            showTerminalIntro();
        }
    });
}

// ─── Session Restore ─────────────────────────────────────

/**
 * Check if there's a saved session token and validate it.
 * If valid, skip directly to the optimizer.
 */
export async function checkSavedSession() {
    const token = sessionStorage.getItem('cf_session');
    if (!token) return;

    try {
        // Validate the session by hitting a protected endpoint
        const res = await fetch(`${API_BASE}/auth/verify`, {
            headers: { 'X-Session-Token': token },
        });
        if (res.ok) {
            state.sessionToken = token;
            ui.transitionTo('optimizer');
            initOptimizer();
        } else {
            sessionStorage.removeItem('cf_session');
        }
    } catch {
        sessionStorage.removeItem('cf_session');
    }
}

// ─── Terminal Login Flow ─────────────────────────────────

async function showTerminalIntro() {
    await ui.typeLines([
        'CF-IP-OPTIMIZER v0.2.0',
        '━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
        '',
        '> 初始化安全连接...',
        '> 加载认证模块...',
        '> 等待验证码输入...',
        '',
    ], 30);

    ui.showCodeInput();

    // Bind input handler
    const input = document.getElementById('code-input');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && input.value.length === 6) {
            submitCode(input.value);
        }
    });
}

/**
 * Submit TOTP code for authentication.
 * @param {string} code - 6-digit TOTP code
 */
async function submitCode(code) {
    ui.setInputState(false);
    await ui.typeLine('> 验证中...');

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ totp_code: code }),
        });
        const data = await res.json();

        if (res.ok) {
            state.sessionToken = data.session_token;
            sessionStorage.setItem('cf_session', data.session_token);

            await ui.typeLines([
                '',
                '╔══════════════════════════════╗',
                '║      ✓ ACCESS GRANTED        ║',
                '╚══════════════════════════════╝',
                '',
                `> Token 有效期: ${Math.floor(data.expires_in / 3600)}h`,
                '> 正在加载优选模块...',
            ], 25);

            await ui.sleep(800);
            ui.transitionTo('optimizer');
            initOptimizer();
        } else {
            const err = data.detail || data;
            if (err.error === 'TOO_MANY_ATTEMPTS') {
                ui.addTerminalLine(
                    `> ⛔ 访问受限，${err.retry_after}s 后重试`,
                    'error'
                );
            } else {
                ui.addTerminalLine(
                    `> ✗ 验证失败. 剩余尝试: ${err.remaining ?? '?'}`,
                    'error'
                );
                ui.setInputState(true);
            }
        }
    } catch (e) {
        ui.addTerminalLine('> ✗ 网络错误，请检查连接', 'error');
        ui.setInputState(true);
    }
}
