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

    function updateNextButtonState() {
        const nextBtn = document.getElementById('next-btn');
        const turnCounter = document.getElementById('turn-counter');

        if (!nextBtn) return;

        const remaining = MIN_USER_MESSAGES - userMessageCount;

        if (remaining > 0) {
            nextBtn.disabled = true;
            nextBtn.classList.add('btn-disabled');
            if (turnCounter) {
                turnCounter.textContent = `Please send at least ${remaining} more message${remaining > 1 ? 's' : ''} before continuing.`;
                turnCounter.style.display = 'block';
            }
        } else {
            nextBtn.disabled = false;
            nextBtn.classList.remove('btn-disabled');
            if (turnCounter) {
                turnCounter.textContent = 'You may now continue when ready.';
                turnCounter.style.display = 'block';
            }
        }
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

        try {
            const response = await fetch('/api/chat/send/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
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
                                // Update button state after AI response
                                updateNextButtonState();
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
            aiTextDiv.textContent = 'An error occurred. Please try again.';
            logEvent('send_error', { error: error.message });
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

    // Save messages before leaving page
    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) {
        nextBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            await saveChatMessages();
            // Navigate to the form's action URL
            const form = this.closest('form');
            if (form) {
                window.location.href = form.action;
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

    // Count existing user messages from chat history rendered on page
    const existingUserMessages = chatMessages.querySelectorAll('.message-user');
    userMessageCount = existingUserMessages.length;

    // Initialize next button state
    updateNextButtonState();

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

        try {
            const response = await fetch('/api/chat/init/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
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

        } catch (error) {
            console.error('Error getting initial message:', error);
            aiTextDiv.textContent = 'An error occurred. Please refresh the page.';
        }

        setLoading(false);
        chatInput.focus();
    }

    // Request initial AI message on load
    requestInitialMessage();
})();
