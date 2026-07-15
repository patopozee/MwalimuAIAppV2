import json
import os
import re
import streamlit as st

@st.cache_resource(show_spinner=False)
def load_cached_json_file(file_path):
    """
    Reads data assets from disc exactly once and keeps them in server RAM
    across all concurrent active user sessions.
    """
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Knowledge Layer Error] Failed parsing {file_path}: {e}")
            return {}
    return {}

class MwalimuKnowledgeLayer:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.curriculum_path = os.path.join(data_dir, "curriculum_knowledge.json")
        self.past_papers_path = os.path.join(data_dir, "past_papers.json")
        
        # Pulling files directly out of global cached RAM instead of reading from hard disk
        self.curriculum_data = load_cached_json_file(self.curriculum_path)
        self.past_papers_data = load_cached_json_file(self.past_papers_path)

    def get_curriculum_context(self, subject, topic, sub_topic):
        """
        Extracts verified definitions, objectives, and flawless worked examples 
        matching the specific structural target layer. Returns empty structures safely if not found.
        """
        # Case-insensitive safe navigation helper
        def find_case_insensitive(dictionary, target_key):
            if not dictionary or not isinstance(dictionary, dict):
                return None
            for key in dictionary.keys():
                if key.strip().lower() == str(target_key).strip().lower():
                    return dictionary[key]
            return None

        subj_node = find_case_insensitive(self.curriculum_data, subject)
        topic_node = find_case_insensitive(subj_node, topic)
        sub_topic_node = find_case_insensitive(topic_node, sub_topic)

        if sub_topic_node:
            return {
                "definition": sub_topic_node.get("definition", "Standard KICD CBC learning parameters apply."),
                "learning_objectives": sub_topic_node.get("learning_objectives", []),
                "worked_examples": sub_topic_node.get("worked_examples", [])
            }
        return {
            "definition": "Standard KICD CBC learning parameters apply.",
            "learning_objectives": ["Understand core concepts related to the active syllabus topic."],
            "worked_examples": []
        }

    def get_past_papers_context(self, subject, topic):
        """Pulls a list of verified past paper problems to anchor LLM logic foundations."""
        if not self.past_papers_data:
            return []
        for subj_key, topics in self.past_papers_data.items():
            if subj_key.strip().lower() == str(subject).strip().lower():
                if isinstance(topics, dict):
                    for t_key, items in topics.items():
                        if t_key.strip().lower() == str(topic).strip().lower():
                            return items
        return []

    def get_flashcards_context(self, subject, topic, sub_topic):
        """Pulls pre-verified flashcard baselines for grounding vocabulary."""
        node = self.get_curriculum_context(subject, topic, sub_topic)
        return self.curriculum_data.get(subject, {}).get(topic, {}).get(sub_topic, {}).get("flashcard_deck", [])

    def get_study_milestones(self, subject, topic, sub_topic):
        """Extracts timeline blocks for the custom study planner."""
        return self.curriculum_data.get(subject, {}).get(topic, {}).get(sub_topic, {}).get("study_plan_milestones", {})

# ==========================================
# 1. STANDALONE PRODUCTION UTILITY FUNCTION
# ==========================================
def clean_and_parse_json(raw_text):
    """Production fallback utility to extract and repair broken JSON fragments."""
    if raw_text is None:
        return []
    match = re.search(r'\[.*\]', raw_text, re.DOTALL)
    if match:
        clean_str = match.group(0)
    else:
        clean_str = raw_text.strip()
    try:
        return json.loads(clean_str)
    except json.JSONDecodeError:
        clean_str = re.sub(r',\s*([\]}])', r'\1', clean_str)
        try:
            return json.loads(clean_str)
        except Exception:
            raise Exception("Unrepairable JSON structure returned from endpoint.")
