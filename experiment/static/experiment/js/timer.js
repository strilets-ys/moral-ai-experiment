/**
 * Timer functionality for timed pages in the experiment.
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

    const timerElement = document.getElementById('timer');
    const timerDisplay = document.getElementById('timer-display');

    if (!timerElement || !timerDisplay) {
        return;
    }

    const totalSeconds = parseInt(timerElement.dataset.seconds, 10);
    const pageName = timerElement.dataset.page || window.pageName || 'unknown';
    let remainingSeconds = totalSeconds;
    let timerInterval;

    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    function updateDisplay() {
        timerDisplay.textContent = formatTime(remainingSeconds);

        // Warning state at 60 seconds
        if (remainingSeconds <= 60 && remainingSeconds > 0) {
            timerElement.classList.add('timer-warning');
        }

        // Expired state
        if (remainingSeconds <= 0) {
            timerElement.classList.remove('timer-warning');
            timerElement.classList.add('timer-expired');
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
                page: pageName,
                data: data
            })
        }).catch(console.error);
    }

    function handleTimerExpired() {
        logEvent('timer_expired', { remaining_seconds: 0 });

        // Show the "please move on" message
        const warningMessage = document.getElementById('timer-warning-message');
        if (warningMessage) {
            warningMessage.style.display = 'block';
        }
    }

    function tick() {
        remainingSeconds--;
        updateDisplay();

        if (remainingSeconds <= 0) {
            clearInterval(timerInterval);
            handleTimerExpired();
        }
    }

    function startTimer() {
        updateDisplay();
        timerInterval = setInterval(tick, 1000);
        logEvent('timer_started', { total_seconds: totalSeconds });
    }

    // Start the timer when the page loads
    startTimer();

    // Log when user leaves the page
    window.addEventListener('beforeunload', function() {
        logEvent('page_unload', { remaining_seconds: remainingSeconds });
    });
})();
