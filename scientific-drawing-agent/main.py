import os
import sys
from dotenv import load_dotenv
from workflow import graph
from state import ScientificDrawingState
from word_reader import read_word_document

load_dotenv()


def run_scientific_drawing_agent(article_text: str, input_source: str = "text") -> dict:
    print("=" * 60)
    print("🚀 科研绘图Agent启动")
    print("=" * 60)
    
    initial_state: ScientificDrawingState = {
        "article_text": article_text,
        "generated_prompt": "",
        "cleaned_prompt": "",
        "corrected_prompt": "",
        "critic_feedback": None,
        "image_path": "",
        "image_quality_score": 0,
        "image_critic_feedback": None,
        "need_regenerate": False,
        "retry_count": 0,
        "error": None
    }
    
    result = graph.invoke(initial_state)
    
    print("\n" + "=" * 60)
    print("📊 任务完成")
    print("=" * 60)
    
    if result.get("image_path"):
        print(f"✅ 图片已保存: {result['image_path']}")
        print(f"📊 图片质量评分: {result.get('image_quality_score', 0)}/10")
        print(f"🔄 重试次数: {result.get('retry_count', 0)}")
    else:
        print("❌ 图片生成失败")
    
    if result.get("critic_feedback"):
        print("\n🔍 Prompt Critic反馈:")
        print(result["critic_feedback"])
    
    if result.get("image_critic_feedback"):
        print("\n🖼️  Image Critic反馈:")
        print(result["image_critic_feedback"])
    
    return result


if __name__ == "__main__":
    article_text = ""
    input_source = "text"
    
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        if input_path.endswith('.docx') or input_path.endswith('.doc'):
            print(f"📄 从 Word 文档读取: {input_path}")
            article_text = read_word_document(input_path)
            input_source = "word"
        else:
            with open(input_path, 'r', encoding='utf-8') as f:
                article_text = f.read()
            input_source = "file"
    else:
        default_word_path = "input/b.docx"
        if os.path.exists(default_word_path):
            print(f"📄 从默认 Word 文档读取: {default_word_path}")
            article_text = read_word_document(default_word_path)
            input_source = "word"
        else:
            print("📝 使用示例文本")
            article_text = """
请基于以下研究内容生成绘图 prompt

b）多源异构知识的冲突消解与推理检索
在 a）实现时变事实驱动的动态图谱构建与检索基础上，进一步考虑多源异构知识并存条件下的冲突与不一致问题，拟设计适用于知识动态更新场景的多源异构知识图谱检索增强方法，以缓解多源数据冲突导致的检索支撑不一致。首先，从外部非结构化或半结构化的多源数据中抽取结构化知识，形成不同模态或来源对应的初始知识图谱；在实现上，可参考现有多源信息抽取方法（如 R-GCN [Zhao et al., MM-22]等）完成多源结构化知识抽取。
进一步，结合现有多源信息对齐与融合方法（如BLIP-2 [Li et al., ICML-23]等），对多源异构知识进行多粒度语义对齐与统一表征，构建带有时变信息且可动态更新的多源异构知识图谱。然后，面向用户查询设计融合多源信息的推理检索机制，在所构建的多源异构知识图谱中检索与查询相关的 Top-T 条三元组，可表示为
Tretrievalm=Top(RetrievermQuery,Gm,tq,T)，
其中， Gm 表示多源异构知识图谱，Retrieverm 表示多源知识检索器，tq 表示查询中的时间信息；若查询未显式给出时间，则采用当前时间；T 为超参数。
随后，结合用户查询给定的时间信息、检索三元组及其附属多源内容的时间戳，判断其中所包含知识是否过时；若存在过时知识，则触发对应三元组、附属多源信息及图谱的更新机制，并在更新过程中维持多源知识之间的一致性与可解释性。
最后，将用户查询与检索得到的多源内容按照预设提示模板共同输入大模型，辅助其生成回答，从而缓解由多源冲突、不一致与错配引发的跨源拼接幻觉，提升大模型在多源异构知识场景下回答的可靠性
"""
    
    result = run_scientific_drawing_agent(article_text, input_source)
    
    print("\n📝 最终结果:")
    print(f"图片路径: {result.get('image_path', 'N/A')}")
    if result.get('error'):
        print(f"错误信息: {result['error']}")
