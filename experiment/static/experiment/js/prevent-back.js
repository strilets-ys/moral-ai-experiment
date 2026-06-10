/**
 * Prevent back navigation in the experiment.
 *
 * This script uses multiple techniques to prevent participants from
 * using the browser's back button to return to previous pages.
 */
(function() {
    'use strict';

    // Check if we should redirect (set by server when rating already exists)
    if (window.alreadyRatedRedirectUrl) {
        window.location.replace(window.alreadyRatedRedirectUrl);
        return;
    }

    // Force reload when page is restored from bfcache (back-forward cache)
    // Use a flag to prevent infinite reload loops
    var reloadKey = 'prevent_back_reload_' + window.location.pathname;

    window.addEventListener('pageshow', function(event) {
        if (event.persisted) {
            // Page was restored from bfcache - check if we recently reloaded
            var lastReload = sessionStorage.getItem(reloadKey);
            var now = Date.now();

            if (!lastReload || (now - parseInt(lastReload)) > 2000) {
                // Haven't reloaded recently, do it now
                sessionStorage.setItem(reloadKey, now.toString());
                window.location.reload();
            }
        }
    });

    // Clear the reload flag after successful page load
    setTimeout(function() {
        sessionStorage.removeItem(reloadKey);
    }, 3000);

    // Push a state to prevent back navigation
    history.pushState(null, null, location.href);

    window.addEventListener('popstate', function(e) {
        // Push state again to stay on current page
        history.pushState(null, null, location.href);

        // Log the back button attempt
        logBackAttempt();
    });

    /**
     * Log the back button attempt to the server.
     */
    function logBackAttempt() {
        const csrfToken = getCookie('csrftoken');
        const pageName = window.pageName || 'unknown';

        fetch('/api/log-event/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                event_type: 'back_button_attempt',
                page: pageName,
                data: {
                    url: location.href,
                    timestamp: new Date().toISOString()
                }
            })
        }).catch(function(err) {
            // Silently fail - don't break the page
            console.error('Failed to log back button attempt:', err);
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
