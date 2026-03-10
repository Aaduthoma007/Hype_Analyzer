/**
 * BUZZ ANALYZER — FIGHT CLUB EDITION
 * "It's only after we've lost everything
 *  that we're free to do anything."
 *
 * Dashboard JavaScript — Chart.js + API layer
 */

// ── State ────────────────────────────────────────────────
let sentimentChart = null;
let refreshInterval = null;
let currentMovieId = null;
let activeTaskId = null;

// Flash State
let isFlashing = false;
let flashTimeout = null;
let glitchIntensity = 'normal';

const FLASH_CONFIG = {
    subtle: { firstDelay: 1300, minWait: 12000, maxWait: 18000 },
    normal: { firstDelay: 900, minWait: 8000, maxWait: 15000 },
    hardcore: { firstDelay: 350, minWait: 3000, maxWait: 7000 },
};

// Fight Club quotes for the rotating quote bar
const TYLER_QUOTES = [
    '"You are not your movie opinion. You are not your Rotten Tomatoes score. You are the all-singing, all-dancing <span>BUZZ SCORE</span> of the world."',
    '"The first rule of Buzz Club: <span>you do not fabricate</span> the Buzz Score."',
    '"I want you to analyze me <span>as hard</span> as you can."',
    '"It\'s only after we\'ve <span>analyzed everything</span> that we\'re free to score anything."',
    '"Sticking feathers up your butt <span>does not</span> make you a chicken. Data makes you <span>dangerous</span>."',
    '"This is your data. And it\'s ending <span>one comment</span> at a time."',
    '"The things you <span>stream</span> end up streaming you."',
    '"I am Jack\'s <span>complete sentiment analysis</span>."',
    '"Without pain, without sacrifice, <span>we would have nothing</span>. Like a movie with zero buzz."',
];

const FLASH_QUOTES = [
    "TRUST THE DATA.",
    "IT'S ONLY AFTER WE'VE LOST EVERYTHING...",
    "I AM JACK'S WASTED TIME.",
    "THIS IS YOUR BUZZ SCORE.",
    "PROJECT MAYHEM ON STANDBY.",
    "DO NOT FABRICATE.",
    "WAKE UP."
];

// ── API Helpers ──────────────────────────────────────────

async function apiFetch(endpoint) {
    const res = await fetch(endpoint);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

async function apiPost(endpoint, body) {
    const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.error || `API error: ${res.status}`);
    return payload;
}

// ── Toast ────────────────────────────────────────────────

function showToast(msg, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toastMsg');
    const toastIcon = document.getElementById('toastIcon');

    toastMsg.textContent = msg;
    toastIcon.textContent = type === 'success' ? '✓' : type === 'error' ? '✕' : '⚡';
    toast.className = `toast ${type} show`;

    setTimeout(() => toast.classList.remove('show'), 4000);
}


function setStatusBadge(label, state = 'idle') {
    const statusText = document.getElementById('statusText');
    const statusDot = document.getElementById('statusDot');
    if (!statusText || !statusDot) return;

    statusText.textContent = label;
    const colors = {
        idle: 'var(--blood-red)',
        running: 'var(--ember)',
        success: 'var(--blood-red)',
        failed: 'var(--ash)',
    };
    statusDot.style.background = colors[state] || colors.idle;
}

// ── Quote Rotation ───────────────────────────────────────

function rotateQuote() {
    const bar = document.getElementById('quoteBar');
    if (!bar) return;
    const quote = TYLER_QUOTES[Math.floor(Math.random() * TYLER_QUOTES.length)];
    bar.innerHTML = quote;
}

// ── Subliminal Flash ─────────────────────────────────────


function loadGlitchIntensityPreference() {
    const saved = localStorage.getItem('glitchIntensity');
    if (saved && FLASH_CONFIG[saved]) {
        glitchIntensity = saved;
    }

    const select = document.getElementById('glitchIntensity');
    if (select) select.value = glitchIntensity;
}

