// =======================================================
//  Recorder Bootstrap
//  This runs inside the AUT (Application Under Test)
// =======================================================

// Global container for recorded steps
window.__recordedSteps = window.__recordedSteps || [];

// Track last URL to avoid duplicate entries
let lastUrl = window.location.href;

// -------------------------------------------------------
// Helper to push navigation event
// -------------------------------------------------------
function recordNavigation(newUrl) {
    if (!newUrl || newUrl === lastUrl) return;

    lastUrl = newUrl;

    window.__recordedSteps.push({
        order: window.__recordedSteps.length + 1,
        action: "NAVIGATE",
        selector: null,
        input_value: null,
        url: newUrl,
        meta: {
            type: "navigation",
            timestamp: Date.now()
        }
    });

    console.log("[Recorder] Navigation event recorded:", newUrl);
}

// -------------------------------------------------------
// 1️⃣ Capture initial page URL
// -------------------------------------------------------
recordNavigation(window.location.href);

// -------------------------------------------------------
// 2️⃣ Capture pushState() & replaceState() (SPA routing)
// -------------------------------------------------------
(function(history) {
    const originalPush = history.pushState;
    const originalReplace = history.replaceState;

    history.pushState = function() {
        const result = originalPush.apply(history, arguments);
        recordNavigation(window.location.href);
        return result;
    };

    history.replaceState = function() {
        const result = originalReplace.apply(history, arguments);
        recordNavigation(window.location.href);
        return result;
    };
})(window.history);

// -------------------------------------------------------
// 3️⃣ Capture browser back/forward navigation
// -------------------------------------------------------
window.addEventListener("popstate", () => {
    recordNavigation(window.location.href);
});

// -------------------------------------------------------
// 4️⃣ Detect full-page navigations via window.location
// -------------------------------------------------------
let originalLocation = window.location;

Object.defineProperty(window, "location", {
    configurable: true,
    enumerable: true,
    get() {
        return originalLocation;
    },
    set(url) {
        recordNavigation(url);
        originalLocation.href = url;
    }
});

// Export for recorder UI if needed
window.__recorderHooks = {
    recordNavigation
};
