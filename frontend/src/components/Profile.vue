<template>
  <div class="profile-container">
    <div class="page-header">
      <button type="button" class="back-btn" @click="goChat">← 返回助手</button>
      <h2>完善个人信息</h2>
    </div>
    <form @submit.prevent="send">
      <!-- 基本信息 -->
      <h3>基本信息</h3>
      <div class="form-item">
        <label>姓名 <span class="required">*</span></label>
        <input v-model="student.name" type="text" placeholder="请输入姓名">
      </div>
      <div class="form-item">
        <label>性别</label>
        <select v-model="student.gender">
          <option value="">请选择</option>
          <option value="男">男</option>
          <option value="女">女</option>
        </select>
      </div>
      <div class="form-item">
        <label>电话</label>
        <input v-model="student.phone" type="text" placeholder="请输入电话">
      </div>
      <div class="form-item">
        <label>邮箱 <span class="required">*</span></label>
        <input v-model="student.email" type="email" placeholder="请输入邮箱" readonly>
      </div>

      <!-- 教育背景 -->
      <h3>教育背景</h3>
      <div class="form-item">
        <label>学校</label>
        <input v-model="student.school" type="text" placeholder="请输入学校">
      </div>
      <div class="form-item">
        <label>专业 <span class="required">*</span></label>
        <input v-model="student.major" type="text" placeholder="请输入专业">
      </div>
      <div class="form-item">
        <label>学历</label>
        <select v-model="student.education">
          <option value="">请选择</option>
          <option value="本科">本科</option>
          <option value="硕士">硕士</option>
          <option value="博士">博士</option>
          <option value="专科">专科</option>
        </select>
      </div>
      <div class="form-item">
        <label>年级 <span class="required">*</span></label>
        <select v-model="student.grade">
          <option value="">请选择</option>
          <option value="大一">大一</option>
          <option value="大二">大二</option>
          <option value="大三">大三</option>
          <option value="大四">大四</option>
          <option value="研一">研一</option>
          <option value="研二">研二</option>
          <option value="研三">研三</option>
        </select>
      </div>

      <!-- 求职意向 -->
      <h3>求职意向</h3>
      <div class="form-item">
        <label>目标城市</label>
        <input v-model="student.target_city" type="text" placeholder="请输入目标城市">
      </div>
      <div class="form-item">
        <label>目标岗位</label>
        <input v-model="student.target_job" type="text" placeholder="请输入目标岗位（可选）">
      </div>

      <!-- 简历上传 -->
      <h3>简历</h3>
      <div class="form-item" v-if="templates.length">
        <label>简历模板</label>
        <div class="template-list">
          <div v-for="t in templates" :key="t.label" class="template-item">
            <span class="tpl-name">📄 {{ t.label }}</span>
            <a
              v-if="t.preview_url"
              class="tpl-btn tpl-preview"
              :href="`${BASE_URL}${t.preview_url}`"
              target="_blank"
            >预览</a>
            <a
              class="tpl-btn tpl-download"
              :href="`${BASE_URL}${t.download_url}`"
              :download="t.download_name"
            >下载</a>
          </div>
        </div>
        <span class="hint-text">（不知道怎么写？先预览或下载模板参考）</span>
      </div>
      <div class="form-item">
        <label>上传简历</label>
        <input type="file" accept=".pdf,.docx" @change="uploadResume">
      </div>
      <p v-if="uploading" class="uploading-tip">简历解析中，请稍候...</p>

      <!-- 面试能力画像（面试评价后自动生成，只读） -->
      <h3>面试能力画像</h3>
      <div class="form-item ability-item">
        <p class="ability-text">{{ student.interview_ability || '暂无，完成一次模拟面试后自动生成' }}</p>
      </div>

      <!-- 技能与经历 -->
      <h3>技能与经历</h3>
      <div class="form-item">
        <label>技能</label>
        <input v-model="skillsInput" type="text" placeholder="多个技能用逗号分隔，如 Python,Java">
      </div>
      <div class="form-item">
        <label>证书</label>
        <input v-model="certificatesInput" type="text" placeholder="多个证书用逗号分隔">
      </div>
      <div class="form-item">
        <label>抗压能力</label>
        <input v-model="student.pressure_ability" type="text" placeholder="简单描述你的抗压能力">
      </div>
      <div class="form-item">
        <label>实习经历</label>
        <textarea v-model="internshipInput" rows="2" placeholder="多条经历用换行或逗号分隔"></textarea>
      </div>
      <div class="form-item">
        <label>项目经验</label>
        <textarea v-model="projectInput" rows="2" placeholder="多个项目用换行或逗号分隔"></textarea>
      </div>
      <div class="form-item">
        <label>校园经历</label>
        <textarea v-model="campusInput" rows="2" placeholder="多条经历用换行或逗号分隔"></textarea>
      </div>

      <!-- 错误提示 -->
      <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

      <!-- 发送按钮 -->
      <div class="btn-group">
        <button type="submit" class="submit-btn">保存信息</button>
        <button type="button" class="reset-btn" @click="reset">重置</button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, getCurrentInstance } from "vue";
