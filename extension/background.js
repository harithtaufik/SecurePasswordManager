// extension/background.js

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    // Listen for requests coming from either popup.js or content.js
    if (request.action === "get_credentials") {

        let targetUrl = request.url;
        let masterPassword = request.password;

        // Failsafe: Ensure a URL was actually provided before bothering Python
        if (!targetUrl) {
            sendResponse({ success: false, error: "Blocked: No URL provided for validation." });
            return false;
        }

        // Package the payload exactly how the Python Bouncer expects it
        let messagePayload = {
            "action": "get_credentials",
            "password": masterPassword,
            "url": targetUrl
        };

        // Send to the Python Native Host securely
        chrome.runtime.sendNativeMessage(
            'com.harith.securepass',
            messagePayload,
            function(response) {
                if (chrome.runtime.lastError) {
                    console.error("Native Host Error:", chrome.runtime.lastError.message);
                    sendResponse({ success: false, error: "Native Host not connected or failed." });
                } else {
                    // Send the Python response back to whoever asked for it (popup or content script)
                    sendResponse(response);
                }
            }
        );

        // Returning true tells Chrome that we are waiting for a background response
        return true;
    }
});