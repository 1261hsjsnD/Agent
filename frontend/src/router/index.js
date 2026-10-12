//引入路由配置文件
import {createRouter, createWebHistory} from "vue-router";

//定义路由配置对象
const routes = [
    {
        // 默认首页 -> 登录页
        path: "/",
        redirect: "/Login"
    },
    {
        path: "/Profile",
        component: () => import("../components/Profile.vue")
    },
    {
        path: "/Login",
        component: () => import("../components/Login.vue")
    },
    {
        path: "/Register",
        component: () => import("../components/Register.vue")
    },
    {
        path: "/Chat",
        component: () => import("../components/Chat.vue")
    },
]

//设置路由模式为history模式----默认hash模型，访问路径中有一个#号
const router = createRouter({
    history: createWebHistory(),
    routes
})
//导出路由实例
export default router
