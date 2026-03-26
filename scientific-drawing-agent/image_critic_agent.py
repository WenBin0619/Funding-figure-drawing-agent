import base64
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from config import OPENAI_API_KEY, BASE_URL, PROMPT_MODEL
from state import ScientificDrawingState


IMAGE_CRITIC_SYSTEM_PROMPT = """你是一个专业的科研绘图质量审核专家。你的任务是评价生成的科研绘图质量，并在需要时提供修正后的提示词。

你需要检查以下几个方面：

1. **文字清晰度**：
   - 图中所有文字是否清晰可读
   - 字体大小是否合适
   - 是否存在文字重叠或模糊的情况

2. **格式规范检查**：
   - 是否符合浅灰蓝色细线描边的大圆角矩形模块框
   - 是否有浅蓝灰色标题栏，且标题栏与外框一体化连接
   - 除标题栏外，所有模块内容区域是否严格纯白填充
   - 是否存在浅灰底、浅蓝底、彩色底或渐变底（这些都是不允许的）

3. **布局合理性**：
   - 图片是否存在留白区域过多的问题
   - 各模块之间的间距是否合理
   - 整体布局是否平衡

4. **内容一致性**：
   - 图片内容能否和原始输入需要做图的内容对得上
   - 是否遗漏了重要的概念或流程
   - 是否存在与原始内容不符的地方

5. **逻辑清晰度**：
   - 若存在指向箭头，是否清晰明确
   - 是否存在指向冲突或逻辑混乱
   - 流程走向是否合理

请按照以下格式输出评价结果：

## 图片质量评价

### 评分（满分10分）
[给出一个0-10的评分]

### 发现的问题
[列出发现的所有问题，如果没有问题则写"无"]

### 改进建议
[列出具体的改进建议，特别是如何修改提示词来改进图片质量]

### 是否需要重新生成
[是/否]

### 修正后的提示词
[如果需要重新生成，请提供完整的修正后的提示词。如果不需要重新生成，则写"无需修正"]

注意：
- 如果评分低于7分，必须输出"是否需要重新生成：是"，并提供修正后的提示词
- 修正后的提示词应该直接可用，基于原始提示词进行改进，解决发现的问题
- 确保修正后的提示词仍然包含所有必要的格式要求（16:9比例、纯白背景、中文文字等）
- 文字规范：图中所有文字必须为中文，专有名词（如R-GCN、BLIP-2、LLM等模型名称和技术术语）可以保留英文"""


class ImageCriticAgent:
    def __init__(self):
        self.model = ChatOpenAI(
            model=PROMPT_MODEL,
            base_url=BASE_URL,
            api_key=OPENAI_API_KEY,
            temperature=0.1,
        )
    
    def __call__(self, state: ScientificDrawingState) -> dict:
        print("🖼️  [Image Critic Agent] 正在评价图片质量...")
        
        image_path = state.get("image_path", "")
        original_text = state.get("article_text", "")
        cleaned_prompt = state.get("cleaned_prompt", "")
        
        if not image_path:
            return {
                "image_quality_score": 0,
                "need_regenerate": True,
                "corrected_prompt": cleaned_prompt
            }
        
        try:
            image_base64 = self._encode_image(image_path)
            
            critic_message = f"""
原始输入内容：
{original_text}

使用的提示词：
{cleaned_prompt}

请评价这张生成的科研绘图的质量。

请从以下几个方面进行评价：
1. 文字是否清晰（专有名词如R-GCN、BLIP-2、LLM等可以保留英文，其他文字必须为中文）
2. 格式是否符合规范（浅灰蓝色细线描边、浅蓝灰色标题栏、纯白填充等）
3. 是否存在留白区域过多
4. 内容是否与原始输入对应
5. 指向是否清晰无冲突

请给出评分和改进建议。如果需要重新生成，请提供修正后的完整提示词。
"""
            
            response = self.model.invoke([
                SystemMessage(content=IMAGE_CRITIC_SYSTEM_PROMPT),
                HumanMessage(
                    content=[
                        {"type": "text", "text": critic_message},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                )
            ])
            
            critic_output = response.content
            if isinstance(critic_output, list):
                critic_output = "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in critic_output
                )
            
            score = self._extract_score(critic_output)
            need_regenerate = self._check_need_regenerate(critic_output, score)
            corrected_prompt = self._extract_corrected_prompt(critic_output, cleaned_prompt)
            
            if need_regenerate:
                print(f"⚠️  [Image Critic Agent] 图片质量评分: {score}/10，需要重新生成")
            else:
                print(f"✅ [Image Critic Agent] 图片质量评分: {score}/10，质量合格")
            
            return {
                "image_quality_score": score,
                "image_critic_feedback": critic_output,
                "need_regenerate": need_regenerate,
                "corrected_prompt": corrected_prompt
            }
            
        except Exception as e:
            print(f"❌ [Image Critic Agent] 图片评价失败: {str(e)}")
            return {
                "image_quality_score": 0,
                "need_regenerate": True,
                "corrected_prompt": cleaned_prompt
            }
    
    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _extract_score(self, critic_output: str) -> int:
        patterns = [
            r'评分（满分10分）\s*\n\s*(\d+(?:\.\d+)?)',
            r'评分.*?[:：]\s*(\d+(?:\.\d+)?)\s*(?:分|/10)?',
            r'(\d+(?:\.\d+)?)\s*[/／]\s*10',
            r'得分[:：]\s*(\d+(?:\.\d+)?)',
            r'分数[:：]\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*分',
        ]
        
        for pattern in patterns:
            score_match = re.search(pattern, critic_output)
            if score_match:
                score_str = score_match.group(1)
                score = int(float(score_str))
                if 0 <= score <= 10:
                    return score
        
        if "无" in critic_output and "问题" in critic_output:
            return 8
        
        if "是否需要重新生成：是" in critic_output or "是否需要重新生成: 是" in critic_output:
            return 6
        
        return 6
    
    def _check_need_regenerate(self, critic_output: str, score: int) -> bool:
        if score < 7:
            return True
        if "是否需要重新生成：是" in critic_output or "是否需要重新生成: 是" in critic_output:
            return True
        return False
    
    def _extract_corrected_prompt(self, critic_output: str, original_prompt: str) -> str:
        if "修正后的提示词" in critic_output:
            parts = critic_output.split("修正后的提示词")
            if len(parts) > 1:
                corrected = parts[1].strip()
                lines = corrected.split('\n')
                prompt_lines = []
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        prompt_lines.append(line)
                    elif line.startswith('#') and prompt_lines:
                        break
                
                corrected_text = '\n'.join(prompt_lines).strip()
                if corrected_text and corrected_text != "无需修正":
                    return corrected_text
        
        return original_prompt


def image_critic_node(state: ScientificDrawingState) -> dict:
    agent = ImageCriticAgent()
    return agent(state)