function setGlitchIntensity(value) {
    if (!FLASH_CONFIG[value]) return;
    glitchIntensity = value;
    localStorage.setItem('glitchIntensity', value);

    const flashContainer = document.getElementById('subliminalFlash');
    if (!flashContainer) return;

    flashContainer.classList.remove('intensity-subtle', 'intensity-normal', 'intensity-hardcore');
    flashContainer.classList.add(`intensity-${glitchIntensity}`);
}

function startSubliminalFlashes() {
    isFlashing = true;
    const flashContainer = document.getElementById('subliminalFlash');
    flashContainer.classList.remove('hidden');
    flashContainer.classList.add('active');
    setGlitchIntensity(glitchIntensity);

    triggerNextFlash(100); // Override config delay for immediate feedback
}

function stopSubliminalFlashes() {
    isFlashing = false;
    clearTimeout(flashTimeout);
    const flashContainer = document.getElementById('subliminalFlash');
    flashContainer.classList.add('hidden');
    flashContainer.classList.remove('active', 'flash-now');
}

function triggerNextFlash(delayMs = null) {
    if (!isFlashing) return;

    const config = FLASH_CONFIG[glitchIntensity] || FLASH_CONFIG.normal;
    // Fast glitch for rapid operations (1s to 2.5s)
    const nextWait = typeof delayMs === "number" ? delayMs : (Math.random() * 1500 + 1000);

    flashTimeout = setTimeout(() => {
        if (!isFlashing) return;

        const flashContainer = document.getElementById('subliminalFlash');

        // Pick random quote
        const quote = FLASH_QUOTES[Math.floor(Math.random() * FLASH_QUOTES.length)];
        flashContainer.innerHTML = `<span class="subliminal-text">${quote}</span>`;

        // Trigger CSS animation
        flashContainer.classList.add('flash-now');

        // Play click sound optionally? No, keep it visual for now

        // Remove class quickly (flash duration is ~200ms in CSS, we'll strip class after 250ms)
        setTimeout(() => {
            flashContainer.classList.remove('flash-now');
            triggerNextFlash(); // queue next flash
        }, 250);

    }, nextWait);
}

// ── Start Analysis ───────────────────────────────────────

async function startAnalysis() {
    const title = document.getElementById('movieTitle').value.trim();
    const videoId = document.getElementById('videoId').value.trim() || 'auto';

    if (!title) {
        showToast('Name your target first.', 'error');
        return;
    }

    const btn = document.getElementById('btnAnalyze');
    if (btn) {
        btn.classList.add('loading');
        btn.disabled = true;
    }
    setStatusBadge('Hunting...', 'running');

    // Show Progress Bar & Reset
    const progressContainer = document.getElementById('progressContainer');
    progressContainer.classList.remove('hidden');
    document.getElementById('progressPct').textContent = '0%';
    document.getElementById('progressMessage').textContent = 'STANDING BY...';
    document.getElementById('progressFill').style.width = '0%';

    // Start Fight Club flashes
    startSubliminalFlashes();

    try {
        const result = await apiPost('/api/run', {
            movie_title: title,
            video_id: videoId,
        });

        activeTaskId = result.task_id || null;
        showToast(`Target acquired: \"${title}\"`, 'info');
        startPolling(activeTaskId);

    } catch (err) {
        showToast('Mission failed: ' + err.message, 'error');
        setStatusBadge('Mission Failed', 'failed');
        stopSubliminalFlashes();
    } finally {
        setTimeout(() => {
            if (btn) {
                btn.classList.remove('loading');
                btn.disabled = false;
            }
        }, 2000);
    }
}

