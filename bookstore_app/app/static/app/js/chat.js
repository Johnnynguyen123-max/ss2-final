/**
 * chat.js — Chat Widget Logic
 * Được tách từ base.html để dễ bảo trì
 * Xử lý: Customer chat, Staff chat, AI Bot, AJAX polling
 */
(function(){
  const isStaff = window.CHAT_IS_STAFF || false;
  const csrfToken = getCookie('csrftoken');

  // ── State ──
  let panelOpen    = false;
  let lastMsgId    = 0;
  let pollTimer    = null;
  let autoReplied  = false;
  let currentSid   = null;
  let staffLastId  = 0;
  let staffPollT   = null;
  let sessionPollT = null;

  // ── Elements ──
  const panel      = document.getElementById('chat-panel');
  const badge      = document.getElementById('chat-notif-badge');
  const bubbleIcon = document.getElementById('chat-bubble-icon');
  const backBtn    = document.getElementById('cp-back-btn');
  const headerTitle= document.getElementById('cp-header-title');
  const headerSub  = document.getElementById('cp-header-sub');

  // ── Toggle panel ──
  window.chatToggle = function(){
    panelOpen = !panelOpen;
    panel.classList.toggle('open', panelOpen);
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
    document.getElementById('cp-header-icon').innerHTML = '<i class="fas fa-comments"></i>';
    backBtn.classList.remove('show');
    document.getElementById('cp-view-mode').style.display = 'flex';
    document.getElementById('cp-view-bot').style.display  = 'none';
    document.getElementById('cp-view-chat').style.display = 'none';
  }

  window.custChooseMode = function(mode){
    custMode = mode;
    if(mode === 'bot'){
      headerTitle.textContent = 'DDC Books AI Bot';
      headerSub.textContent   = '✨ Trả lời ngay lập tức';
      document.getElementById('cp-header-icon').innerHTML = '<i class="fas fa-robot"></i>';
      backBtn.classList.add('show');
      backBtn.onclick = function(){ custMode = null; showModeSelection(); };
      document.getElementById('cp-view-mode').style.display = 'none';
      document.getElementById('cp-view-bot').style.display  = 'flex';
      document.getElementById('cp-view-chat').style.display = 'none';
      initBot();
    } else {
      headerTitle.textContent = 'DDC Books – Hỗ trợ';
      headerSub.textContent   = 'Nhân viên trực tuyến';
      document.getElementById('cp-header-icon').innerHTML = '<i class="fas fa-headset"></i>';
      backBtn.classList.add('show');
      backBtn.onclick = function(){ custMode = null; stopAllPolls(); showModeSelection(); };
      document.getElementById('cp-view-mode').style.display = 'none';
      document.getElementById('cp-view-bot').style.display  = 'none';
      document.getElementById('cp-view-chat').style.display = 'flex';
      loadCustHistory();
    }
  };

  // ════════════════════════════════════════
  //  BOT logic
  // ════════════════════════════════════════
  let botInited = false;
  let botTypingEl = null;

  function initBot(){
    if(botInited) return;
    botInited = true;
    const el = document.getElementById('cp-bot-messages');
    el.innerHTML = '';
    appendBotMsg('other', 'Xin chào! Mình là DDC Books AI Bot 🤖\nMình có thể giúp bạn tìm sách, kiểm tra đơn hàng, tư vấn theo sở thích và nhiều hơn nữa!\n\nBạn muốn hỏi gì hôm nay? 😊');
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
      quickReply = '📍 DDC Books tọa lạc tại:\n📌 Số 9 Nguyễn Trãi, Hà Đông, Hà Nội\n⏰ Giờ mở cửa: 08:00 – 22:00 (Hàng ngày)\n📞 Hotline: 094.152.7660';
    } else if(/(đổi trả|hoàn hàng|trả hàng|chính sách|bảo hành)/i.test(lower)){
      quickReply = '↩️ Chính sách đổi trả DDC Books:\n• Đổi trả trong vòng 7 ngày kể từ ngày nhận hàng\n• Sản phẩm còn nguyên seal, chưa qua sử dụng\n• Lỗi do nhà sản xuất: đổi mới 100%\n• Liên hệ: support@ddcbooks.com hoặc Hotline 094.152.7660';
    } else if(/(vận chuyển|giao hàng|ship|phí ship|thời gian giao)/i.test(lower)){
      quickReply = '🚚 Thông tin vận chuyển:\n• Nội thành Hà Nội: 1–2 ngày (miễn phí từ 250.000đ)\n• Toàn quốc: 3–5 ngày làm việc\n• Phí ship: 25.000đ – 40.000đ tùy khu vực\n• Có thể theo dõi đơn qua mã vận đơn';
    } else if(/(đơn hàng|kiểm tra đơn|tình trạng đơn|mã đơn|order)/i.test(lower)){
      quickReply = '📦 Để kiểm tra đơn hàng, bạn vui lòng:\n1. Truy cập mục "Lịch sử mua hàng" trên tài khoản\n2. Hoặc cung cấp mã đơn hàng để mình tra giúp!\n\nBạn có mã đơn hàng không?';
    } else if(/(giảm giá|sale|khuyến mãi|ưu đãi|đang sale)/i.test(lower)){
      quickReply = '🔥 Sách đang giảm giá hot tại DDC Books:\n\nMình sẽ chuyển bạn đến trang khuyến mãi ngay!\n👉 <a href="/?filter=sale" style="color:#f39c12;font-weight:600;">Xem sách giảm giá</a>';
    } else if(/(tặng quà|quà tặng|gift|sinh nhật|quà)/i.test(lower)){
      quickReply = '🎁 Tư vấn sách tặng quà:\n\nBạn cho mình biết thêm:\n• Người nhận bao nhiêu tuổi?\n• Họ thích chủ đề gì? (Văn học, kỹ năng, khoa học...)\n• Ngân sách dự kiến?\n\nMình sẽ gợi ý những cuốn sách phù hợp nhất! 😊';
    } else if(/(lập trình|coding|code|python|javascript|công nghệ|it|dev)/i.test(lower)){
      quickReply = '💻 Sách lập trình cho bạn:\n\nMình gợi ý một số hướng:\n• Người mới bắt đầu: "Python Cơ Bản", "Lập Trình Không Khó"\n• Web development: "HTML/CSS Thực Chiến"\n• Tư duy logic: "Cấu Trúc Dữ Liệu & Giải Thuật"\n\n👉 <a href="/?category=&q=lập+trình" style="color:#f39c12;font-weight:600;">Xem tất cả sách lập trình</a>';
    } else if(/(wishlist|yêu thích|sách yêu thích)/i.test(lower)){
      quickReply = '❤️ Danh sách yêu thích của bạn:\n\nBạn có thể xem danh sách sách yêu thích tại:\n👉 <a href="/wishlist/" style="color:#f39c12;font-weight:600;">Xem Wishlist của tôi</a>\n\nMình sẽ thông báo ngay khi sách trong wishlist được giảm giá! 🔔';
    } else if(/(giỏ hàng|cart|chưa thanh toán|bỏ quên)/i.test(lower)){
      quickReply = '🛒 Bạn còn sản phẩm trong giỏ hàng chưa thanh toán!\n\n👉 <a href="/cart/" style="color:#f39c12;font-weight:600;">Xem giỏ hàng ngay</a>\n\nMình nhắc nhẹ: nhiều sách đang có giá ưu đãi, đừng để lỡ nhé! 😉';
    } else if(/(hết hàng|out of stock|thông báo khi có hàng|nhận thông báo)/i.test(lower)){
      quickReply = '🔔 Đăng ký nhận thông báo khi có hàng:\n\nBạn chỉ cần:\n1. Vào trang sản phẩm đang hết hàng\n2. Nhấn nút "Thông báo khi có hàng"\n3. Mình sẽ email ngay khi sách về kho!\n\nHoặc cho mình biết tên sách, mình hỗ trợ đăng ký luôn nhé!';
    } else if(/(gợi ý|recommend|tư vấn|nên đọc|đọc gì|sách hay)/i.test(lower)){
      quickReply = '✨ Gợi ý sách cá nhân hóa cho bạn:\n\nĐể gợi ý chính xác nhất, bạn cho mình biết:\n• Bạn thích thể loại gì? (Tiểu thuyết, Self-help, Kinh tế, Khoa học...)\n• Bạn đang cần đọc để làm gì? (Học tập, giải trí, công việc...)\n• Ngân sách bạn có là bao nhiêu?\n\nMình sẽ chọn ra những cuốn "best match" cho bạn! 📚';
    } else if(/(tiếng anh|english|tiếng nhật|tiếng hàn|tiếng trung|ngoại văn|foreign)/i.test(lower)){
      quickReply = '🌍 DDC Books có đa dạng sách ngoại văn:\n\n🇺🇸 Tiếng Anh • 🇯🇵 Tiếng Nhật\n🇰🇷 Tiếng Hàn • 🇨🇳 Tiếng Trung\n\nBạn đang tìm sách ngoại văn ở trình độ nào?\n(Sơ cấp / Trung cấp / Nâng cao)\n\n👉 <a href="/?q=ngoại+văn" style="color:#f39c12;font-weight:600;">Xem sách ngoại văn</a>';
    } else if(/(đánh giá|review|phản hồi|nhận xét|feedback)/i.test(lower)){
      quickReply = '⭐ Cảm ơn bạn đã quan tâm đến việc đánh giá!\n\nSau khi nhận hàng, bạn có thể:\n1. Vào trang chi tiết sách đã mua\n2. Cuộn xuống phần "Đánh giá"\n3. Để lại nhận xét và số sao\n\nĐánh giá của bạn giúp cộng đồng độc giả rất nhiều! 🙏';
    }

    setTimeout(()=>{
      showBotTyping(false);
      if(quickReply){
        appendBotMsgHtml('other', quickReply);
      } else {
        callClaudeBot(text);
        return;
      }
      scrollBotBottom();
    }, 700);
  }

  // ── Lưu lịch sử hội thoại bot (multi-turn) ──
  let botHistory = [];

  async function callClaudeBot(userText){
    botHistory.push({ role: 'user', content: userText });
    try {
      const res = await fetch('/chat/bot/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
          message: userText,
          history: botHistory.slice(0, -1),
        })
      });
      const data = await res.json();
      showBotTyping(false);
      if(data.reply){
        botHistory.push({ role: 'assistant', content: data.reply });
        if(botHistory.length > 40) botHistory = botHistory.slice(-40);
        appendBotMsg('other', data.reply);
      } else {
        appendBotMsg('other', 'Xin lỗi, có lỗi xảy ra. Bạn thử lại hoặc liên hệ nhân viên nhé! 🙏');
      }
      scrollBotBottom();
    } catch(e){
      showBotTyping(false);
      appendBotMsg('other', 'Xin lỗi, không kết nối được server. Vui lòng thử lại! 🙏');
      scrollBotBottom();
    }
  }

  function appendBotMsg(type, text){
    const el = document.getElementById('cp-bot-messages');
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2,'0')+':'+now.getMinutes().toString().padStart(2,'0');
    const row = document.createElement('div');
    row.className = 'msg-row' + (type==='me'?' me':'');
    if(type !== 'me'){
      const av = document.createElement('div');
      av.className = 'msg-av';
      av.innerHTML = '<i class="fas fa-robot" style="font-size:0.65rem;"></i>';
      row.appendChild(av);
    }
    const wrap = document.createElement('div');
    const bub = document.createElement('div');
    bub.className = 'msg-bubble ' + type;
    bub.style.whiteSpace = 'pre-line';
    bub.textContent = text;
    const t = document.createElement('div');
    t.className = 'msg-time'; t.textContent = timeStr;
    wrap.appendChild(bub); wrap.appendChild(t);
    row.appendChild(wrap);
    el.appendChild(row);
  }

  function appendBotMsgHtml(type, html){
    const el = document.getElementById('cp-bot-messages');
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2,'0')+':'+now.getMinutes().toString().padStart(2,'0');
    const row = document.createElement('div');
    row.className = 'msg-row' + (type==='me'?' me':'');
    if(type !== 'me'){
      const av = document.createElement('div');
      av.className = 'msg-av';
      av.innerHTML = '<i class="fas fa-robot" style="font-size:0.65rem;"></i>';
      row.appendChild(av);
    }
    const wrap = document.createElement('div');
    const bub = document.createElement('div');
    bub.className = 'msg-bubble ' + type;
    bub.style.whiteSpace = 'pre-line';
    bub.innerHTML = html;
    const t = document.createElement('div');
    t.className = 'msg-time'; t.textContent = timeStr;
    wrap.appendChild(bub); wrap.appendChild(t);
    row.appendChild(wrap);
    el.appendChild(row);
  }

  function showBotTyping(show){
    const el = document.getElementById('cp-bot-messages');
    if(show && !botTypingEl){
      botTypingEl = document.createElement('div');
      botTypingEl.className = 'msg-row';
      botTypingEl.innerHTML = '<div class="msg-av"><i class="fas fa-robot" style="font-size:0.65rem;"></i></div><div class="typing-dots"><span></span><span></span><span></span></div>';
      el.appendChild(botTypingEl); scrollBotBottom();
    } else if(!show && botTypingEl){ botTypingEl.remove(); botTypingEl = null; }
  }

  function scrollBotBottom(){ setTimeout(()=>{ const e=document.getElementById('cp-bot-messages'); if(e) e.scrollTop=e.scrollHeight; },30); }

  // ════════════════════════════════════════
  //  CUSTOMER (Staff chat) logic
  // ════════════════════════════════════════
  function loadCustHistory(){
    const msgsEl = document.getElementById('cp-messages');
    msgsEl.innerHTML = '<div style="text-align:center;padding:20px;color:#bbb;font-size:0.8rem;">Đang tải...</div>';

    fetch('/chat/customer/poll/?after=0&history=1')
      .then(r=>r.json())
      .then(d=>{
        msgsEl.innerHTML = '';
        if(d.messages.length === 0){
          msgsEl.innerHTML = `
            <div class="msg-row">
              <div class="msg-av"><i class="fas fa-headset" style="font-size:0.65rem;"></i></div>
              <div>
                <div class="msg-bubble other">Xin chào bạn! Bạn cần giúp gì? 😊</div>
                <div class="msg-time">DDC Books</div>
              </div>
            </div>`;
        } else {
          d.messages.forEach(m => {
            if(m.id > lastMsgId) lastMsgId = m.id;
            appendMsgWithTime(m.content, m.is_mine ? 'me' : 'other', m.created_at);
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
    if(!txt) return;
    appendMsg(txt, 'me');
    inp.value = '';
    scrollBottom('cp-messages');

    fetch('/chat/customer/send/', {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},
      body: JSON.stringify({content: txt})
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
            if(!m.is_mine) appendMsgWithTime(m.content, 'other', m.created_at);
          });
          if(d.messages.some(m=>!m.is_mine)) scrollBottom('cp-messages');
        });
    }, 3000);
  }

  // ════════════════════════════════════════
  //  STAFF logic
  // ════════════════════════════════════════
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
      el.innerHTML = '<div class="session-empty"><i class="fas fa-comments" style="font-size:1.8rem;color:#ddd;display:block;margin-bottom:8px;"></i>Chưa có yêu cầu hỗ trợ</div>';
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

    document.getElementById('cp-view-list').classList.remove('active');
    document.getElementById('cp-view-chat').classList.add('active');
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
    document.getElementById('cp-view-chat').classList.remove('active');
    document.getElementById('cp-view-list').classList.add('active');
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
          appendMsg(m.content, m.is_mine ? 'me' : 'other');
        });
        if(hasNew) scrollBottom('cp-messages');
      });
  }

  window.staffSend = function(){
    if(!currentSid) return;
    const inp = document.getElementById('cp-staff-input');
    const txt = inp.value.trim();
    if(!txt) return;
    appendMsg(txt,'me');
    inp.value = '';
    scrollBottom('cp-messages');

    fetch(`/chat/staff/${currentSid}/send/`, {
      method:'POST',
      headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},
      body: JSON.stringify({content: txt})
    })
    .then(r=>r.json())
    .then(d=>{ if(d.id) staffLastId = Math.max(staffLastId, d.id); });
  };

  // ── Badge toàn cục (staff) ──
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
  function appendMsg(text, type){ appendMsgWithTime(text, type, null); }

  function appendMsgWithTime(text, type, timeStr){
    const el = document.getElementById('cp-messages');
    if(!timeStr){
      const now = new Date();
      timeStr = now.getHours().toString().padStart(2,'0')+':'+now.getMinutes().toString().padStart(2,'0');
    }
    const row = document.createElement('div');
    row.className = 'msg-row' + (type==='me' ? ' me' : '');
    if(type !== 'me'){
      const av = document.createElement('div');
      av.className = 'msg-av';
      av.innerHTML = isStaff ? '<i class="fas fa-user" style="font-size:0.65rem;"></i>'
                              : '<i class="fas fa-headset" style="font-size:0.65rem;"></i>';
      row.appendChild(av);
    }
    const wrap  = document.createElement('div');
    const bub   = document.createElement('div');
    bub.className = 'msg-bubble ' + type;
    bub.textContent = text;
    const t = document.createElement('div');
    t.className = 'msg-time'; t.textContent = timeStr;
    wrap.appendChild(bub); wrap.appendChild(t);
    row.appendChild(wrap);
    el.appendChild(row);
  }

  function appendSystem(text){
    const el = document.getElementById('cp-messages');
    const row = document.createElement('div');
    row.className = 'msg-row';
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
      typingEl.innerHTML = '<div class="msg-av"><i class="fas fa-headset" style="font-size:0.65rem;"></i></div><div class="typing-dots"><span></span><span></span><span></span></div>';
      el.appendChild(typingEl); scrollBottom('cp-messages');
    } else if(!show && typingEl){ typingEl.remove(); typingEl = null; }
  }

  function scrollBottom(id){ setTimeout(()=>{ const e=document.getElementById(id); if(e) e.scrollTop=e.scrollHeight; },30); }
  function stopAllPolls(){ clearInterval(pollTimer); clearInterval(staffPollT); clearInterval(sessionPollT); }
  function escHtml(s){ const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }

})();
