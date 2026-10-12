<template>
  <div class="register-page">
    <!-- 背景装饰光斑 -->
    <div class="deco deco-1"></div>
    <div class="deco deco-2"></div>
    <div class="deco deco-3"></div>

    <div class="register-card">
      <div class="register-header">
        <div class="register-logo">AI</div>
        <h1 class="register-title">创建账号</h1>
        <p class="register-subtitle">邮箱验证，安全注册</p>
      </div>

      <form class="register-form" @submit.prevent="Register">
        <!-- 邮箱 + 发送验证码 -->
        <div class="input-row">
          <input
            v-model="email"
            type="email"
            placeholder="请输入邮箱号"
            class="register-input"
            :disabled="ticket !== ''"
          >
          <button
            type="button"
            class="code-btn"
            :disabled="counting || !email || ticket !== ''"
            @click="sendCode"
          >
            {{ codeBtnText }}
          </button>
        </div>

        <!-- 验证码 -->
        <input
          v-model="code"
          type="text"
          maxlength="4"
          placeholder="请输入 4 位验证码"
          class="register-input"
          :disabled="ticket !== ''"
        >

        <!-- 验证通过提示 -->
        <p v-if="ticket" class="ok-tip">✓ 邮箱验证通过，请填写账号信息</p>

        <input
          v-model="name"
          type="text"
          placeholder="请输入姓名"
          class="register-input"
        >
        <input
          v-model="password"
          type="password"
          placeholder="请输入密码"
          class="register-input"
        >

        <button type="submit" class="register-btn" :disabled="loading">
          {{ loading ? "注册中..." : "注 册" }}
        </button>

        <div class="register-footer">
          <span class="footer-text">已有账号？</span>
          <a class="footer-link" @click="router.push('/Login')">去登录</a>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ref, computed, getCurrentInstance, onUnmounted } from "vue";

const router = useRouter();
const { proxy } = getCurrentInstance();

const email = ref("");
const code = ref("");
const name = ref("");
const password = ref("");

// 一次性注册凭证（验证码通过后由后端返回）
const ticket = ref("");
// 发送按钮倒计时
const countdown = ref(0);
const loading = ref(false);
let timer = null;

const counting = computed(() => countdown.value > 0);
const codeBtnText = computed(() =>
  counting.value ? `${countdown.value}s 后重发` : "发送验证码"
);

// -------------------- 1. 发送验证码 --------------------
function sendCode() {
  const e = email.value.trim();
  if (!e) {
    alert("请先输入邮箱");
    return;
  }
  // 简单邮箱格式校验
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)) {
    alert("邮箱格式不正确");
    return;
  }

  proxy.$axios({
    url: "login/register",
    method: "post",
    params: { email: e },
  })
    .then((res) => {
      alert(res.data.msg);
      if (res.data.code === 200) {
        startCountdown();
      }
    })
    .catch((err) => {
      alert("发送失败：" + (err.response?.data?.msg || err.message));
    });
}

// 60 秒倒计时
function startCountdown() {
  countdown.value = 60;
  if (timer) clearInterval(timer);
  timer = setInterval(() => {
    countdown.value -= 1;
    if (countdown.value <= 0) {
      clearInterval(timer);
      timer = null;
    }
  }, 1000);
}

