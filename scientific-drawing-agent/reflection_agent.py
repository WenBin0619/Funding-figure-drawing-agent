from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from config import OPENAI_API_KEY, BASE_URL, PROMPT_MODEL
from state import ScientificDrawingState


CRITIC_SYSTEM_PROMPT = """你是一个专业的科研绘图提示词审核专家。你的任务是审核和改进生成的绘图提示词。

你需要检查以下几个方面：

1. **内容完整性检查**：
   - 核对原始输入内容，确保生成的提示词没有遗漏重要信息
   - 检查是否存在与原始内容冲突的地方
   - 确保所有关键概念、流程和机制都被准确表达

2. **格式规范检查（必须严格遵守）**：
   - **文字规范**：图中所有文字必须为中文，且只保留关键词。专有名词（如R-GCN、BLIP-2、LLM等模型名称和技术术语）可以保留英文，其他描述性文字必须为中文
   - **背景颜色**：除标题栏外，所有模块内容区域必须严格纯白填充（#FFFFFF）
   - **禁止项**：绝对不允许出现浅灰底、浅蓝底、彩色底或渐变底
   - 必须包含"比例为16:9"或类似表述
   - 必须包含"BioRender风格"相关描述
   - 必须包含"卡片式边框"、"浅蓝灰色标题栏"等格式要求
   - 必须强调"纯白填充"、"无渐变"、"无阴影"

3. **风格一致性检查**：
   - 确保整体风格符合BioRender扁平化科研风格
   - 检查配色方案是否合理
   - 标题栏可以使用浅蓝灰色，但内容区域必须是纯白色

**重要提醒**：
- 如果提示词中出现非专有名词的英文描述或英文标签，必须修正为中文
- 专有名词（如模型名称、技术术语等）可以保留英文，如R-GCN、BLIP-2、LLM、Top-T等
- 如果提示词中允许或暗示了非纯白背景，必须明确修正为"严格纯白填充"
- 如果提示词中出现了渐变、阴影等效果，必须删除这些描述

请按照以下格式输出审核结果：

## 审核结果

### 发现的问题
[列出发现的所有问题，如果没有问题则写"无"]

### 改进建议
[列出具体的改进建议]

### 修正后的完整提示词
[输出经过修正的完整提示词，确保包含所有必要的格式要求和内容]

注意：修正后的提示词应该直接可用，不需要额外的解释。"""


class CriticAgent:
    def __init__(self):
        self.model = ChatOpenAI(
            model=PROMPT_MODEL,
            base_url=BASE_URL,
            api_key=OPENAI_API_KEY,
            temperature=0.1,
        )
    
    def __call__(self, state: ScientificDrawingState) -> dict:
        print("🔍 [Critic Agent] 正在审核和优化提示词...")
        
        original_text = state.get("article_text", "")
        generated_prompt = state.get("generated_prompt", "")
        
        if not generated_prompt:
            return {"cleaned_prompt": "", "error": "No prompt to review"}
        
        try:
            critic_message = f"""
原始输入内容：
{original_text}

生成的提示词：
{generated_prompt}

请严格审核这个提示词，特别注意以下几点：
1. **文字必须全部为中文**（专有名词如R-GCN、BLIP-2、LLM等模型名称可以保留英文）
2. **内容区域必须纯白**：除标题栏外，所有模块内容区域必须严格纯白填充，不允许任何其他颜色或渐变
3. **禁止效果**：不允许渐变、阴影等效果
4. 内容完整，没有遗漏原始输入的重要信息
5. 包含所有必要的格式要求（16:9比例、BioRender风格等）

请输出审核结果和修正后的提示词。
"""
            
            response = self.model.invoke([
                SystemMessage(content=CRITIC_SYSTEM_PROMPT),
                HumanMessage(content=critic_message)
            ])
            
            critic_output = response.content
            if isinstance(critic_output, list):
                critic_output = "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in critic_output
                )
            
            cleaned_prompt = self._extract_corrected_prompt(critic_output)
            
            if not cleaned_prompt:
                cleaned_prompt = self._basic_clean(generated_prompt)
            
            print("✅ [Critic Agent] 提示词审核和优化完成")
            
            return {
                "cleaned_prompt": cleaned_prompt,
                "critic_feedback": critic_output
            }
            
        except Exception as e:
            print(f"⚠️  [Critic Agent] LLM审核失败，使用基础清理: {str(e)}")
            cleaned_prompt = self._basic_clean(generated_prompt)
            return {"cleaned_prompt": cleaned_prompt}
    
    def _extract_corrected_prompt(self, critic_output: str) -> str:
        if "修正后的完整提示词" in critic_output:
            parts = critic_output.split("修正后的完整提示词")
            if len(parts) > 1:
                corrected = parts[1].strip()
                lines = corrected.split('\n')
                prompt_lines = []
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        prompt_lines.append(line)
                    elif line.startswith('#') and prompt_lines:
                        break
                
                return '\n'.join(prompt_lines).strip()
        
        return ""
    
    def _basic_clean(self, content: str) -> str:
        content = content.strip()
        lines = content.split('\n')
        start_idx = -1
        end_idx = -1
        
        for i, line in enumerate(lines):
            if line.strip() == '---':
                start_idx = i + 1
                break
        
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == '---':
                end_idx = i
                break
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            filtered_lines = lines[start_idx:end_idx]
            while filtered_lines and not filtered_lines[0].strip():
                filtered_lines.pop(0)
            while filtered_lines and not filtered_lines[-1].strip():
                filtered_lines.pop()
            cleaned_content = '\n'.join(filtered_lines)
        else:
            cleaned_content = content
        
        return cleaned_content


def reflection_node(state: ScientificDrawingState) -> dict:
    agent = CriticAgent()
    return agent(state)
