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
    const enforceWait = timerElement.dataset.enforceWait === 'True';  // Only enforce in production
    let timerInterval;

    // Persist timer start time across page refreshes
    const timerStorageKey = `timer_state_${pageName}`;

    function getTimerState() {
        try {
            const stored = sessionStorage.getItem(timerStorageKey);
            return stored ? JSON.parse(stored) : null;
        } catch (e) {
            return null;
        }
    }

    function saveTimerState(state) {
        try {
            sessionStorage.setItem(timerStorageKey, JSON.stringify(state));
        } catch (e) {
            // Ignore storage errors
        }
    }

    // Initialize or restore timer state
    let timerState = getTimerState();
    if (!timerState) {
        timerState = { startTime: Date.now(), expired: false };
        saveTimerState(timerState);
    }

    // Restore window.timerExpired from sessionStorage (survives page refresh)
    if (timerState.expired) {
        window.timerExpired = true;
    }

    // Calculate remaining seconds based on elapsed time
    const elapsedMs = Date.now() - timerState.startTime;
    const elapsedSeconds = Math.floor(elapsedMs / 1000);
    let remainingSeconds = Math.max(0, totalSeconds - elapsedSeconds);

    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    function updateDisplay() {
        // Only show top-right timer if NOT enforcing (informational mode)
        // When enforcing, the countdown is shown on the button instead
        if (!enforceWait) {
            timerDisplay.textContent = formatTime(remainingSeconds);
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

        // Enable navigation - set global flag and dispatch event
        window.timerExpired = true;
        window.dispatchEvent(new CustomEvent('timerExpired'));

        // Enable all navigation buttons that were waiting for timer
        const buttons = document.querySelectorAll('[data-wait-for-timer="true"]');
        buttons.forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('btn-waiting');
            // Remove the wait attribute so clicks work even after page refresh
            // (when window.timerExpired resets to undefined)
            delete btn.dataset.waitForTimer;
            if (btn.dataset.originalText) {
                btn.textContent = btn.dataset.originalText;
                delete btn.dataset.originalText;
            }
        });

        // Also persist timer expired state in sessionStorage for reliability
        saveTimerState({ startTime: timerState.startTime, expired: true });
    }

    function tick() {
        remainingSeconds--;
        updateDisplay();
        updateWaitingButtons();

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

    // Disable navigation buttons until timer expires (production only)
    function disableNavigationUntilExpired() {
        if (!enforceWait) return;  // Skip in development/testing

        // Find submit/next buttons
        const buttons = document.querySelectorAll('button[type="submit"], #next-btn, .btn-primary');
        buttons.forEach(btn => {
            // Don't disable send button in chat
            if (btn.id === 'send-btn') return;

            btn.disabled = true;
            btn.dataset.waitForTimer = 'true';
            btn.dataset.originalText = btn.textContent;
            btn.classList.add('btn-waiting');
        });

        // Also prevent form submission until timer expires
        // (disabled buttons don't fully prevent form submission via keyboard)
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            // Skip chat form (it's handled separately)
            if (form.id === 'chat-form') return;

            form.addEventListener('submit', function(e) {
                if (!window.timerExpired) {
                    e.preventDefault();
                    e.stopPropagation();
                    return false;
                }
            });
        });

        // Update button text with remaining time
        updateWaitingButtons();
    }

    function updateWaitingButtons() {
        const buttons = document.querySelectorAll('[data-wait-for-timer="true"]');
        buttons.forEach(btn => {
            if (btn.disabled) {
                btn.textContent = `Available in ${formatTime(remainingSeconds)}`;
            }
        });
    }

    // Initialize: disable navigation until timer expires
    disableNavigationUntilExpired();

    // Hide top-right timer when enforcing (countdown shown on button instead)
    if (enforceWait) {
        const timerContainer = document.getElementById('timer-container');
        if (timerContainer) {
            timerContainer.style.display = 'none';
        }
    }

    // Start the timer when the page loads (or handle already expired)
    if (remainingSeconds <= 0) {
        // Timer already expired before page load
        handleTimerExpired();
    } else {
        startTimer();
    }

    // Log when user leaves the page
    window.addEventListener('beforeunload', function() {
        logEvent('page_unload', { remaining_seconds: remainingSeconds });
    });
})();
