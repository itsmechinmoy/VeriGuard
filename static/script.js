document.addEventListener("DOMContentLoaded", () => {
  const inputMethodRadios = document.querySelectorAll(
    'input[name="input-method"]'
  );
  const uploadInput = document.getElementById("upload-input");
  const urlInput = document.getElementById("url-input");
  const textInput = document.getElementById("text-input");
  const submitBtn = document.getElementById("submit-btn");
  const resultsDiv = document.getElementById("results");
  const errorDiv = document.getElementById("error");
  const textContent = document.getElementById("text-content");
  const pubmedList = document.getElementById("pubmed-list");
  const factCheckList = document.getElementById("fact-check-list");
  const grokContent = document.getElementById("grok-content");

  // Toggle input fields
  inputMethodRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      uploadInput.classList.add("hidden");
      urlInput.classList.add("hidden");
      textInput.classList.add("hidden");
      if (radio.value === "upload") uploadInput.classList.remove("hidden");
      if (radio.value === "url") urlInput.classList.remove("hidden");
      if (radio.value === "text") textInput.classList.remove("hidden");
    });
  });

  // Handle form submission
  submitBtn.addEventListener("click", async () => {
    resultsDiv.classList.add("hidden");
    errorDiv.classList.add("hidden");
    submitBtn.textContent = "Analyzing...";
    submitBtn.disabled = true;

    const formData = new FormData();
    const inputMethod = document.querySelector(
      'input[name="input-method"]:checked'
    ).value;
    const googleApiKey = document.getElementById("google-api-key").value;
    const xaiApiKey = document.getElementById("xai-api-key").value;

    if (inputMethod === "upload") {
      const fileInput = document.getElementById("image-file");
      if (fileInput.files[0]) formData.append("file", fileInput.files[0]);
    } else if (inputMethod === "url") {
      const imageUrl = document.getElementById("image-url").value;
      if (imageUrl) formData.append("image_url", imageUrl);
    } else if (inputMethod === "text") {
      const text = document.getElementById("text-area").value;
      if (text) formData.append("text", text);
    }

    try {
      const response = await fetch("/process", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Request failed");
      }
      const data = await response.json();

      // Display results
      textContent.textContent = data.extracted_text || "No text extracted";
      pubmedList.innerHTML = data.pubmed_results.length
        ? data.pubmed_results
            .map((r) => `<li>${r.title} by ${r.authors} (${r.pubdate})</li>`)
            .join("")
        : "<li>No PubMed articles found.</li>";
      factCheckList.innerHTML = data.fact_checks.length
        ? data.fact_checks
            .map(
              (c) =>
                `<li>Claim: ${c.text || "No text"}<ul>${
                  c.claimReview
                    ?.map(
                      (r) =>
                        `<li>Rating: ${r.textualRating || "N/A"} by ${
                          r.publisher?.name || "Unknown"
                        } (<a href="${r.url}" target="_blank">Link</a>)</li>`
                    )
                    .join("") || ""
                }</ul></li>`
            )
            .join("")
        : "<li>No fact checks found.</li>";
      grokContent.textContent =
        data.grok_analysis || "No Grok analysis available.";
      resultsDiv.classList.remove("hidden");
    } catch (error) {
      errorDiv.textContent = error.message;
      errorDiv.classList.remove("hidden");
    } finally {
      submitBtn.textContent = "Analyze";
      submitBtn.disabled = false;
    }
  });

  // Register service worker for PWA
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker
      .register("/static/service-worker.js")
      .then((reg) => console.log("Service Worker registered", reg))
      .catch((err) => console.error("Service Worker registration failed", err));
  }
});