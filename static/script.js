document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const fileUpload = document.getElementById('file-upload');
    const sendBtn = document.getElementById('send-btn');
    const chatList = document.getElementById('chat-list');
    const sidebar = document.querySelector('.sidebar');
    const askButton = document.querySelector('.ask-button');
    const chatArea = document.getElementById('chat-area');
    const branding = document.querySelector('.branding');
    const chatbox = document.querySelector('.chatbox');
    let chatHistory = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    let currentChatId = null;

    // History is open by default
    sidebar.classList.add('expanded');
    chatList.classList.remove('hidden');

    // Load chat history with nesting
    function renderChatHistory() {
        chatList.innerHTML = '';
        chatHistory.forEach((chat, index) => {
            const chatItem = document.createElement('div');
            chatItem.className = 'chat-item-nested';
            chatItem.textContent = `${chat.timestamp} - ${chat.title || `Chat ${index + 1}`}`;
            chatItem.onclick = () => loadChat(index);
            chatList.appendChild(chatItem);
        });
    }

    // Load a specific chat
    function loadChat(index) {
        currentChatId = index;
        chatArea.innerHTML = ''; // Clear previous content
        const chat = chatHistory[index];
        const userMessage = document.createElement('div');
        userMessage.textContent = chat.extracted_text || inputText;
        userMessage.className = 'chat-message user';
        chatArea.appendChild(userMessage);
        if (chat.grok_analysis) {
            const reply = document.createElement('div');
            reply.textContent = chat.grok_analysis;
            reply.className = 'chat-message reply';
            chatArea.appendChild(reply);
        }
        branding.style.display = 'none'; // Hide branding
        chatbox.classList.add('bottom'); // Move chatbox to bottom
    }

    // Create new chat
    askButton.addEventListener('click', () => {
        currentChatId = null;
        chatArea.innerHTML = '';
        branding.style.display = 'flex'; // Show branding for new chat
        chatbox.classList.remove('bottom'); // Reset chatbox position
        chatInput.value = '';
        fileUpload.value = '';
        chatInput.focus();
    });

    // Handle file upload click
    document.querySelector('.upload-icon').addEventListener('click', () => {
        fileUpload.click();
    });

    // Handle form submission
    sendBtn.addEventListener("click", async () => {
      sendBtn.disabled = true;

      const formData = new FormData();
      const inputText = chatInput.value.trim();
      const file = fileUpload.files[0];

      if (file) {
        formData.append("file", file);
      } else if (
        inputText &&
        (inputText.startsWith("http://") || inputText.startsWith("https://"))
      ) {
        formData.append("image_url", inputText);
      } else if (inputText) {
        formData.append("text", inputText);
      } else {
        sendBtn.disabled = false;
        return;
      }

      // Display user input
      const userMessage = document.createElement("div");
      userMessage.textContent = inputText;
      userMessage.className = "chat-message user";
      chatArea.appendChild(userMessage);
      branding.style.display = "none"; // Hide branding after input
      chatbox.classList.add("bottom"); // Move chatbox to bottom after query

      try {
        const response = await fetch(
          "https://veriguard.onrender.com/process",  // Backend on Render
          {
            method: "POST",
            body: formData,
          }
        );
        if (!response.ok) {
          throw new Error("Request failed");
        }
        const data = await response.json();

        const reply = document.createElement("div");
        reply.innerHTML = data.summary; // Render formatted summary with links
        reply.className = "chat-message reply";
        chatArea.appendChild(reply);

        const chat = {
          timestamp: new Date().toLocaleString("en-US", {
            hour12: true,
            hour: "2-digit",
            minute: "2-digit",
            timeZone: "Asia/Kolkata",
          }),
          title: `Chat ${chatHistory.length + 1}`,
          extracted_text: data.extracted_text || inputText,
          pubmed_results: data.sources.pubmed || [],
          fact_checks: data.sources.fact_checks || [],
          grok_analysis: "", // Removed as we're using summary
          chatgpt_analysis: "", // Removed
        };
        chatHistory.push(chat);
        localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
        renderChatHistory();
        loadChat(chatHistory.length - 1);
      } catch (error) {
        const reply = document.createElement("div");
        reply.textContent = `Error: ${error.message}`;
        reply.className = "chat-message reply";
        chatArea.appendChild(reply);
      } finally {
        sendBtn.disabled = false;
        chatInput.value = "";
        fileUpload.value = "";
      }
    });

    // Handle Enter key
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });

    // Register service worker for PWA
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/service-worker.js')
            .then(reg => console.log('Service Worker registered', reg))
            .catch(err => console.error('Service Worker registration failed', err));
    }

    // Initial render
    renderChatHistory();
    chatInput.focus();
});