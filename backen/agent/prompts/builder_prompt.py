import os
import yaml

class BuilderPrompt:
    @staticmethod
    def to_text(value)->str:
        # 字符串直接返回，列表用换行拼接
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return chr(10).join(str(i) for i in value)
        return str(value)

    @staticmethod
    def get_prompt(file_name: str) -> str:
        # 当前文件绝对路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        prompt = (
            f"一 角色:{BuilderPrompt.to_text(config['role'])}\n"
            f"二 任务:\n{BuilderPrompt.to_text(config['task'])}\n"
            f"三 规则:\n{BuilderPrompt.to_text(config['rule'])}\n"
            f"四 输出:\n{BuilderPrompt.to_text(config['output'])}\n"
            f"五 示例:\n{BuilderPrompt.to_text(config['example'])}\n"
        )
        return prompt.strip()

if __name__ == '__main__':
    print(BuilderPrompt.get_prompt("job/job_intent_node.yaml"))