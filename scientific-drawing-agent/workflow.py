from langgraph.graph import StateGraph, END
from state import ScientificDrawingState
from prompt_agent import prompt_generator_node
from reflection_agent import reflection_node
from image_agent import image_generator_node
from image_critic_agent import image_critic_node


MAX_RETRIES = 3


def check_for_errors(state: ScientificDrawingState) -> str:
    if state.get("error"):
        return "error"
    return "continue"


def check_need_regenerate(state: ScientificDrawingState) -> str:
    retry_count = state.get("retry_count", 0)
    need_regenerate = state.get("need_regenerate", False)
    
    if need_regenerate and retry_count < MAX_RETRIES:
        print(f"🔄 需要重新生成 (尝试 {retry_count + 1}/{MAX_RETRIES})")
        return "regenerate"
    return "end"


def error_handler_node(state: ScientificDrawingState) -> dict:
    print(f"⚠️  Error occurred: {state.get('error', 'Unknown error')}")
    return {}


def increment_retry_node(state: ScientificDrawingState) -> dict:
    retry_count = state.get("retry_count", 0)
    corrected_prompt = state.get("corrected_prompt", state.get("cleaned_prompt", ""))
    
    print(f"📝 使用修正后的提示词重新生成...")
    
    return {
        "retry_count": retry_count + 1,
        "cleaned_prompt": corrected_prompt
    }


def build_scientific_drawing_graph():
    builder = StateGraph(ScientificDrawingState)
    
    builder.add_node("prompt_generator", prompt_generator_node)
    builder.add_node("reflection", reflection_node)
    builder.add_node("image_generator", image_generator_node)
    builder.add_node("image_critic", image_critic_node)
    builder.add_node("error_handler", error_handler_node)
    builder.add_node("increment_retry", increment_retry_node)
    
    builder.set_entry_point("prompt_generator")
    
    builder.add_conditional_edges(
        "prompt_generator",
        check_for_errors,
        {
            "continue": "reflection",
            "error": "error_handler"
        }
    )
    
    builder.add_conditional_edges(
        "reflection",
        check_for_errors,
        {
            "continue": "image_generator",
            "error": "error_handler"
        }
    )
    
    builder.add_conditional_edges(
        "image_generator",
        check_for_errors,
        {
            "continue": "image_critic",
            "error": "error_handler"
        }
    )
    
    builder.add_conditional_edges(
        "image_critic",
        check_need_regenerate,
        {
            "regenerate": "increment_retry",
            "end": END
        }
    )
    
    builder.add_edge("increment_retry", "image_generator")
    builder.add_edge("error_handler", END)
    
    return builder.compile()


graph = build_scientific_drawing_graph()
