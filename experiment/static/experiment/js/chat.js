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

        // Add user message to UI
        const userMessage = createMessageElement('user', message);
        chatMessages.appendChild(userMessage);
        scrollToBottom();

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
                    dilemma_id: dilemmaId
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
                                logEvent('response_received', { response_length: fullResponse.length });
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

    // Focus input on load
    chatInput.focus();

    // Log page load
    logEvent('chat_page_loaded', { dilemma_id: dilemmaId });
})();
