import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

// 创建应用并挂载
const app = createApp(App)
//注册路由对象
import router from "./router"
app.use(router)
//最后挂载
app.mount('#app')

// axios 全局配置
import axios from 'axios'   // 导入axios包
axios.defaults.baseURL = 'http://localhost:8080/' // 服务器请求路径公共部分
axios.defaults.headers.post['Content-Type'] = 'application/json' // post请求发送json数据给服务器
axios.defaults.headers.put['Content-Type'] = 'application/json' // put请求发送json数据给服务器
app.config.globalProperties.$axios = axios // 挂载axios，使用对象.$axios替代原生的axios