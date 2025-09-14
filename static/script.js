document.addEventListener("DOMContentLoaded", () => {
  const chatInput = document.getElementById("chat-input");
  const fileUpload = document.getElementById("file-upload");
  const sendBtn = document.getElementById("send-btn");
  const chatList = document.getElementById("chat-list");
  const sidebar = document.querySelector(".sidebar");
  const askButton = document.querySelector(".ask-button");
  const chatArea = document.getElementById("chat-area");
  const branding = document.querySelector(".branding");
  const chatbox = document.querySelector(".chatbox");
  let chatHistory = JSON.parse(localStorage.getItem("chatHistory") || "[]");
  let currentChatId = null;

  // Create loading spinner
  const loadingSpinner = document.createElement("div");
  loadingSpinner.className = "loading-spinner";
  loadingSpinner.style.display = "none";
  loadingSpinner.innerHTML = `
    <svg class="spinner" viewBox="0 0 50 50">
      <circle class="path" cx="25" cy="25" r="20" fill="none" stroke="#93C5FD" stroke-width="5"></circle>
    </svg>
  `;
  chatArea.appendChild(loadingSpinner);

  // History is open by default
  sidebar.classList.add("expanded");
  chatList.classList.remove("hidden");

  // Load chat history
  function renderChatHistory() {
    chatList.innerHTML = "";
    chatHistory.forEach((chat, index) => {
      const chatItem = document.createElement("div");
      chatItem.className = "chat-item-nested";
      chatItem.textContent = `${chat.timestamp} - ${
        chat.title || `Chat ${index + 1}`
      }`;
      chatItem.onclick = () => loadChat(index);
      chatList.appendChild(chatItem);
    });
  }

  // Load a specific chat
  function loadChat(index) {
    currentChatId = index;
    chatArea.innerHTML = "";
    chatArea.appendChild(loadingSpinner);
    const chat = chatHistory[index];
    const userMessage = document.createElement("div");
    userMessage.textContent = chat.extracted_text;
    userMessage.className = "chat-message user";
    chatArea.appendChild(userMessage);
    if (chat.summary) {
      const reply = document.createElement("div");
      reply.innerHTML = chat.summary;
      reply.className = "chat-message reply";
      chatArea.appendChild(reply);
    }
    branding.style.display = "none";
    chatbox.style.display = "flex";
    chatbox.classList.add("bottom");
    chatArea.scrollTop = chatArea.scrollHeight;
    chatInput.focus();
  }

  // Create new chat
  askButton.addEventListener("click", () => {
    currentChatId = null;
    chatArea.innerHTML = "";
    chatArea.appendChild(loadingSpinner);
    branding.style.display = "flex";
    chatbox.style.display = "flex";
    chatbox.classList.remove("bottom");
    chatInput.value = "";
    fileUpload.value = "";
    chatInput.focus();
  });

  // Handle file upload click
  document.querySelector(".upload-icon").addEventListener("click", () => {
    fileUpload.click();
  });

  // Handle form submission
  sendBtn.addEventListener("click", async () => {
    if (!chatInput.value.trim() && !fileUpload.files[0]) return;

    sendBtn.disabled = true;
    chatbox.style.display = "none";
    loadingSpinner.style.display = "block";

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
      chatbox.style.display = "flex";
      loadingSpinner.style.display = "none";
      return;
    }

    const userMessage = document.createElement("div");
    userMessage.textContent = inputText;
    userMessage.className = "chat-message user";
    chatArea.appendChild(userMessage);
    branding.style.display = "none";
    chatArea.scrollTop = chatArea.scrollHeight;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
      console.error("Fetch aborted: Timeout after 10 seconds");
    }, 10000);

    try {
      const response = await fetch("https://veriguard.onrender.com/process", {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `HTTP error! status: ${response.status}, message: ${errorText}`
        );
      }

      const data = await response.json();
      console.log("Backend response:", data);

      const reply = document.createElement("div");
      reply.innerHTML = data.summary || "Error: No summary provided by backend";
      reply.className = "chat-message reply";
      chatArea.appendChild(reply);
      chatArea.scrollTop = chatArea.scrollHeight;

      const chat = {
        timestamp: new Date().toLocaleString("en-US", {
          hour12: true,
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "Asia/Kolkata",
        }),
        title: data.chat_title || `Chat ${chatHistory.length + 1}`,
        extracted_text: inputText,
        summary: data.summary,
        pubmed_results: data.sources.pubmed || [],
        fact_checks: data.sources.fact_checks || [],
      };
      chatHistory.push(chat);
      localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
      renderChatHistory();
      currentChatId = chatHistory.length - 1;
    } catch (error) {
      console.error("Fetch error:", error.name, error.message);
      const reply = document.createElement("div");
      reply.textContent = `Error: ${error.message}. Please try again or check your connection.`;
      reply.className = "chat-message reply error";
      chatArea.appendChild(reply);
      chatArea.scrollTop = chatArea.scrollHeight;
    } finally {
      sendBtn.disabled = false;
      chatbox.style.display = "flex";
      chatbox.classList.add("bottom");
      loadingSpinner.style.display = "none";
      chatInput.value = "";
      fileUpload.value = "";
      chatInput.focus();
    }
  });

  // Handle Enter key
  chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    }
  });

  // Register service worker for PWA
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker
      .register("service-worker.js")
      .then((reg) => console.log("Service Worker registered", reg))
      .catch((err) => console.error("Service Worker registration failed", err));
  }

  // Initial render
  renderChatHistory();
  chatInput.focus();
});
