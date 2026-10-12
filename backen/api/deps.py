from fastapi import Request


def get_graph(request: Request):
    """从 app.state 取出已初始化的 Graph 实例。

    实例在 main.py 的 lifespan 中创建并挂到 app.state.graph，
    路由通过依赖调用本函数获取，避免每次请求都新建智能体。
    """
    return request.app.state.graph