function startPolling(taskId) {
    if (refreshInterval) clearInterval(refreshInterval);

    if (!taskId) {
        showToast('Missing task reference. Unable to track progress.', 'error');
        stopSubliminalFlashes();
        return;
    }

    refreshInterval = setInterval(async () => {
        try {
            const status = await apiFetch(`/api/status/${encodeURIComponent(taskId)}`);
            const task = status.task || {};

            if (task.progress !== undefined) {
                document.getElementById('progressPct').textContent = `${task.progress}%`;
                document.getElementById('progressFill').style.width = `${task.progress}%`;
            }
            if (task.message) {
                document.getElementById('progressMessage').textContent = task.message;
            }
            if (task.message) {
                document.getElementById('progressMessage').textContent = task.message;
            }

            if (task.status === 'running') return;

            if (task.status === 'running') return;

            clearInterval(refreshInterval);
            refreshInterval = null;
            document.getElementById('statusText').textContent = 'Standing By';

            // Finalize Progress Bar
            document.getElementById('progressPct').textContent = '100%';
            document.getElementById('progressFill').style.width = '100%';
            setTimeout(() => {
                document.getElementById('progressContainer').classList.add('hidden');
            }, 1000);

            if (task.status === 'failed') {
                showToast(`Analysis failed: ${task.error || 'unknown error'}`, 'error');
            } else {
                showToast('Analysis complete. The score has been set.', 'success');
                loadDashboard(task.movie_title);
            }
            stopSubliminalFlashes();
            activeTaskId = null;
        } catch (e) {
            clearInterval(refreshInterval);
            refreshInterval = null;
            showToast(`Polling failed: ${e.message}`, 'error');
            stopSubliminalFlashes();
            activeTaskId = null;
        }
    }, 3000);
}

// ── Dashboard Rendering ──────────────────────────────────

