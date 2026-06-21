// extension/content.js

function injectKeyIcons() {
    // Find username/email input fields
    const inputs = document.querySelectorAll('input[type="email"], input[type="text"], input[name*="user"], input[name*="login"]');

    inputs.forEach(input => {
        if (input.dataset.spInjected || input.offsetWidth < 50) return;

        // Create the key icon
        const icon = document.createElement('img');
        icon.src = chrome.runtime.getURL('key.png');
        icon.style.cssText = "position: absolute; right: 8px; top: 50%; transform: translateY(-50%); width: 24px; height: 24px; cursor: pointer; z-index: 10000; opacity: 0.5; transition: opacity 0.2s;";

        icon.onmouseover = () => icon.style.opacity = '1';
        icon.onmouseout = () => icon.style.opacity = '0.5';

        // When the user clicks the key icon
        icon.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();

            // 1. Prompt for Master Password securely
            let mpw = prompt("SecurePass: Enter Master Password to unlock vault for " + window.location.hostname);
            if (!mpw) return;

            // 2. Send request to background.js
            let hostname = window.location.hostname;
            chrome.runtime.sendMessage({action: "get_credentials", url: hostname, password: mpw}, (response) => {

                if (chrome.runtime.lastError) {
                    alert("SecurePass Error: Native Host not connected.");
                    return;
                }

                if (response && response.success && response.accounts.length > 0) {

                    if (response.accounts.length === 1) {
                        // Exactly 1 account found -> Autofill instantly
                        fillFields(input, response.accounts[0]);
                    } else {
                        // Multiple accounts found -> Show a selection menu
                        showAccountMenu(icon, input, response.accounts);
                    }

                } else {
                    alert("SecurePass: " + (response.error || "No credentials found for this website."));
                }
            });
        };

        const container = input.parentElement;
        if (window.getComputedStyle(container).position === 'static') {
            container.style.position = 'relative';
        }
        container.appendChild(icon);
        input.dataset.spInjected = 'true';
    });
}

// Helper to fill the fields
function fillFields(inputElement, account) {
    inputElement.value = account.email;
    let form = inputElement.closest('form') || document;
    let passField = form.querySelector('input[type="password"]');
    if (passField) {
        passField.value = account.password;
    }
}

// Helper to show a dropdown menu if there are multiple accounts
function showAccountMenu(iconElement, inputElement, accounts) {
    // Remove any existing menu first
    let existingMenu = document.getElementById('securepass-dropdown');
    if (existingMenu) existingMenu.remove();

    // Create the dropdown container
    const menu = document.createElement('div');
    menu.id = 'securepass-dropdown';
    menu.style.cssText = "position: absolute; top: calc(50% + 15px); right: 0; background: white; border: 1px solid #ccc; border-radius: 4px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); z-index: 10001; padding: 5px; min-width: 150px; font-family: Arial, sans-serif;";

    // Create a button for each account
    accounts.forEach(acc => {
        let btn = document.createElement('button');
        btn.innerText = acc.email;
        btn.style.cssText = "display: block; width: 100%; padding: 8px; margin-bottom: 2px; border: none; background: #f0f0f0; cursor: pointer; text-align: left; font-size: 13px; border-radius: 3px;";

        btn.onmouseover = () => btn.style.background = '#e0e0e0';
        btn.onmouseout = () => btn.style.background = '#f0f0f0';

        // When clicked, fill the fields and close the menu
        btn.onclick = (e) => {
            e.preventDefault();
            fillFields(inputElement, acc);
            menu.remove();
        };
        menu.appendChild(btn);
    });

    // Close menu if user clicks anywhere else on the page
    document.addEventListener('click', function closeMenu(e) {
        if (!menu.contains(e.target) && e.target !== iconElement) {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        }
    });

    // Attach menu to the same container as the icon
    iconElement.parentElement.appendChild(menu);
}

// Run immediately, and keep watching for dynamically loaded login forms
injectKeyIcons();
new MutationObserver(injectKeyIcons).observe(document.body, { childList: true, subtree: true });