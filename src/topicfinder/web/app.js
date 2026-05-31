async function addChannel() {
  const url = document.getElementById('url').value.trim();
  if (!url) return;
  await fetch('/api/channels', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({url}),
  });
  document.getElementById('url').value = '';
  loadChannels();
}

async function loadChannels() {
  const r = await fetch('/api/channels');
  const chs = await r.json();
  document.getElementById('channels').innerHTML =
    '구독 채널: ' + chs.map(c => c.title || c.url).join(', ');
}

function fmtTime(iso) {
  try { return new Date(iso).toLocaleTimeString('ko-KR'); }
  catch { return iso; }
}

async function loadTopics() {
  const r = await fetch('/api/topics');
  const topics = await r.json();
  const box = document.getElementById('topics');
  if (!topics.length) { box.innerHTML = '아직 분석된 주제가 없습니다.'; return; }
  box.innerHTML = topics.map(t => `
    <div class="topic">
      <div class="label">${t.label}
        <span class="score">· 핫점수 ${t.hot_score.toFixed(1)} · ${t.channel_count}개 채널</span>
      </div>
      ${t.members.map(m => `
        <div class="member">▶ <a href="${m.jump_url}" target="_blank">${m.video_id}</a>
          — 시작 ${fmtTime(m.start_abs)}</div>`).join('')}
    </div>`).join('');
}

loadChannels();
loadTopics();
setInterval(loadTopics, 30000);
setInterval(loadChannels, 60000);
