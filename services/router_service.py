import re
from typing import Dict, Any, Optional

class RouterService:
    GREETING_PATTERN = re.compile(
        r"^(hi|hello|hey|jambo|habari|mambo|good morning|good evening|good afternoon|test|ping)[\s!.]*$", 
        re.IGNORECASE
    )

    @classmethod
    def route_query(
        cls, 
        question: str, 
        attachment: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        clean_q = question.strip().lower()

        # Rule 1: Visual / Multimodal Route
        if attachment is not None:
            return {
                "model_name": "gemini-3.6-flash",
                "mode": "VISION",
                "enable_thinking": False,
                "reason": "Attachment detected: image/file vision processing required."
            }

        # Rule 2: Ultra-Fast Greeting / Simple Query Route
        if cls.GREETING_PATTERN.match(clean_q) or len(clean_q.split()) <= 2:
            return {
                "model_name": "gemini-3.6-flash",
                "mode": "FAST",
                "enable_thinking": False,
                "reason": "Short conversational trigger detected."
            }

        # Rule 3: Deep Thinking / Reasoning Route Triggers
        thinking_keywords = [
            "calculate", "solve", "step by step", "explain why", 
            "debug", "proof", "derivation", "compare and contrast",
            "hesabu", "eleza kwa kina", "thibitisha"
        ]
        
        is_complex = any(kw in clean_q for kw in thinking_keywords) or len(clean_q.split()) > 40

        if is_complex:
            return {
                "model_name": "gemini-3.6-flash",  # Or gemini-3.1-pro if enabled on your plan
                "mode": "THINKING",
                "enable_thinking": True,
                "reason": "Complex problem or multi-step reasoning prompt detected."
            }

        # Default Fallback Route
        return {
            "model_name": "gemini-3.6-flash",
            "mode": "STANDARD",
            "enable_thinking": False,
            "reason": "Standard instructional prompt."
        }