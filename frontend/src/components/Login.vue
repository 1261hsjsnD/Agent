<template>
  <div class="login-page">
    <!-- 背景装饰光斑 -->
    <div class="deco deco-1"></div>
    <div class="deco deco-2"></div>
    <div class="deco deco-3"></div>

    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">AI</div>
        <h1 class="login-title">欢迎回来</h1>
        <p class="login-subtitle">登录后开启你的职业规划之旅</p>
      </div>

      <form class="login-form" @submit.prevent="Login">
        <input
          v-model="email"
          type="email"
          placeholder="请输入邮箱号"
          class="login-input"
        >
        <input
          v-model="password"
          type="password"
          placeholder="请输入密码"
          class="login-input"
        >

        <button type="submit" class="login-btn">登 录</button>

        <div class="login-footer">
          <span class="footer-text">还没有账号？</span>
          <a class="footer-link" @click="register">立即注册</a>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, getCurrentInstance } from "vue";
import { useRouter } from "vue-router";

const { proxy } = getCurrentInstance();
const router = useRouter();

const email = ref("");
const password = ref("");

// 登录验证账号密码函数
function Login() {
  proxy.$axios({
    url: "login/login",
    method: "post",
    data: {
      email: email.value,
      password: password.value,
    },
  }).then((res) => {
    let code = res.data.code;
    let msg = res.data.msg;
    let name = res.data.name;
    let userId = res.data.user_id;

    if (code === 200) {
      alert(msg);
      // 换用户必须换会话，否则会读到上一位用户的窗口记忆；
      // 同时清掉本地会话列表缓存，避免看到上一个账号的历史对话
      sessionStorage.removeItem("session_id");
      sessionStorage.removeItem("chat_sessions");
      sessionStorage.removeItem("chat_current_sid");
      sessionStorage.removeItem("chat_messages_cache");
      sessionStorage.setItem("name", name);
      sessionStorage.setItem("email", email.value);
      if (userId) sessionStorage.setItem("user_id", String(userId));
      setTimeout(() => {
        router.push("/Chat");
      }, 500);
    } else {
      alert(msg);
    }
  }).catch((err) => {
    alert("登录失败：" + (err.response?.data?.msg || err.message));
  });
}

function register() {
  router.push("/Register");
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  font-family: system-ui, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 45%, #312e81 100%);
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
  background: #6366f1;
  top: -120px;
  left: -140px;
}
.deco-2 {
  width: 340px;
  height: 340px;
  background: #22d3ee;
  bottom: -100px;
  right: -120px;
  animation-delay: 2s;
}
.deco-3 {
  width: 200px;
  height: 200px;
  background: #ec4899;
  top: 55%;
  left: 12%;
  opacity: 0.25;
  animation-delay: 4s;
}
@keyframes float {
  0%, 100% { transform: translateY(0) translateX(0); }
  50% { transform: translateY(-24px) translateX(14px); }
}

/* ============ 登录卡片 ============ */
.login-card {
  position: relative;
  z-index: 1;
  width: 400px;
  padding: 44px 40px 32px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 20px;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
  box-sizing: border-box;
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-logo {
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
  background: linear-gradient(135deg, #6366f1, #22d3ee);
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
}

.login-title {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  color: #fff;
}

.login-subtitle {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.65);
}

/* ============ 表单 ============ */
.login-form {
  display: flex;
  flex-direction: column;
}

.login-input {
  margin-bottom: 18px;
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

.login-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.login-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.35);
}

.login-btn {
  width: 100%;
  margin-top: 6px;
  height: 44px;
  font-size: 16px;
  letter-spacing: 4px;
  color: #fff;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  cursor: pointer;
  transition: opacity 0.3s;
}

.login-btn:hover {
  opacity: 0.9;
}

.login-footer {
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