import { useRouter } from "vue-router";

const { proxy } = getCurrentInstance();
const router = useRouter();

// 返回聊天助手页
function goChat() {
  router.push("/Chat");
}

const student = reactive({
  name: "",
  gender: "",
  phone: "",
  email: "",
  school: "",
  major: "",
  education: "",
  grade: "",
  target_city: "",
  target_job: "",
  pressure_ability: "",
  interview_ability: "",
});

// 用字符串输入，提交时再拆成数组（对应后端 jsonb 字段）
const skillsInput = ref("");
const certificatesInput = ref("");
const internshipInput = ref("");
const projectInput = ref("");
const campusInput = ref("");

const errorMsg = ref("");
const uploading = ref(false);

// 后端地址（模板下载链接需要拼完整地址）
const BASE_URL = "http://localhost:8080";

// 简历模板列表（由后端 /resume/templates 接口返回）
const templates = ref([]);

// 拉取可下载的简历模板（后端新增模板文件后自动出现在这里）
function fetchTemplates() {
  proxy.$axios({
    url: "resume/templates",
    method: "get",
  })
    .then((res) => {
      if (res.data.code === 200 && Array.isArray(res.data.data)) {
        templates.value = res.data.data;
      }
    })
    .catch((err) => {
      console.error("获取简历模板失败：", err);
    });
}

// 从 sessionStorage 取登录时的 email
const loginEmail = sessionStorage.getItem("email") || "";

