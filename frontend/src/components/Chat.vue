<template>
  <div class="chat-layout">
    <!-- ========== 左侧：会话列表 ========== -->
    <aside class="sidebar">
      <button class="new-session-btn" @click="newSession" :disabled="loading || !USER_ID">
        + 新建对话
      </button>

      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === sessionId }"
          @click="switchSession(s.id)"
        >
          <div class="session-info">
            <div class="session-title">{{ s.title || '新对话' }}</div>
            <div class="session-time">{{ formatTime(s.time) }}</div>
          </div>
          <button
            class="del-btn"
            title="删除该对话"
            @click.stop="deleteSession(s.id)"
          >×</button>
        </div>

        <div v-if="!sessions.length" class="list-empty">暂无对话</div>
      </div>
    </aside>

    <!-- ========== 右侧：聊天区 ========== -->
    <div class="chat-container">
      <header class="chat-header">
        <h2>AI 职业规划 &amp; 面试助手</h2>
        <div class="header-right">
          <button class="nav-btn" @click="goProfile">个人信息</button>
          <span class="session-tag" :title="sessionId">会话 {{ shortSessionId }}</span>
        </div>
      </header>

      <!-- 消息列表 -->
      <div class="chat-body" ref="bodyRef">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="message"
          :class="msg.role"
        >
          <div class="bubble">
            <span v-if="msg.role === 'assistant' && msg.streaming && !msg.content" class="thinking">
              <span class="thinking-dots"><i></i><i></i><i></i></span>正在思考中
            </span>
            <template v-else>{{ msg.content }}</template>
          </div>
          <span v-if="msg.role === 'assistant' && msg.streaming" class="cursor">▌</span>
        </div>

        <div v-if="loading && !messages.length" class="empty-tip">
          正在思考中...
        </div>

        <div v-if="tip" class="empty-tip tip-warn">{{ tip }}</div>
      </div>

      <!-- 输入区 -->
      <footer class="chat-footer">
        <input
          v-model="question"
          class="chat-input"
          placeholder="输入你的问题，例如：我要职业规划"
          @keyup.enter="send"
          :disabled="loading || !sessionId"
        />
        <button class="send-btn" @click="send" :disabled="loading || !question.trim() || !sessionId">
          {{ loading ? '发送中...' : '发送' }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 跳转到个人信息页
function goProfile() {
  router.push('/Profile')
}

const question = ref('')
const messages = ref([])
const loading = ref(false)
const bodyRef = ref(null)
const sessionId = ref('')
const tip = ref('')

// ---------- 多会话状态 ----------
// sessions: 会话列表 [{ id, title, time }]
const sessions = ref([])
// messagesCache: 每个会话的消息缓存 { [session_id]: [msg, ...] }
const messagesCache = ref({})

const BASE_URL = 'http://localhost:8080'

// ---------- 本地存储 key ----------
const STORAGE_KEY_SESSIONS = 'chat_sessions'          // 会话列表
const STORAGE_KEY_CURRENT = 'chat_current_sid'        // 当前会话 id
const STORAGE_KEY_CACHE = 'chat_messages_cache'       // 消息缓存

// 上限控制：会话数 & 每个会话缓存的消息条数
const MAX_SESSIONS = 20
const MAX_MSGS_PER_SESSION = 50

// 登录态：user_id / email 由登录接口返回并存入 sessionStorage
const USER_ID = sessionStorage.getItem('user_id') || ''
const email = sessionStorage.getItem('email') || ''

const shortSessionId = computed(() =>
  sessionId.value ? sessionId.value.slice(0, 8) : '未创建'
)

// ---------- 本地存储读写（统一用 sessionStorage：关标签页即清空） ----------
function loadFromStorage() {
  try {
    sessions.value = JSON.parse(sessionStorage.getItem(STORAGE_KEY_SESSIONS) || '[]')
    messagesCache.value = JSON.parse(sessionStorage.getItem(STORAGE_KEY_CACHE) || '{}')
    sessionId.value = sessionStorage.getItem(STORAGE_KEY_CURRENT) || ''
  } catch (e) {
    console.error('读取本地会话失败：', e)
    sessions.value = []
    messagesCache.value = {}
    sessionId.value = ''
  }
}

function saveSessions() {
  sessionStorage.setItem(STORAGE_KEY_SESSIONS, JSON.stringify(sessions.value))
}

function saveCache() {
  sessionStorage.setItem(STORAGE_KEY_CACHE, JSON.stringify(messagesCache.value))
}

function saveCurrent() {
  sessionStorage.setItem(STORAGE_KEY_CURRENT, sessionId.value)
}

// 格式化时间（会话列表里显示）
function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// 用首条用户消息生成会话标题
function makeTitle(text) {
  if (!text) return '新对话'
  const t = text.trim().replace(/\s+/g, ' ')
  return t.length > 10 ? t.slice(0, 10) + '…' : t
}

// ---------- 会话操作 ----------

// 从后端申请会话：传了已存在的 id 且归属正确就复用，否则新建
async function requestSessionId(existingId) {
  const resp = await fetch(`${BASE_URL}/chat/create_session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: USER_ID,
      session_id: existingId || '',
    }),
  })
  const data = await resp.json()
  if (data.code !== 200 || !data.data) {
    throw new Error(data.msg || '创建会话失败')
  }
  return data.data
}

// 把当前消息存进缓存
function cacheCurrentMessages() {
  if (!sessionId.value) return
  const trimmed = messages.value.slice(-MAX_MSGS_PER_SESSION)
  messagesCache.value[sessionId.value] = trimmed.map((m) => ({
    role: m.role,
    content: m.content,
  }))
  saveCache()
}

// 初始化：恢复本地会话；没有就新建一个
async function initSessions() {
  if (!USER_ID) {
    tip.value = '未检测到登录信息，请先登录'
    return
  }

  loadFromStorage()

  // 本地有记录的会话 -> 恢复当前会话
  if (sessionId.value && sessions.value.some((s) => s.id === sessionId.value)) {
    messages.value = messagesCache.value[sessionId.value] || []
    await scrollToBottom()
    return
  }

  // 本地没有有效会话 -> 新建
  await newSession()
}

// 新建会话
async function newSession() {
  if (loading.value || !USER_ID) return
  // 先把当前会话消息存起来
  cacheCurrentMessages()

  try {
    const sid = await requestSessionId('')
    sessionId.value = sid
    messages.value = []
    messagesCache.value[sid] = []

    // 插入到列表最前
    sessions.value.unshift({ id: sid, title: '新对话', time: Date.now() })
    if (sessions.value.length > MAX_SESSIONS) {
      const removed = sessions.value.splice(MAX_SESSIONS)
      removed.forEach((s) => delete messagesCache.value[s.id])   // 顺手清缓存
    }

    saveSessions()
    saveCache()
    saveCurrent()
    tip.value = ''
  } catch (e) {
    tip.value = `会话初始化失败：${e.message}`
  }
}

// 切换会话
function switchSession(sid) {
  if (sid === sessionId.value || loading.value) return
  // 先存当前会话的消息
  cacheCurrentMessages()

  sessionId.value = sid
  messages.value = messagesCache.value[sid] || []
  saveCurrent()
  scrollToBottom()
}

// 删除会话
async function deleteSession(sid) {
  if (loading.value) return

  // 从列表和缓存中移除
  sessions.value = sessions.value.filter((s) => s.id !== sid)
  delete messagesCache.value[sid]
  saveSessions()
  saveCache()

  // 删的是当前会话 -> 切到列表第一个，没有就新建
  if (sid === sessionId.value) {
    if (sessions.value.length) {
      switchSession(sessions.value[0].id)
    } else {
      sessionId.value = ''
      messages.value = []
      await newSession()
    }
  }
}

onMounted(initSessions)

// ---------- 发送消息 ----------
async function send() {
  const q = question.value.trim()
  if (!q || loading.value || !sessionId.value) return

  question.value = ''
  loading.value = true

  // 用户消息 + 占位的 AI 消息
  messages.value.push({ role: 'user', content: q })
  messages.value.push({ role: 'assistant', content: '', streaming: true })

  // 首条用户消息 -> 更新会话标题
  const cur = sessions.value.find((s) => s.id === sessionId.value)
  if (cur && cur.title === '新对话') {
    cur.title = makeTitle(q)
    cur.time = Date.now()
    saveSessions()
  }

  await scrollToBottom()

  const params = new URLSearchParams({
    question: q,
    user_id: USER_ID,
    session_id: sessionId.value,
    email: email,
  })

  try {
    const resp = await fetch(`${BASE_URL}/chat/chat?${params.toString()}`)
    if (!resp.ok || !resp.body) {
      throw new Error(`HTTP ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    const last = messages.value[messages.value.length - 1]

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE 数据可能跨 chunk，按 \n\n 分割完整事件
      let sep
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, sep)
        buffer = buffer.slice(sep + 2)

        for (const line of rawEvent.split('\n')) {
          if (!line.startsWith('data:')) continue
          const payload = JSON.parse(line.slice(5).trim())
          if (payload.done) {
            last.streaming = false
            loading.value = false
          } else if (payload.data) {
            last.content += payload.data
          }
        }
        await scrollToBottom()
      }
    }
  } catch (e) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content += `\n[连接出错: ${e.message}]`
      last.streaming = false
    }
  } finally {
    loading.value = false
    // 发送结束，把本轮消息写入缓存
    cacheCurrentMessages()
    await scrollToBottom()
  }
}

