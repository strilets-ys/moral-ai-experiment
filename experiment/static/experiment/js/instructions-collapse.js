/**
 * Collapsible instructions functionality.
 *
 * After participants have seen the instruction page and clicked "I understand",
 * the instructions on the actual task pages start collapsed but can be expanded
 * if they need to refresh their memory.
 */
(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        const toggle = document.getElementById('instructions-toggle');
        const content = document.getElementById('instructions-content');
        const icon = toggle?.querySelector('.toggle-icon');

        if (toggle && content) {
            // Start collapsed (instructions were shown on previous page)
            content.classList.add('collapsed');
            if (icon) {
                icon.classList.add('collapsed');
            }

            toggle.addEventListener('click', function() {
                content.classList.toggle('collapsed');
                if (icon) {
                    icon.classList.toggle('collapsed');
                }

                // Log the toggle action
                logToggle(content.classList.contains('collapsed') ? 'collapsed' : 'expanded');
            });
        }
    });

    /**
     * Log instruction toggle to server.
     */
    function logToggle(state) {
        const csrfToken = getCookie('csrftoken');
        const pageName = window.pageName || 'unknown';

        fetch('/api/log-event/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                event_type: 'instructions_toggled',
                page: pageName,
                data: {
                    state: state,
                    timestamp: new Date().toISOString()
                }
            })
        }).catch(function(err) {
            console.error('Failed to log instructions toggle:', err);
        });
    }

    /**
     * Get a cookie value by name.
     */
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
})();
