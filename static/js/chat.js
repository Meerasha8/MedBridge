(function () {
  const sessionId = window.MEDBRIDGE_SESSION_ID;
  const userId = window.MEDBRIDGE_USER_ID;
  const role = window.MEDBRIDGE_ROLE;

  const messagesEl = document.getElementById("messages");
  const inputEl = document.getElementById("msg-input");
  const sendBtn = document.getElementById("send-btn");

  let lat = null, lng = null;
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => { lat = pos.coords.latitude; lng = pos.coords.longitude; },
      () => {}
    );
  }

  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(
    `${protocol}//${location.host}/chat/ws?session_id=${sessionId}&user_id=${userId}&role=${role}`
  );

  let currentAiBubble = null;

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function appendUserBubble(text) {
    const div = document.createElement("div");
    div.className = "bg-primary text-white rounded-xl p-4 shadow-sm max-w-lg ml-auto";
    div.textContent = text;
    messagesEl.appendChild(div);
    scrollToBottom();
  }

  function appendSystemBubble(text, tone) {
    const div = document.createElement("div");
    const colorClass = tone === "amber"
      ? "bg-amber-50 border border-amber-200 text-amber-700"
      : "bg-red-50 border border-red-200 text-red-700";
    div.className = `${colorClass} rounded-xl p-3 text-sm max-w-lg`;
    div.textContent = text;
    messagesEl.appendChild(div);
    scrollToBottom();
  }

  function startAiBubble() {
    currentAiBubble = document.createElement("div");
    currentAiBubble.className = "bg-white border border-teal-100 rounded-xl p-4 shadow-sm max-w-lg whitespace-pre-wrap";
    currentAiBubble.textContent = "";
    messagesEl.appendChild(currentAiBubble);
    scrollToBottom();
  }

  let isTypingPlaceholder = false;

  function showTypingIndicator() {
    startAiBubble();
    currentAiBubble.innerHTML = '<span class="inline-flex gap-1"><span class="animate-bounce">●</span><span class="animate-bounce" style="animation-delay:0.1s">●</span><span class="animate-bounce" style="animation-delay:0.2s">●</span></span>';
    isTypingPlaceholder = true;
  }

  function removeTypingIndicator() {
    if (currentAiBubble && isTypingPlaceholder) {
      currentAiBubble.remove();
    }
    currentAiBubble = null;
    isTypingPlaceholder = false;
  }

  function renderDoctorCards(cards) {
    const wrap = document.createElement("div");
    wrap.className = "flex flex-wrap gap-3";
    cards.forEach((c) => {
      const initials = (c.name || "Dr").split(" ").map(w => w[0]).slice(0, 2).join("");
      const card = document.createElement("div");
      card.className = "bg-white border border-teal-200 rounded-xl p-4 shadow-sm max-w-sm my-2";
      card.innerHTML = `
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 rounded-full bg-teal-100 text-teal-700 font-bold flex items-center justify-center text-sm">${initials}</div>
          <div>
            <p class="font-semibold text-gray-800">${c.name}</p>
            <p class="text-sm text-teal-600">${c.specialization}</p>
          </div>
        </div>
        <p class="text-sm text-gray-500 mb-3">
          📍 ${c.distance_km} km away · ⭐ ${c.rating} · ₹${c.consultation_fee} consult
          <br>🗣 ${(c.languages_spoken || []).join(", ")}
        </p>
        <a href="/doctors/${c.doctor_id}/book" class="block text-center bg-primary text-white py-2 rounded-lg hover:bg-secondary transition text-sm font-medium">Book Appointment →</a>
      `;
      wrap.appendChild(card);
    });
    messagesEl.appendChild(wrap);
    scrollToBottom();
  }

  ws.addEventListener("open", () => {});

  ws.addEventListener("message", (event) => {
    let parsed = null;
    try {
      parsed = JSON.parse(event.data);
    } catch (e) {
      parsed = null;
    }

    if (parsed && typeof parsed === "object" && parsed.type) {
      if (parsed.type === "mcp_waking") {
        appendSystemBubble("Connecting to health services, please hold on a moment... ⏳", "amber");
      } else if (parsed.type === "doctor_cards") {
        renderDoctorCards(parsed.data || []);
      } else if (parsed.type === "error") {
        appendSystemBubble(parsed.message || "Something went wrong.", "red");
      } else if (parsed.type === "done") {
        removeTypingIndicator();
      }
      return;
    }

    // plain text token/chunk
    if (!currentAiBubble) startAiBubble();
    if (isTypingPlaceholder) {
      currentAiBubble.textContent = "";
      isTypingPlaceholder = false;
    }
    currentAiBubble.textContent += event.data;
    scrollToBottom();
  });

  function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;
    appendUserBubble(text);
    inputEl.value = "";
    showTypingIndicator();
    ws.send(JSON.stringify({ message: text, lat, lng }));
  }

  sendBtn.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });
})();
