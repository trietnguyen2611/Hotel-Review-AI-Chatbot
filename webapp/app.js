/**
 * Hotel Aspect AI QA Studio - Frontend Application Logic
 * - 100% Vector SVGs (Zero emojis)
 * - Multi-conversation state management (Pin/Unpin, Delete, LocalStorage persistence)
 * - Responsive Collapsible Sidebar (Desktop & Mobile with backdrop scrim)
 * - Transparent Topbar with active model status and model.pt upload
 * - Interactive Google Maps & Collapsible Multi-Review Citations
 * - Auto-scrolling within locked viewport with top scroll dissolve mask
 */

(function () {
    'use strict';

    // -------------------------------------------------------------------------
    // SVG Templates (Feather/Lucide style, stroke-width: 2, 100% Vector)
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
        book: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`,
        message: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
        edit: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`,
        pin: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14l-2-6V4H7v7l-2 6z"/><line x1="9" y1="4" x2="9" y2="2"/><line x1="15" y1="4" x2="15" y2="2"/></svg>`,
        pinFilled: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24" style="fill: currentColor;"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14l-2-6V4H7v7l-2 6z"/><line x1="9" y1="4" x2="9" y2="2"/><line x1="15" y1="4" x2="15" y2="2"/></svg>`,
        trash: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`
    };

    // -------------------------------------------------------------------------
    // Storage Keys & State
    // -------------------------------------------------------------------------
    const STORAGE_CONVERSATIONS_KEY = 'hotel_qa_conversations_v1';
    const STORAGE_ACTIVE_ID_KEY = 'hotel_qa_active_conv_id';
    const STORAGE_SIDEBAR_COLLAPSED_KEY = 'hotel_qa_sidebar_collapsed';

    let conversations = [];
    let activeConvId = null;
    let isRequestPending = false;

    // DOM Elements
    const elements = {
        appLayout: document.querySelector('.app-layout'),
        sidebar: document.getElementById('sidebar'),
        sidebarToggleBtn: document.getElementById('sidebarToggleBtn'),
        sidebarBackdrop: document.getElementById('sidebarBackdrop'),
        newChatBtn: document.getElementById('newChatBtn'),
        pinnedSection: document.getElementById('pinnedSection'),
        pinnedList: document.getElementById('pinnedList'),
        recentSection: document.getElementById('recentSection'),
        recentList: document.getElementById('recentList'),
        activeChatTitle: document.getElementById('activeChatTitle'),

        modelDropdownWrapper: document.getElementById('modelDropdownWrapper'),
        modelSelectorBtn: document.getElementById('modelSelectorBtn'),
        currentModelLabel: document.getElementById('currentModelLabel'),
        modelDropdownMenu: document.getElementById('modelDropdownMenu'),
        modelDropdownList: document.getElementById('modelDropdownList'),

        topbarBrowseBtn: document.getElementById('topbarBrowseBtn'),
        hotelCarouselSection: document.getElementById('hotelCarouselSection'),
        cityFilterBar: document.getElementById('cityFilterBar'),
        hotelSearchInput: document.getElementById('hotelSearchInput'),
        carouselToggleBtn: document.getElementById('carouselToggleBtn'),
        hotelCarouselTrack: document.getElementById('hotelCarouselTrack'),
        activeHotelBanner: document.getElementById('activeHotelBanner'),
        activeHotelTitle: document.getElementById('activeHotelTitle'),
        activeHotelTag: document.getElementById('activeHotelTag'),
        changeHotelBtn: document.getElementById('changeHotelBtn'),
        deselectHotelBtn: document.getElementById('deselectHotelBtn'),
        quickAspectPills: document.getElementById('quickAspectPills'),

        messagesContainer: document.getElementById('messagesContainer'),
        messagesList: document.getElementById('messagesList'),
        welcomeHero: document.getElementById('welcomeHero'),
        chatForm: document.getElementById('chatForm'),
        promptInput: document.getElementById('promptInput'),
        sendBtn: document.getElementById('sendBtn'),

        themeToggleBtn: document.getElementById('themeToggleBtn'),
        themeLabelText: document.getElementById('themeLabelText'),
        sunIcon: document.getElementById('sunIcon'),
        moonIcon: document.getElementById('moonIcon')
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

        // Icon must strictly match the current active mode
        if (theme === 'dark') {
            elements.sunIcon.style.display = 'none';
            elements.moonIcon.style.display = 'inline-block';
            elements.themeLabelText.textContent = 'Dark Mode';
        } else {
            elements.sunIcon.style.display = 'inline-block';
            elements.moonIcon.style.display = 'none';
            elements.themeLabelText.textContent = 'Light Mode';
        }
    }

    elements.themeToggleBtn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        setTheme(current === 'dark' ? 'light' : 'dark');
    });

    // -------------------------------------------------------------------------
    // Sidebar Collapse / Expand Mechanism (Desktop & Mobile)
    // -------------------------------------------------------------------------
    function initSidebar() {
        // Restore desktop collapse state
        const isCollapsed = localStorage.getItem(STORAGE_SIDEBAR_COLLAPSED_KEY) === 'true';
        if (isCollapsed && window.innerWidth > 840) {
            elements.appLayout.classList.add('sidebar-collapsed');
        }

        elements.sidebarToggleBtn.addEventListener('click', () => {
            if (window.innerWidth <= 840) {
                // Mobile Drawer
                const isOpen = elements.sidebar.classList.toggle('open');
                elements.sidebarBackdrop.classList.toggle('active', isOpen);
            } else {
                // Desktop Collapse/Expand
                const collapsed = elements.appLayout.classList.toggle('sidebar-collapsed');
                localStorage.setItem(STORAGE_SIDEBAR_COLLAPSED_KEY, collapsed);
            }
        });

        if (elements.sidebarBackdrop) {
            elements.sidebarBackdrop.addEventListener('click', () => {
                closeMobileSidebar();
            });
        }
    }

    function closeMobileSidebar() {
        elements.sidebar.classList.remove('open');
        if (elements.sidebarBackdrop) {
            elements.sidebarBackdrop.classList.remove('active');
        }
    }

    // -------------------------------------------------------------------------
    // Multi-Conversation State Management
    // -------------------------------------------------------------------------
    function createNewConversationData(title = 'New Conversation') {
        const id = 'conv_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
        return {
            id: id,
            title: title,
            createdAt: Date.now(),
            updatedAt: Date.now(),
            pinned: false,
            sessionId: 'session_' + Math.random().toString(36).substring(2, 11),
            selectedHotel: null,
            messages: []
        };
    }

    function loadConversations() {
        try {
            const raw = localStorage.getItem(STORAGE_CONVERSATIONS_KEY);
            if (raw) {
                conversations = JSON.parse(raw);
            }
        } catch (e) {
            console.warn('Failed to parse conversations from localStorage:', e);
            conversations = [];
        }

        if (!Array.isArray(conversations) || conversations.length === 0) {
            const initial = createNewConversationData('New Conversation');
            conversations = [initial];
            activeConvId = initial.id;
            saveConversations();
        } else {
            const savedActiveId = localStorage.getItem(STORAGE_ACTIVE_ID_KEY);
            const found = conversations.find(c => c.id === savedActiveId);
            activeConvId = found ? found.id : conversations[0].id;
        }
    }

    function saveConversations() {
        try {
            localStorage.setItem(STORAGE_CONVERSATIONS_KEY, JSON.stringify(conversations));
            if (activeConvId) {
                localStorage.setItem(STORAGE_ACTIVE_ID_KEY, activeConvId);
            }
        } catch (e) {
            console.warn('Failed to save conversations to localStorage:', e);
        }
    }

    function getActiveConversation() {
        let conv = conversations.find(c => c.id === activeConvId);
        if (!conv) {
            conv = conversations[0];
            activeConvId = conv ? conv.id : null;
        }
        return conv;
    }

    function handleNewChat() {
        const newConv = createNewConversationData('New Conversation');
        conversations.unshift(newConv);
        activeConvId = newConv.id;
        saveConversations();
        renderConversationLists();
        renderActiveConversationMessages();
        updateActiveHotelBanner();
        highlightSelectedCard();

        // Main screen displays hotel selection cards first
        if (elements.hotelCarouselSection) {
            elements.hotelCarouselSection.classList.remove('collapsed');
        }
        if (elements.carouselToggleBtn) {
            elements.carouselToggleBtn.classList.remove('collapsed');
        }

        elements.promptInput.value = '';
        elements.promptInput.placeholder = 'Ask about a hotel or select a card above...';
        elements.sendBtn.disabled = true;
        elements.promptInput.focus();

        if (window.innerWidth <= 840) {
            closeMobileSidebar();
        }
    }

    function switchConversation(id) {
        if (activeConvId === id) return;
        activeConvId = id;
        saveConversations();
        renderConversationLists();
        renderActiveConversationMessages();
        updateActiveHotelBanner();
        highlightSelectedCard();

        const conv = getActiveConversation();
        if (conv && conv.selectedHotel) {
            if (elements.hotelCarouselSection) {
                elements.hotelCarouselSection.classList.add('collapsed');
            }
            if (elements.carouselToggleBtn) {
                elements.carouselToggleBtn.classList.add('collapsed');
            }
            elements.promptInput.placeholder = `Ask anything about ${conv.selectedHotel.hotel_name}...`;
        } else {
            if (elements.hotelCarouselSection) {
                elements.hotelCarouselSection.classList.remove('collapsed');
            }
            if (elements.carouselToggleBtn) {
                elements.carouselToggleBtn.classList.remove('collapsed');
            }
            elements.promptInput.placeholder = 'Ask about a hotel or select a card above...';
        }

        elements.promptInput.value = '';
        elements.sendBtn.disabled = true;
        elements.promptInput.focus();

        if (window.innerWidth <= 840) {
            closeMobileSidebar();
        }
    }

    function togglePinConversation(id, e) {
        if (e) e.stopPropagation();
        const conv = conversations.find(c => c.id === id);
        if (conv) {
            conv.pinned = !conv.pinned;
            conv.updatedAt = Date.now();
            saveConversations();
            renderConversationLists();
        }
    }

    function deleteConversation(id, e) {
        if (e) e.stopPropagation();
        const conv = conversations.find(c => c.id === id);
        if (!conv) return;

        const confirmTitle = conv.title || 'this conversation';
        if (!confirm(`Delete conversation "${confirmTitle}"?`)) return;

        conversations = conversations.filter(c => c.id !== id);

        if (conversations.length === 0) {
            const initial = createNewConversationData('New Conversation');
            conversations = [initial];
            activeConvId = initial.id;
        } else if (activeConvId === id) {
            activeConvId = conversations[0].id;
        }

        saveConversations();
        renderConversationLists();
        renderActiveConversationMessages();
    }

    function createConvItemHtml(conv) {
        const isActive = conv.id === activeConvId;
        const pinIcon = conv.pinned ? SVG.pinFilled : SVG.pin;
        const pinTitle = conv.pinned ? 'Unpin conversation' : 'Pin conversation';
        const pinClass = conv.pinned ? 'conv-action-btn pin-btn is-pinned' : 'conv-action-btn pin-btn';

        return `
            <div class="conv-item ${isActive ? 'active' : ''}" data-conv-id="${escapeHtml(conv.id)}" role="button" tabindex="0">
                <div class="conv-item-left">
                    ${SVG.message}
                    <div class="conv-item-title-wrap">
                        <span class="conv-item-title" title="${escapeHtml(conv.title || 'Conversation')}">${escapeHtml(conv.title || 'Conversation')}</span>
                    </div>
                </div>
                <div class="conv-actions">
                    <button type="button" class="conv-action-btn edit-btn" data-action="rename" title="Rename conversation" aria-label="Rename conversation">
                        ${SVG.edit}
                    </button>
                    <button type="button" class="${pinClass}" data-action="pin" title="${pinTitle}" aria-label="${pinTitle}">
                        ${pinIcon}
                    </button>
                    <button type="button" class="conv-action-btn delete-btn" data-action="delete" title="Delete conversation" aria-label="Delete conversation">
                        ${SVG.trash}
                    </button>
                </div>
            </div>
        `;
    }

    function renderConversationLists() {
        const pinned = conversations.filter(c => c.pinned).sort((a, b) => b.updatedAt - a.updatedAt);
        const recent = conversations.filter(c => !c.pinned).sort((a, b) => b.updatedAt - a.updatedAt);

        // Pinned section
        if (pinned.length > 0) {
            elements.pinnedSection.style.display = 'flex';
            elements.pinnedList.innerHTML = pinned.map(c => createConvItemHtml(c)).join('');
        } else {
            elements.pinnedSection.style.display = 'none';
            elements.pinnedList.innerHTML = '';
        }

        // Recent section
        if (recent.length > 0) {
            elements.recentList.innerHTML = recent.map(c => createConvItemHtml(c)).join('');
        } else {
            elements.recentList.innerHTML = '<div style="padding: 10px 8px; font-size: 0.76rem; color: var(--text-muted); font-style: italic;">No recent conversations</div>';
        }

        const currentConv = getActiveConversation();
        if (currentConv && elements.activeChatTitle) {
            elements.activeChatTitle.textContent = currentConv.title || 'New Conversation';
        }
    }

    // -------------------------------------------------------------------------
    // Conversation Renaming
    // -------------------------------------------------------------------------
    function startRenameConversation(convId) {
        const conv = conversations.find(c => c.id === convId);
        if (!conv) return;

        const convItem = document.querySelector(`.conv-item[data-conv-id="${convId}"]`);
        if (!convItem) return;

        const titleWrap = convItem.querySelector('.conv-item-title-wrap');
        const actionsWrap = convItem.querySelector('.conv-actions');
        if (!titleWrap) return;

        const originalTitle = conv.title || 'Conversation';
        titleWrap.innerHTML = `<input type="text" class="conv-title-input" value="${escapeHtml(originalTitle)}" maxlength="80">`;
        if (actionsWrap) actionsWrap.style.display = 'none';

        const input = titleWrap.querySelector('input');
        input.focus();
        input.select();

        let isFinished = false;

        function commitRename() {
            if (isFinished) return;
            isFinished = true;
            const newTitle = input.value.trim();
            if (newTitle && newTitle !== originalTitle) {
                conv.title = newTitle;
                conv.updatedAt = Date.now();
                saveConversations();
            }
            renderConversationLists();
        }

        function cancelRename() {
            if (isFinished) return;
            isFinished = true;
            renderConversationLists();
        }

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                e.stopPropagation();
                commitRename();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                cancelRename();
            }
        });

        input.addEventListener('blur', () => {
            commitRename();
        });

        input.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    function handleConvListClick(e) {
        // If clicking inside rename input, ignore
        if (e.target.classList.contains('conv-title-input')) return;

        const actionBtn = e.target.closest('button[data-action]');
        const convItem = e.target.closest('.conv-item');
        if (!convItem) return;
        const convId = convItem.getAttribute('data-conv-id');

        if (actionBtn) {
            e.stopPropagation();
            const action = actionBtn.getAttribute('data-action');
            if (action === 'rename') {
                startRenameConversation(convId);
            } else if (action === 'pin') {
                togglePinConversation(convId, e);
            } else if (action === 'delete') {
                deleteConversation(convId, e);
            }
            return;
        }

        switchConversation(convId);
    }

    function handleConvListKeydown(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            if (e.target.classList.contains('conv-title-input')) return;
            const convItem = e.target.closest('.conv-item');
            if (convItem && !e.target.closest('button[data-action]')) {
                e.preventDefault();
                handleConvListClick(e);
            }
        }
    }

    elements.pinnedList.addEventListener('click', handleConvListClick);
    elements.pinnedList.addEventListener('keydown', handleConvListKeydown);
    elements.recentList.addEventListener('click', handleConvListClick);
    elements.recentList.addEventListener('keydown', handleConvListKeydown);
    elements.newChatBtn.addEventListener('click', handleNewChat);

    // -------------------------------------------------------------------------
    // Project Model Selection (from folder model/)
    // -------------------------------------------------------------------------
    let availableModels = [];

    async function fetchModels() {
        try {
            const res = await fetch('/api/models');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            availableModels = data.models || [];

            if (data.active_model && elements.currentModelLabel) {
                elements.currentModelLabel.textContent = data.active_model;
            }

            renderModelDropdownList(availableModels, data.active_model);
        } catch (e) {
            console.warn('Could not fetch models:', e);
            if (elements.modelDropdownList) {
                elements.modelDropdownList.innerHTML = `<div class="model-dropdown-empty">Failed to load models</div>`;
            }
        }
    }

    function renderModelDropdownList(models, activeName) {
        if (!elements.modelDropdownList) return;
        if (!models || models.length === 0) {
            elements.modelDropdownList.innerHTML = `<div class="model-dropdown-empty">No checkpoints found in model/</div>`;
            return;
        }

        elements.modelDropdownList.innerHTML = models.map(m => {
            const isActive = m.active || m.is_active || (m.name === activeName);
            return `
                <button type="button" class="model-dropdown-item ${isActive ? 'active' : ''}" data-model-name="${escapeHtml(m.name)}">
                    <div class="model-item-info">
                        <span class="model-item-name">${escapeHtml(m.name)}</span>
                        <span class="model-item-size">${m.size_mb.toFixed(1)} MB</span>
                    </div>
                    ${isActive ? `<span class="model-item-badge">Active</span>` : ''}
                </button>
            `;
        }).join('');
    }

    async function selectModel(modelName) {
        if (!modelName) return;
        try {
            if (elements.currentModelLabel) {
                elements.currentModelLabel.textContent = 'Loading...';
            }
            closeModelDropdown();

            const res = await fetch('/api/select-model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: modelName })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.error || errData.detail || errData.message || `HTTP ${res.status}`);
            }

            const data = await res.json();
            if (elements.currentModelLabel) {
                elements.currentModelLabel.textContent = data.active_model || modelName;
            }
            showSystemNotification(`Active model switched to: ${data.active_model || modelName}`);
            await fetchModels();
        } catch (e) {
            alert(`Failed to load model: ${e.message}`);
            await fetchModels();
        }
    }

    function toggleModelDropdown() {
        if (!elements.modelDropdownMenu) return;
        const isHidden = elements.modelDropdownMenu.style.display === 'none';
        if (isHidden) {
            elements.modelDropdownMenu.style.display = 'block';
            if (elements.modelSelectorBtn) {
                elements.modelSelectorBtn.setAttribute('aria-expanded', 'true');
            }
        } else {
            closeModelDropdown();
        }
    }

    function closeModelDropdown() {
        if (elements.modelDropdownMenu) {
            elements.modelDropdownMenu.style.display = 'none';
        }
        if (elements.modelSelectorBtn) {
            elements.modelSelectorBtn.setAttribute('aria-expanded', 'false');
        }
    }

    function initModelSelector() {
        if (elements.modelSelectorBtn) {
            elements.modelSelectorBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleModelDropdown();
            });
        }

        if (elements.modelDropdownList) {
            elements.modelDropdownList.addEventListener('click', (e) => {
                const item = e.target.closest('.model-dropdown-item');
                if (item) {
                    const modelName = item.getAttribute('data-model-name');
                    if (modelName) {
                        selectModel(modelName);
                    }
                }
            });
        }

        document.addEventListener('click', (e) => {
            if (elements.modelDropdownWrapper && !elements.modelDropdownWrapper.contains(e.target)) {
                closeModelDropdown();
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeModelDropdown();
            }
        });

        fetchModels();
    }

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

    // -------------------------------------------------------------------------
    // Chat Submission & Rendering
    // -------------------------------------------------------------------------
    elements.chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = elements.promptInput.value.trim();
        if (!query || isRequestPending) return;

        const conv = getActiveConversation();
        if (!conv) return;

        // Auto-title if still default
        if (conv.title === 'New Conversation' || !conv.title) {
            const cleanTitle = query.replace(/\s+/g, ' ').trim();
            conv.title = cleanTitle.length > 60 ? cleanTitle.slice(0, 60) + '...' : cleanTitle;
            elements.activeChatTitle.textContent = conv.title;
        }

        // Hide welcome hero on user query
        if (elements.welcomeHero && elements.welcomeHero.parentNode) {
            elements.welcomeHero.remove();
        }

        // Add user message to conversation history
        conv.messages.push({
            role: 'user',
            text: query,
            timestamp: Date.now()
        });
        conv.updatedAt = Date.now();
        saveConversations();
        renderConversationLists();

        // Render user message to DOM
        renderUserMessageNode(query);

        // Clear input
        elements.promptInput.value = '';
        elements.promptInput.style.height = 'auto';
        elements.sendBtn.disabled = true;
        isRequestPending = true;

        // Render Typing Indicator
        const typingId = appendTypingIndicator();
        scrollToBottom();

        try {
            const chatPayload = {
                session_id: conv.sessionId,
                query: query,
                selected_hotel: (conv.selectedHotel && conv.selectedHotel.hotel_name) ? conv.selectedHotel.hotel_name : ""
            };

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(chatPayload)
            });

            removeTypingIndicator(typingId);

            if (!response.ok) {
                throw new Error(`Server returned HTTP ${response.status}`);
            }

            const data = await response.json();

            // Add bot message to conversation history
            conv.messages.push({
                role: 'bot',
                data: data,
                timestamp: Date.now()
            });
            conv.updatedAt = Date.now();
            saveConversations();

            // Render bot message to DOM only if this conversation is still active
            if (activeConvId === conv.id) {
                renderBotMessageNode(data);
                scrollToBottom();
            }
        } catch (err) {
            removeTypingIndicator(typingId);
            const errMsg = `Unable to process request: ${err.message}. Please check if the backend server is running.`;
            conv.messages.push({
                role: 'error',
                text: errMsg,
                timestamp: Date.now()
            });
            conv.updatedAt = Date.now();
            saveConversations();

            // Render error message to DOM only if this conversation is still active
            if (activeConvId === conv.id) {
                renderErrorMessageNode(errMsg);
                scrollToBottom();
            }
        } finally {
            isRequestPending = false;
            elements.sendBtn.disabled = !elements.promptInput.value.trim();
        }
    });

    // -------------------------------------------------------------------------
    // DOM Message Nodes
    // -------------------------------------------------------------------------
    function renderActiveConversationMessages() {
        elements.messagesList.innerHTML = '';
        const conv = getActiveConversation();
        if (!conv || !conv.messages || conv.messages.length === 0) {
            if (elements.welcomeHero) {
                elements.messagesList.appendChild(elements.welcomeHero);
            }
            return;
        }

        conv.messages.forEach(msg => {
            if (msg.role === 'user') {
                renderUserMessageNode(msg.text);
            } else if (msg.role === 'bot') {
                renderBotMessageNode(msg.data || { answer: msg.text });
            } else if (msg.role === 'error') {
                renderErrorMessageNode(msg.text);
            } else if (msg.role === 'system') {
                renderSystemNotificationNode(msg.text);
            }
        });

        scrollToBottom();
    }

    function renderUserMessageNode(text) {
        const row = document.createElement('div');
        row.className = 'msg-row user';
        row.innerHTML = `
            <div class="avatar-box user">${SVG.user}</div>
            <div class="msg-body">
                <div class="msg-bubble">${escapeHtml(text)}</div>
            </div>
        `;
        elements.messagesList.appendChild(row);
    }

    function renderBotMessageNode(data) {
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
    }

    function renderErrorMessageNode(msg) {
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

    function renderSystemNotificationNode(text) {
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
    }

    function showSystemNotification(text) {
        const conv = getActiveConversation();
        if (conv) {
            conv.messages.push({
                role: 'system',
                text: text,
                timestamp: Date.now()
            });
            saveConversations();
        }
        renderSystemNotificationNode(text);
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
    // Hotel Carousel & Active Hotel Lock Management
    // -------------------------------------------------------------------------
    let allLoadedHotels = [];
    let currentFilterCity = 'all';
    let currentSearchQuery = '';
    let searchDebounceTimer = null;
    let fetchHotelsRequestId = 0;

    async function fetchHotels(city = 'all', search = '') {
        const requestId = ++fetchHotelsRequestId;
        try {
            const params = new URLSearchParams();
            if (city && city !== 'all') params.set('city', city);
            if (search) params.set('search', search);
            params.set('limit', '40');

            const res = await fetch(`/api/hotels?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            
            // Guard against race conditions from rapid clicking
            if (requestId !== fetchHotelsRequestId) return;

            allLoadedHotels = data.hotels || [];
            renderHotelCarousel(allLoadedHotels);
        } catch (e) {
            if (requestId !== fetchHotelsRequestId) return;
            console.warn('Could not fetch hotels:', e);
            if (elements.hotelCarouselTrack) {
                elements.hotelCarouselTrack.innerHTML = '<div class="hotel-card-skeleton">Unable to load hotels. Please ensure the backend server is running.</div>';
            }
        }
    }

    function renderHotelCarousel(hotels) {
        if (!elements.hotelCarouselTrack) return;
        const conv = getActiveConversation();
        const selNormKey = conv && conv.selectedHotel ? conv.selectedHotel.norm_key : null;
        const selName = conv && conv.selectedHotel ? conv.selectedHotel.hotel_name : null;

        if (!hotels || hotels.length === 0) {
            elements.hotelCarouselTrack.innerHTML = '<div class="hotel-card-skeleton">No hotels found matching criteria.</div>';
            return;
        }

        elements.hotelCarouselTrack.innerHTML = hotels.map(h => {
            const isSelected = (selNormKey && h.norm_key === selNormKey) || (selName && h.hotel_name === selName);
            const mapsUrl = h.maps_search_url || ('https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(h.hotel_name + ' ' + (h.location || 'Vietnam')));
            const mediaHtml = (h.photo_url && h.photo_url.trim()) ? `
                    <div class="hotel-card-media" style="display: none;">
                        <img src="${escapeHtml(h.photo_url.trim())}" alt="${escapeHtml(h.hotel_name)}" loading="lazy"
                             onload="this.parentElement.style.display='block';"
                             onerror="this.parentElement.style.display='none'; this.remove();">
                    </div>` : '';
            return `
                <div class="hotel-card ${isSelected ? 'selected' : ''}" data-norm-key="${escapeHtml(h.norm_key)}" role="button" tabindex="0">
                    ${mediaHtml}
                    <div class="hotel-card-top">
                        <span class="card-star-badge">${escapeHtml(h.star)}</span>
                        <span class="card-score-badge">★ ${h.score.toFixed(1)}</span>
                        <span class="card-rev-badge">${h.review_count} revs</span>
                    </div>
                    <h4 class="hotel-card-name" title="${escapeHtml(h.hotel_name)}">${escapeHtml(h.hotel_name)}</h4>
                    <div class="hotel-card-loc">
                        ${SVG.mapPin}
                        <span>${escapeHtml(h.location)}</span>
                    </div>
                    ${h.sample_snippet ? `<p class="hotel-card-snippet">"${escapeHtml(h.sample_snippet)}"</p>` : ''}
                    <div class="hotel-card-footer">
                        <span class="select-hint">Select &amp; Inquire →</span>
                        <span class="selected-indicator">✓ Selected</span>
                        <a href="${escapeHtml(mapsUrl)}" target="_blank" rel="noopener noreferrer" class="card-maps-link" title="Open on Google Maps" onclick="event.stopPropagation();">
                            ${SVG.externalLink}
                            <span>Maps</span>
                        </a>
                    </div>
                </div>
            `;
        }).join('');
    }

    function selectHotel(hotel) {
        const conv = getActiveConversation();
        if (!conv) return;
        conv.selectedHotel = hotel;
        saveConversations();
        updateActiveHotelBanner();
        highlightSelectedCard();

        // Collapse carousel to focus on chat
        if (elements.hotelCarouselSection) {
            elements.hotelCarouselSection.classList.add('collapsed');
        }
        if (elements.carouselToggleBtn) {
            elements.carouselToggleBtn.classList.add('collapsed');
        }

        // Update placeholder
        elements.promptInput.placeholder = `Ask anything about ${hotel.hotel_name}...`;

        // If conversation is empty, display a welcome concierge greeting for the hotel
        if (conv.messages.length === 0) {
            if (elements.welcomeHero && elements.welcomeHero.parentNode) {
                elements.welcomeHero.remove();
            }
            const introMsg = {
                role: 'bot',
                data: {
                    hotel_info: {
                        hotel_name: hotel.hotel_name,
                        star: hotel.star,
                        score: hotel.score,
                        address: hotel.address,
                        location: hotel.location,
                        total_reviews: hotel.review_count
                    },
                    answer: `You are now exploring **${hotel.hotel_name}** (${hotel.star}, rated ${hotel.score.toFixed(1)}/5.0 stars with ${hotel.review_count} verified reviews in ${hotel.location}). What would you like to know about its customer service, breakfast quality, room comfort, or swimming pool? Ask any question or tap a quick topic below.`,
                    predicted_aspect: "Overview",
                    aspect_confidence: 1.0,
                    sentiment_consensus: "Positive",
                    predicted_rating: hotel.score,
                    cited_reviews: []
                },
                timestamp: Date.now()
            };
            conv.messages.push(introMsg);
            saveConversations();
            renderBotMessageNode(introMsg.data);
            scrollToBottom();
        }

        elements.promptInput.focus();
    }

    function deselectHotel() {
        const conv = getActiveConversation();
        if (!conv) return;
        conv.selectedHotel = null;
        saveConversations();
        updateActiveHotelBanner();
        highlightSelectedCard();

        // Expand carousel to allow selecting hotel again
        if (elements.hotelCarouselSection) {
            elements.hotelCarouselSection.classList.remove('collapsed');
        }
        if (elements.carouselToggleBtn) {
            elements.carouselToggleBtn.classList.remove('collapsed');
        }
        elements.promptInput.placeholder = 'Ask about a hotel or select a card above...';
    }

    function updateActiveHotelBanner() {
        const conv = getActiveConversation();
        const banner = elements.activeHotelBanner;
        if (!banner) return;

        if (conv && conv.selectedHotel) {
            banner.style.display = 'flex';
            if (elements.activeHotelTitle) {
                elements.activeHotelTitle.textContent = conv.selectedHotel.hotel_name;
            }
            if (elements.activeHotelTag) {
                elements.activeHotelTag.textContent = `${conv.selectedHotel.star} · ${conv.selectedHotel.score}★`;
            }
        } else {
            banner.style.display = 'none';
        }
    }

    function highlightSelectedCard() {
        const conv = getActiveConversation();
        const selNormKey = conv && conv.selectedHotel ? conv.selectedHotel.norm_key : null;
        const selName = conv && conv.selectedHotel ? conv.selectedHotel.hotel_name : null;

        const cards = document.querySelectorAll('.hotel-card');
        cards.forEach(card => {
            const normKey = card.getAttribute('data-norm-key');
            if (normKey === selNormKey || (selName && card.querySelector('.hotel-card-name')?.textContent === selName)) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        });
    }

    function initHotelCarousel() {
        if (elements.hotelCarouselTrack) {
            elements.hotelCarouselTrack.addEventListener('click', (e) => {
                const card = e.target.closest('.hotel-card');
                if (!card) return;
                const normKey = card.getAttribute('data-norm-key');
                const found = allLoadedHotels.find(h => h.norm_key === normKey);
                if (found) {
                    selectHotel(found);
                }
            });

            elements.hotelCarouselTrack.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    const card = e.target.closest('.hotel-card');
                    if (card) {
                        e.preventDefault();
                        card.click();
                    }
                }
            });
        }

        if (elements.deselectHotelBtn) {
            elements.deselectHotelBtn.addEventListener('click', () => {
                deselectHotel();
            });
        }

        if (elements.changeHotelBtn) {
            elements.changeHotelBtn.addEventListener('click', () => {
                if (elements.hotelCarouselSection) {
                    elements.hotelCarouselSection.classList.remove('collapsed');
                }
                if (elements.carouselToggleBtn) {
                    elements.carouselToggleBtn.classList.remove('collapsed');
                }
                elements.hotelCarouselSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }

        if (elements.topbarBrowseBtn) {
            elements.topbarBrowseBtn.addEventListener('click', () => {
                if (elements.hotelCarouselSection) {
                    const isCollapsed = elements.hotelCarouselSection.classList.toggle('collapsed');
                    if (elements.carouselToggleBtn) {
                        elements.carouselToggleBtn.classList.toggle('collapsed', isCollapsed);
                    }
                }
            });
        }

        if (elements.cityFilterBar) {
            elements.cityFilterBar.addEventListener('click', (e) => {
                const pill = e.target.closest('.city-pill');
                if (!pill) return;
                document.querySelectorAll('.city-pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                currentFilterCity = pill.getAttribute('data-city') || 'all';
                fetchHotels(currentFilterCity, currentSearchQuery);
            });
        }

        if (elements.hotelSearchInput) {
            elements.hotelSearchInput.addEventListener('input', (e) => {
                currentSearchQuery = e.target.value.trim();
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(() => {
                    fetchHotels(currentFilterCity, currentSearchQuery);
                }, 220);
            });
        }

        if (elements.carouselToggleBtn) {
            elements.carouselToggleBtn.addEventListener('click', () => {
                if (elements.hotelCarouselSection) {
                    elements.hotelCarouselSection.classList.toggle('collapsed');
                }
                elements.carouselToggleBtn.classList.toggle('collapsed');
            });
        }

        if (elements.quickAspectPills) {
            elements.quickAspectPills.addEventListener('click', (e) => {
                const pill = e.target.closest('.aspect-pill');
                if (!pill) return;
                const query = pill.getAttribute('data-query');
                if (!query) return;
                elements.promptInput.value = query;
                elements.sendBtn.disabled = false;
                elements.promptInput.focus();
                elements.chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            });
        }

        fetchHotels('all', '');
    }

    // -------------------------------------------------------------------------
    // App Initialization
    // -------------------------------------------------------------------------
    initTheme();
    initSidebar();
    loadConversations();
    renderConversationLists();
    renderActiveConversationMessages();
    initModelSelector();
    initHotelCarousel();
    updateActiveHotelBanner();

    // Synchronize carousel state and prompt placeholder based on active conversation
    const initialConv = getActiveConversation();
    if (initialConv && initialConv.selectedHotel) {
        if (elements.hotelCarouselSection) {
            elements.hotelCarouselSection.classList.add('collapsed');
        }
        if (elements.carouselToggleBtn) {
            elements.carouselToggleBtn.classList.add('collapsed');
        }
        elements.promptInput.placeholder = `Ask anything about ${initialConv.selectedHotel.hotel_name}...`;
    } else {
        if (elements.hotelCarouselSection) {
            elements.hotelCarouselSection.classList.remove('collapsed');
        }
        if (elements.carouselToggleBtn) {
            elements.carouselToggleBtn.classList.remove('collapsed');
        }
        elements.promptInput.placeholder = 'Ask about a hotel or select a card above...';
    }

})();
