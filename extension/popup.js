// extension/popup.js

document.getElementById('search-btn').addEventListener('click', async () => {
    let pw = document.getElementById('master-pw').value;
    let statusTxt = document.getElementById('status');
    let accountList = document.getElementById('account-list');

    if (!pw) {
        statusTxt.innerText = "Please enter Master Password";
        return;
    }

    accountList.innerHTML = ""; // Clear previous list
    statusTxt.innerText = "Searching vault...";
    statusTxt.style.color = "blue";

    // 1. Get the current active tab securely
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    let url = new URL(tab.url).hostname;

    // 2. Send message to the background.js hub instead of Python directly
    chrome.runtime.sendMessage(
        { action: "get_credentials", url: url, password: pw },
        function(response) {
            if (chrome.runtime.lastError) {
                statusTxt.innerText = "Error: Background script not responding.";
                statusTxt.style.color = "red";
                return;
            }

            if (response && response.success) {
                let accounts = response.accounts;

                if (accounts.length === 1) {
                    // Only one account found, autofill immediately
                    injectCredentials(tab.id, accounts[0].email, accounts[0].password);
                    statusTxt.innerText = "Autofill Success! ✅";
                    statusTxt.style.color = "green";
                } else {
                    // Multiple accounts found, let user choose
                    statusTxt.innerText = "Multiple accounts found. Click one to autofill:";
                    statusTxt.style.color = "black";

                    accounts.forEach(acc => {
                        let btn = document.createElement('button');
                        btn.className = "account-btn";
                        btn.innerText = "Use: " + acc.email;
                        btn.onclick = () => {
                            injectCredentials(tab.id, acc.email, acc.password);
                            statusTxt.innerText = "Autofilled " + acc.email + " ✅";
                            statusTxt.style.color = "green";
                        };
                        accountList.appendChild(btn);
                    });
                }
            } else {
                statusTxt.innerText = response.error || "No password found.";
                statusTxt.style.color = "red";
            }
        }
    );
});

// Helper function to send data to the webpage
function injectCredentials(tabId, email, password) {
    chrome.scripting.executeScript({
        target: { tabId: tabId },
        func: fillForm,
        args: [email, password]
    });
}

// This function runs INSIDE the website you are looking at
function fillForm(email, password) {
    let userFields = document.querySelectorAll('input[type="email"], input[type="text"], input[name*="user"], input[name*="login"]');
    let passFields = document.querySelectorAll('input[type="password"]');

    if(userFields.length > 0) userFields[0].value = email;
    if(passFields.length > 0) passFields[0].value = password;
}