import base64
import re
import os
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from config import OPENAI_API_KEY, BASE_URL, IMAGE_MODEL
from state import ScientificDrawingState


class ImageGeneratorAgent:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.model = ChatOpenAI(
            model=IMAGE_MODEL,
            base_url=BASE_URL,
            api_key=OPENAI_API_KEY,
            temperature=1.0
        )
    
    def _save_base64_image(self, markdown_content: str) -> str:
        match = re.search(r'!\[.*?\]\(data:image/(png|jpeg);base64,(.*?)\)', markdown_content)
        if match:
            image_format = match.group(1)
            base64_data = match.group(2)
            image_data = base64.b64decode(base64_data)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scientific_drawing_{timestamp}.{image_format}"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(image_data)
            
            return filepath
        return None
    
    def __call__(self, state: ScientificDrawingState) -> dict:
        print("🖼️  [Image Agent] 正在生成科研绘图...")
        
        try:
            prompt = state.get("cleaned_prompt", state.get("generated_prompt", ""))
            
            if not prompt:
                return {"error": "No prompt available for image generation"}
            
            response = self.model.invoke([HumanMessage(content=prompt)])
            
            content = response.content
            if isinstance(content, list):
                content = "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in content
                )
            
            image_path = self._save_base64_image(content)
            
            if image_path:
                print(f"✅ [Image Agent] 图片已保存至: {image_path}")
                return {"image_path": image_path}
            else:
                print("❌ [Image Agent] 未找到有效的图片数据")
                return {"error": "No valid image data found in response"}
                
        except Exception as e:
            print(f"❌ [Image Agent] 图片生成失败: {str(e)}")
            return {"error": f"Image generation failed: {str(e)}"}


def image_generator_node(state: ScientificDrawingState) -> dict:
    agent = ImageGeneratorAgent()
    return agent(state)
