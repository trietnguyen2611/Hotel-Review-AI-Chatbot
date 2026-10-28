

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
        starOutline: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
        sparkles: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z"/><path d="m19 14 1.1 2.9L23 18l-2.9 1.1L19 22l-1.1-2.9L15 18l2.9-1.1L19 14Z"/><path d="m5 2 .8 2.2L8 5l-2.2.8L5 8l-.8-2.2L2 5l2.2-.8L5 2Z"/></svg>`,
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
        trash: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`,
        download: `<svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`
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
    let homeTitleFrame = null;
    let homeTitleVisible = false;

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
        chatHeader: document.querySelector('.chat-header'),
        activeChatTitle: document.getElementById('activeChatTitle'),
        selectionHeroTitle: document.querySelector('.selection-hero-title'),

        modelDropdownWrapper: document.getElementById('modelDropdownWrapper'),
        modelSelectorBtn: document.getElementById('modelSelectorBtn'),
        currentModelLabel: document.getElementById('currentModelLabel'),
        modelDropdownMenu: document.getElementById('modelDropdownMenu'),
        modelDropdownList: document.getElementById('modelDropdownList'),

        topbarBrowseBtn: document.getElementById('topbarBrowseBtn'),
        exportDebugLogBtn: document.getElementById('exportDebugLogBtn'),
        hotelSelectionView: document.getElementById('hotelSelectionView'),
        hotelSelectionGrid: document.getElementById('hotelSelectionGrid'),
        chatWorkspaceView: document.getElementById('chatWorkspaceView'),
        mobileSidebarClose: document.getElementById('mobileSidebarClose'),
        cityFilterBar: document.getElementById('cityFilterBar'),
        provinceSelect: document.getElementById('provinceSelect'),
        hotelSearchInput: document.getElementById('hotelSearchInput'),
        hotelCounterTag: document.getElementById('hotelCounterTag'),
        loadMoreHotelsWrap: document.getElementById('loadMoreHotelsWrap'),
        loadMoreHotelsBtn: document.getElementById('loadMoreHotelsBtn'),
        loadMoreHotelsText: document.getElementById('loadMoreHotelsText'),
        allLoadedIndicator: document.getElementById('allLoadedIndicator'),

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
            setTheme('light');
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
        const current = document.documentElement.getAttribute('data-theme') || 'light';
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

        if (elements.mobileSidebarClose) {
            elements.mobileSidebarClose.addEventListener('click', () => {
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

        if (!Array.isArray(conversations)) {
            conversations = [];
        }

        // Retain conversations that have a selected hotel or messages
        conversations = conversations.filter(c => c && (c.selectedHotel || (c.messages && c.messages.length > 0)));

        const savedActiveId = localStorage.getItem(STORAGE_ACTIVE_ID_KEY);
        const found = conversations.find(c => c.id === savedActiveId);
        if (found) {
            activeConvId = found.id;
        } else if (conversations.length > 0) {
            activeConvId = conversations[0].id;
        } else {
            activeConvId = null;
        }
    }

    function saveConversations() {
        try {
            localStorage.setItem(STORAGE_CONVERSATIONS_KEY, JSON.stringify(conversations));
            if (activeConvId) {
                localStorage.setItem(STORAGE_ACTIVE_ID_KEY, activeConvId);
            } else {
                localStorage.removeItem(STORAGE_ACTIVE_ID_KEY);
            }
        } catch (e) {
            console.warn('Failed to save conversations to localStorage:', e);
        }
    }

    function getActiveConversation() {
        if (!activeConvId) return null;
        return conversations.find(c => c.id === activeConvId) || null;
    }

    function updateHomeTitle() {
        if (!elements.hotelSelectionView || !elements.selectionHeroTitle || !elements.activeChatTitle) {
            return;
        }

        if (homeTitleFrame !== null) return;

        homeTitleFrame = window.requestAnimationFrame(() => {
            homeTitleFrame = null;
            const isHomeView = elements.hotelSelectionView.style.display !== 'none';
            const headerBottom = elements.chatHeader?.getBoundingClientRect().bottom ?? 0;
            const titleBottom = elements.selectionHeroTitle.getBoundingClientRect().bottom;
            const shouldShowTitle = isHomeView
                && elements.hotelSelectionView.scrollTop > 0
                && titleBottom <= headerBottom;

            if (shouldShowTitle === homeTitleVisible) return;

            homeTitleVisible = shouldShowTitle;
            elements.appLayout.classList.toggle('home-title-visible', shouldShowTitle);
            elements.activeChatTitle.textContent = shouldShowTitle
                ? elements.selectionHeroTitle.textContent
                : '';
        });
    }

   // Lưu vị trí cuộn của danh sách khách sạn
    let savedHotelScrollTop = 0;
    
    /**
     * Animation khi chuyển giữa màn hình chọn khách sạn và màn hình chat.
     */
    function animateViewEntry(view) {
        if (!view) return;

        // Xóa class cũ để có thể chạy animation nhiều lần.
        view.classList.remove('view-entering');

        // Buộc trình duyệt cập nhật trạng thái trước khi chạy lại animation.
        void view.offsetWidth;

        view.classList.add('view-entering');

        // Xóa class sau khi animation kết thúc.
        window.setTimeout(() => {
            view.classList.remove('view-entering');
        }, 520);
    }

    function showHotelSelectionView(options = {}) {
    const { resetScroll = false } = options;

    // Lưu ý: Chỉ reset khi bắt đầu cuộc hội thoại mới
    if (resetScroll) {
        savedHotelScrollTop = 0;
    }

    homeTitleVisible = false;
    elements.appLayout.classList.add('home-view');
    elements.appLayout.classList.remove('home-title-visible');

    // Hiện màn hình chọn khách sạn và chạy animation
    if (elements.hotelSelectionView) {
        const view = elements.hotelSelectionView;

        view.style.display = 'flex';
        view.classList.remove('view-entering');

        // Buộc trình duyệt cập nhật trước khi chạy animation
        void view.offsetWidth;

        view.classList.add('view-entering');

        window.setTimeout(() => {
            view.classList.remove('view-entering');
        }, 520);
    }

    // Ẩn màn hình chat
    if (elements.chatWorkspaceView) {
        elements.chatWorkspaceView.style.display = 'none';
        elements.chatWorkspaceView.classList.remove('view-entering');
    }

    if (elements.activeChatTitle) {
        elements.activeChatTitle.textContent = '';
    }

    if (elements.topbarBrowseBtn) {
        elements.topbarBrowseBtn.classList.add('active');
    }

    // Bỏ trạng thái active của hội thoại trong sidebar
    document.querySelectorAll('.conv-item').forEach(item => {
        item.classList.remove('active');
    });

    highlightSelectedCard();

    // Khôi phục vị trí cuộn cũ thay vì luôn nhảy lên đầu
    if (elements.hotelSelectionView) {
        requestAnimationFrame(() => {
            elements.hotelSelectionView.scrollTop = savedHotelScrollTop;
            updateHomeTitle();
        });
    }

    updateHomeTitle();
}

    function showChatWorkspaceView(conv) {
        if (!conv) {
            showHotelSelectionView();
            return;
        }

        // Lưu vị trí danh sách trước khi chuyển sang màn hình chat
        if (elements.hotelSelectionView) {
            savedHotelScrollTop = elements.hotelSelectionView.scrollTop;
        }

        homeTitleVisible = false;
        elements.appLayout.classList.remove('home-view', 'home-title-visible');

        activeConvId = conv.id;
        saveConversations();

        if (elements.hotelSelectionView) {
            elements.hotelSelectionView.style.display = 'none';
        }

        if (elements.chatWorkspaceView) {
            elements.chatWorkspaceView.style.display = 'flex';
        }

        if (elements.topbarBrowseBtn) {
            elements.topbarBrowseBtn.classList.remove('active');
        }

        if (elements.activeChatTitle) {
            elements.activeChatTitle.textContent =
                conv.title ||
                (conv.selectedHotel
                    ? conv.selectedHotel.hotel_name
                    : 'Conversation');
        }

        if (conv.selectedHotel) {
            elements.promptInput.placeholder =
                `Ask anything about ${conv.selectedHotel.hotel_name}...`;
        } else {
            elements.promptInput.placeholder =
                'Ask about a hotel or select a card...';
        }

        updateActiveHotelBanner();
        renderConversationLists();
        renderActiveConversationMessages();
        highlightSelectedCard();

        elements.promptInput.focus();
    }

    function handleNewChat() {
        // Cuộc hội thoại mới: reset bộ lọc và vị trí cuộn
        resetAllHotelFilters();
        showHotelSelectionView({ resetScroll: true });

        if (window.innerWidth <= 840) {
            closeMobileSidebar();
        }
    }

    function switchConversation(id) {
        if (activeConvId === id && elements.chatWorkspaceView && elements.chatWorkspaceView.style.display !== 'none') {
            if (window.innerWidth <= 840) closeMobileSidebar();
            return;
        }
        const conv = conversations.find(c => c.id === id);
        if (conv) {
            showChatWorkspaceView(conv);
        } else {
            showHotelSelectionView();
        }

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

        if (activeConvId === id) {
            if (conversations.length > 0) {
                showChatWorkspaceView(conversations[0]);
            } else {
                activeConvId = null;
                saveConversations();
                renderConversationLists();
                showHotelSelectionView();
            }
        } else {
            saveConversations();
            renderConversationLists();
        }
    }

    function showToast(message, duration = 3200) {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = 'toast-item';
        toast.innerHTML = `
            <svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24" style="stroke: #10b981; fill: none; stroke-width: 2;">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>${escapeHtml(message)}</span>
        `;
        container.appendChild(toast);
        window.requestAnimationFrame(() => {
            toast.classList.add('show');
        });
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 250);
        }, duration);
    }

    async function exportConversationLog(targetConvId) {
        const convId = targetConvId || activeConvId;
        const conv = conversations.find(c => c.id === convId);
        if (!conv) {
            alert('Không tìm thấy cuộc hội thoại để xuất log.');
            return;
        }

        const msgList = conv.messages || [];
        if (msgList.length === 0) {
            if (!confirm('Cuộc hội thoại hiện tại chưa có tin nhắn nào. Bạn có muốn xuất thông tin metadata khởi tạo không?')) {
                return;
            }
        }

        // Fetch backend debug state for session if available
        let backendDebug = null;
        if (conv.sessionId) {
            try {
                const resp = await fetch(`/api/session-debug?session_id=${encodeURIComponent(conv.sessionId)}`);
                if (resp.ok) {
                    backendDebug = await resp.json();
                }
            } catch (err) {
                console.warn('Backend debug fetch failed:', err);
            }
        }

        const currentModel = elements.currentModelLabel ? elements.currentModelLabel.textContent.trim() : 'model_v4';

        const exportPayload = {
            export_version: "2.0-debug",
            exported_at: new Date().toISOString(),
            metadata: {
                app_name: "DAP-Hotel AI Concierge (CRAM-ABSA Framework)",
                conversation_id: conv.id,
                session_id: conv.sessionId || 'default_session',
                title: conv.title || 'Conversation',
                created_at: new Date(conv.createdAt || Date.now()).toISOString(),
                updated_at: new Date(conv.updatedAt || Date.now()).toISOString(),
                total_turns: msgList.length,
                pinned: Boolean(conv.pinned),
                active_model: currentModel
            },
            selected_hotel: conv.selectedHotel ? {
                hotel_name: conv.selectedHotel.hotel_name || '',
                star: conv.selectedHotel.star || 'Standard',
                score: conv.selectedHotel.score || null,
                location: conv.selectedHotel.location || '',
                address: conv.selectedHotel.address || '',
                review_count: conv.selectedHotel.review_count || 0,
                aspect_scores: conv.selectedHotel.aspect_scores || {}
            } : null,
            backend_session_state: backendDebug ? backendDebug.session : null,
            backend_environment: backendDebug ? {
                active_model: backendDebug.active_model,
                model_type: backendDebug.model_type,
                database_size: backendDebug.database_size
            } : null,
            dialogue_turns: msgList.map((m, idx) => {
                if (m.role === 'user') {
                    return {
                        turn_index: idx + 1,
                        role: 'user',
                        timestamp: new Date(m.timestamp || Date.now()).toISOString(),
                        query: m.text || ''
                    };
                } else if (m.role === 'bot') {
                    const d = m.data || {};
                    return {
                        turn_index: idx + 1,
                        role: 'bot',
                        timestamp: new Date(m.timestamp || Date.now()).toISOString(),
                        answer: d.answer || d.reply || '',
                        inference_mode: d.inference_mode || 'neural_generation',
                        model_name: d.model_name || currentModel,
                        model_type: d.model_type || 'seq2seq',
                        target_aspect: d.aspect || null,
                        aspect_title: d.aspect_title || null,
                        predicted_sentiment: d.sentiment || null,
                        confidence_score: d.confidence || null,
                        context_applied: Boolean(d.context_applied),
                        prompt_given_to_model: d.prompt_used || null,
                        retrieved_citations_count: (d.citations || d.original_reviews || []).length,
                        retrieved_evidence: (d.citations || d.original_reviews || []).map(r => ({
                            date: r.date || 'Recent',
                            score: r.score || null,
                            sentiment: r.sentiment || null,
                            recency_weight: r.recency_weight || null,
                            text: r.text || '',
                            aspect_spans: r.aspect_spans || []
                        })),
                        raw_response_payload: d
                    };
                } else {
                    return {
                        turn_index: idx + 1,
                        role: m.role || 'system',
                        timestamp: new Date(m.timestamp || Date.now()).toISOString(),
                        content: m.text || m.data || ''
                    };
                }
            })
        };

        const jsonContent = JSON.stringify(exportPayload, null, 2);
        const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8' });
        const url = URL.createObjectURL(blob);

        const safeHotel = (conv.selectedHotel?.hotel_name || conv.title || 'chat')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_+|_+$/g, '')
            .slice(0, 25);
        const timestampStr = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const filename = `dap_debug_${safeHotel}_${timestampStr}.json`;

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast(`Đã xuất JSON log: ${filename}`);
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
                    <button type="button" class="conv-action-btn export-btn" data-action="export" title="Xuất JSON log để debug" aria-label="Export JSON log">
                        ${SVG.download}
                    </button>
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
            if (action === 'export') {
                exportConversationLog(convId);
            } else if (action === 'rename') {
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

    if (elements.exportDebugLogBtn) {
        elements.exportDebugLogBtn.addEventListener('click', (e) => {
            e.preventDefault();
            exportConversationLog(activeConvId);
        });
    }

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



    function highlightSpansInText(text, spans) {
        if (!text) return '';
        if (!spans || !Array.isArray(spans) || spans.length === 0) return escapeHtml(text);

        // Find match ranges in raw text
        const intervals = [];
        const lowerText = text.toLowerCase();
        for (const span of spans) {
            if (!span || span.length < 3) continue;
            const spanLower = span.toLowerCase();
            let startPos = 0;
            let idx = lowerText.indexOf(spanLower, startPos);
            while (idx !== -1) {
                intervals.push([idx, idx + span.length]);
                idx = lowerText.indexOf(spanLower, idx + span.length);
            }
        }
        if (intervals.length === 0) return escapeHtml(text);

        // Merge overlapping or adjacent intervals
        intervals.sort((a, b) => a[0] - b[0]);
        const merged = [intervals[0]];
        for (let i = 1; i < intervals.length; i++) {
            const last = merged[merged.length - 1];
            const curr = intervals[i];
            if (curr[0] <= last[1]) {
                last[1] = Math.max(last[1], curr[1]);
            } else {
                merged.push(curr);
            }
        }

        // Construct safe HTML
        let result = '';
        let lastIdx = 0;
        for (const [start, end] of merged) {
            result += escapeHtml(text.substring(lastIdx, start));
            result += `<mark class="aspect-highlight">${escapeHtml(text.substring(start, end))}</mark>`;
            lastIdx = end;
        }
        result += escapeHtml(text.substring(lastIdx));
        return result;
    }

    function renderSingleReviewCardHtml(r) {
        const sentimentClass = r.sentiment === 'Positive' ? 'badge-positive' : (r.sentiment === 'Negative' ? 'badge-negative' : 'badge-neutral');
        const highlightedText = highlightSpansInText(r.text, r.aspect_spans);

        return `
            <div class="review-item-card">
                <div class="review-item-header">
                    <div class="review-item-header-left">
                        ${SVG.calendar}
                        <span>${escapeHtml(r.date || 'Recent')}</span>
                        <span style="display:inline-flex; align-items:center; gap:2px; margin-left:6px; color:var(--warning);">
                            ${SVG.star} ${r.score}/5.0
                        </span>
                        ${r.sentiment ? `<span class="review-item-badge ${sentimentClass}">${escapeHtml(r.sentiment)}</span>` : ''}
                    </div>
                    <div class="review-item-weight" title="Feature 10 Exponential Recency Weight w = exp(-0.03 * delta_m)">
                        ${SVG.weight} Weight: ${r.recency_weight}
                    </div>
                </div>
                <div class="review-item-text">
                    &ldquo;${highlightedText}&rdquo;
                </div>
            </div>
        `;
    }

    window.__loadMoreReviews = function (toggleId, pageSize = 5) {
        const cache = window.__reviewsCache ? window.__reviewsCache[toggleId] : null;
        if (!cache) return;
        const listBody = document.getElementById('listBody_' + toggleId);
        const itemsWrap = document.getElementById('itemsWrap_' + toggleId);
        const btn = document.getElementById('loadMoreBtn_' + toggleId);
        if (!listBody || !itemsWrap) return;

        let currentOffset = parseInt(listBody.getAttribute('data-offset') || '5', 10);
        const nextBatch = cache.slice(currentOffset, currentOffset + pageSize);
        const newHtml = nextBatch.map(r => renderSingleReviewCardHtml(r)).join('');
        itemsWrap.insertAdjacentHTML('beforeend', newHtml);

        currentOffset += nextBatch.length;
        listBody.setAttribute('data-offset', currentOffset.toString());

        const remaining = cache.length - currentOffset;
        if (remaining > 0 && btn) {
            btn.innerHTML = `<span>View more (${remaining} remaining)</span>`;
        } else if (btn) {
            btn.remove();
        }
    };

    function renderBotMessageNode(data) {
        const row = document.createElement('div');
        row.className = 'msg-row bot';

        // 1. Hotel Metadata Header
        let metaHtml = '';
        if (data.hotel_name) {
            const starText = data.star || 'Standard';
            const scoreText = (typeof data.score === 'number' && !isNaN(data.score)) ? data.score.toFixed(1) : '4.5';
            const aspectSentimentHtml = data.aspect || data.sentiment ? `
                <div class="hotel-meta-insights">
                    ${data.aspect ? `
                        <span class="hotel-meta-tag aspect-tag">
                            ${SVG.sparkles}
                            <span>${escapeHtml(data.aspect)}</span>
                        </span>
                    ` : ''}
                    ${data.aspect && data.sentiment ? '<span class="hotel-meta-divider" aria-hidden="true"></span>' : ''}
                    ${data.sentiment ? `
                        <span class="hotel-meta-tag sentiment-tag sentiment-${data.sentiment.toLowerCase()}">
                            <span>${escapeHtml(data.sentiment)}</span>
                        </span>
                    ` : ''}
                </div>
            ` : '';
            metaHtml = `
                <div class="msg-hotel-meta">
                    <div class="hotel-meta-heading">
                        <span class="hotel-meta-badge">
                            ${SVG.hotel}
                            <strong>${escapeHtml(data.hotel_name)}</strong>
                        </span>
                        <div class="hotel-meta-ratings">
                            <span class="hotel-meta-tag star-tag">
                                ${SVG.starOutline}
                                <span>${escapeHtml(starText)}</span>
                            </span>
                            <span class="hotel-meta-tag score-tag">
                                ${SVG.star}
                                <span>${scoreText}</span>
                            </span>
                        </div>
                    </div>
                    ${aspectSentimentHtml}
                </div>
            `;
        }

        // 2. Google Maps Interactive Embed Card
        let mapsHtml = '';
        if (data.maps_card && data.maps_card.embed_url) {
            mapsHtml = `
                <div class="maps-embed-card">
                    <div class="maps-embed-header">
                        <div class="maps-header-left">
                            ${SVG.mapPin}
                            <div>
                                <div class="maps-hotel-name">${escapeHtml(data.maps_card.hotel_name)}</div>
                                <div class="maps-hotel-address">${escapeHtml(data.maps_card.address || data.maps_card.location)}</div>
                            </div>
                        </div>
                        <a href="${escapeHtml(data.maps_card.search_url)}" target="_blank" rel="noopener noreferrer" class="maps-open-btn" title="Open in Google Maps">
                            <span>Open Maps</span>
                            ${SVG.externalLink}
                        </a>
                    </div>
                    <iframe class="maps-iframe" src="${escapeHtml(data.maps_card.embed_url)}" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade"></iframe>
                </div>
            `;
        }

        // 3. Collapsible Multi-Review Citations (Max 5 per view with pagination)
        let collapsibleHtml = '';
        if (data.original_reviews && data.original_reviews.length > 0) {
            const toggleId = 'rev_toggle_' + Math.random().toString(36).substring(2, 9);
            window.__reviewsCache = window.__reviewsCache || {};
            window.__reviewsCache[toggleId] = data.original_reviews;

            const initialReviews = data.original_reviews.slice(0, 5);
            const initialHtml = initialReviews.map(r => renderSingleReviewCardHtml(r)).join('');
            const remaining = data.original_reviews.length - 5;

            const loadMoreBtnHtml = remaining > 0 ? `
                <button type="button" class="load-more-reviews-btn" id="loadMoreBtn_${toggleId}" onclick="window.__loadMoreReviews('${toggleId}', 5)">

                    <span>View more reviews (${remaining} remaining)</span>
                </button>
            ` : '';

            collapsibleHtml = `
                <details class="original-reviews-toggle">
                    <summary>
                        <div class="summary-left">
                            ${SVG.book}
                            <span>View original reviews (${data.original_reviews.length} analyzed)</span>
                        </div>
                        ${SVG.chevron}
                    </summary>
                    <div class="reviews-list-body" id="listBody_${toggleId}" data-offset="5">
                        <div class="reviews-items-container" id="itemsWrap_${toggleId}">
                            ${initialHtml}
                        </div>
                        ${loadMoreBtnHtml}
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
                        ${formatBotText(data.answer)}
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

    function formatBotText(str) {
        if (!str) return '';
        let escaped = escapeHtml(str);
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        escaped = escaped.replace(/(^|[^\*])\*(?!\*)(.*?)\*(?!\*)/g, '$1<em>$2</em>');
        escaped = escaped.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
        return escaped;
    }

    // -------------------------------------------------------------------------
    // Hotel Selection Hub & Active Hotel Management
    // -------------------------------------------------------------------------
    function resolveHotelPhotoUrl(hotel) {
    if (!hotel || typeof hotel.photo_url !== 'string') {
        return null;
    }

    const photoUrl = hotel.photo_url.trim();

    if (!photoUrl) {
        return null;
    }

    try {
        const parsedUrl = new URL(photoUrl, window.location.href);

        if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
            return null;
        }

        return parsedUrl.href;
    } catch (error) {
        console.error('[Hotel Image] Invalid URL:', photoUrl);
        return null;
    }
}

    const HOTEL_PAGE_SIZE = 9;
    let allLoadedHotels = [];
    let currentFilterCity = 'all';
    let currentSearchQuery = '';
    let currentOffset = 0;
    let totalMatchingHotels = 0;
    let hasMoreHotels = false;
    let isLoadingHotels = false;
    let provincesLoaded = false;
    let searchDebounceTimer = null;
    let fetchHotelsRequestId = 0;

    async function fetchHotels(city = 'all', search = '', append = false) {
        // Only block duplicate concurrent requests when paginating (Load More)
        if (append && isLoadingHotels) return;
        isLoadingHotels = true;
        const requestId = ++fetchHotelsRequestId;

        if (!append) {
            currentOffset = 0;
            allLoadedHotels = [];
            if (elements.hotelSelectionGrid) {
                elements.hotelSelectionGrid.innerHTML = '<div class="hotel-card-skeleton">Loading hotel properties...</div>';
            }
            if (elements.loadMoreHotelsWrap) {
                elements.loadMoreHotelsWrap.style.display = 'none';
            }
            if (elements.hotelCounterTag) {
                elements.hotelCounterTag.textContent = 'Loading...';
            }
        } else {
            if (elements.loadMoreHotelsBtn) {
                elements.loadMoreHotelsBtn.classList.add('loading');
            }
            if (elements.loadMoreHotelsText) {
                elements.loadMoreHotelsText.textContent = 'Loading more hotels...';
            }
        }

        try {
            
            const params = new URLSearchParams();

            if (city && city !== 'all') params.set('city', city);
            if (search) params.set('search', search);

            const sortSelect = document.getElementById('hotelSort');
            const minRatingSelect = document.getElementById('minHotelRating');
            const minReviewsSelect = document.getElementById('minHotelReviews');

            params.set('sort', sortSelect?.value || 'recommended');
            params.set('min_rating', minRatingSelect?.value || '0');
            params.set('min_reviews', minReviewsSelect?.value || '0');

            params.set('limit', String(HOTEL_PAGE_SIZE));
            params.set('offset', String(currentOffset));


            const res = await fetch(`/api/hotels?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            // Guard against race conditions from rapid clicking or debounced input
            if (requestId !== fetchHotelsRequestId) return;

            totalMatchingHotels = data.total || 0;
            hasMoreHotels = !!data.has_more;
            const newHotels = data.hotels || [];

            // Populate all 48 provinces in dropdown filter once
            if (!provincesLoaded && data.provinces && Array.isArray(data.provinces) && elements.provinceSelect) {
                provincesLoaded = true;
                const totalAll = data.provinces.reduce((sum, p) => sum + p.count, 0);
                elements.provinceSelect.innerHTML = `
                    <option value="all">All provinces</option>
                    ${data.provinces.map(p => `
                        <option value="${escapeHtml(p.name)}">${escapeHtml(p.name)} (${p.count.toLocaleString()})</option>
                    `).join('')}
                `;
                if (currentFilterCity && currentFilterCity !== 'all') {
                    elements.provinceSelect.value = currentFilterCity;
                }
            }

            if (!append) {
                allLoadedHotels = newHotels;
                renderHotelSelectionGrid(allLoadedHotels, false);
            } else {
                allLoadedHotels = allLoadedHotels.concat(newHotels);
                renderHotelSelectionGrid(newHotels, true);
            }

            currentOffset += newHotels.length;

            // Update Counter Text
            if (elements.hotelCounterTag) {
                const cityLabel = (city && city !== 'all') ? ` in ${city}` : '';
                const searchLabel = search ? ` matching "${search}"` : '';
                elements.hotelCounterTag.textContent = `Showing ${allLoadedHotels.length} of ${totalMatchingHotels.toLocaleString()} hotels${cityLabel}${searchLabel}`;
            }

            // Update Load More Button & Indicator
            if (elements.loadMoreHotelsWrap) {
                if (totalMatchingHotels === 0) {
                    elements.loadMoreHotelsWrap.style.display = 'none';
                } else {
                    elements.loadMoreHotelsWrap.style.display = 'flex';
                    if (hasMoreHotels && elements.loadMoreHotelsBtn) {
                        elements.loadMoreHotelsBtn.style.display = 'inline-flex';
                        elements.loadMoreHotelsBtn.classList.remove('loading');
                        const remaining = Math.max(0, totalMatchingHotels - allLoadedHotels.length);
                        const nextBatch = Math.min(HOTEL_PAGE_SIZE, remaining);
                        if (elements.loadMoreHotelsText) {
                            elements.loadMoreHotelsText.textContent = `View more ${nextBatch} hotels (remaining: ${remaining.toLocaleString()})`;
                        }
                        if (elements.allLoadedIndicator) elements.allLoadedIndicator.style.display = 'none';
                    } else {
                        if (elements.loadMoreHotelsBtn) elements.loadMoreHotelsBtn.style.display = 'none';
                        if (elements.allLoadedIndicator) {
                            elements.allLoadedIndicator.style.display = 'flex';
                            elements.allLoadedIndicator.innerHTML = `
                                <svg class="svg-icon svg-icon-sm" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
                                <span>All ${totalMatchingHotels.toLocaleString()} hotels are displayed</span>
                            `;
                        }
                    }
                }
            }
        } catch (e) {
            if (requestId !== fetchHotelsRequestId) return;
            console.warn('Could not fetch hotels:', e);
            if (!append && elements.hotelSelectionGrid) {
                elements.hotelSelectionGrid.innerHTML = '<div class="hotel-card-skeleton">Unable to load hotel properties. Please ensure the backend server is running.</div>';
            }
            if (elements.loadMoreHotelsBtn) {
                elements.loadMoreHotelsBtn.classList.remove('loading');
                if (elements.loadMoreHotelsText) {
                    elements.loadMoreHotelsText.textContent = 'Retry loading hotels';
                }
            }
        } finally {
            if (requestId === fetchHotelsRequestId) {
                isLoadingHotels = false;
            }
        }
    }

    
function renderHotelCardHtml(h) {
    const conv = getActiveConversation();
    const selNormKey = conv && conv.selectedHotel
        ? conv.selectedHotel.norm_key
        : null;
    const selName = conv && conv.selectedHotel
        ? conv.selectedHotel.hotel_name
        : null;

    const isSelected =
        (selNormKey && h.norm_key === selNormKey) ||
        (selName && h.hotel_name === selName);

    // Ưu tiên địa chỉ chi tiết nếu dữ liệu có sẵn.
const hotelAddress = (
    h.address ||
    h.hotel_address ||
    h.full_address ||
    (
        h.district
            ? `${h.district}, ${h.location || ''}`
            : h.location || ''
    )
)
    .replace(/,\s*(VN|Vietnam|Việt Nam)\s*$/i, '')
    .replace(/\s+(VN|Vietnam|Việt Nam)\s*$/i, '')
    .trim();


    const mapsQuery = `${h.hotel_name || ''} ${hotelAddress}`;
    const mapsUrl = h.maps_search_url ||
        ('https://www.google.com/maps/search/?api=1&query=' +
            encodeURIComponent(mapsQuery));

    const photoUrl = resolveHotelPhotoUrl(h);
    const scoreVal =
        (typeof h.score === 'number' && !isNaN(h.score))
            ? h.score.toFixed(1)
            : '4.5';

    const revCount =
        (typeof h.review_count === 'number' && !isNaN(h.review_count))
            ? h.review_count
            : 0;

    const starVal = h.star || '4-star';

    // Always render a stable media frame. Missing/broken hotel photos fall back
    // to a neutral hotel image rather than collapsing the card header.
    const fallbackPhotoUrl = 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1000&q=80';
    const initialPhotoUrl = photoUrl || fallbackPhotoUrl;
    const mediaHtml = `
        <div class="hotel-card-media">
            <div class="hotel-card-media-placeholder" aria-hidden="true">
                <span class="hotel-card-placeholder-icon">✦</span>
                <span>Hotel preview</span>
            </div>
            <img
                src="${escapeHtml(initialPhotoUrl)}"
                alt="${escapeHtml(h.hotel_name || 'Hotel')}"
                loading="lazy"
                onload="this.classList.add('loaded'); this.previousElementSibling.style.display='none';"
                onerror="if (!this.dataset.fallbackTried) { this.dataset.fallbackTried='1'; this.src='${fallbackPhotoUrl}'; } else { this.style.display='none'; this.previousElementSibling.style.display='flex'; }"
            >
            <div class="hotel-card-media-gradient"></div>
            <div class="card-badge-top-left">
                <span class="card-star-badge">${escapeHtml(starVal)}</span>
                <span class="card-score-badge">★ ${scoreVal}</span>
            </div>
            <div class="card-badge-top-right">
                <span class="card-rev-badge">${revCount} revs</span>
            </div>
        </div>
    `;

    return `
        <div
            class="hotel-card ${isSelected ? 'selected' : ''}"
            data-norm-key="${escapeHtml(h.norm_key || '')}"
            role="button"
            tabindex="0"
        >
            ${mediaHtml}

            <div class="hotel-card-body">
                <h4
                    class="hotel-card-name"
                    title="${escapeHtml(h.hotel_name || '')}"
                >
                    ${escapeHtml(h.hotel_name || 'Unknown hotel')}
                </h4>

                <div class="hotel-card-loc">
                    ${SVG.mapPin}
                    <span>${escapeHtml(hotelAddress)}</span>
                </div>

                ${h.sample_snippet ? `
                    <p class="hotel-card-snippet">
                        &ldquo;${escapeHtml(h.sample_snippet)}&rdquo;
                    </p>
                ` : ''}


                <div class="hotel-card-footer">
                    <a
                        href="${escapeHtml(mapsUrl)}"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="card-maps-link"
                        title="Open on Google Maps"
                        onclick="event.stopPropagation();"
                    >
                        ${SVG.externalLink}
                        <span>Maps</span>
                    </a>
                </div>
            </div>
        </div>
    `;
}

    function resetAllHotelFilters() {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = null;
        currentFilterCity = 'all';
        currentSearchQuery = '';
        if (elements.hotelSearchInput) {
            elements.hotelSearchInput.value = '';
        }
        if (elements.provinceSelect) {
            elements.provinceSelect.value = 'all';
        }
        if (elements.cityFilterBar) {
            elements.cityFilterBar.querySelectorAll('.city-pill').forEach(p => {
                p.classList.toggle('active', p.getAttribute('data-city') === 'all');
            });
        }
        fetchHotels('all', '', false);
    }
    window.__resetHotelFilters = resetAllHotelFilters;

    function renderHotelSelectionGrid(hotels, append = false) {
        if (!elements.hotelSelectionGrid) return;

        if (!append && (!hotels || hotels.length === 0)) {
            elements.hotelSelectionGrid.innerHTML = `
                <div class="hotel-empty-state">
                    <svg class="svg-icon svg-icon-lg" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    <h3>No matching hotels found</h3>
                    <p>No hotels match your current search and filters.</p>
                    <button type="button" class="empty-reset-btn" onclick="window.__resetHotelFilters()">Show all hotels</button>
                </div>
            `;
            return;
        }

        const cardsHtml = hotels.map(h => renderHotelCardHtml(h)).join('');
        if (!append) {
            elements.hotelSelectionGrid.innerHTML = cardsHtml;
        } else {
            elements.hotelSelectionGrid.insertAdjacentHTML('beforeend', cardsHtml);
        }
    }

    function handleSelectHotelCard(hotel) {
        if (!hotel) return;

        // Reuse active conversation if it has no user messages yet, otherwise create a new one
        const activeConv = getActiveConversation();
        const canReuse = activeConv && (!activeConv.messages || activeConv.messages.filter(m => m.role === 'user').length === 0);

        let targetConv;
        if (canReuse) {
            targetConv = activeConv;
            targetConv.selectedHotel = hotel;
            targetConv.title = hotel.hotel_name;
            targetConv.messages = [];
            targetConv.sessionId = 'session_' + Math.random().toString(36).substring(2, 11);
            targetConv.updatedAt = Date.now();
        } else {
            targetConv = createNewConversationData(hotel.hotel_name);
            targetConv.selectedHotel = hotel;
            conversations.unshift(targetConv);
        }

        saveConversations();
        showChatWorkspaceView(targetConv);
        updateActiveHotelBanner();

        if (elements.welcomeHero && elements.welcomeHero.parentNode) {
            elements.welcomeHero.remove();
        }

        const greeting = {
            answer: `Ask me about ${hotel.hotel_name}'s rooms, service, amenities, or guest reviews.`,
            original_reviews: []
        };
        renderBotMessageNode(greeting);
        targetConv.messages.push({
            role: 'bot',
            data: greeting,
            timestamp: Date.now()
        });
        saveConversations();
        scrollToBottom();
    }

    function deselectHotel() {
        const conv = getActiveConversation();
        if (!conv) return;
        conv.selectedHotel = null;
        saveConversations();
        updateActiveHotelBanner();
        highlightSelectedCard();
        elements.promptInput.placeholder = 'Ask about a hotel or select a card above...';
        showSystemNotification('Hotel focus cleared. You can now inquire about any hotel or select a new card.');
    }

    function updateActiveHotelBanner() {
        // Focus bar removed for minimal UI
    }

    function highlightSelectedCard() {
        const conv = getActiveConversation();
        const selNormKey = conv && conv.selectedHotel ? conv.selectedHotel.norm_key : null;
        const selName = conv && conv.selectedHotel ? conv.selectedHotel.hotel_name : null;

        const cards = document.querySelectorAll('.hotel-card');
        cards.forEach(card => {
            const normKey = card.getAttribute('data-norm-key');
            const cardName = card.querySelector('.hotel-card-name')?.textContent;
            if ((selNormKey && normKey === selNormKey) || (selName && cardName === selName)) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        });
    }

    function initHotelSelection() {
        // Remove the hotel-card aspect tags and the separate Recommended / Filter controls.
        // City and hotel-search controls remain available.
        document.querySelectorAll('.hotel-aspect-tags, .hotel-aspect-tag, .hotel-tags, .hotel-tag').forEach(node => node.remove());

        const sortControl = document.getElementById('hotelSort');
        if (sortControl) {
            const sortLabel = sortControl.labels;
            if (sortLabel) Array.from(sortLabel).forEach(label => label.remove());
            sortControl.remove();
        }

        const filterToggle = document.getElementById('toggleFilters');
        if (filterToggle) {
            const filterWrapper = filterToggle.closest('.hotel-filter-control, .hotel-filter-wrap, .filter-control, .hotel-toolbar-filter') || filterToggle;
            filterWrapper.remove();
        }
        const filterPanel = document.getElementById('hotelFilters');
        if (filterPanel) filterPanel.remove();
    
        if (elements.hotelSelectionGrid) {
            elements.hotelSelectionGrid.addEventListener('click', (e) => {
                if (e.target.closest('.card-maps-link')) return;
                const card = e.target.closest('.hotel-card');
                if (!card) return;
                const normKey = card.getAttribute('data-norm-key');
                const found = allLoadedHotels.find(h => h.norm_key === normKey);
                if (found) {
                    handleSelectHotelCard(found);
                }
            });

            elements.hotelSelectionGrid.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    if (e.target.closest('.card-maps-link')) return;
                    const card = e.target.closest('.hotel-card');
                    if (card) {
                        e.preventDefault();
                        card.click();
                    }
                }
            });
        }

        if (elements.topbarBrowseBtn) {
            elements.topbarBrowseBtn.addEventListener('click', () => {
                if (elements.hotelSelectionView && elements.hotelSelectionView.style.display !== 'none') {
                    const conv = getActiveConversation();
                    if (conv) {
                        showChatWorkspaceView(conv);
                    }
                } else {
                    showHotelSelectionView();
                }
            });
        }

        // Quick Destination Pills Filtering
        if (elements.cityFilterBar) {
            elements.cityFilterBar.addEventListener('click', (e) => {
                const pill = e.target.closest('.city-pill');
                if (!pill) return;

                document.querySelectorAll('.city-pill').forEach(p => {
                    p.classList.remove('active');
                });
                pill.classList.add('active');

                currentFilterCity = pill.getAttribute('data-city') || 'all';

                if (elements.provinceSelect) {
                    const normalizeLocation = (value) =>
                        String(value || '')
                            .normalize('NFD')
                            .replace(/[\u0300-\u036f]/g, '')
                            .replace(/đ/gi, 'd')
                            .toLowerCase()
                            .replace(/[^a-z0-9]/g, '');

                    const cityKey = normalizeLocation(currentFilterCity);
                    const pillLabel = normalizeLocation(pill.textContent);

                    // Map city buttons to the actual province names in the dropdown
                    const cityAliases = {
                        hanoi: ['hanoi', 'hanoi city', 'thanhphohanoi'],
                        hochiminhcity: [
                            'tphcm',
                            'tpho chi minh',
                            'hochiminh',
                            'hochiminhcity',
                            'hcm',
                            'saigon',
                            'thanhphohochiminh',
                            'tp hochiminh',
                            'tp hcm'
                        ],
                        danang: ['danang', 'thanhphodanang']
                    };

                    if (cityKey === 'all' || pillLabel === 'all') {
                        elements.provinceSelect.value = 'all';
                    } else {
                        const aliases = new Set([
                            cityKey,
                            pillLabel,
                            ...(cityAliases[cityKey] || []),
                            ...(cityAliases[pillLabel] || [])
                        ].map(normalizeLocation));

                        const options = Array.from(
                            elements.provinceSelect.options
                        );

                        const matchingOption = options.find(option => {
                            const value = normalizeLocation(option.value);
                            const text = normalizeLocation(
                                option.textContent.replace(/\s*\(\d[\d,]*\)\s*$/, '')
                            );

                            return aliases.has(value) || aliases.has(text);
                        });

                        if (matchingOption) {
                            elements.provinceSelect.value = matchingOption.value;
                        } else {
                            // Avoid leaving an unrelated province selected
                            elements.provinceSelect.value = 'all';
                        }
                    }
                }

                fetchHotels(currentFilterCity, currentSearchQuery, false);
            });
        }

        // All 48 Provinces Dropdown Filtering
        if (elements.provinceSelect) {
            elements.provinceSelect.addEventListener('change', (e) => {
                currentFilterCity = e.target.value;
                document.querySelectorAll('.city-pill').forEach(p => {
                    if (p.getAttribute('data-city') === currentFilterCity) {
                        p.classList.add('active');
                    } else {
                        p.classList.remove('active');
                    }
                });
                fetchHotels(currentFilterCity, currentSearchQuery, false);
            });
        }

        // Search Input (Debounced hotel name & address filter)
        const sortSelect = document.getElementById('hotelSort');
        const toggleFilters = document.getElementById('toggleFilters');
        const hotelFilters = document.getElementById('hotelFilters');
        const minRatingSelect = document.getElementById('minHotelRating');
        const minReviewsSelect = document.getElementById('minHotelReviews');
        const resetFiltersBtn = document.getElementById('resetHotelFilters');

        if (toggleFilters && hotelFilters) {
            toggleFilters.addEventListener('click', () => {
                hotelFilters.classList.toggle('show');
            });
        }

        function reloadHotelResults() {
            fetchHotels(currentFilterCity, currentSearchQuery, false);
        }

        sortSelect?.addEventListener('change', reloadHotelResults);
        minRatingSelect?.addEventListener('change', reloadHotelResults);
        minReviewsSelect?.addEventListener('change', reloadHotelResults);

        resetFiltersBtn?.addEventListener('click', () => {
            if (sortSelect) sortSelect.value = 'recommended';
            if (minRatingSelect) minRatingSelect.value = '0';
            if (minReviewsSelect) minReviewsSelect.value = '0';

            reloadHotelResults();
        });
        if (elements.hotelSearchInput) {
            elements.hotelSearchInput.addEventListener('input', (e) => {
                currentSearchQuery = e.target.value.trim();
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(() => {
                    fetchHotels(currentFilterCity, currentSearchQuery, false);
                }, 220);
            });
        }

        // Load More Hotels (Pagination 9 hotels at a time)
        if (elements.loadMoreHotelsBtn) {
            elements.loadMoreHotelsBtn.addEventListener('click', () => {
                if (hasMoreHotels && !isLoadingHotels) {
                    fetchHotels(currentFilterCity, currentSearchQuery, true);
                }
            });
        }

        fetchHotels('all', '', false);
    }

    // -------------------------------------------------------------------------
    // App Initialization
    // -------------------------------------------------------------------------
    initTheme();
    initSidebar();
    if (elements.hotelSelectionView) {
        elements.hotelSelectionView.addEventListener('scroll', updateHomeTitle, { passive: true });
        window.addEventListener('resize', updateHomeTitle);
    }
    loadConversations();
    renderConversationLists();
    renderActiveConversationMessages();
    initModelSelector();
    initHotelSelection();
    updateActiveHotelBanner();

    // Determine initial view: if there is an active conversation with a selected hotel, show chat; otherwise show hotel selection hub
    const initialConv = getActiveConversation();
    if (initialConv && initialConv.selectedHotel) {
        showChatWorkspaceView(initialConv);
    } else {
        showHotelSelectionView();
    }

})();