// 把逗号/换行分隔的字符串拆成数组
function splitToArray(str) {
  if (!str) return [];
  return str
    .split(/[,，\n]/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

// 把数组拼回逗号分隔字符串（回填表单用）
function joinFromArray(arr) {
  if (!arr) return "";
  if (Array.isArray(arr)) return arr.join(",");
  return arr;
}

// 用查询结果回填表单（更新函数）
function fillForm(data) {
  if (!data) return;
  student.name = data.name || "";
  student.gender = data.gender || "";
  student.phone = data.phone || "";
  student.email = data.email || loginEmail;
  student.school = data.school || "";
  student.major = data.major || "";
  student.education = data.education || "";
  student.grade = data.grade || "";
  student.target_city = data.target_city || "";
  student.target_job = data.target_job || "";
  student.pressure_ability = data.pressure_ability || "";
  student.interview_ability = data.interview_ability || "";
  skillsInput.value = joinFromArray(data.skills);
  certificatesInput.value = joinFromArray(data.certificates);
  internshipInput.value = joinFromArray(data.internship);
  projectInput.value = joinFromArray(data.project_experience);
  campusInput.value = joinFromArray(data.campus_experience);
}

// 更新函数：按 email 查询并回填
function refreshProfile() {
  const email = loginEmail;
  if (!email) return;
  proxy.$axios({
    url: "profile/query",
    method: "get",
    params: { email },
  })
    .then((res) => {
      if (res.data.code === 200 && res.data.data) {
        fillForm(res.data.data);
      }
    })
    .catch((err) => {
      console.error("查询用户信息失败：", err);
    });
}

// 上传简历
async function uploadResume(e) {
  const file = e.target.files[0];
  if (!file) return;
  if (!loginEmail) {
    errorMsg.value = "未获取到登录邮箱，请先登录";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  uploading.value = true;
  try {
    const res = await proxy.$axios({
      url: "resume/upload",
      method: "post",
      params: { email: loginEmail },
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    });
    alert(res.data.msg);
    // 上传解析成功后，重新查询回填表单
    refreshProfile();
  } catch (err) {
    alert("上传失败：" + (err.response?.data?.msg || err.message));
  } finally {
    uploading.value = false;
    e.target.value = ""; // 清空文件选择，允许重复上传同一文件
  }
}

// 必填校验
function validate() {
  const required = [
    { field: "name", label: "姓名", value: student.name },
    { field: "email", label: "邮箱", value: student.email },
    { field: "major", label: "专业", value: student.major },
    { field: "grade", label: "年级", value: student.grade },
  ];
  for (const item of required) {
    if (!item.value || !item.value.trim()) {
      errorMsg.value = `请填写${item.label}`;
      return false;
    }
  }
  // 邮箱格式校验
  const emailReg = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailReg.test(student.email)) {
    errorMsg.value = "邮箱格式不正确";
    return false;
  }
  errorMsg.value = "";
  return true;
}

// 发送
function send() {
  if (!validate()) return;

  // 后端接口 /profile/profile 接收的是扁平的 StudentModel，
  // 不能包一层 { student: {...} }，否则 FastAPI 解析不到字段会返回 422。
  const payload = {
    ...student,
    skills: splitToArray(skillsInput.value),
    certificates: splitToArray(certificatesInput.value),
    internship: splitToArray(internshipInput.value),
    project_experience: splitToArray(projectInput.value),
    campus_experience: splitToArray(campusInput.value),
  };

  proxy.$axios({
    url: "profile/profile",
    method: "post",
    data: payload,
  })
    .then((res) => {
      alert(res.data.msg);
    })
    .catch((err) => {
      // FastAPI 校验失败返回 { detail: [...] }，没有 msg 字段
      const detail = err.response?.data?.detail;
      const msg = err.response?.data?.msg
        || (Array.isArray(detail) ? JSON.stringify(detail) : detail)
        || err.message;
      alert("提交失败：" + msg);
    });
}

// 重置
function reset() {
  Object.keys(student).forEach((k) => (student[k] = ""));
  skillsInput.value = "";
  certificatesInput.value = "";
  internshipInput.value = "";
  projectInput.value = "";
  campusInput.value = "";
  errorMsg.value = "";
}

// 页面加载时：初始化 email 并回填已有信息
onMounted(() => {
  student.email = loginEmail;
  refreshProfile();
  fetchTemplates();
});
</script>

<style scoped>
.profile-container {
  max-width: 600px;
  margin: 20px auto;
  padding: 24px;
  background: #fff;
  border: 1px solid #e5e4e7;
  border-radius: 12px;
}

.page-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.profile-container h2 {
  text-align: center;
  color: #08060d;
  margin: 0;
}

.back-btn {
  position: absolute;
  left: 0;
  padding: 6px 14px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  background: #fff;
  color: #555;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.back-btn:hover {
  border-color: #4a90d9;
  color: #4a90d9;
}

h3 {
  margin: 20px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0f0f0;
  color: #333;
  font-size: 16px;
}

.form-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.form-item label {
  width: 100px;
  flex-shrink: 0;
  text-align: right;
  margin-right: 12px;
  font-size: 14px;
  color: #555;
}

.required {
  color: #f56c6c;
  margin-left: 2px;
}

.form-item input,
.form-item select,
.form-item textarea {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}

.form-item input:focus,
.form-item select:focus,
.form-item textarea:focus {
  border-color: #4a90d9;
}

.template-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px dashed #cfd8e3;
  border-radius: 8px;
  background: #fafcff;
}

.tpl-name {
  flex: 1;
  font-size: 14px;
  color: #444;
}

.tpl-btn {
  flex-shrink: 0;
  padding: 5px 14px;
  border-radius: 6px;
  font-size: 13px;
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
  cursor: pointer;
}

.tpl-preview {
  border: 1px solid #4a90d9;
  background: #fff;
  color: #4a90d9;
}

.tpl-preview:hover {
  background: #eef6ff;
}

.tpl-download {
  border: 1px solid #4a90d9;
  background: #4a90d9;
  color: #fff;
}

.tpl-download:hover {
  background: #3a7bc0;
  border-color: #3a7bc0;
}

.hint-text {
  margin-left: 10px;
  color: #a0a6b1;
  font-size: 12px;
}

.ability-item {
  align-items: flex-start;
}

.ability-text {
  flex: 1;
  margin: 0;
  padding: 12px 14px;
  background: #fafcff;
  border: 1px dashed #cfd8e3;
  border-radius: 8px;
  color: #555;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.error-msg {
  color: #f56c6c;
  text-align: center;
  margin: 12px 0;
  font-size: 14px;
}

.uploading-tip {
  color: #4a90d9;
  text-align: center;
  margin: 8px 0;
  font-size: 14px;
}

.btn-group {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
}

.submit-btn,
.reset-btn {
  padding: 10px 28px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
}

.submit-btn {
  background: #4a90d9;
  color: #fff;
}

.submit-btn:hover {
  background: #3a7bc0;
}

.reset-btn {
  background: #f0f0f0;
  color: #555;
}

.reset-btn:hover {
  background: #e0e0e0;
}
</style>
