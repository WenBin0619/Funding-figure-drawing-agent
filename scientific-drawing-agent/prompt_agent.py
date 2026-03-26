import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from config import OPENAI_API_KEY, BASE_URL, PROMPT_MODEL, SYSTEM_PROMPT
from state import ScientificDrawingState


class PromptGeneratorAgent:
    def __init__(self):
        self.model = ChatOpenAI(
            model=PROMPT_MODEL,
            base_url=BASE_URL,
            api_key=OPENAI_API_KEY,
            temperature=0.3,
        )
    
    def __call__(self, state: ScientificDrawingState) -> dict:
        print("🎨 [Prompt Agent] 正在生成BioRender绘图提示词...")
        
        try:
            response = self.model.invoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=state["article_text"])
            ])
            
            content = response.content
            if isinstance(content, list):
                content = "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in content
                )
            else:
                content = str(content)
            
            print("✅ [Prompt Agent] 提示词生成完成")
            return {"generated_prompt": content}
            
        except Exception as e:
            print(f"❌ [Prompt Agent] 生成失败: {str(e)}")
            return {"error": f"Prompt generation failed: {str(e)}"}


def prompt_generator_node(state: ScientificDrawingState) -> dict:
    agent = PromptGeneratorAgent()
    return agent(state)
