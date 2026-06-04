/**
 * chat.js — Chat Widget Logic
 * Xử lý: Customer chat, Staff chat, AI Bot, AJAX polling, SSE Streaming
 * Giao diện Premium Overhaul: Midnight Slate & Amber Theme
 */
(function(){
  const isStaff = window.CHAT_IS_STAFF || false;
  const csrfToken = getCookie('csrftoken');

  // Custom SVG Avatar Code
  const botSvgAvatarHTML = `
  <svg class="bot-svg-avatar" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <rect x="6" y="8" width="20" height="16" rx="4" fill="url(#bot-grad)"/>
    <rect x="9" y="11" width="14" height="6" rx="2" fill="#0f172a"/>
    <circle class="eye left" cx="13" cy="14" r="2" fill="#06b6d4"/>
    <circle class="eye right" cx="19" cy="14" r="2" fill="#06b6d4"/>
    <rect x="13" y="20" width="6" height="2" rx="1" fill="#06b6d4"/>
    <line x1="16" y1="8" x2="16" y2="4" stroke="#818cf8" stroke-width="2"/>
    <circle cx="16" cy="3" r="1.5" fill="#06b6d4"/>
    <defs>
      <linearGradient id="bot-grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#818cf8" />
        <stop offset="100%" stop-color="#4f46e5" />
      </linearGradient>
    </defs>
  </svg>
  `;

  // Inject greeting avatar immediately
  const greetAv = document.getElementById('greeting-avatar-svg');
  if (greetAv) {
    greetAv.innerHTML = botSvgAvatarHTML;
    greetAv.classList.add('bot-svg-greeting');
  }

  // ── State ──
  let panelOpen    = false;
  let lastMsgId    = 0;
  let pollTimer    = null;
  let autoReplied  = false;
  let currentSid   = null;
  let staffLastId  = 0;
  let staffPollT   = null;
  let sessionPollT = null;

  // Timestamps for date separator and grouping
  let botLastTimestamp = null;
  let custLastTimestamp = null;

  // Image Selection State
  let custSelectedImageFile = null;
  let staffSelectedImageFile = null;

  // ── Elements ──
  const panel      = document.getElementById('chat-panel');
  const badge      = document.getElementById('chat-notif-badge');
  const bubbleIcon = document.getElementById('chat-bubble-icon');
  const backBtn    = document.getElementById('cp-back-btn');
  const headerTitle= document.getElementById('cp-header-title');
  const headerSub  = document.getElementById('cp-header-sub');
  const headerCont = document.getElementById('cp-header-container');
  const tooltip    = document.getElementById('chat-tooltip');
  const bubbleBtn  = document.getElementById('chat-bubble-btn');

  // ── Tooltip Logic ──
  let tooltipTimeout = null;
  
  function showTooltip() {
    if (panelOpen) return;
    if (tooltip) {
      tooltip.classList.add('show');
      clearTimeout(tooltipTimeout);
      tooltipTimeout = setTimeout(hideTooltip, 4000);
    }
  }

  function hideTooltip() {
    if (tooltip) tooltip.classList.remove('show');
  }

  setTimeout(showTooltip, 3500);

  if (bubbleBtn) {
    bubbleBtn.addEventListener('mouseenter', showTooltip);
    bubbleBtn.addEventListener('mouseleave', hideTooltip);
  }

  // ── Helper: Set Active View (Class-based display) ──
  function setActiveView(activeId) {
    const views = ['cp-view-mode', 'cp-view-bot', 'cp-view-chat', 'cp-view-list'];
    views.forEach(v => {
      const el = document.getElementById(v);
      if (el) {
        if (v === activeId) {
          el.classList.add('active');
        } else {
          el.classList.remove('active');
        }
      }
    });
  }

  // ── Toggle panel ──
  window.chatToggle = function(){
    panelOpen = !panelOpen;
    panel.classList.toggle('open', panelOpen);
    hideTooltip();
    bubbleIcon.className = panelOpen
      ? 'fas fa-times'
      : (isStaff ? 'fas fa-headset' : 'fas fa-comments');

    if(panelOpen){
      badge.classList.remove('show');
      if(isStaff){ loadSessionList(); startSessionPoll(); }
      else {
        if(!custMode){
          showModeSelection();
        } else if(custMode === 'staff'){
          loadCustHistory();
        }
      }
    } else {
      stopAllPolls();
      if(isStaff && currentSid){ staffBackToList(); }
    }
  };

  // ── Customer mode state ──
  let custMode = null; // null | 'bot' | 'staff'

  function showModeSelection(){
    headerTitle.textContent = 'DDC Books – Hỗ trợ';
    headerSub.textContent   = 'Chọn kênh hỗ trợ';
    if(headerCont) headerCont.classList.remove('bot-theme');
    
    const headerIcon = document.getElementById('cp-header-icon');
    if (headerIcon) headerIcon.innerHTML = `<i class="fas fa-comments"></i>`;

    backBtn.classList.remove('show');
    setActiveView('cp-view-mode');
  }

  window.custChooseMode = function(mode){
    custMode = mode;
    if(mode === 'bot'){
      headerTitle.textContent = 'DDC Books AI Bot';
      headerSub.textContent   = '✨ Trả lời ngay lập tức';
      if(headerCont) headerCont.classList.add('bot-theme');
      
      const headerIcon = document.getElementById('cp-header-icon');
      if (headerIcon) headerIcon.innerHTML = botSvgAvatarHTML;

      backBtn.classList.add('show');
      backBtn.onclick = function(){ custMode = null; showModeSelection(); };
      setActiveView('cp-view-bot');
      initBot();
    } else {
      headerTitle.textContent = 'DDC Books – Hỗ trợ';
      headerSub.textContent   = 'Nhân viên trực tuyến';
      if(headerCont) headerCont.classList.remove('bot-theme');
      
      const headerIcon = document.getElementById('cp-header-icon');
      if (headerIcon) headerIcon.innerHTML = `<i class="fas fa-headset"></i>`;

      backBtn.classList.add('show');
      backBtn.onclick = function(){ custMode = null; stopAllPolls(); showModeSelection(); };
      setActiveView('cp-view-chat');
      if (window.CHAT_IS_AUTHENTICATED) {
        loadCustHistory();
      }
    }
  };

  // ════════════════════════════════════════
  //  HTML-Aware Typewriter Effect (Neon Fast)
  // ════════════════════════════════════════
  function typeWriter(element, htmlContent, onComplete) {
    element.innerHTML = '';
    element.classList.add('typing-cursor');
    let index = 0;
    let currentHTML = '';
    
    function step() {
      if (index >= htmlContent.length) {
        element.classList.remove('typing-cursor');
        if (onComplete) onComplete();
        return;
      }
      
      if (htmlContent[index] === '<') {
        let tagEnd = htmlContent.indexOf('>', index);
        if (tagEnd !== -1) {
          currentHTML += htmlContent.substring(index, tagEnd + 1);
          index = tagEnd + 1;
          element.innerHTML = currentHTML;
          
          const container = element.closest('#cp-bot-messages, #cp-messages');
          if (container) container.scrollTop = container.scrollHeight;
          
          setTimeout(step, 8);
          return;
        }
      }
      
      currentHTML += htmlContent[index];
      element.innerHTML = currentHTML;
      index++;
      
      const container = element.closest('#cp-bot-messages, #cp-messages');
      if (container) container.scrollTop = container.scrollHeight;
      
      setTimeout(step, 5);
    }
    
    step();
  }

  // ════════════════════════════════════════
  //  BOT logic
  // ════════════════════════════════════════
  let botInited = false;
  let botTypingEl = null;

  function formatCurrency(v) {
    return new Intl.NumberFormat('vi-VN').format(v);
  }

  function initBot(){
    if(botInited) return;
    botInited = true;
    const el = document.getElementById('cp-bot-messages');
    el.innerHTML = '<div style="text-align:center;padding:20px;color:#94a3b8;font-size:0.8rem;"><i class="fas fa-spinner fa-spin"></i> Đang tải hội thoại...</div>';
    
    fetch('/chat/bot/history/')
      .then(r => r.json())
      .then(d => {
        el.innerHTML = '';
        if (d.messages && d.messages.length > 0) {
          d.messages.forEach(m => {
            appendBotMsgHtml(
              m.role === 'user' ? 'me' : 'other',
              m.content,
              false,
              m.id,
              m.rating,
              m.books,
              m.orders
            );
          });
        } else {
          appendBotMsgHtml('other', 'Xin chào! Mình là DDC Books AI Bot 🤖\nMình có thể hỗ trợ bạn:\n\n&bull; 📚 <strong>Gợi ý & tư vấn sách</strong> theo sở thích cá nhân\n&bull; 📦 <strong>Tra cứu tình trạng đơn hàng</strong> nhanh chóng\n&bull; 🚚 <strong>Thông tin vận chuyển & đổi trả</strong> sản phẩm\n\nBạn muốn tìm hiểu thông tin gì hôm nay? 😊', true);
        }
        scrollBotBottom();
      })
      .catch(() => {
        el.innerHTML = '';
        appendBotMsgHtml('other', 'Xin chào! Mình là DDC Books AI Bot 🤖\nMình có thể hỗ trợ bạn:\n\n&bull; 📚 <strong>Gợi ý & tư vấn sách</strong> theo sở thích cá nhân\n&bull; 📦 <strong>Tra cứu tình trạng đơn hàng</strong> nhanh chóng\n&bull; 🚚 <strong>Thông tin vận chuyển & đổi trả</strong> sản phẩm\n\nBạn muốn tìm hiểu thông tin gì hôm nay? 😊', true);
      });
  }

  window.botChip = function(text){
    appendBotMsg('me', text);
    processBotInput(text);
  };

  window.botSend = function(){
    const inp = document.getElementById('cp-bot-input');
    const txt = inp.value.trim();
    if(!txt) return;
    appendBotMsg('me', txt);
    inp.value = '';
    processBotInput(txt);
  };

  function processBotInput(text){
    showBotTyping(true);
    const lower = text.toLowerCase();

    // ── Rule-based fast responses ──
    let quickReply = null;

    if(/(địa chỉ|cửa hàng|ở đâu|chỗ nào)/i.test(lower)){
      quickReply = '📍 <strong>DDC Books tọa lạc tại:</strong>\n📌 Số 9 Nguyễn Trãi, Hà Đông, Hà Nội\n⏰ Giờ mở cửa: 08:00 – 22:00 (Hàng ngày)\n📞 Hotline: 094.152.7660';
    } else if(/(đổi trả|hoàn hàng|trả hàng|chính sách|bảo hành)/i.test(lower)){
      quickReply = '↩️ <strong>Chính sách đổi trả DDC Books:</strong>\n&bull; Đổi trả trong vòng 7 ngày kể từ ngày nhận hàng\n&bull; Sản phẩm còn nguyên seal, chưa qua sử dụng\n&bull; Lỗi do nhà sản xuất: đổi mới 100%\n&bull; Liên hệ: support@ddcbooks.com hoặc Hotline 094.152.7660';
    } else if(/(vận chuyển|giao hàng|ship|phí ship|thời gian giao)/i.test(lower)){
      quickReply = '🚚 <strong>Thông tin vận chuyển:</strong>\n&bull; Nội thành Hà Nội: 1–2 ngày (miễn phí từ 250.000đ)\n&bull; Toàn quốc: 3–5 ngày làm việc\n&bull; Phí ship: 25.000đ – 40.000đ tùy khu vực\n&bull; Có thể theo dõi đơn qua mã vận đơn';
    } else if(/(wishlist|yêu thích|sách yêu thích)/i.test(lower)){
      if (!window.CHAT_IS_AUTHENTICATED) {
        quickReply = '🔒 Bạn vui lòng đăng nhập để lưu và xem danh sách sách yêu thích nhé!';
      } else {
        quickReply = '❤️ <strong>Danh sách yêu thích của bạn:</strong>\n\nBạn có thể xem danh sách sách yêu thích tại:\n👉 <a href="/wishlist/" style="color:#06b6d4;font-weight:600;text-decoration:underline;">Xem Wishlist của tôi</a>\n\nMình sẽ thông báo ngay khi sách trong wishlist được giảm giá! 🔔';
      }
    } else if(/(giỏ hàng|cart|chưa thanh toán|bỏ quên)/i.test(lower)){
      quickReply = '🛒 <strong>Xem và thanh toán giỏ hàng của bạn tại đây:</strong>\n\n👉 <a href="/cart/" style="color:#06b6d4;font-weight:600;text-decoration:underline;">Xem giỏ hàng ngay</a>\n\nNhiều sách đang giảm giá, hoàn tất đơn hàng sớm nha! 😉';
    } else if(/(coupon|giảm giá|mã giảm|khuyến mãi|uu dai|ưu đãi)/i.test(lower)){
      quickReply = '🎟️ <strong>Mã giảm giá đang hoạt động tại DDC Books:</strong>\n\n&bull; <strong>SAVE10</strong>: Giảm ngay 10% trên tổng giá trị đơn hàng.\n\n👉 <em>Hãy lưu lại mã này và nhập ở trang thanh toán khi mua sách nhé!</em>';
    }

    setTimeout(()=>{
      showBotTyping(false);
      if(quickReply){
        appendBotMsgHtml('other', quickReply, true);
      } else {
        callClaudeBot(text);
        return;
      }
    }, 500);
  }

  function hideSuggestionsAndFeedback() {
    const prevChips = document.querySelectorAll('.msg-suggestions');
    prevChips.forEach(c => c.remove());
  }

  async function callClaudeBot(userText){
    hideSuggestionsAndFeedback();
    showBotTyping(true);

    try {
      const res = await fetch('/chat/bot/stream/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ message: userText })
      });

      if (!res.ok) {
        showBotTyping(false);
        let errMsg = 'Xin lỗi, máy chủ AI đang bận. Bạn thử lại nhé! 🙏';
        try {
          const errData = await res.json();
          if (errData.error) {
            errMsg = `Lỗi: ${errData.error}`;
          }
        } catch (err) {}
        appendBotMsgHtml('other', errMsg, true);
        return;
      }

      showBotTyping(false);

      const bubEl = createBotMsgBubbleEmpty();
      let accumText = "";

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;

          try {
            const data = JSON.parse(trimmed.slice(5).trim());
            if (data.error) {
              bubEl.textContent = "Lỗi: " + data.error;
              bubEl.classList.remove('typing-cursor');
              scrollBotBottom();
            } else if (data.chunk) {
              accumText += data.chunk;
              let cleanStream = accumText
                .replace(/\[SUGGESTIONS:[\s\S]*?\]/g, "")
                .replace(/\[SET_PRICE_ALERT:[\s\S]*?\]/g, "")
                .replace(/\[TRACK_GUEST_ORDER:[\s\S]*?\]/g, "");
              bubEl.innerHTML = cleanStream;
              scrollBotBottom();
            } else if (data.metadata) {
              bubEl.classList.remove('typing-cursor');
              const meta = data.metadata;
              
              let finalClean = accumText
                .replace(/\[SUGGESTIONS:[\s\S]*?\]/g, "")
                .replace(/\[SET_PRICE_ALERT:[\s\S]*?\]/g, "")
                .replace(/\[TRACK_GUEST_ORDER:[\s\S]*?\]/g, "");
              bubEl.innerHTML = finalClean;

              if (meta.alert_created) {
                const alertNote = document.createElement('div');
                alertNote.className = 'chat-order-tracking';
                alertNote.style.marginTop = '8px';
                alertNote.style.borderColor = '#f39c12';
                alertNote.style.color = '#f39c12';
                alertNote.innerHTML = `<i class="fas fa-bell"></i> <strong>Đã lưu nhắc nhở giá!</strong> Hệ thống sẽ báo khi sách <strong>${escHtml(meta.alert_book_title)}</strong> xuống mức giá mục tiêu.`;
                bubEl.appendChild(alertNote);
              }

              if (meta.books && meta.books.length > 0) {
                renderBookCards(bubEl, meta.books);
                const cats = [];
                meta.books.forEach(b => {
                  if (b.category && b.category.trim()) {
                    const catTrimmed = b.category.trim();
                    if (!cats.includes(catTrimmed)) {
                      cats.push(catTrimmed);
                    }
                  }
                });
                if (cats.length > 0) {
                  const suggestions = cats.map(c => `Tìm sách cùng chủ đề ${c}`);
                  renderSuggestionChips(bubEl.parentElement.parentElement, suggestions);
                } else {
                  hideSuggestionsAndFeedback();
                }
              } else {
                hideSuggestionsAndFeedback();
              }

              if (meta.orders && meta.orders.length > 0) {
                renderOrderCards(bubEl, meta.orders);
              }

              if (meta.message_id) {
                renderFeedbackButtons(bubEl.parentElement, meta.message_id, 0);
              }

              scrollBotBottom();
            }
          } catch (e) {
            console.error("Stream parse error", e);
          }
        }
      }
    } catch (e) {
      showBotTyping(false);
      appendBotMsgHtml('other', 'Mất kết nối với máy chủ AI. Vui lòng thử lại sau! 🙏', true);
    }
  }

  function createBotMsgBubbleEmpty() {
    const el = document.getElementById('cp-bot-messages');
    if(!el) return null;

    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2,'0')+':'+now.getMinutes().toString().padStart(2,'0');

    const row = document.createElement('div');
    row.className = 'msg-row';
    
    const av = document.createElement('div');
    av.className = 'msg-av';
    av.innerHTML = botSvgAvatarHTML;
    row.appendChild(av);
    
    const wrap = document.createElement('div');
    wrap.className = 'msg-bubble-wrap';
    
    const bub = document.createElement('div');
    bub.className = 'msg-bubble other typing-cursor';
    bub.style.whiteSpace = 'pre-line';
    
    const t = document.createElement('div');
    t.className = 'msg-time'; t.textContent = timeStr;
    
    wrap.appendChild(bub); wrap.appendChild(t);
    row.appendChild(wrap);
    el.appendChild(row);
    
    scrollBotBottom();
    return bub;
  }

  function insertAfter(newElement, targetElement) {
    const parent = targetElement.parentNode;
    if (parent.lastChild === targetElement) {
      parent.appendChild(newElement);
    } else {
      parent.insertBefore(newElement, targetElement.nextSibling);
    }
  }

  function renderBookCards(container, books) {
    const scrollDiv = document.createElement('div');
    scrollDiv.className = 'chat-books-scroll';
    
    books.forEach(b => {
      const card = document.createElement('div');
      card.className = 'chat-book-card';
      
      const img = document.createElement('img');
      img.src = b.image_url;
      img.alt = b.title;
      
      const title = document.createElement('div');
      title.className = 'chat-book-title';
      title.textContent = b.title;
      
      const author = document.createElement('div');
      author.className = 'chat-book-author';
      author.textContent = b.author;
      
      const price = document.createElement('div');
      price.className = 'chat-book-price';
      price.textContent = formatCurrency(b.price) + 'đ';
      
      const btn = document.createElement('button');
      btn.className = 'chat-book-btn-cart';
      btn.innerHTML = '<i class="fas fa-shopping-cart"></i> Mua ngay';
      btn.onclick = (e) => {
        e.stopPropagation();
        addBookToCartInline(b.id, btn);
      };
      
      card.appendChild(img);
      card.appendChild(title);
      card.appendChild(author);
      card.appendChild(price);
      card.appendChild(btn);
      
      scrollDiv.appendChild(card);
    });
    
    insertAfter(scrollDiv, container);
  }

  function addBookToCartInline(bookId, buttonEl) {
    const originalHTML = buttonEl.innerHTML;
    buttonEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>...';
    buttonEl.disabled = true;
    
    const formData = new FormData();
    formData.append('quantity', 1);
    
    fetch(`/add-to-cart/${bookId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      body: formData
    })
    .then(res => {
      if (res.ok) {
        buttonEl.innerHTML = '<i class="fas fa-check"></i> Đã thêm';
        buttonEl.style.background = '#2ecc71';
        
        const countBadge = document.getElementById('cart-count');
        if (countBadge) {
          let current = parseInt(countBadge.textContent) || 0;
          countBadge.textContent = current + 1;
        }
        
        setTimeout(() => {
          buttonEl.innerHTML = originalHTML;
          buttonEl.style.background = '';
          buttonEl.disabled = false;
        }, 2500);
      } else {
        buttonEl.innerHTML = '<i class="fas fa-times"></i> Hết hàng';
        buttonEl.style.background = '#e74c3c';
        setTimeout(() => {
          buttonEl.innerHTML = originalHTML;
          buttonEl.style.background = '';
          buttonEl.disabled = false;
        }, 2500);
      }
    })
    .catch(() => {
      buttonEl.innerHTML = originalHTML;
      buttonEl.disabled = false;
    });
  }

  function renderOrderCards(container, orders) {
    orders.forEach(o => {
      const card = document.createElement('div');
      card.className = 'chat-order-card';
      
      const header = document.createElement('div');
      header.className = 'chat-order-header';
      
      const title = document.createElement('div');
      title.className = 'chat-order-title';
      title.innerHTML = `<i class="fas fa-box"></i> Đơn hàng #${o.id}`;
      
      const badge = document.createElement('span');
      badge.className = 'chat-order-badge ' + o.status.toLowerCase();
      badge.textContent = o.status_display;
      
      header.appendChild(title);
      header.appendChild(badge);
      
      const grid = document.createElement('div');
      grid.className = 'chat-order-grid';
      grid.innerHTML = `
        <div class="chat-order-item">Tổng tiền: <strong>${formatCurrency(o.total_price)}đ</strong></div>
        <div class="chat-order-item">Ngày đặt: <strong>${o.created_at}</strong></div>
        <div class="chat-order-item" style="grid-column: span 2">Vận chuyển: <strong>${escHtml(o.shipping_unit)}</strong></div>
      `;
      
      const tracking = document.createElement('div');
      tracking.className = 'chat-order-tracking';
      tracking.innerHTML = `<i class="fas fa-truck-moving"></i> ${escHtml(o.last_tracking)}`;
      
      card.appendChild(header);
      card.appendChild(grid);
      card.appendChild(tracking);
      
      insertAfter(card, container);
    });
  }

  function renderFeedbackButtons(wrapContainer, messageId, currentRating) {
    if (wrapContainer.querySelector('.msg-feedback')) return;
    
    const fbDiv = document.createElement('div');
    fbDiv.className = 'msg-feedback';
    
    const btnLike = document.createElement('button');
    btnLike.className = 'btn-feedback';
    btnLike.innerHTML = '<i class="far fa-thumbs-up"></i>';
    btnLike.title = 'Hữu ích';
    if (currentRating === 1) btnLike.classList.add('active-like');
    
    const btnDislike = document.createElement('button');
    btnDislike.className = 'btn-feedback';
    btnDislike.innerHTML = '<i class="far fa-thumbs-down"></i>';
    btnDislike.title = 'Chưa hữu ích';
    if (currentRating === -1) btnDislike.classList.add('active-dislike');
    
    btnLike.onclick = () => submitFeedback(messageId, 1, btnLike, btnDislike);
    btnDislike.onclick = () => submitFeedback(messageId, -1, btnLike, btnDislike);
    
    fbDiv.appendChild(btnLike);
    fbDiv.appendChild(btnDislike);
    wrapContainer.appendChild(fbDiv);
  }

  function submitFeedback(messageId, rating, btnLike, btnDislike) {
    let newRating = rating;
    if (rating === 1 && btnLike.classList.contains('active-like')) {
      newRating = 0;
    } else if (rating === -1 && btnDislike.classList.contains('active-dislike')) {
      newRating = 0;
    }
    
    fetch('/chat/bot/feedback/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ message_id: messageId, rating: newRating })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        btnLike.classList.remove('active-like');
        btnDislike.classList.remove('active-dislike');
        if (newRating === 1) {
          btnLike.classList.add('active-like');
        } else if (newRating === -1) {
          btnDislike.classList.add('active-dislike');
        }
      }
    });
  }

  function renderSuggestionChips(messageRow, suggestions) {
    const prevChips = document.querySelectorAll('.msg-suggestions');
    prevChips.forEach(c => c.remove());
    
    const div = document.createElement('div');
    div.className = 'msg-suggestions';
    
    suggestions.forEach(s => {
      const chip = document.createElement('button');
      chip.className = 'msg-suggestion-chip';
      chip.textContent = s;
      chip.onclick = () => {
        appendBotMsg('me', s);
        processBotInput(s);
        div.remove();
      };
      div.appendChild(chip);
    });
    
    messageRow.parentNode.insertBefore(div, messageRow.nextSibling);
    scrollBotBottom();
  }

  // Ghi âm bằng Web Speech API
  let recognition = null;
  let isRecording = false;

  window.toggleVoiceInput = function() {
    const micBtn = document.getElementById('cp-bot-mic');
    const inputEl = document.getElementById('cp-bot-input');
    if (!micBtn || !inputEl) return;
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Trình duyệt của bạn không hỗ trợ Speech Recognition! Hãy dùng Google Chrome hoặc Microsoft Edge.");
      return;
    }
    
    if (isRecording) {
      recognition.stop();
      return;
    }
    
    if (!recognition) {
      recognition = new SpeechRecognition();
      recognition.lang = 'vi-VN';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      
      recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add('recording');
        inputEl.placeholder = 'Đang lắng nghe... Hãy nói đi';
      };
      
      recognition.onend = () => {
        isRecording = false;
        micBtn.classList.remove('recording');
        inputEl.placeholder = 'Hỏi gì cũng được...';
      };
      
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          inputEl.value = transcript;
          setTimeout(botSend, 500);
        }
      };
      
      recognition.onerror = (event) => {
        console.error("Lỗi Speech Recognition:", event.error);
        isRecording = false;
        micBtn.classList.remove('recording');
        inputEl.placeholder = 'Hỏi gì cũng được...';
      };
    }
    
    recognition.start();
  };

  function appendBotMsg(type, text) {
    appendBotMsgHtml(type, escHtml(text), false);
  }

  function appendBotMsgHtml(type, html, isTypewriter = false, msgId = null, rating = 0, books = null, orders = null){
    const el = document.getElementById('cp-bot-messages');
    if(!el) return;

    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2,'0')+':'+now.getMinutes().toString().padStart(2,'0');

    if(botLastTimestamp && (now - botLastTimestamp > 5 * 60 * 1000)) {
      const sep = document.createElement('div');
      sep.className = 'chat-date-separator';
      sep.textContent = timeStr;
      el.appendChild(sep);
    }
    botLastTimestamp = now;

    const lastRow = el.lastElementChild;
    const isSameSender = lastRow && lastRow.classList.contains('msg-row') && 
                         !lastRow.classList.contains('system') &&
                         ((type === 'me' && lastRow.classList.contains('me')) || 
                           (type !== 'me' && !lastRow.classList.contains('me')));

    const row = document.createElement('div');
    row.className = 'msg-row' + (type==='me'?' me':'') + (isSameSender ? ' no-avatar' : '');
    
    if(type !== 'me'){
      const av = document.createElement('div');
      av.className = 'msg-av';
      av.innerHTML = botSvgAvatarHTML;
      row.appendChild(av);
    }
    
    const wrap = document.createElement('div');
    wrap.className = 'msg-bubble-wrap';
    const bub = document.createElement('div');
    bub.className = 'msg-bubble ' + type;
    bub.style.whiteSpace = 'pre-line';
    
    const t = document.createElement('div');
    t.className = 'msg-time'; t.textContent = timeStr;
    
    wrap.appendChild(bub); wrap.appendChild(t);
    row.appendChild(wrap);
    el.appendChild(row);

    if (type === 'other') {
      if (isTypewriter) {
        typeWriter(bub, html, () => {
          scrollBotBottom();
        });
      } else {
        let cleanHtml = html
          .replace(/\[SUGGESTIONS:[\s\S]*?\]/g, "")
          .replace(/\[SET_PRICE_ALERT:[\s\S]*?\]/g, "")
          .replace(/\[TRACK_GUEST_ORDER:[\s\S]*?\]/g, "");
        bub.innerHTML = cleanHtml;
        
        if (books && books.length > 0) {
          renderBookCards(bub, books);
        }
        if (orders && orders.length > 0) {
          renderOrderCards(bub, orders);
        }
        if (msgId) {
          renderFeedbackButtons(wrap, msgId, rating);
        }
        scrollBotBottom();
      }
    } else {
      bub.innerHTML = html;
      scrollBotBottom();
    }
  }

  function showBotTyping(show){
    const el = document.getElementById('cp-bot-messages');
    if(show && !botTypingEl){
      botTypingEl = document.createElement('div');
      botTypingEl.className = 'msg-row';
      botTypingEl.innerHTML = `<div class="msg-av">${botSvgAvatarHTML}</div><div class="typing-dots"><span></span><span></span><span></span></div>`;
      el.appendChild(botTypingEl); scrollBotBottom();
    } else if(!show && botTypingEl){ botTypingEl.remove(); botTypingEl = null; }
  }

  function scrollBotBottom(){ setTimeout(()=>{ const e=document.getElementById('cp-bot-messages'); if(e) e.scrollTo({top: e.scrollHeight, behavior: 'smooth'}); },30); }

  // ════════════════════════════════════════
  //  CUSTOMER (Staff chat) logic
  // ════════════════════════════════════════
  function loadCustHistory(){
    const msgsEl = document.getElementById('cp-messages');
    msgsEl.innerHTML = '<div style="text-align:center;padding:20px;color:#bdc3c7;font-size:0.8rem;">Đang tải...</div>';

    fetch('/chat/customer/poll/?after=0&history=1')
      .then(r=>r.json())
      .then(d=>{
        msgsEl.innerHTML = '';
        if(d.messages.length === 0){
          msgsEl.innerHTML = `
            <div class="msg-row">
              <div class="msg-av"><i class="fas fa-headset" style="font-size:0.75rem;"></i></div>
              <div class="msg-bubble-wrap">
                <div class="msg-bubble other">Xin chào bạn! Bạn cần giúp gì? 😊</div>
                <div class="msg-time">DDC Books</div>
              </div>
            </div>`;
        } else {
          d.messages.forEach(m => {
            if(m.id > lastMsgId) lastMsgId = m.id;
            appendMsgWithTime(m.content, m.is_mine ? 'me' : 'other', m.created_at, m.image_url);
          });
          autoReplied = true;
        }
        scrollBottom('cp-messages');
        startCustPoll();
      })
      .catch(()=>{
        msgsEl.innerHTML = '';
        startCustPoll();
      });
  }

  window.custSend = function(){
    const inp = document.getElementById('cp-cust-input');
    const txt = inp.value.trim();
    const imageFile = custSelectedImageFile;
    if(!txt && !imageFile) return;

    if (imageFile) {
      const localUrl = URL.createObjectURL(imageFile);
      appendMsgWithTime(txt, 'me', null, localUrl);
    } else {
      appendMsg(txt, 'me');
    }

    inp.value = '';
    removeCustPreview();
    scrollBottom('cp-messages');

    let bodyData;
    let headersData = {'X-CSRFToken':csrfToken};
    if (imageFile) {
      bodyData = new FormData();
      bodyData.append('content', txt);
      bodyData.append('image', imageFile);
    } else {
      bodyData = JSON.stringify({content: txt});
      headersData['Content-Type'] = 'application/json';
    }

    fetch('/chat/customer/send/', {
      method:'POST',
      headers: headersData,
      body: bodyData
    })
    .then(r=>r.json())
    .then(d=>{ if(d.id) lastMsgId = Math.max(lastMsgId, d.id); });

    if(!autoReplied){
      autoReplied = true;
      showTyping(true);
      setTimeout(()=>{
        showTyping(false);
        appendSystem('✅ Yêu cầu đã được ghi nhận. Nhân viên sẽ hỗ trợ bạn sớm nhất!');
        scrollBottom('cp-messages');
      }, 900);
    }
  };

  function startCustPoll(){
    stopAllPolls();
    pollTimer = setInterval(()=>{
      fetch(`/chat/customer/poll/?after=${lastMsgId}`)
        .then(r=>r.json())
        .then(d=>{
          d.messages.forEach(m=>{
            if(m.id > lastMsgId) lastMsgId = m.id;
            if(!m.is_mine) appendMsgWithTime(m.content, 'other', m.created_at, m.image_url);
          });
          if(d.messages.some(m=>!m.is_mine)) scrollBottom('cp-messages');
        });
    }, 3000);
  }

  // ── STAFF logic ──
  function loadSessionList(){
    fetch('/chat/staff/sessions/')
      .then(r=>r.json())
      .then(d=>{
        renderSessionList(d.sessions);
        updateGlobalBadge(d.total_unread);
      });
  }

  function startSessionPoll(){
    clearInterval(sessionPollT);
    sessionPollT = setInterval(loadSessionList, 4000);
  }

  function renderSessionList(sessions){
    const el = document.getElementById('cp-session-list');
    if(!sessions || sessions.length === 0){
      el.innerHTML = '<div class="session-empty"><i class="fas fa-comments" style="font-size:2rem;color:#555;display:block;margin-bottom:12px;"></i>Chưa có yêu cầu hỗ trợ</div>';
      return;
    }
    el.innerHTML = sessions.map(s=>`
      <div class="session-item ${currentSid===s.id?'active':''}"
           onclick="staffOpenChat(${s.id},'${escHtml(s.customer_name)}')">
        <div class="session-avatar">
          ${s.customer_name.charAt(0).toUpperCase()}
          <div class="session-unread-dot ${s.unread>0?'show':''}">${s.unread>0?s.unread:''}</div>
        </div>
        <div class="session-info">
          <div class="session-name">${escHtml(s.customer_name)}</div>
          <div class="session-preview">${escHtml(s.last_message)}</div>
        </div>
        <div class="session-time">${s.last_time}</div>
      </div>
    `).join('');
  }

  window.staffOpenChat = function(sid, name){
    currentSid   = sid;
    staffLastId  = 0;
    clearInterval(sessionPollT);

    setActiveView('cp-view-chat');
    backBtn.classList.add('show');
    headerTitle.textContent = name;
    headerSub.textContent   = 'Đang trò chuyện';
    document.getElementById('cp-messages').innerHTML = '';

    fetchStaffMsgs();
    staffPollT = setInterval(fetchStaffMsgs, 3000);
    setTimeout(()=>document.getElementById('cp-staff-input').focus(), 200);
  };

  window.staffBackToList = function(){
    currentSid = null;
    clearInterval(staffPollT);
    setActiveView('cp-view-list');
    backBtn.classList.remove('show');
    headerTitle.textContent = 'Hỗ trợ khách hàng';
    headerSub.textContent   = 'Danh sách yêu cầu';
    document.getElementById('cp-messages').innerHTML = '';
    startSessionPoll();
  };

  function fetchStaffMsgs(){
    if(!currentSid) return;
    fetch(`/chat/staff/${currentSid}/poll/?after=${staffLastId}`)
      .then(r=>r.json())
      .then(d=>{
        let hasNew = false;
        d.messages.forEach(m=>{
          if(m.id > staffLastId){ staffLastId = m.id; hasNew = true; }
          appendMsg(m.content, m.is_mine ? 'me' : 'other', m.image_url);
        });
        if(hasNew) scrollBottom('cp-messages');
      });
  }

  window.staffSend = function(){
    if(!currentSid) return;
    const inp = document.getElementById('cp-staff-input');
    const txt = inp.value.trim();
    const imageFile = staffSelectedImageFile;
    if(!txt && !imageFile) return;

    if (imageFile) {
      const localUrl = URL.createObjectURL(imageFile);
      appendMsgWithTime(txt, 'me', null, localUrl);
    } else {
      appendMsg(txt, 'me');
    }

    inp.value = '';
    removeStaffPreview();
    scrollBottom('cp-messages');

    let bodyData;
    let headersData = {'X-CSRFToken':csrfToken};
    if (imageFile) {
      bodyData = new FormData();
      bodyData.append('content', txt);
      bodyData.append('image', imageFile);
    } else {
      bodyData = JSON.stringify({content: txt});
      headersData['Content-Type'] = 'application/json';
    }

    fetch(`/chat/staff/${currentSid}/send/`, {
      method:'POST',
      headers: headersData,
      body: bodyData
    })
    .then(r=>r.json())
    .then(d=>{ if(d.id) staffLastId = Math.max(staffLastId, d.id); });
  };

  function updateGlobalBadge(count){
    if(!panelOpen){
      badge.textContent = count > 0 ? (count > 99 ? '99+' : count) : '';
      badge.classList.toggle('show', count > 0);
    }
  }

  function startBgBadgePoll(){
    if(!isStaff) return;
    setInterval(()=>{
      if(!panelOpen){
        fetch('/chat/staff/sessions/')
          .then(r=>r.json())
          .then(d=>updateGlobalBadge(d.total_unread));
      }
    }, 8000);
  }

  if(isStaff){
    fetch('/chat/staff/sessions/')
      .then(r=>r.json())
      .then(d=>updateGlobalBadge(d.total_unread));
    startBgBadgePoll();
  } else {
    setTimeout(()=>{ if(!panelOpen) badge.classList.add('show'); }, 3000);
  }

  // ── Helpers ──
  function appendMsg(text, type, imageUrl){ appendMsgWithTime(text, type, null, imageUrl); }

  function appendMsgWithTime(text, type, timeStr, imageUrl){
    const el = document.getElementById('cp-messages');
    if(!el) return;

    const now = new Date();
    if(!timeStr){
      timeStr = now.getHours().toString().padStart(2,'0')+':'+now.getMinutes().toString().padStart(2,'0');
    }

    if(custLastTimestamp && (now - custLastTimestamp > 5 * 60 * 1000)) {
      const sep = document.createElement('div');
      sep.className = 'chat-date-separator';
      sep.textContent = timeStr;
      el.appendChild(sep);
    }
    custLastTimestamp = now;

    const lastRow = el.lastElementChild;
    const isSameSender = lastRow && lastRow.classList.contains('msg-row') && 
                         !lastRow.classList.contains('system') &&
                         ((type === 'me' && lastRow.classList.contains('me')) || 
                           (type !== 'me' && !lastRow.classList.contains('me')));

    const row = document.createElement('div');
    row.className = 'msg-row' + (type==='me' ? ' me' : '') + (isSameSender ? ' no-avatar' : '');
    
    if(type !== 'me'){
      const av = document.createElement('div');
      av.className = 'msg-av';
      av.innerHTML = isStaff ? '<i class="fas fa-user" style="font-size:0.75rem;"></i>'
                            : '<i class="fas fa-headset" style="font-size:0.75rem;"></i>';
      row.appendChild(av);
    }
    
    const wrap  = document.createElement('div');
    wrap.className = 'msg-bubble-wrap';
    const bub   = document.createElement('div');
    bub.className = 'msg-bubble ' + type;
    
    if (imageUrl) {
      const img = document.createElement('img');
      img.src = imageUrl;
      img.className = 'chat-msg-img';
      img.style.cursor = 'pointer';
      img.onclick = function() { zoomChatImage(imageUrl); };
      bub.appendChild(img);
      if (text) {
        const txtDiv = document.createElement('div');
        txtDiv.className = 'chat-msg-text';
        txtDiv.textContent = text;
        txtDiv.style.marginTop = '6px';
        bub.appendChild(txtDiv);
      }
    } else {
      bub.textContent = text;
    }
    
    const t = document.createElement('div');
    t.className = 'msg-time'; t.textContent = timeStr;
    
    wrap.appendChild(bub); wrap.appendChild(t);
    row.appendChild(wrap);
    el.appendChild(row);
  }

  function appendSystem(text){
    const el = document.getElementById('cp-messages');
    if(!el) return;

    const row = document.createElement('div');
    row.className = 'msg-row system';
    const bub = document.createElement('div');
    bub.className = 'msg-bubble system';
    bub.innerHTML = text;
    row.appendChild(bub);
    el.appendChild(row);
  }

  let typingEl = null;
  function showTyping(show){
    const el = document.getElementById('cp-messages');
    if(show && !typingEl){
      typingEl = document.createElement('div');
      typingEl.className = 'msg-row';
      typingEl.innerHTML = '<div class="msg-av"><i class="fas fa-headset" style="font-size:0.75rem;"></i></div><div class="typing-dots"><span></span><span></span><span></span></div>';
      el.appendChild(typingEl); scrollBottom('cp-messages');
    } else if(!show && typingEl){ typingEl.remove(); typingEl = null; }
  }

  function scrollBottom(id){ setTimeout(()=>{ const e=document.getElementById(id); if(e) e.scrollTo({top: e.scrollHeight, behavior: 'smooth'}); },30); }
  function stopAllPolls(){ clearInterval(pollTimer); clearInterval(staffPollT); clearInterval(sessionPollT); }
  function escHtml(s){ const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }

  // Image zoom lightbox
  function zoomChatImage(src) {
    const lightbox = document.getElementById('chat-image-lightbox');
    const lightboxImg = document.getElementById('chat-lightbox-img');
    if (lightbox && lightboxImg) {
      lightboxImg.src = src;
      lightbox.classList.add('show');
    }
  }

  window.closeChatLightbox = function() {
    const lightbox = document.getElementById('chat-image-lightbox');
    if (lightbox) {
      lightbox.classList.remove('show');
    }
  };

  // Previews
  function showPreview(file, imgEl, containerEl, isCust) {
    const reader = new FileReader();
    reader.onload = function(e) {
      imgEl.src = e.target.result;
      containerEl.style.display = 'flex';
      scrollBottom('cp-messages');
    };
    reader.readAsDataURL(file);
  }

  window.removeCustPreview = function() {
    custSelectedImageFile = null;
    const f = document.getElementById('cp-cust-file');
    if (f) f.value = '';
    const container = document.getElementById('cp-cust-preview-container');
    if (container) container.style.display = 'none';
    const img = document.getElementById('cp-cust-preview-img');
    if (img) img.src = '';
  };

  window.removeStaffPreview = function() {
    staffSelectedImageFile = null;
    const f = document.getElementById('cp-staff-file');
    if (f) f.value = '';
    const container = document.getElementById('cp-staff-preview-container');
    if (container) container.style.display = 'none';
    const img = document.getElementById('cp-staff-preview-img');
    if (img) img.src = '';
  };

  function initImageListeners() {
    // Cust File Input
    const custFile = document.getElementById('cp-cust-file');
    if (custFile) {
      custFile.addEventListener('change', function(e) {
        if (e.target.files && e.target.files[0]) {
          custSelectedImageFile = e.target.files[0];
          showPreview(
            custSelectedImageFile,
            document.getElementById('cp-cust-preview-img'),
            document.getElementById('cp-cust-preview-container'),
            true
          );
        }
      });
    }

    // Cust Paste
    const custInput = document.getElementById('cp-cust-input');
    if (custInput) {
      custInput.addEventListener('paste', function(e) {
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        for (let i = 0; i < items.length; i++) {
          if (items[i].type.indexOf('image') !== -1) {
            const file = items[i].getAsFile();
            custSelectedImageFile = file;
            showPreview(
              custSelectedImageFile,
              document.getElementById('cp-cust-preview-img'),
              document.getElementById('cp-cust-preview-container'),
              true
            );
            e.preventDefault();
            break;
          }
        }
      });
    }

    // Staff File Input
    const staffFile = document.getElementById('cp-staff-file');
    if (staffFile) {
      staffFile.addEventListener('change', function(e) {
        if (e.target.files && e.target.files[0]) {
          staffSelectedImageFile = e.target.files[0];
          showPreview(
            staffSelectedImageFile,
            document.getElementById('cp-staff-preview-img'),
            document.getElementById('cp-staff-preview-container'),
            false
          );
        }
      });
    }

    // Staff Paste
    const staffInput = document.getElementById('cp-staff-input');
    if (staffInput) {
      staffInput.addEventListener('paste', function(e) {
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        for (let i = 0; i < items.length; i++) {
          if (items[i].type.indexOf('image') !== -1) {
            const file = items[i].getAsFile();
            staffSelectedImageFile = file;
            showPreview(
              staffSelectedImageFile,
              document.getElementById('cp-staff-preview-img'),
              document.getElementById('cp-staff-preview-container'),
              false
            );
            e.preventDefault();
            break;
          }
        }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', initImageListeners);
  setTimeout(initImageListeners, 200);

})();
