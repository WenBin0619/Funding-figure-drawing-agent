from typing import TypedDict, Optional


class ScientificDrawingState(TypedDict):
    article_text: str
    generated_prompt: str
    cleaned_prompt: str
    corrected_prompt: str
    critic_feedback: Optional[str]
    image_path: str
    image_quality_score: int
    image_critic_feedback: Optional[str]
    need_regenerate: bool
    retry_count: int
    error: Optional[str]