// -------------------- 2 + 3. 校验验证码 -> 创建账号 --------------------
async function Register() {
  const e = email.value.trim();

  if (!e || !code.value.trim() || !password.value) {
    alert("邮箱、验证码和密码不能为空");
    return;
  }

  loading.value = true;
  try {
    // 2. 校验验证码，拿一次性凭证（若已拿过就跳过）
    if (!ticket.value) {
      const checkRes = await proxy.$axios({
        url: "login/check",
        method: "get",
        params: { email: e, code: code.value.trim() },
      });
      const c = checkRes.data;
      if (c.code !== 200 || !c.ticket) {
        alert(c.msg || "验证码校验失败");
        return;
      }
      ticket.value = c.ticket;
    }

    // 3. 创建账号
    const res = await proxy.$axios({
      url: "login/create",
      method: "post",
      data: {
        email: e,
        name: name.value,
        password: password.value,
        ticket: ticket.value,
      },
    });

    const code2 = res.data.code;
    const msg = res.data.msg;
    if (code2 === 200) {
      alert(msg);
      // 新账号：清掉可能残留的旧登录信息与会话缓存，避免会话串号
      sessionStorage.removeItem("user_id");
      sessionStorage.removeItem("session_id");
      sessionStorage.removeItem("chat_sessions");
      sessionStorage.removeItem("chat_current_sid");
      sessionStorage.removeItem("chat_messages_cache");
      sessionStorage.setItem("name", name.value);
      sessionStorage.setItem("email", e);
      setTimeout(() => {
        router.push("/Login");
      }, 500);
    } else {
      // 凭证失效则重置，让用户重新验证
      if (code2 === 401) ticket.value = "";
      alert(msg);
    }
  } catch (err) {
    alert("注册失败：" + (err.response?.data?.msg || err.message));
  } finally {
    loading.value = false;
  }
}

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  font-family: system-ui, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  background: linear-gradient(135deg, #0f172a 0%, #312e81 50%, #831843 100%);
}

/* ============ 背景装饰光斑 ============ */
.deco {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.5;
  animation: float 8s ease-in-out infinite;
}
.deco-1 {
  width: 400px;
  height: 400px;
  background: #ec4899;
  top: -120px;
  right: -140px;
}
.deco-2 {
  width: 340px;
  height: 340px;
  background: #22d3ee;
  bottom: -100px;
  left: -120px;
  animation-delay: 2s;
}
.deco-3 {
  width: 200px;
  height: 200px;
  background: #6366f1;
  top: 50%;
  right: 12%;
  opacity: 0.25;
  animation-delay: 4s;
}
@keyframes float {
  0%, 100% { transform: translateY(0) translateX(0); }
  50% { transform: translateY(-24px) translateX(14px); }
}

/* ============ 注册卡片 ============ */
.register-card {
  position: relative;
  z-index: 1;
  width: 420px;
  padding: 40px 40px 30px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 20px;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
  box-sizing: border-box;
}

.register-header {
  text-align: center;
  margin-bottom: 24px;
}

.register-logo {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #fff;
  background: linear-gradient(135deg, #ec4899, #6366f1);
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(236, 72, 153, 0.4);
}

.register-title {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  color: #fff;
}

.register-subtitle {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.65);
}

/* ============ 表单 ============ */
.register-form {
  display: flex;
  flex-direction: column;
}

.input-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.register-input {
  margin-bottom: 16px;
  height: 44px;
  padding: 0 14px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 10px;
  font-size: 15px;
  color: #fff;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.3s;
}

/* 行内的输入框不额外留下边距（间距由 .input-row 控制） */
.input-row .register-input {
  flex: 1;
  margin-bottom: 0;
  min-width: 0;
}

.register-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.register-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.35);
}

.register-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.code-btn {
  flex-shrink: 0;
  width: 116px;
  height: 44px;
  border: 1px solid #6366f1;
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.2);
  color: #c7d2fe;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.code-btn:hover:not(:disabled) {
  background: rgba(99, 102, 241, 0.35);
}

.code-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ok-tip {
  margin: -6px 0 14px;
  font-size: 13px;
  color: #4ade80;
}

.register-btn {
  width: 100%;
  height: 44px;
  margin-top: 6px;
  font-size: 16px;
  letter-spacing: 2px;
  color: #fff;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  cursor: pointer;
  transition: opacity 0.3s;
}

.register-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.register-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.register-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 20px;
}

.footer-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.footer-link {
  font-size: 13px;
  color: #818cf8;
  cursor: pointer;
}
</style>
