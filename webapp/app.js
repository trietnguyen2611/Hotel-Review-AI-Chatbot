/**
 * Hotel Aspect AI QA Studio - Frontend Application Logic
 * - 100% Vector SVGs (Zero emojis)
 * - Model.pt upload with progress and real-time backend reload
 * - Theme switcher with localStorage persistence
 * - Auto-scrolling within locked viewport container
 * - Interactive Google Maps & Collapsible Multi-Review Citations
 */

(function () {
    'use strict';

    // -------------------------------------------------------------------------
    // SVG Templates (Feather/Lucide style, stroke-width: 2)
    // -------------------------------------------------------------------------
    const SVG = {
        bot: `<svg class="svg-icon" viewBox="0 0 24 24"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>`,
        user: `<svg class="svg-icon" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
        hotel: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><path d="M3 21h18M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16M9 7h1M9 11h1M9 15h1M14 7h1M14 11h1M14 15h1M10 21v-3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3"/></svg>`,
        star: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
        mapPin: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
        calendar: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
        weight: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/></svg>`,
        chevron: `<svg class="svg-icon svg-icon-sm summary-chevron" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>`,
        externalLink: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
        book: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`
    };

    // -------------------------------------------------------------------------
    // Session State
    // -------------------------------------------------------------------------
    let sessionId = 'session_' + Math.random().toString(36).substring(2, 11);
    let isRequestPending = false;

    // DOM Elements
    const elements = {
        sidebar: document.getElementById('sidebar'),
        sidebarToggleBtn: document.getElementById('sidebarToggleBtn'),
        messagesContainer: document.getElementById('messagesContainer'),
        messagesList: document.getElementById('messagesList'),
        welcomeHero: document.getElementById('welcomeHero'),
        chatForm: document.getElementById('chatForm'),
        promptInput: document.getElementById('promptInput'),
        sendBtn: document.getElementById('sendBtn'),
        newChatBtn: document.getElementById('newChatBtn'),
        themeToggleBtn: document.getElementById('themeToggleBtn'),
        themeLabelText: document.getElementById('themeLabelText'),
        sunIcon: document.getElementById('sunIcon'),
        moonIcon: document.getElementById('moonIcon'),
        uploadDropzone: document.getElementById('uploadDropzone'),
        modelFileInput: document.getElementById('modelFileInput'),
        uploadProgressBar: document.getElementById('uploadProgressBar'),
        uploadProgressFill: document.getElementById('uploadProgressFill'),
        modelStatusLabel: document.getElementById('modelStatusLabel'),
        modelTypeBadge: document.getElementById('modelTypeBadge'),
        modelDetailsText: document.getElementById('modelDetailsText'),
        statHotelsCount: document.getElementById('statHotelsCount')
    };

    // -------------------------------------------------------------------------
    // Theme Management (Light / Dark)
    // -------------------------------------------------------------------------
    function initTheme() {
        const storedTheme = localStorage.getItem('theme');
        if (storedTheme) {
            setTheme(storedTheme);
        } else {
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            setTheme(prefersDark ? 'dark' : 'light');
        }
    }

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);

        if (theme === 'dark') {
            elements.sunIcon.style.display = 'inline-block';
            elements.moonIcon.style.display = 'none';
            elements.themeLabelText.textContent = 'Dark Mode';
        } else {
            elements.sunIcon.style.display = 'none';
            elements.moonIcon.style.display = 'inline-block';
            elements.themeLabelText.textContent = 'Light Mode';
        }
    }

    elements.themeToggleBtn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        setTheme(current === 'dark' ? 'light' : 'dark');
    });

    // -------------------------------------------------------------------------
    // Sidebar Mobile Toggle
    // -------------------------------------------------------------------------
    elements.sidebarToggleBtn.addEventListener('click', () => {
        elements.sidebar.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 840) {
            if (!elements.sidebar.contains(e.target) && !elements.sidebarToggleBtn.contains(e.target)) {
                elements.sidebar.classList.remove('open');
            }
        }
    });

    // -------------------------------------------------------------------------
    // Health Check & Stats
    // -------------------------------------------------------------------------
    async function checkHealth() {
        try {
            const res = await fetch('/api/health');
            if (res.ok) {
                const data = await res.json();
                if (data.hotels_loaded) {
                    elements.statHotelsCount.textContent = Number(data.hotels_loaded).toLocaleString();
                }
            }
        } catch (e) {
            console.warn('Backend health check delayed:', e);
        }
    }

    // -------------------------------------------------------------------------
    // Model Upload Handling (model.pt)
    // -------------------------------------------------------------------------
    elements.uploadDropzone.addEventListener('click', () => {
        elements.modelFileInput.click();
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        elements.uploadDropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            elements.uploadDropzone.classList.add('drag-active');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        elements.uploadDropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            elements.uploadDropzone.classList.remove('drag-active');
        }, false);
    });

    elements.uploadDropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    elements.modelFileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    function handleFileUpload(file) {
        if (!file.name.endsWith('.pt') && !file.name.endsWith('.bin') && !file.name.endsWith('.safetensors')) {
            alert('Please select a PyTorch model checkpoint (.pt, .bin, or .safetensors)');
            return;
        }

        const formData = new FormData();
        formData.append('model_file', file);

        elements.uploadProgressBar.style.display = 'block';
        elements.uploadProgressFill.style.width = '0%';
        elements.modelStatusLabel.textContent = 'Uploading...';
        elements.modelTypeBadge.textContent = 'Upload';

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload-model', true);

        xhr.upload.onprogress = function (e) {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                elements.uploadProgressFill.style.width = percent + '%';
                elements.modelStatusLabel.textContent = `Uploading ${percent}%`;
            }
        };

        xhr.onload = function () {
            elements.uploadProgressBar.style.display = 'none';
            if (xhr.status === 200) {
                try {
                    const res = JSON.parse(xhr.responseText);
                    elements.modelStatusLabel.textContent = 'Custom Checkpoint';
                    elements.modelTypeBadge.textContent = 'Loaded';
                    elements.modelDetailsText.textContent = `Successfully loaded ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB). Ready for inference.`;
                    showSystemNotification(`Model weights ${file.name} loaded successfully.`);
                } catch (err) {
                    handleUploadError('Invalid response from server');
                }
            } else {
                handleUploadError(`Upload failed with status code ${xhr.status}`);
            }
        };

        xhr.onerror = function () {
            elements.uploadProgressBar.style.display = 'none';
            handleUploadError('Network connection error during upload');
        };

        xhr.send(formData);
    }

    function handleUploadError(msg) {
        elements.modelStatusLabel.textContent = 'Upload Failed';
        elements.modelTypeBadge.textContent = 'Error';
        elements.modelDetailsText.textContent = msg;
        alert(msg);
    }

    function showSystemNotification(text) {
        const row = document.createElement('div');
        row.className = 'msg-row bot';
        row.innerHTML = `
            <div class="avatar-box bot">${SVG.bot}</div>
            <div class="msg-body">
                <div class="msg-bubble" style="border-left: 3px solid var(--success); font-size: 0.88rem;">
                    ${escapeHtml(text)}
                </div>
            </div>
        `;
        elements.messagesList.appendChild(row);
        scrollToBottom();
    }

    // -------------------------------------------------------------------------
    // Session Reset
    // -------------------------------------------------------------------------
    elements.newChatBtn.addEventListener('click', () => {
        sessionId = 'session_' + Math.random().toString(36).substring(2, 11);
        elements.messagesList.innerHTML = '';
        if (elements.welcomeHero) {
            elements.messagesList.appendChild(elements.welcomeHero);
        }
        elements.promptInput.value = '';
        elements.sendBtn.disabled = true;
        elements.promptInput.focus();
    });

    // -------------------------------------------------------------------------
    // Prompt Input Handling
    // -------------------------------------------------------------------------
    elements.promptInput.addEventListener('input', () => {
        elements.sendBtn.disabled = !elements.promptInput.value.trim() || isRequestPending;
        // Auto-expand textarea
        elements.promptInput.style.height = 'auto';
        elements.promptInput.style.height = Math.min(elements.promptInput.scrollHeight, 120) + 'px';
    });

    elements.promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!elements.sendBtn.disabled) {
                elements.chatForm.dispatchEvent(new Event('submit'));
            }
        }
    });

    // Suggestion chips delegation
    document.addEventListener('click', (e) => {
        const chip = e.target.closest('.suggestion-chip');
        if (chip) {
            const query = chip.getAttribute('data-query');
            if (query) {
                elements.promptInput.value = query;
                elements.sendBtn.disabled = false;
                elements.chatForm.dispatchEvent(new Event('submit'));
            }
        }
    });

    // -------------------------------------------------------------------------
    // Chat Submission & Rendering
    // -------------------------------------------------------------------------
    elements.chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = elements.promptInput.value.trim();
        if (!query || isRequestPending) return;

        // Hide welcome hero on first user query
        if (elements.welcomeHero && elements.welcomeHero.parentNode) {
            elements.welcomeHero.remove();
        }

        // Render User Message
        appendUserMessage(query);

        // Clear input
        elements.promptInput.value = '';
        elements.promptInput.style.height = 'auto';
        elements.sendBtn.disabled = true;
        isRequestPending = true;

        // Render Typing Indicator
        const typingId = appendTypingIndicator();
        scrollToBottom();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    query: query
                })
            });

            removeTypingIndicator(typingId);

            if (!response.ok) {
                throw new Error(`Server returned HTTP ${response.status}`);
            }

            const data = await response.json();
            appendBotMessage(data);
        } catch (err) {
            removeTypingIndicator(typingId);
            appendErrorMessage(`Unable to process request: ${err.message}. Please check if the backend server is running.`);
        } finally {
            isRequestPending = false;
            elements.sendBtn.disabled = !elements.promptInput.value.trim();
            scrollToBottom();
        }
    });

    function appendUserMessage(text) {
        const row = document.createElement('div');
        row.className = 'msg-row user';
        row.innerHTML = `
            <div class="avatar-box user">${SVG.user}</div>
            <div class="msg-body">
                <div class="msg-bubble">${escapeHtml(text)}</div>
            </div>
        `;
        elements.messagesList.appendChild(row);
        scrollToBottom();
    }

    function appendTypingIndicator() {
        const id = 'typing_' + Date.now();
        const row = document.createElement('div');
        row.className = 'msg-row bot';
        row.id = id;
        row.innerHTML = `
            <div class="avatar-box bot">${SVG.bot}</div>
            <div class="msg-body">
                <div class="msg-bubble">
                    <div class="typing-dots">
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                    </div>
                </div>
            </div>
        `;
        elements.messagesList.appendChild(row);
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function appendErrorMessage(msg) {
        const row = document.createElement('div');
        row.className = 'msg-row bot';
        row.innerHTML = `
            <div class="avatar-box bot">${SVG.bot}</div>
            <div class="msg-body">
                <div class="msg-bubble" style="border-left: 3px solid var(--danger);">
                    ${escapeHtml(msg)}
                </div>
            </div>
        `;
        elements.messagesList.appendChild(row);
    }

    function appendBotMessage(data) {
        const row = document.createElement('div');
        row.className = 'msg-row bot';

        // 1. Meta Badges
        let metaHtml = '';
        if (data.hotel_name) {
            const starClass = data.star && data.star.includes('star') ? 'star' : '';
            const sentimentClass = data.sentiment ? `sentiment-${data.sentiment.toLowerCase()}` : '';

            metaHtml = `
                <div class="hotel-meta-row">
                    <span class="meta-pill">
                        ${SVG.hotel}
                        <span>${escapeHtml(data.hotel_name)}</span>
                    </span>
                    ${data.star ? `
                        <span class="meta-pill ${starClass}">
                            ${SVG.star}
                            <span>${escapeHtml(data.star)}</span>
                        </span>
                    ` : ''}
                    ${data.aspect_title ? `
                        <span class="meta-pill aspect">
                            ${SVG.bot}
                            <span>${escapeHtml(data.aspect_title)}</span>
                        </span>
                    ` : ''}
                    ${data.sentiment ? `
                        <span class="meta-pill ${sentimentClass}">
                            <span>${escapeHtml(data.sentiment)}</span>
                        </span>
                    ` : ''}
                </div>
            `;
        }

        // 2. Google Maps Embed Card (Zero emojis)
        let mapsHtml = '';
        if (data.maps_card && data.maps_card.embed_url) {
            mapsHtml = `
                <div class="maps-card-wrapper">
                    <div class="maps-header">
                        <div class="maps-title">
                            ${SVG.mapPin}
                            <span>${escapeHtml(data.maps_card.hotel_name || 'Hotel Location')}</span>
                        </div>
                        <a href="${escapeHtml(data.maps_card.search_url)}" target="_blank" rel="noopener noreferrer" class="maps-link-btn">
                            <span>Open in Google Maps</span>
                            ${SVG.externalLink}
                        </a>
                    </div>
                    <iframe class="maps-iframe" src="${escapeHtml(data.maps_card.embed_url)}" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade"></iframe>
                </div>
            `;
        }

        // 3. Collapsible Multi-Review Citations (Feature 10 Weighted)
        let collapsibleHtml = '';
        if (data.original_reviews && data.original_reviews.length > 0) {
            const reviewItems = data.original_reviews.map(r => `
                <div class="review-item-card">
                    <div class="review-item-header">
                        <div class="review-item-header-left">
                            ${SVG.calendar}
                            <span>${escapeHtml(r.date)}</span>
                            <span style="display:inline-flex; align-items:center; gap:2px; margin-left:6px; color:var(--warning);">
                                ${SVG.star} ${r.score}/5.0
                            </span>
                        </div>
                        <div class="review-item-weight" title="Feature 10 Exponential Recency Weight w = exp(-0.03 * delta_m)">
                            ${SVG.weight} Weight: ${r.recency_weight}
                        </div>
                    </div>
                    <div class="review-item-text">
                        &ldquo;${escapeHtml(r.text)}&rdquo;
                    </div>
                </div>
            `).join('');

            collapsibleHtml = `
                <details class="original-reviews-toggle">
                    <summary>
                        <div class="summary-left">
                            ${SVG.book}
                            <span>View original reviews (${data.original_reviews.length} analyzed)</span>
                        </div>
                        ${SVG.chevron}
                    </summary>
                    <div class="reviews-list-body">
                        ${reviewItems}
                    </div>
                </details>
            `;
        }

        row.innerHTML = `
            <div class="avatar-box bot">${SVG.bot}</div>
            <div class="msg-body">
                <div class="msg-bubble">
                    ${metaHtml}
                    <div style="font-size: 0.94rem; line-height: 1.6; margin-top: 4px;">
                        ${escapeHtml(data.answer)}
                    </div>
                    ${mapsHtml}
                    ${collapsibleHtml}
                </div>
            </div>
        `;

        elements.messagesList.appendChild(row);
        scrollToBottom();
    }

    function scrollToBottom() {
        elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/[&<>"']/g, function (m) {
            return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
        });
    }

    // -------------------------------------------------------------------------
    // Initialization
    // -------------------------------------------------------------------------
    initTheme();
    checkHealth();

})();