async function loadDashboard(targetTitle = null) {
    try {
        const leaderboard = await apiFetch('/api/leaderboard');
        const entries = leaderboard.leaderboard || [];

        if (entries.length === 0) {
            showEmptyState();
            return;
        }

        let activeMovie = entries[0];

        // If a specific movie was requested (e.g., just finished analyzing)
        if (targetTitle) {
            const found = entries.find(m => m.title.toLowerCase() === targetTitle.toLowerCase());
            if (found) {
                activeMovie = found;
            }
        }

        currentMovieId = activeMovie.movie_id;
        renderDashboard(activeMovie, entries);

    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

function showEmptyState() {
    document.getElementById('dashboardContent').innerHTML = `
        <div class="empty-state card" id="emptyState">
            <div class="icon">🎬</div>
            <h3>No Targets Analyzed</h3>
            <p>"The things you own end up owning you." — Enter a movie title above and let the machine do its work.</p>
            <div class="rule-number">1st Rule of Buzz Club: You do not talk about the Buzz Score until it's calculated</div>
        </div>
    `;
}

function renderDashboard(movie, leaderboard) {
    const grid = document.getElementById('dashboardContent');

    // Determine buzz verdict
    let verdict, verdictStyle;
    if (movie.score >= 75) { verdict = 'MAXIMUM HYPE'; verdictStyle = 'color: var(--blood-red)'; }
    else if (movie.score >= 50) { verdict = 'CONTENDER'; verdictStyle = 'color: var(--ember)'; }
    else if (movie.score >= 25) { verdict = 'UNDERGROUND'; verdictStyle = 'color: var(--nicotine)'; }
    else { verdict = 'DEAD ON ARRIVAL'; verdictStyle = 'color: var(--ash)'; }

    grid.innerHTML = `
        <!-- Buzz Score Gauge -->
        <div class="card buzz-gauge-card">
            <div class="card-title"><span class="icon">👊</span> Buzz Score</div>
            <div class="gauge-container">
                <svg width="220" height="220" viewBox="0 0 220 220">
                    <circle class="gauge-bg" cx="110" cy="110" r="95"
                            transform="rotate(-90 110 110)"
                            stroke-dasharray="597" stroke-dashoffset="0" />
                    <circle class="gauge-fill" cx="110" cy="110" r="95" id="gaugeFill"
                            transform="rotate(-90 110 110)"
                            stroke-dasharray="597" stroke-dashoffset="597"
                            stroke="url(#gaugeGrad)" />
                    <defs>
                        <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#8b1a1a" />
                            <stop offset="50%" stop-color="#c41e1e" />
                            <stop offset="100%" stop-color="#d4602a" />
                        </linearGradient>
                    </defs>
                </svg>
                <div class="gauge-score">
                    <div class="gauge-number" id="gaugeNumber">0</div>
                    <div class="gauge-label">out of 100</div>
                </div>
            </div>
            <div class="gauge-sublabel">${escapeHtml(movie.title)}</div>
            <div style="font-family: 'Bebas Neue', sans-serif; font-size: 0.8rem; letter-spacing: 3px; margin-top: 0.3rem; ${verdictStyle}">${verdict}</div>
        </div>

        <!-- Sentiment Pie -->
        <div class="card sentiment-pie-card">
            <div class="card-title"><span class="icon">🩸</span> Sentiment Breakdown</div>
            <div class="pie-chart-container">
                <canvas id="sentimentPieChart"></canvas>
            </div>
            <div class="sentiment-legend">
                <div class="legend-item">
                    <span class="legend-dot hype"></span>
                    <span class="legend-label">High Hype</span>
                    <span class="legend-value">${(movie.high_hype_pct || 0).toFixed(1)}%</span>
                </div>
                <div class="legend-item">
                    <span class="legend-dot neutral"></span>
                    <span class="legend-label">Neutral / Curious</span>
                    <span class="legend-value">${(movie.neutral_pct || 0).toFixed(1)}%</span>
                </div>
                <div class="legend-item">
                    <span class="legend-dot negative"></span>
                    <span class="legend-label">Negative / Dead</span>
                    <span class="legend-value">${(movie.negative_pct || 0).toFixed(1)}%</span>
                </div>
            </div>
        </div>

        <!-- Score Breakdown -->
        <div class="card breakdown-card">
            <div class="card-title"><span class="icon">⚙️</span> The Formula</div>
            <div class="breakdown-bars">
                ${renderBreakdownBar('Sentiment', 'sentiment', movie.sentiment_avg ? ((movie.sentiment_avg - 1) / 2 * 100) : 0, 0.35)}
                ${renderBreakdownBar('Volume', 'volume', normalizeLog(movie.mention_volume || 0), 0.25)}
                ${renderBreakdownBar('Growth', 'growth', ((movie.growth_rate || 0) + 100) / 2, 0.20)}
                ${renderBreakdownBar('Engagement', 'engagement', movie.engagement || 0, 0.20)}
            </div>
        </div>

        <!-- Stats Row -->
        <div class="stats-row">
            <div class="card stat-card">
                <div class="stat-value red">${(movie.score || 0).toFixed(1)}</div>
                <div class="stat-label">Buzz Score</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value bone">${(movie.total_comments || 0).toLocaleString()}</div>
                <div class="stat-label">Comments Scraped</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value ember">${(movie.mention_volume || 0).toLocaleString()}</div>
                <div class="stat-label">Social Mentions</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value ash">${(movie.growth_rate || 0).toFixed(1)}%</div>
                <div class="stat-label">Growth Rate</div>
            </div>
        </div>

        <!-- Leaderboard -->
        <div class="card leaderboard-card">
            <div class="card-title"><span class="icon">🏴</span> The List</div>
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Target</th>
                        <th>Buzz</th>
                        <th>Sentiment</th>
                        <th>Intel</th>
                        <th>Reach</th>
                        <th>Timestamp</th>
                    </tr>
                </thead>
                <tbody>
                    ${leaderboard.map((m, i) => renderLeaderboardRow(m, i)).join('')}
                </tbody>
            </table>
        </div>
    `;

    animateGauge(movie.score || 0);
    renderSentimentPie(
        movie.high_hype_pct || 0,
        movie.neutral_pct || 0,
        movie.negative_pct || 0
    );
}

// ── Charts ───────────────────────────────────────────────

function renderSentimentPie(hype, neutral, negative) {
    const ctx = document.getElementById('sentimentPieChart');
    if (!ctx) return;

    if (sentimentChart) sentimentChart.destroy();

    sentimentChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['High Hype', 'Neutral / Curious', 'Negative / Dead'],
            datasets: [{
                data: [hype, neutral, negative],
                backgroundColor: [
                    '#c41e1e',   // blood red
                    '#b8a88a',   // nicotine
                    '#5a5348',   // ash
                ],
                borderColor: '#0a0a08',
                borderWidth: 3,
                hoverOffset: 6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '68%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(18, 18, 16, 0.95)',
                    titleFont: { family: "'Bebas Neue', sans-serif", size: 13 },
                    bodyFont: { family: "'Source Code Pro', monospace", size: 11 },
                    titleColor: '#d4c5a9',
                    bodyColor: '#8a7e6e',
                    borderColor: 'rgba(196, 30, 30, 0.3)',
                    borderWidth: 1,
                    cornerRadius: 0,
                    padding: 12,
                    callbacks: {
                        label: (ctx) => ` ${ctx.label}: ${ctx.parsed.toFixed(1)}%`,
                    },
                },
            },
            animation: {
                animateRotate: true,
                duration: 1500,
                easing: 'easeOutQuart',
            },
        },
    });
}