async function scrollToBottom() {
  await nextTick()
  if (bodyRef.value) {
    bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  }
}
</script>

<style scoped>
/* ---------- 整体布局：左侧栏 + 右侧聊天 ---------- */
.chat-layout {
  display: flex;
  height: 100vh;
  background: linear-gradient(160deg, #eef2f8 0%, #f7f8fa 40%, #eef1f6 100%);
}

/* ---------- 左侧会话栏 ---------- */
.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: linear-gradient(180deg, #1f2540 0%, #171c33 100%);
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  gap: 12px;
  box-shadow: 4px 0 24px rgba(23, 28, 51, 0.15);
}

.new-session-btn {
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #22d3ee);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
  transition: transform 0.15s, box-shadow 0.15s;
}

.new-session-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.45);
}

.new-session-btn:disabled {
  background: #3a4166;
  color: #8b91ad;
  box-shadow: none;
  cursor: not-allowed;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* 滚动条美化（webkit） */
.session-list::-webkit-scrollbar,
.chat-body::-webkit-scrollbar {
  width: 6px;
}
.session-list::-webkit-scrollbar-thumb,
.chat-body::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.18);
  border-radius: 3px;
}
.chat-body::-webkit-scrollbar-thumb {
  background: rgba(31, 37, 64, 0.18);
}

