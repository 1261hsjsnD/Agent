from langchain_openai import ChatOpenAI
from dotenv import  load_dotenv
import os
from vosk import Model
load_dotenv()

# 内部 LLM 调用标记：节点里那些「只用于逻辑判断、不该让用户看到」的调用
INTERNAL_TAG = "internal_llm"

"""
基于单例模式的模型封装
"""
class MyModel:
    #定义私有属性
    _model = None
    #定义本地模型私有属性
    _local_model=None
    _vosk_model=None
    #定义静态函数，在线模型
    @staticmethod
    def get_model():
        #判断模型是否已经实例化
        if MyModel._model is None:
            #实例化模型
            MyModel._model = ChatOpenAI(
                model=os.getenv("MODEL_LINE_NAME"),
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url=os.getenv("OPENAI_API_BASE"),
                streaming=True,
            )
        return MyModel._model
    #定义静态函数，本地模型
    @staticmethod
    def get_local_model():
        #判断模型是否已经实例化
        if MyModel._local_model is None:
            #实例化模型
            MyModel._local_model = ChatOpenAI(
                model=os.getenv("OLLAMA_MODEL_NAME"),
                api_key="aaa",
                base_url=os.getenv("OLLAMA_BASE_URL"),
                streaming=True,
            )
        return MyModel._local_model

    @staticmethod
    def get_vosk_model():
        if MyModel._vosk_model is None:
            model_path = os.getenv("VOSK_PATH")
            MyModel._vosk_model = Model(model_path=model_path)
        return MyModel._vosk_model