function animateGauge(score) {
    const circumference = 597;
    const offset = circumference - (score / 100) * circumference;
    const gaugeFill = document.getElementById('gaugeFill');
    const gaugeNumber = document.getElementById('gaugeNumber');

    if (!gaugeFill || !gaugeNumber) return;

    setTimeout(() => {
        gaugeFill.style.strokeDashoffset = offset;
    }, 400);

    let current = 0;
    const step = score / 80;
    const timer = setInterval(() => {
        current += step;
        if (current >= score) {
            current = score;
            clearInterval(timer);
        }
        gaugeNumber.textContent = current.toFixed(1);
    }, 18);
}

// ── Helpers ──────────────────────────────────────────────

function renderBreakdownBar(name, cls, value, weight) {
    const weighted = (value * weight).toFixed(1);
    const pct = Math.min(Math.max(value, 0), 100);
    return `
        <div class="breakdown-item">
            <div class="breakdown-header">
                <span class="breakdown-name">${name} (×${weight})</span>
                <span class="breakdown-value">${weighted}</span>
            </div>
            <div class="breakdown-bar">
                <div class="breakdown-bar-fill ${cls}" style="width: ${pct}%"></div>
            </div>
        </div>
    `;
}

function renderLeaderboardRow(movie, index) {
    const rank = index + 1;
    const rankClass = rank <= 3 ? `rank-${rank}` : 'rank-default';
    const buzzClass = movie.score >= 70 ? 'high' : movie.score >= 40 ? 'medium' : 'low';

    const hype = movie.high_hype_pct || 0;
    const neutral = movie.neutral_pct || 0;
    const negative = movie.negative_pct || 0;

    const date = movie.calculated_at
        ? new Date(movie.calculated_at + 'Z').toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        })
        : '—';

    return `
        <tr>
            <td><div class="rank-badge ${rankClass}">${rank}</div></td>
            <td class="movie-title-cell">${escapeHtml(movie.title)}</td>
            <td><span class="buzz-pill ${buzzClass}">${movie.score.toFixed(1)}</span></td>
            <td>
                <div class="sentiment-bar-mini">
                    <div class="seg-hype" style="width: ${hype}%"></div>
                    <div class="seg-neutral" style="width: ${neutral}%"></div>
                    <div class="seg-negative" style="width: ${negative}%"></div>
                </div>
            </td>
            <td>${(movie.total_comments || 0).toLocaleString()}</td>
            <td>${(movie.mention_volume || 0).toLocaleString()}</td>
            <td style="color: var(--text-muted); font-size: 0.75rem;">${date}</td>
        </tr>
    `;
}

function normalizeLog(val, max = 100000) {
    if (val <= 0) return 0;
    return (Math.log10(val + 1) / Math.log10(max + 1)) * 100;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ── Init ─────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    setStatusBadge('Standing By', 'idle');
    loadGlitchIntensityPreference();
    setGlitchIntensity(glitchIntensity);
    loadDashboard();

    // Rotate quotes every 12 seconds
    setInterval(rotateQuote, 12000);

    const intensitySelect = document.getElementById('glitchIntensity');
    if (intensitySelect) {
        intensitySelect.addEventListener('change', (e) => setGlitchIntensity(e.target.value));
    }

    // Keyboard shortcuts
    document.getElementById('videoId').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') startAnalysis();
    });
    document.getElementById('movieTitle').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') document.getElementById('videoId').focus();
    });
});