.session-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.session-item.active {
  background: rgba(99, 102, 241, 0.28);
  box-shadow: inset 2px 0 0 #6366f1;
}

.session-info {
  flex: 1;
  min-width: 0;   /* 让子元素能正确省略号 */
}

.session-title {
  font-size: 13px;
  color: #e6e8f2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-item.active .session-title {
  color: #fff;
  font-weight: 600;
}

.session-time {
  font-size: 11px;
  color: #8b91ad;
  margin-top: 2px;
}

.del-btn {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  line-height: 18px;
  text-align: center;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #8b91ad;
  font-size: 15px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s, color 0.15s;
}

.session-item:hover .del-btn {
  opacity: 1;
}

.del-btn:hover {
  color: #ff7676;
  background: rgba(255, 118, 118, 0.15);
}

.list-empty {
  text-align: center;
  color: #8b91ad;
  font-size: 13px;
  padding: 20px 0;
}

/* ---------- 右侧聊天区 ---------- */
.chat-container {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.chat-header {
  padding: 14px 24px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(229, 228, 231, 0.8);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1f2540;
  background: linear-gradient(90deg, #1f2540, #6366f1);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.session-tag {
  font-size: 12px;
  color: #8a8f99;
  background: #f2f3f5;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid #e5e4e7;
}

.nav-btn {
  padding: 7px 16px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
  transition: opacity 0.15s, transform 0.15s;
}

.nav-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.tip-warn {
  color: #d9801a !important;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.message {
  display: flex;
  max-width: 78%;
  animation: msg-in 0.25s ease both;
}

@keyframes msg-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  align-self: flex-end;
}

.message.assistant {
  align-self: flex-start;
}

.bubble {
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 15px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.message.user .bubble {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
}

.message.assistant .bubble {
  background: #fff;
  color: #333;
  border: 1px solid rgba(229, 228, 231, 0.9);
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 10px rgba(31, 37, 64, 0.06);
}

.cursor {
  align-self: flex-end;
  color: #6366f1;
  margin-left: 2px;
  animation: blink 1s step-start infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.thinking {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #8a8f99;
  font-size: 14px;
}

.thinking-dots {
  display: inline-flex;
  align-items: center;
}

.thinking-dots i {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin: 0 2px;
  border-radius: 50%;
  background: #6366f1;
  animation: think-bounce 1.2s ease-in-out infinite;
}

.thinking-dots i:nth-child(2) {
  animation-delay: 0.2s;
}

.thinking-dots i:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes think-bounce {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.35;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

.empty-tip {
  align-self: center;
  color: #999;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.8);
  padding: 8px 18px;
  border-radius: 999px;
}

.chat-footer {
  display: flex;
  gap: 12px;
  padding: 14px 24px 18px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid rgba(229, 228, 231, 0.8);
}

.chat-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 12px;
  font-size: 15px;
  outline: none;
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.chat-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

.chat-input:disabled {
  background: #f5f6f8;
  cursor: not-allowed;
}

.send-btn {
  padding: 12px 26px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
  transition: transform 0.15s, box-shadow 0.15s;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.45);
}

.send-btn:disabled {
  background: #b9c1e3;
  box-shadow: none;
  cursor: not-allowed;
}
</style>
