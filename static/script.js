document.addEventListener("DOMContentLoaded", () => {
  const chatInput = document.getElementById("chat-input");
  const fileUpload = document.getElementById("file-upload");
  const sendBtn = document.getElementById("send-btn");
  const chatList = document.getElementById("chat-list");
  const sidebar = document.querySelector(".sidebar");
  const askButton = document.querySelector(".ask-button");
  const toggleHistoryBtn = document.querySelector(".toggle-history");
  const chatArea = document.getElementById("chat-area");
  const branding = document.querySelector(".branding");
  const chatbox = document.querySelector(".chatbox");

  // Use sessionStorage instead of localStorage to avoid browser restrictions
  let chatHistory = [];
  try {
    chatHistory = JSON.parse(sessionStorage.getItem("chatHistory") || "[]");
  } catch (e) {
    console.error("Failed to load chat history:", e);
    chatHistory = [];
  }

  let currentChatId = null;
  let isInConversation = false;

  // Create loading spinner
  const loadingSpinner = document.createElement("div");
  loadingSpinner.className = "loading-spinner";
  loadingSpinner.style.display = "none";
  loadingSpinner.innerHTML = `
    <svg class="spinner" viewBox="0 0 50 50">
      <circle class="path" cx="25" cy="25" r="20" fill="none" stroke="#93C5FD" stroke-width="5"></circle>
    </svg>
  `;

  // Initialize chat interface - centered layout
  function initializeChatInterface() {
    console.log("Initializing chat interface - centered mode");
    isInConversation = false;

    // Clear chat area and add spinner
    chatArea.innerHTML = "";
    chatArea.appendChild(loadingSpinner);

    // Show branding and center chatbox
    if (branding) branding.style.display = "flex";
    if (chatbox) {
      chatbox.style.display = "flex";
      chatbox.classList.remove("bottom");
      chatbox.style.position = "static";
      chatbox.style.transform = "none";
      chatbox.style.left = "auto";
      chatbox.style.bottom = "auto";
    }

    // Focus input
    if (chatInput) chatInput.focus();
  }

  // Switch to conversation mode - chatbox at bottom
  function enterConversationMode() {
    console.log("Entering conversation mode - chatbox at bottom");
    isInConversation = true;

    // Hide branding
    if (branding) branding.style.display = "none";

    // Add conversation mode class to main content
    const mainContent = document.querySelector(".main-content");
    if (mainContent) mainContent.classList.add("conversation-mode");

    // Move chatbox to bottom
    if (chatbox) {
      chatbox.classList.add("bottom");
    }
  }

  // Load chat history and render with date grouping
  function renderChatHistory() {
    console.log("Rendering chat history:", chatHistory);
    if (!chatList) return;

    chatList.innerHTML = "";

    if (chatHistory.length === 0) {
      const emptyMessage = document.createElement("div");
      emptyMessage.className = "chat-item-nested";
      emptyMessage.innerHTML = "No chat history";
      emptyMessage.style.color = "#6B7280";
      emptyMessage.style.fontStyle = "italic";
      chatList.appendChild(emptyMessage);
      return;
    }

    // Group chats by date
    const groupedChats = {};
    chatHistory.forEach((chat, index) => {
      const date = new Date(chat.created_at || Date.now()).toLocaleDateString(
        "en-US",
        {
          month: "short",
          day: "2-digit",
        }
      );
      if (!groupedChats[date]) {
        groupedChats[date] = [];
      }
      groupedChats[date].push({ ...chat, originalIndex: index });
    });

    // Render grouped chats
    Object.entries(groupedChats).forEach(([date, chats]) => {
      // Date header
      const dateHeader = document.createElement("div");
      dateHeader.style.color = "#9CA3AF";
      dateHeader.style.fontSize = "0.75rem";
      dateHeader.style.fontWeight = "bold";
      dateHeader.style.padding = "0.5rem 0.75rem";
      dateHeader.style.marginTop = "0.5rem";
      dateHeader.textContent = date;
      chatList.appendChild(dateHeader);

      // Chats for this date
      chats.forEach((chat) => {
        const chatItem = document.createElement("div");
        chatItem.className = "chat-item-nested";

        const chatTitle = document.createElement("span");
        chatTitle.textContent = chat.title || `Chat ${chat.originalIndex + 1}`;
        chatTitle.style.flex = "1";
        chatTitle.style.overflow = "hidden";
        chatTitle.style.textOverflow = "ellipsis";
        chatTitle.style.whiteSpace = "nowrap";

        const deleteIcon = document.createElement("span");
        deleteIcon.className = "delete-icon";
        deleteIcon.innerHTML = "&times;";
        deleteIcon.setAttribute("data-index", chat.originalIndex);
        deleteIcon.style.marginLeft = "0.5rem";
        deleteIcon.style.cursor = "pointer";
        deleteIcon.style.color = "#dc2626";
        deleteIcon.style.fontSize = "1.2rem";

        deleteIcon.addEventListener("mouseenter", () => {
          deleteIcon.style.color = "#ef4444";
        });
        deleteIcon.addEventListener("mouseleave", () => {
          deleteIcon.style.color = "#dc2626";
        });

        chatItem.appendChild(chatTitle);
        chatItem.appendChild(deleteIcon);

        chatTitle.addEventListener("click", () => loadChat(chat.originalIndex));
        deleteIcon.addEventListener("click", (e) => {
          e.stopPropagation();
          deleteChat(chat.originalIndex);
        });

        chatList.appendChild(chatItem);
      });
    });
  }

  // Delete chat function
  function deleteChat(index) {
    if (confirm("Are you sure you want to delete this chat?")) {
      chatHistory.splice(index, 1);
      try {
        sessionStorage.setItem("chatHistory", JSON.stringify(chatHistory));
      } catch (e) {
        console.error("Failed to save chat history:", e);
      }
      renderChatHistory();

      // If current chat was deleted, start new chat
      if (currentChatId === chatHistory[index]?.chat_id) {
        startNewChat();
      }
    }
  }

  // Generate better chat titles (like other AI assistants)
  function generateChatTitle(text) {
    if (!text || text.trim().length === 0) return "New Chat";

    const words = text.trim().split(" ");
    if (words.length <= 3) {
      return text.trim();
    }

    // Take first 3-4 meaningful words
    const meaningfulWords = words.filter(
      (word) =>
        word.length > 2 &&
        ![
          "the",
          "and",
          "but",
          "for",
          "are",
          "with",
          "can",
          "you",
          "have",
          "this",
          "that",
          "will",
          "from",
          "they",
          "been",
          "said",
          "each",
          "which",
          "what",
          "where",
          "when",
          "why",
          "how",
        ].includes(word.toLowerCase())
    );

    return meaningfulWords.slice(0, 4).join(" ");
  }

  // Load a specific chat with all messages
  function loadChat(index) {
    if (index < 0 || index >= chatHistory.length) {
      console.error("Invalid chat index:", index);
      return;
    }

    const chat = chatHistory[index];
    currentChatId = chat.chat_id;
    console.log("Loading chat:", currentChatId);

    // Enter conversation mode
    enterConversationMode();

    // Clear chat area
    chatArea.innerHTML = "";
    chatArea.appendChild(loadingSpinner);

    // Load all messages if available, otherwise use legacy format
    if (chat.messages && chat.messages.length > 0) {
      chat.messages.forEach((message) => {
        const messageContainer = document.createElement("div");
        messageContainer.style.marginBottom = "1rem";

        const messageLabel = document.createElement("div");
        messageLabel.textContent =
          message.type === "user" ? "You:" : "VeriGuard:";
        messageLabel.style.fontWeight = "bold";
        messageLabel.style.color = "#E5E7EB";
        messageLabel.style.marginBottom = "0.25rem";
        messageLabel.style.fontSize = "0.9rem";

        const messageContent = document.createElement("div");
        if (message.type === "assistant") {
          try {
            messageContent.innerHTML = marked.parse(message.content);
          } catch (e) {
            console.error("Markdown parsing error:", e);
            messageContent.textContent = message.content;
          }
          messageContent.className = "chat-message reply";
        } else {
          messageContent.textContent = message.content;
          messageContent.className = "chat-message user";
        }

        messageContainer.appendChild(messageLabel);
        messageContainer.appendChild(messageContent);
        chatArea.appendChild(messageContainer);
      });
    } else {
      // Legacy format - single message pair
      const userMessageContainer = document.createElement("div");
      userMessageContainer.style.marginBottom = "1rem";

      const userLabel = document.createElement("div");
      userLabel.textContent = "You:";
      userLabel.style.fontWeight = "bold";
      userLabel.style.color = "#E5E7EB";
      userLabel.style.marginBottom = "0.25rem";
      userLabel.style.fontSize = "0.9rem";

      const userMessage = document.createElement("div");
      userMessage.textContent = chat.extracted_text || "No query provided";
      userMessage.className = "chat-message user";

      userMessageContainer.appendChild(userLabel);
      userMessageContainer.appendChild(userMessage);
      chatArea.appendChild(userMessageContainer);

      if (chat.summary) {
        const replyContainer = document.createElement("div");
        replyContainer.style.marginBottom = "1rem";

        const replyLabel = document.createElement("div");
        replyLabel.textContent = "VeriGuard:";
        replyLabel.style.fontWeight = "bold";
        replyLabel.style.color = "#E5E7EB";
        replyLabel.style.marginBottom = "0.25rem";
        replyLabel.style.fontSize = "0.9rem";

        const reply = document.createElement("div");
        try {
          reply.innerHTML = marked.parse(chat.summary);
        } catch (e) {
          console.error("Markdown parsing error:", e);
          reply.textContent = chat.summary;
        }
        reply.className = "chat-message reply";

        replyContainer.appendChild(replyLabel);
        replyContainer.appendChild(reply);
        chatArea.appendChild(replyContainer);
      }
    }

    // Scroll to bottom
    chatArea.scrollTop = chatArea.scrollHeight;

    // Focus input
    if (chatInput) chatInput.focus();

    // Update URL
    updateURL(`/chat/${chat.chat_id}`);
  }

  // Handle URL routing
  function handleRouting() {
    const path = window.location.pathname;
    console.log("Handling route:", path);

    const match = path.match(/\/chat\/(.+)/);
    if (match) {
      const chatId = match[1];
      const index = chatHistory.findIndex((chat) => chat.chat_id === chatId);
      if (index !== -1) {
        loadChat(index);
        return;
      } else {
        console.log("Chat not found, redirecting to home");
        updateURL("/");
        startNewChat();
        return;
      }
    }

    // Default to new chat
    startNewChat();
  }

  // Update URL safely
  function updateURL(url) {
    try {
      if (window.history && window.history.pushState) {
        window.history.pushState({ chat_id: currentChatId }, "", url);
        console.log("URL updated to:", url);
      }
    } catch (e) {
      console.error("URL update error:", e);
    }
  }

  // Create new chat
  function startNewChat() {
    currentChatId = null;
    console.log("Starting new chat");

    // Initialize centered interface
    initializeChatInterface();

    // Remove conversation mode from main content
    const mainContent = document.querySelector(".main-content");
    if (mainContent) mainContent.classList.remove("conversation-mode");

    // Clear inputs
    if (chatInput) {
      chatInput.value = "";
      chatInput.focus();
    }
    if (fileUpload) fileUpload.value = "";

    // Reset URL
    updateURL("/");
  }

  // Handle file upload click
  if (document.querySelector(".upload-icon")) {
    document.querySelector(".upload-icon").addEventListener("click", () => {
      if (fileUpload) fileUpload.click();
    });
  }

  // Handle form submission
  if (sendBtn) {
    sendBtn.addEventListener("click", async () => {
      const inputText = chatInput ? chatInput.value.trim() : "";
      const file = fileUpload ? fileUpload.files[0] : null;

      if (!inputText && !file) {
        console.log("No input provided");
        return;
      }

      console.log("Submitting query:", inputText || "Image");

      // Enter conversation mode if not already
      if (!isInConversation) {
        enterConversationMode();
      }

      // Disable send button and hide chatbox
      sendBtn.disabled = true;
      if (chatbox) chatbox.style.display = "none";
      loadingSpinner.style.display = "block";

      const formData = new FormData();

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
        if (chatbox) chatbox.style.display = "flex";
        loadingSpinner.style.display = "none";
        return;
      }

      // Create user message with label
      const userMessageContainer = document.createElement("div");
      userMessageContainer.style.marginBottom = "1rem";

      const userLabel = document.createElement("div");
      userLabel.textContent = "You:";
      userLabel.style.fontWeight = "bold";
      userLabel.style.color = "#E5E7EB";
      userLabel.style.marginBottom = "0.25rem";
      userLabel.style.fontSize = "0.9rem";

      const userMessage = document.createElement("div");
      userMessage.textContent = inputText || "Image uploaded";
      userMessage.className = "chat-message user";

      userMessageContainer.appendChild(userLabel);
      userMessageContainer.appendChild(userMessage);
      chatArea.appendChild(userMessageContainer);

      // Scroll to bottom
      chatArea.scrollTop = chatArea.scrollHeight;

      // Set up timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        controller.abort();
        console.error("Request timeout after 30 seconds");
      }, 30000);

      try {
        console.log("Fetching from backend...");
        const response = await fetch("https://veriguard.onrender.com/process", {
          method: "POST",
          body: formData,
          signal: controller.signal,
          headers: {
            "Cache-Control": "no-cache",
          },
        });

        clearTimeout(timeoutId);
        console.log("Backend response status:", response.status);

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        console.log("Backend response data:", data);

        // Create reply message with label
        const replyContainer = document.createElement("div");
        replyContainer.style.marginBottom = "1rem";

        const replyLabel = document.createElement("div");
        replyLabel.textContent = "VeriGuard:";
        replyLabel.style.fontWeight = "bold";
        replyLabel.style.color = "#E5E7EB";
        replyLabel.style.marginBottom = "0.25rem";
        replyLabel.style.fontSize = "0.9rem";

        const reply = document.createElement("div");
        const summaryText = data.summary || "No summary provided by backend";

        try {
          reply.innerHTML = marked.parse(summaryText);
        } catch (e) {
          console.error("Markdown parsing error:", e);
          reply.textContent = summaryText;
        }

        reply.className = `chat-message reply ${data.summary ? "" : "error"}`;

        replyContainer.appendChild(replyLabel);
        replyContainer.appendChild(reply);
        chatArea.appendChild(replyContainer);
        chatArea.scrollTop = chatArea.scrollHeight;

        // Save or update chat in history
        let existingChatIndex = -1;
        if (currentChatId) {
          existingChatIndex = chatHistory.findIndex(
            (chat) => chat.chat_id === currentChatId
          );
        }

        const chatData = {
          chat_id:
            currentChatId ||
            data.chat_id ||
            `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          created_at:
            existingChatIndex >= 0
              ? chatHistory[existingChatIndex].created_at
              : Date.now(),
          updated_at: Date.now(),
          title:
            data.chat_title ||
            (existingChatIndex >= 0
              ? chatHistory[existingChatIndex].title
              : generateChatTitle(inputText)),
          messages:
            existingChatIndex >= 0
              ? [
                  ...chatHistory[existingChatIndex].messages,
                  {
                    type: "user",
                    content: inputText || "Image input",
                    timestamp: Date.now(),
                  },
                  {
                    type: "assistant",
                    content: data.summary,
                    timestamp: Date.now(),
                  },
                ]
              : [
                  {
                    type: "user",
                    content: inputText || "Image input",
                    timestamp: Date.now(),
                  },
                  {
                    type: "assistant",
                    content: data.summary,
                    timestamp: Date.now(),
                  },
                ],
          // Legacy fields for compatibility
          extracted_text: inputText || "Image input",
          summary: data.summary,
          pubmed_results: data.sources?.pubmed || [],
          fact_checks: data.sources?.fact_checks || [],
        };

        if (existingChatIndex >= 0) {
          // Update existing chat
          chatHistory[existingChatIndex] = chatData;
          // Move to front
          chatHistory.unshift(chatHistory.splice(existingChatIndex, 1)[0]);
        } else {
          // Add new chat to front
          chatHistory.unshift(chatData);
          currentChatId = chatData.chat_id;
        }

        try {
          sessionStorage.setItem("chatHistory", JSON.stringify(chatHistory));
        } catch (e) {
          console.error("Failed to save chat history:", e);
        }

        renderChatHistory();

        // Update URL with chat ID
        updateURL(`/chat/${chatData.chat_id}`);
      } catch (error) {
        console.error("Request error:", error);

        // Show error message
        const errorContainer = document.createElement("div");
        errorContainer.style.marginBottom = "1rem";

        const errorLabel = document.createElement("div");
        errorLabel.textContent = "Error:";
        errorLabel.style.fontWeight = "bold";
        errorLabel.style.color = "#dc2626";
        errorLabel.style.marginBottom = "0.25rem";
        errorLabel.style.fontSize = "0.9rem";

        const errorMessage = document.createElement("div");
        errorMessage.textContent = `Failed to get response: ${error.message}. Please try again.`;
        errorMessage.className = "chat-message reply error";

        errorContainer.appendChild(errorLabel);
        errorContainer.appendChild(errorMessage);
        chatArea.appendChild(errorContainer);
        chatArea.scrollTop = chatArea.scrollHeight;
      } finally {
        // Show chatbox at bottom and reset UI
        sendBtn.disabled = false;
        if (chatbox) {
          chatbox.style.display = "flex";
          if (isInConversation) {
            chatbox.classList.add("bottom");
          }
        }
        loadingSpinner.style.display = "none";

        // Clear inputs
        if (chatInput) {
          chatInput.value = "";
          chatInput.focus();
        }
        if (fileUpload) fileUpload.value = "";
      }
    });
  }

  // Handle Enter key
  if (chatInput) {
    chatInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (sendBtn) sendBtn.click();
      }
    });
  }

  // Ask button handler
  if (askButton) {
    askButton.addEventListener("click", startNewChat);
  }

  // Toggle history visibility
  if (toggleHistoryBtn) {
    toggleHistoryBtn.addEventListener("click", () => {
      if (sidebar) {
        sidebar.classList.toggle("expanded");
      }
      if (chatList) {
        chatList.classList.toggle("hidden");
      }
    });
  }

  // Handle browser back/forward
  window.addEventListener("popstate", (e) => {
    console.log("Popstate event:", e.state);
    handleRouting();
  });

  // Initialize on page load
  console.log("Initializing application...");
  renderChatHistory();
  handleRouting();

  // Ensure sidebar starts expanded
  if (sidebar) {
    sidebar.classList.add("expanded");
  }

  console.log("Application initialized successfully");
});
