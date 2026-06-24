/**
 * Chat functionality for the AI discussion interface.
 */

(function() {
    'use strict';

    // Get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrfToken = getCookie('csrftoken');

    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendBtn = document.getElementById('send-btn');
    const dilemmaId = document.getElementById('dilemma-id')?.value;

    if (!chatForm || !chatInput || !chatMessages) {
        return;
    }

    let isStreaming = false;
    let chatHistory = [];  // Track all messages locally
    let userMessageCount = 0;  // Track number of user messages sent
    const MIN_USER_MESSAGES = 3;  // Minimum required user messages before proceeding
    const STREAM_TIMEOUT_MS = 90000;  // 90 second timeout for streaming responses

    // Soft limits for encouraging users to wrap up
    const SOFT_TIME_LIMIT_MS = 5 * 60 * 1000;  // 5 minutes
    const MESSAGE_LIMIT = 6;  // Show modal after 6 user messages

    // Persist timer state across page refreshes using sessionStorage
    const storageKey = `chat_state_${dilemmaId}`;

    function getChatState() {
        try {
            const stored = sessionStorage.getItem(storageKey);
            return stored ? JSON.parse(stored) : null;
        } catch (e) {
            return null;
        }
    }

    function saveChatState(state) {
        try {
            const current = getChatState() || {};
            sessionStorage.setItem(storageKey, JSON.stringify({ ...current, ...state }));
        } catch (e) {
            // Ignore storage errors
        }
    }

    // Initialize or restore state
    let chatState = getChatState();
    if (!chatState) {
        chatState = {
            startTime: Date.now(),
            timeBannerShown: false,
            turnModalShown: false
        };
        saveChatState(chatState);
    }

    let timeBannerShown = chatState.timeBannerShown;
    let turnModalShown = chatState.turnModalShown;
    const chatStartTime = chatState.startTime;

    function createMessageElement(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender === 'user' ? 'message-user' : 'message-ai'}`;

        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = sender === 'user' ? 'You' : 'AI';

        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.textContent = text;

        messageDiv.appendChild(senderDiv);
        messageDiv.appendChild(textDiv);

        return messageDiv;
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Show the time limit banner
    function showTimeBanner() {
        const banner = document.getElementById('time-banner');
        if (banner && !timeBannerShown) {
            banner.style.display = 'block';
            timeBannerShown = true;
            saveChatState({ timeBannerShown: true });
            logEvent('time_banner_shown', { minutes: 5 });
        }
    }

    // Show the turn limit modal
    function showTurnModal() {
        const modal = document.getElementById('turn-modal');
        if (modal && !turnModalShown) {
            modal.style.display = 'flex';
            turnModalShown = true;
            saveChatState({ turnModalShown: true });
            logEvent('turn_modal_shown', { user_messages: userMessageCount });
        }
    }

    // Hide the turn limit modal
    function hideTurnModal() {
        const modal = document.getElementById('turn-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Check if we should show the turn modal (after AI response completes)
    function checkTurnLimit() {
        if (userMessageCount >= MESSAGE_LIMIT && !turnModalShown) {
            showTurnModal();
            turnModalShown = true;
        }
    }

    function hasEnoughMessages() {
        return userMessageCount >= MIN_USER_MESSAGES;
    }

    function removePlaceholder() {
        const placeholder = chatMessages.querySelector('.chat-placeholder');
        if (placeholder) {
            placeholder.remove();
        }
    }

    function setLoading(loading) {
        isStreaming = loading;
        sendBtn.disabled = loading;
        chatInput.disabled = loading;

        if (loading) {
            sendBtn.textContent = 'Sending...';
        } else {
            sendBtn.textContent = 'Send';
        }
    }

    function logEvent(eventType, data = {}) {
        fetch('/api/log-event/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                event_type: eventType,
                page: window.pageName || 'chat',
                data: data
            })
        }).catch(console.error);
    }

    async function sendMessage(message) {
        setLoading(true);
        removePlaceholder();

        // Add user message to UI and history
        const userMessage = createMessageElement('user', message);
        chatMessages.appendChild(userMessage);
        scrollToBottom();
        chatHistory.push({ sender: 'user', text: message, timestamp: new Date().toISOString() });

        // Increment user message count
        userMessageCount++;

        // Create AI message placeholder
        const aiMessage = createMessageElement('ai', '');
        const aiTextDiv = aiMessage.querySelector('.message-text');
        chatMessages.appendChild(aiMessage);
        scrollToBottom();

        logEvent('message_sent', { message_length: message.length });

        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(function() {
            controller.abort();
            logEvent('stream_timeout', { timeout_ms: STREAM_TIMEOUT_MS });
        }, STREAM_TIMEOUT_MS);

        try {
            const response = await fetch('/api/chat/send/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                signal: controller.signal,
                body: JSON.stringify({
                    message: message,
                    dilemma_id: dilemmaId,
                    history: chatHistory.slice(0, -1)  // Send history without the just-added user message
                })
            });

            if (!response.ok) {
                throw new Error('Failed to send message');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    break;
                }

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.chunk) {
                                fullResponse += data.chunk;
                                aiTextDiv.textContent = fullResponse;
                                scrollToBottom();
                            }

                            if (data.done) {
                                // Add AI response to history
                                chatHistory.push({ sender: 'ai', text: fullResponse, timestamp: new Date().toISOString() });
                                logEvent('response_received', { response_length: fullResponse.length });
                                // Save messages to database after each exchange
                                saveChatMessages();
                                // Check if we should show the turn limit modal
                                checkTurnLimit();
                            }

                            if (data.error) {
                                aiTextDiv.textContent = 'Error: ' + data.error;
                                logEvent('response_error', { error: data.error });
                            }
                        } catch (e) {
                            // Ignore JSON parse errors for incomplete chunks
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error sending message:', error);
            if (error.name === 'AbortError') {
                aiTextDiv.textContent = 'Response timed out. Please try again.';
                logEvent('send_error', { error: 'timeout' });
            } else {
                aiTextDiv.textContent = 'An error occurred. Please try again.';
                logEvent('send_error', { error: error.message });
            }
        } finally {
            clearTimeout(timeoutId);
        }

        setLoading(false);
        chatInput.focus();
    }

    // Form submission handler
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const message = chatInput.value.trim();
        if (!message || isStreaming) {
            return;
        }

        chatInput.value = '';
        sendMessage(message);
    });

    // Enter key to send (Shift+Enter for new line)
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // Auto-resize textarea
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 150) + 'px';
    });

    // Save chat messages to database
    async function saveChatMessages() {
        if (chatHistory.length === 0) return;

        try {
            await fetch('/api/chat/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    dilemma_id: dilemmaId,
                    messages: chatHistory
                })
            });
        } catch (error) {
            console.error('Error saving chat:', error);
        }
    }

    // Minimum messages modal handling
    function showMinMessagesModal() {
        const modal = document.getElementById('min-messages-modal');
        const textEl = document.getElementById('min-messages-text');
        if (modal) {
            const remaining = MIN_USER_MESSAGES - userMessageCount;
            textEl.textContent = `Please send at least ${remaining} more message${remaining > 1 ? 's' : ''} before continuing.`;
            modal.style.display = 'flex';
            // Focus the "Go Back" button (which is the safe default)
            const cancelBtn = document.getElementById('min-messages-cancel');
            if (cancelBtn) {
                cancelBtn.focus();
            }
            logEvent('min_messages_modal_shown', { user_messages: userMessageCount, remaining: remaining });
        }
    }

    function hideMinMessagesModal() {
        const modal = document.getElementById('min-messages-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Save messages before leaving page
    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) {
        nextBtn.addEventListener('click', async function(e) {
            e.preventDefault();

            // Block if timer hasn't expired yet (timer.js handles the button state)
            if (nextBtn.dataset.waitForTimer === 'true' && !window.timerExpired) {
                return;
            }

            // Show warning modal if not enough messages sent
            if (!hasEnoughMessages()) {
                showMinMessagesModal();
                return;
            }

            await saveChatMessages();
            // Navigate to the form's action URL
            const form = this.closest('form');
            if (form && form.action) {
                window.location.href = form.action;
            } else {
                // Fallback: log error and alert user
                logEvent('navigation_error', { error: 'form_not_found' });
                alert('Navigation error. Please refresh the page and try again.');
            }
        });
    }

    // Min messages modal button handlers
    const minMessagesCancelBtn = document.getElementById('min-messages-cancel');
    const minMessagesContinueBtn = document.getElementById('min-messages-continue');

    if (minMessagesCancelBtn) {
        minMessagesCancelBtn.addEventListener('click', function() {
            hideMinMessagesModal();
            logEvent('min_messages_modal_cancelled', { user_messages: userMessageCount });
            chatInput.focus();
        });
    }

    if (minMessagesContinueBtn) {
        minMessagesContinueBtn.addEventListener('click', async function() {
            logEvent('min_messages_modal_continued', { user_messages: userMessageCount });
            hideMinMessagesModal();
            await saveChatMessages();
            // Navigate to the next page
            const nextBtn = document.getElementById('next-btn');
            if (nextBtn) {
                const form = nextBtn.closest('form');
                if (form && form.action) {
                    window.location.href = form.action;
                } else {
                    logEvent('navigation_error', { error: 'form_not_found', source: 'min_messages_modal' });
                    alert('Navigation error. Please refresh the page and try again.');
                }
            }
        });
    }

    // Also save on page unload (for timer expiration or back button)
    window.addEventListener('beforeunload', function() {
        if (chatHistory.length === 0) return;
        // Use sendBeacon for reliable delivery on page unload
        const data = JSON.stringify({
            dilemma_id: dilemmaId,
            messages: chatHistory
        });
        navigator.sendBeacon('/api/chat/save/', new Blob([data], { type: 'application/json' }));
    });

    // Focus input on load
    chatInput.focus();

    // Log page load
    logEvent('chat_page_loaded', { dilemma_id: dilemmaId });

    // Load existing messages from DOM into chatHistory (for page refresh scenarios)
    const existingMessages = chatMessages.querySelectorAll('.chat-message');
    existingMessages.forEach(function(msgEl) {
        const sender = msgEl.classList.contains('message-user') ? 'user' : 'ai';
        const text = msgEl.querySelector('.message-text').textContent;
        chatHistory.push({ sender: sender, text: text, timestamp: new Date().toISOString() });
    });

    // Count existing user messages
    userMessageCount = chatHistory.filter(function(msg) { return msg.sender === 'user'; }).length;

    // Check if turn modal should be shown on page load (e.g., after refresh with 6+ messages)
    // Only show if not already shown/dismissed before
    if (userMessageCount >= MESSAGE_LIMIT && !turnModalShown) {
        showTurnModal();
    }

    // Request initial AI message if no chat history exists
    async function requestInitialMessage() {
        const placeholder = chatMessages.querySelector('.chat-placeholder');
        if (!placeholder) {
            // Chat history already exists, don't request initial message
            return;
        }

        setLoading(true);
        removePlaceholder();

        // Create AI message placeholder
        const aiMessage = createMessageElement('ai', '');
        const aiTextDiv = aiMessage.querySelector('.message-text');
        chatMessages.appendChild(aiMessage);

        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(function() {
            controller.abort();
            logEvent('init_stream_timeout', { timeout_ms: STREAM_TIMEOUT_MS });
        }, STREAM_TIMEOUT_MS);

        try {
            const response = await fetch('/api/chat/init/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                signal: controller.signal,
                body: JSON.stringify({
                    dilemma_id: dilemmaId
                })
            });

            if (!response.ok) {
                throw new Error('Failed to get initial message');
            }

            // Check if it's a JSON response (already started)
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                if (data.already_started) {
                    aiMessage.remove();
                    setLoading(false);
                    return;
                }
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    break;
                }

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.chunk) {
                                fullResponse += data.chunk;
                                aiTextDiv.textContent = fullResponse;
                                scrollToBottom();
                            }

                            if (data.error) {
                                aiTextDiv.textContent = 'Error: ' + data.error;
                            }
                        } catch (e) {
                            // Ignore JSON parse errors
                        }
                    }
                }
            }

            // Add AI response to history
            chatHistory.push({ sender: 'ai', text: fullResponse, timestamp: new Date().toISOString() });
            logEvent('initial_ai_message_received', { response_length: fullResponse.length });
            // Save initial message to database
            saveChatMessages();

        } catch (error) {
            console.error('Error getting initial message:', error);
            if (error.name === 'AbortError') {
                aiTextDiv.textContent = 'Response timed out. Please refresh the page.';
                logEvent('init_error', { error: 'timeout' });
            } else {
                aiTextDiv.textContent = 'An error occurred. Please refresh the page.';
                logEvent('init_error', { error: error.message });
            }
        } finally {
            clearTimeout(timeoutId);
        }

        setLoading(false);
        chatInput.focus();
    }

    // Request initial AI message on load
    requestInitialMessage();

    // Set up 5-minute timer for showing the time banner (accounting for elapsed time)
    const elapsedTime = Date.now() - chatStartTime;
    const remainingTime = SOFT_TIME_LIMIT_MS - elapsedTime;

    if (timeBannerShown) {
        // Banner was already shown before refresh - show it immediately
        const banner = document.getElementById('time-banner');
        if (banner) banner.style.display = 'block';
    } else if (remainingTime <= 0) {
        // Time already elapsed - show banner immediately
        showTimeBanner();
    } else {
        // Set timer for remaining time
        setTimeout(function() {
            showTimeBanner();
        }, remainingTime);
    }

    // Modal button event listeners
    const modalContinueBtn = document.getElementById('modal-continue');
    const modalNextBtn = document.getElementById('modal-next');

    if (modalContinueBtn) {
        modalContinueBtn.addEventListener('click', function() {
            hideTurnModal();
            logEvent('turn_modal_continue', { user_messages: userMessageCount });
            chatInput.focus();
        });
    }

    if (modalNextBtn) {
        modalNextBtn.addEventListener('click', async function() {
            logEvent('turn_modal_next', { user_messages: userMessageCount });
            await saveChatMessages();
            // Navigate to the next page
            const nextBtn = document.getElementById('next-btn');
            if (nextBtn) {
                const form = nextBtn.closest('form');
                if (form && form.action) {
                    window.location.href = form.action;
                } else {
                    logEvent('navigation_error', { error: 'form_not_found', source: 'turn_modal' });
                    alert('Navigation error. Please refresh the page and try again.');
                }
            }
        });
    }
})();
