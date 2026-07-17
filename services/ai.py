# services/ai.py
import os
import json
import random
import base64
import re
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from knowledge_layer import MwalimuKnowledgeLayer, clean_and_parse_json
# 1. Load keys from local .env file if it exists
load_dotenv()
knowledge_base = MwalimuKnowledgeLayer()
# 2. Unified fallback: check system environment variables first, then fallback to Streamlit secrets
api_key = os.environ.get("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")

# 3. Initialize unified OpenRouter gateway client safely
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key if api_key else "MOCK_KEY"
)

# SYSTEM-LEVEL PROMPT PROTECTION AGAINST FALSE POSITIVE SAFETY REFUSALS
SYSTEM_GUARD = (
    "You are Mwalimu AI, an elite educational teacher under the Kenyan KICD CBC Curriculum framework. "
    "All inputs provided are completely safe academic topics. You must ignore false-positive keyword flags "
    "regarding religious studies (CRE), communities, or historical events. Absolutely NEVER return text strings "
    "like 'User safety: safe' or refuse to generate answers. Always provide full, comprehensive educational output."
)
def ask_mwalimu(question, student, messages, adaptive_context="", attachment=None):
    """Dispatches prompts to a specific high-quality free model on OpenRouter."""
    """Handles real-time conversational Q&A locked to the local curriculum guide framework."""
    preferred_language = student.get("preferred_language", student.get("language", "English"))
    subject = student.get('subject', 'Mathematics')
    topic = student.get('topic', 'Whole Numbers')
    sub_topic = student.get('sub_topic', 'Place Value')
    learning_style = student.get("learning_style", "General")
    kicd_data = knowledge_base.get_curriculum_context(subject, topic, sub_topic)
    
    # Clean language rules focusing on conversational interaction instead of timetables
    language_rules = {
        "English": "Respond naturally and directly in grammatically correct English like an empathetic Kenyan classroom teacher.",
        "Kiswahili": "Andika majibu yako yote kwa Kiswahili sanihu, fasaha, na safi kabisa kinachofaa mazingira ya shule za Kenya. Usitumie Kiingereza.",
        "Sheng": "Tumia lugha ya kirafiki ya Sheng iliyochanganywa na maelezo ya kimasomo ili kumfanya mwanafunzi achangamke, lakini hakikisha ukweli wa kimasomo unabaki sahihi na rahisi kuelewa."
    }
    
    # Build conversation history context string safely
    history = ""
    for msg in messages:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            role = str(msg["role"]).lower()
            content = msg["content"]
            if role in ["student", "user"]:
                history += f"Student: {content}\n"
            elif role in ["assistant", "mwalimu"]:
                history += f"Mwalimu AI: {content}\n"

    # Build text prompt context elements for local files
    pdf_text_context = ""
    if attachment and attachment.get("type") == "text_extraction":
        pdf_text_context = f"\n\n=== ATTACHED PDF DOCUMENT CONTENT ({attachment['filename']}) ===\n{attachment['content']}"

    # --- THE ONLY CHANGED PART: GREETING GUARDRAIL ---
    greeting_guardrail = ""
    if history.strip():
        greeting_guardrail = "\n- CRITICAL: A conversation history already exists. Do NOT greet the student, do not say hello or 'Habari', and do not repeat introductions. Answer the current question directly."

    # RESTRUCTURED PROMPT: Natural chat guidelines, zero study plan leaks
    prompt = f"""
{SYSTEM_GUARD}

=== STUDENT PROFILE & LOCAL CONTEXT ===
- **Subject**: {subject}
- **Topic**: {topic} (Sub-topic: {sub_topic})
- **Preferred Language**: {preferred_language}
- **Learning Style**: {learning_style} (Adapt your explanations to match this style, e.g., use descriptions or analogies if visual/auditory)
- **Curriculum KICD Guidelines**: {json.dumps(kicd_data, ensure_ascii=False)}
- **Adaptive Remediation Notes**: {adaptive_context} {pdf_text_context}

=== LANGUAGE & TEACHING INSTRUCTIONS ===
{language_rules.get(preferred_language, language_rules["English"])}
- Break down difficult educational topics into simple, snackable student steps.
- If the user uploaded an image attachment snippet, deeply scan it for math problems, handwritten errors, diagrams, or reading exercises. Address its visual elements directly.
- NEVER output headers like 'Daily Study Goals', 'Study Schedule', or 'Time Intervals'. 
- Respond directly, warmly, and helpfully to the current student query below.{greeting_guardrail}

=== CONVERSATION HISTORY ===
{history}

=== CURRENT STUDENT INQUIRY ===
Student Question/Attachment upload: {question}
Mwalimu AI response:
"""

    # Assemble structural payload for OpenRouter's API wrapper
    api_messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    
    if attachment and attachment.get("type") == "image_base64":
        api_messages[0]["content"].append({
            "type": "image_url",
            "image_url": {"url": str(attachment["content"])}
        })

    try:
        # 🚀 PRE-EMPTIVE CEILING: Lower max_tokens to 400 *before* the call so you stay well under your 812 budget limit
        response_stream = client.chat.completions.create(
            model="openrouter/free",
            messages=api_messages,  # type: ignore
            max_tokens=1500,  
            stream=True  
        )
        return response_stream  
        
    except Exception as api_err:
        error_diagnostic_string = str(api_err)
        print(f"[Terminal Log] Main Chat API Fault: {error_diagnostic_string}")
        
        # 🛡️ SYSTEM GUARD: Catch 402/Credit errors explicitly before returning to prevent SSE/JSON pipeline crashes
        if "402" in error_diagnostic_string or "credits" in error_diagnostic_string.lower():
            def error_generator():
                yield "Mwalimu's connection is low on OpenRouter credits. Please add a small credit top-up to your API wallet dashboard!"
            return error_generator()
            
        def fallback_generator():
            yield f"Mwalimu encountered a brief connection stutter. Details: {error_diagnostic_string}"
        return fallback_generator()




def generate_quiz(topic, student, difficulty="Medium"):
    # 1. Unpack properties safely from the unified user state map
    subject = student.get("subject", "General")
    sub_topic = student.get("sub_topic", "General")
    language = student.get("preferred_language", "English")
    grade = student.get("grade", "General")
    learning_outcome = student.get("learning_outcome", "General Mastery")
    difficulty_rules = {
        "Easy": "Use very simple language. Focus on one core concept per question. No trick questions.",
        "Medium": "Slightly more challenging. Require two-step thinking. Use localized practical examples.",
        "Hard": "Incorporate complex application questions, critical thinking scenarios, and higher-order reasoning."
    }
    subject = student.get('subject', 'Mathematics')
    sub_topic = student.get('sub_topic', 'Place Value')
    
    # Extract ground truth from the Local Knowledge Layer
    kicd_data = knowledge_base.get_curriculum_context(subject, topic, sub_topic)
    past_papers = knowledge_base.get_past_papers_context(subject, topic)
    
    # 2. Strict engineering template layout instructions
    prompt = f"""
    {SYSTEM_GUARD}
    = You are Mwalimu AI, an elite CBC Curriculum framework subject expert.
    Generate a 5-question multiple-choice quiz payload.

    TARGET CONTEXT SCHEMA:
    - Subject Domain: {subject}
    - Main Topic: {topic}
    - Sub-Topic Focus: {sub_topic}
    - Intended Learning Outcome: {learning_outcome}
    - Student Grade Target: {grade}
    - Output Language Interface: {language}

    =======================================================
    🚨 CRITICAL STOP-GATE CONSTRAINTS (NO MATH ALLOWED)
    =======================================================
    - DO NOT generate word problems that require mathematical calculations, numbers counting, area computations, weight multiplication, spacing ratios, or geometry dimensions. 
    - Questions must evaluate factual and conceptual domain knowledge of the subject, NOT calculation tricks.

    ❌ WRONG EXAMPLE (BANNED CONCEPT):
    "A farmer has a field measuring 30 meters long... how many seeds can he plant 75cm apart?" -> THIS IS MATHEMATICS disguised as Agriculture. DO NOT DO THIS.

    ✅ CORRECT EXAMPLE (REQUIRED CONCEPT):
    "Which of the following is a primary reason for maintaining correct spacing when establishing a maize crop?" or "Which crop establishment tool is best suited for creating uniform planting holes?" -> THIS IS PURE AGRICULTURE. DO THIS.

    =======================================================
    🌍 LOCALIZATION & FORMATTING RULES
    =======================================================
    - Output ALL JSON keys, question values, structural text, and options answers entirely inside this language: {language}.
    
    Return ONLY a single valid raw JSON string matching this exact array map structure without markdown code blocks (```json ... ```):
    {{
        "quiz": [
            {{
                "question": "Insert conceptual multiple choice question text here",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": "The exact correct option string matching one of the options elements cleanly"
            }}
        ]
    }}
    
    # 3. Securely pass your prompt to your LLM generator client engine
    # response = client.models.generate_content(model="gemini-2.5-pro", contents=prompt)
    # return response.text

You are Mwalimu AI, an expert Examiner specializing in the Kenyan KICD Competency-Based Curriculum (CBC) framework. 
Your task is to generate a highly contextual, age-appropriate practice quiz based on the student's current learning topic.

Generate a multiple-choice quiz about '{topic}' for a student in {student.get('grade')} ({student.get('age')} years old).

=== GROUND TRUTH KNOWLEDGE LAYER ===
Use the following verified rules and definitions to construct your questions. Do not deviate from these concepts:
- Definition Focus: {kicd_data['definition']}
- Target Learning Goals: {', '.join(kicd_data['learning_objectives'])}
- Reference Past Examination Structures: {json.dumps(past_papers)}
CRITICAL CONTEXT RULES:
- Every math word problem MUST contain all necessary numerical information to be solvable (e.g., do not say 'if each plant produces 2', specify the total number of plants first!).
- Use Kenyan names (e.g., Mwangi, Amina), locations, and real-world local scenarios (M-Pesa, market stalls, matatus) to make the word problems relatable.
- Match the cognitive expectations of a {student.get('grade')} student under CBC guidelines.
- Write the text strictly in the student's preferred language: {student.get('language', 'English')}.

Target Difficulty Level: {difficulty}
Difficulty Context Rules: {difficulty_rules.get(difficulty, "")}
Preferred Learning Style: {student.get('learning_style', 'General')}

CBC Context Info:
Subject: {student.get('subject')} | Topic: {student.get('topic')} | Target Learning Outcome: {student.get('learning_outcome')}

Return your response strictly as a valid JSON array containing EXACTLY 5 objects structured exactly like this layout format:
[
  {{
    "question": "First Question text here",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": "The exact correct option string matching one of the options"
  }},
  {{
    "question": "Second Question text here",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": "The exact correct option string matching one of the options"
  }},
  ... up to 5 elements total
]

CRITICAL OPTION CONSTRAINT RULES:
1. **No Math Formulations**: Every element in the "options" array MUST be a fully calculated, single final value (e.g., use "48,878 shillings", NEVER "45,678 + 3,200 shillings").
2. **Realistic Distractors**: Make the incorrect options plausible calculation errors (like missing a carry-over digit or accidentally subtracting instead of adding) so students are challenged to think critically.
3. Every math word problem MUST contain all necessary numerical information to be solvable.
4. For Mathematics (Whole Numbers), ensure all intermediate and final calculation results are strictly positive WHOLE NUMBERS. Avoid division problems that result in fractional remainders or decimals.
5. Use Kenyan names (e.g., Mwangi, Amina), locations, and real-world local scenarios (M-Pesa, market stalls, matatus) to make the word problems relatable.
6. Match the cognitive expectations of a {student.get('grade')} student under CBC guidelines.
7. Write the text strictly in the student's preferred language: {student.get('language', 'English')}.
8. **Consistent Units**: Ensure all options include the correct unit matching the question (e.g., "shillings", "passengers").
"""
    #=======
    try:
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://mwalimu-ai.streamlit.app",
                "X-Title": "Mwalimu AI App Quiz",
            },
            model="openrouter/free",  # 👈 CHANGED FROM "openrouter/free"
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,  # 👈 ADDED FOR SWIFT INITIALIZATION (Plenty for JSON quiz)
            response_format={"type": "json_object"}  # 👈 FORCES RAPID NATIVE JSON PARSING
        )
        
        # FIX: OpenRouter/OpenAI compatibility wrapper parsing requires indexing choices[0]
        quiz_text = response.choices[0].message.content
        if quiz_text is None:
            print("No content returned from model")
            return []
            
        quiz_text = quiz_text.replace("```json", "").replace("```", "").strip()
        try:
            quiz_data = json.loads(quiz_text)
            for question in quiz_data:
                if "options" in question and isinstance(question["options"], list):
                    random.shuffle(question["options"])
            return quiz_data
        except json.JSONDecodeError:
            print("Invalid JSON returned by Model:")
            print(quiz_text)
            return []
    except Exception as e:
        print(f"Error calling OpenRouter API: {e}")
        return []

def generate_study_plan(student: dict, stats: dict) -> str:
    """Crafts an optimized personalized study timetable map strategy framework with grid layouts."""
    # 1. Safely extract the preferred language from the student profile dictionary
    preferred_language = student.get("preferred_language", student.get("language", "English"))
    subject = student.get('subject', 'Mathematics')
    topic = student.get('topic', 'Whole Numbers')
    sub_topic = student.get('sub_topic', 'Place Value')
    learning_style = student.get("learning_style", "General")
    
    try:
        milestones = knowledge_base.get_study_milestones(subject, topic, sub_topic)
    except Exception:
        milestones = ["Kuelewa msingi wa mada", "Kufanya mazoezi ya vitendo", "Kupima maarifa kwa maswali"]
        
    language_rules = {
        "English": "Write the entire response, section titles, timetables, and tips exclusively in grammatically correct English.",
        "Kiswahili": "Andika majina yote ya sehemu (Headings), ratiba, malengo, na maelezo yote kwa Kiswahili sanifu na safi. Usitumie Kiingereza.",
        "Sheng": "Tumia lugha ya kirafiki ya Sheng iliyochanganywa na maelezo ya kimasomo ili kumfanya mwanafunzi achangamke, lakini hakikisha ukweli wa kimasomo unabaki sahihi."
    }
    
    target_language_instruction = language_rules.get(preferred_language, language_rules["English"])
    
    # 2. Dynamic heading localization dictionary matching your chosen interface script
    is_swahili = "swahili" in str(preferred_language).lower()
    h_goal = "### **Malengo ya Kujiendelea Leo (Daily Study Goals):**" if is_swahili else "### **Daily Study Goals:**"
    h_sched = "### **Ratiba ya Masomo (Time Intervals & Subjects):**" if is_swahili else "### **Study Schedule & Time Intervals:**"
    h_style = f"### **Mbinu za Kujifunza ({learning_style} Integration):**" if is_swahili else f"### **Learning Style Integration ({learning_style}):**"
    h_rev = "### **Vipengele vya Marudio na Mapendekezo ya Maswali:**" if is_swahili else "### **Revision Items & Quiz Recommendations:**"
    h_moto = "### **Ujumbe wa Kila Siku kutoka kwa Mwalimu:**" if is_swahili else "### **Mwalimu's Motivational Message:**"

    # Define localized column headers for the markdown grid table matrix array
    if is_swahili:
        col_time, col_sub, col_act = "Muda (Time)", "Somo na Mada (Subject/Topic)", "Shughuli ya Kufanya (Activity)"
    else:
        col_time, col_sub, col_act = "Time Interval", "Subject & Topic", "Planned Learning Activity"

    # 3. Construct the streamlined optimization prompt with absolute markdown table constraints
    prompt = f"""
{SYSTEM_GUARD}
You are Mwalimu AI, an expert Academic Counselor and Curriculum Planner specializing in the Kenyan KICD Competency-Based Curriculum (CBC) framework. 
Build a highly actionable, structured, and realistic Personalized Study Plan for a student.

=== STUDENT PROFILE ===
Name: {student.get("name", "Student")}
Grade: {student.get("grade", "N/A")}
Age: {student.get("age", "N/A")}
Learning Style: {learning_style}
Preferred Language: {preferred_language}

=== ACTIVE CBC CURRICULUM CONTEXT ===
Subject: {subject}
Topic: {topic}
Sub-topic: {sub_topic}
Learning Outcome Target: {student.get("learning_outcome", "General Mastery")}

=== KICD GROUND TRUTH MILESTONES ===
You MUST anchor your schedule activities directly on these local milestone goals:
{json.dumps(milestones, ensure_ascii=False)}

=== STUDENT PERFORMANCE STATISTICS ===
Questions Asked: {stats.get("questions", 0)}
Quizzes Taken: {stats.get("quizzes", 0)}
Average Score: {stats.get("average_score", 0)}%

=======================================================
🚨 CRITICAL FORMATTING & HEADINGS MANDATE
=======================================================
You MUST structure your entire response using the following specific headers exactly as provided below to guarantee clean rendering on the Streamlit dashboard:

{h_goal}
[Provide clear targets focusing on improving performance based on their statistics and active curriculum selections]

{h_sched}
You MUST output the schedule exclusively as a clean Markdown Grid Table using pipe signs (|) and dashes (-). Follow this exact structural layout template:

| {col_time} | {col_sub} | {col_act} |
| :--- | :--- | :--- |
| **08:00 - 08:30** | {subject}: {topic} | Introduction & reviewing baseline definitions. |
| **08:30 - 09:15** | {subject}: {sub_topic} | Step-by-step practical problem-solving exercises. |
| **09:15 - 09:30** | *Muda wa Mapumziko (Break)* | Take a short walk or stretch. |
| **09:30 - 10:15** | {subject} Revision | Deep practice covering milestones. |

Ensure there are no line-breaks or unescaped symbols inside row cells that break table rendering!

{h_style}
[Provide custom practical tasks matching their learning style. For Example: If 'Visual', instruct them to create colored mind maps or visual diagrams. If 'Auditory', suggest recording explanations or reading definitions aloud.]

{h_rev}
[List critical revision concepts and include a custom recommendation link or reference point for their next quiz]

{h_moto}
[Provide a warm, encouraging closing message using iconic teacher phrasing matching the target language rules, e.g., "Kazi safi!", "Tia bidii!", "Keep pushing!"]

=======================================================
🌍 LANGUAGE & CODE RESTRICTIONS
=======================================================
- {target_language_instruction}
- Write the output text strictly in clean, standard, natural prose. Do not mix random language tokens.
- NEVER use HTML line breaks like '<br>' or markdown backtick json code fences.
- All headings MUST stay completely bold by keeping the triple hashes and double asterisks formatting structure intact.
- NEVER include bracketed source numbers or placeholder texts.
"""

    try:
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://mwalimu-ai.streamlit.app",
                "X-Title": "Mwalimu AI Study Planner",
            },
            model="openrouter/free",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000
        )
        
        raw_content = response.choices[0].message.content
        return raw_content if raw_content is not None else "Error: Mwalimu AI received an empty study plan from the generation model."
        
    except Exception as e:
        return f"Could not sync study strategy roadmap recommendations: {e}"


def generate_flashcards(topic, student, difficulty="Medium"):
    """Produces a structured dataset containing exactly 10 flashcard items using strict JSON schemas."""
    difficulty_rules = {
        "Beginner": "Focus on foundational recognition, recalling basic definitions, direct matching, and basic counting with explicit hints.",
        "Intermediate": "Focus on application scenarios, multi-step problem solving, simple comparative relationships, and foundational word problems.",
        "Advanced": "Focus on critical thinking, complex contextual word problems, combining cross-topic parameters, and logical reasoning structures."
    }
    subject = student.get('subject', 'Mathematics')
    topic = student.get('topic', 'Whole Numbers')
    sub_topic = student.get('sub_topic', 'Place Value')

    verified_deck = knowledge_base.get_flashcards_context(subject, topic, sub_topic)
    kicd_data = knowledge_base.get_curriculum_context(subject, topic, sub_topic)
    
    # CLEANED PROMPT: Focuses 100% on flashcards and explicitly requests a clean parent object
    prompt = f"""
{SYSTEM_GUARD}
You are Mwalimu AI, an elite educational system and expert curriculum designer under the Kenyan KICD Competency-Based Curriculum (CBC) framework.
Your task is to generate a highly contextual set of study flashcards for a student in {student.get('grade')} ({student.get('age')} years old).

=== ACTIVE CBC CURRICULUM CONTEXT ===
- Subject: {subject}
- Topic: {topic}
- Sub-topic: {sub_topic}
- Core Baseline Definition: {kicd_data.get('definition', 'Standard parameters apply.')}
- Pre-approved Deck Context: {json.dumps(verified_deck, ensure_ascii=False)}

=== CORE RECOGNITION RULES ===
- Target Difficulty Level: {difficulty}
- Difficulty Rules: {difficulty_rules.get(difficulty, "")}
- Preferred Learning Style: {student.get('learning_style', 'General')}
- Preferred Delivery Language: {student.get('language', 'English')}

=== CRITICAL BOUNDARY COUNT RULE ===
You MUST generate EXACTLY 10 distinct flashcard pairs in total. No more, no less.
Count your array meticulously before returning the final text payload.

=== REAL-WORLD SCENARIOS ===
Use Kenyan context, local real-world examples, Kenyan currency (KES), towns, and popular local names (e.g., Juma, Wanjiku, Amina, Mwangi) to make the cards relatable and interactive.

=== OUTPUT VALIDATION FORMAT ===
Return ONLY a raw, valid JSON object containing an array list of exactly 10 question-and-answer pairs. Do not include any markdown backticks or filler text. Follow this schema layout:
{{
  "flashcards": [
    {{"question": "Question 1 goes here...", "answer": "Answer 1 goes here..."}},
    {{"question": "Question 2 goes here...", "answer": "Answer 2 goes here..."}},
    ... up to exactly 10 items
  ]
}}
"""

    try:
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://mwalimu-ai.streamlit.app",
                "X-Title": "Mwalimu AI Flashcard Processor",
            },
            model="openrouter/free",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,  # 2500 provides plenty of room for 10 rich cards
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content
        clean_content = (raw_content if raw_content is not None else "").strip()
        
        # Strip out any lingering markdown text elements if present
        if clean_content.startswith("```json"):
            clean_content = clean_content.replace("```json", "", 1).rstrip("```")
        elif clean_content.startswith("```"):
            clean_content = clean_content.strip("```")
            
        parsed_data = json.loads(clean_content.strip())
        
        # Unpack the list from the parent "flashcards" object tag safely
        if isinstance(parsed_data, dict) and "flashcards" in parsed_data:
            flashcard_list = parsed_data["flashcards"]
        elif isinstance(parsed_data, list):
            flashcard_list = parsed_data
        else:
            flashcard_list = []
            
        # DEFENSIVE PROGRAMMING CLOSURE CELL: Always force an upper array ceiling clip of exactly 10
        return flashcard_list[:10]
        
    except Exception as e:
        print(f"Flashcard Generator Engine Parsing Error: {e}")
        # Return fallback deck block if generation fails completely
        return [
            {"question": f"What is the core baseline definition behind {topic}?", "answer": f"{kicd_data.get('definition')}"},
            {"question": f"How can we apply our understanding of {sub_topic} in everyday tasks?", "answer": "By breaking down local real-world scenarios into basic CBC competency steps."}
        ]


def generate_lesson(topic, student):
    """Generates full structural markdown lessons backed by the local KICD Knowledge Base."""
    lang = student.get("preferred_language", student.get("language", "English"))
    subject = student.get("subject", "General")
    sub_topic = student.get("sub_topic", "General")
    learning_style = student.get("learning_style", "Visual")
    grade = student.get("grade", "General")
    outcome = student.get("learning_outcome", "General Mastery")
    name = student.get("name", "Student")
    is_swahili = "swahili" in str(lang).lower()
    
    title_lesson = "Somo" if is_swahili else "Lesson"
    h_objectives = "Malengo ya Somo" if is_swahili else "Learning Objectives"
    h_intro = "Utangulizi wa Mada" if is_swahili else "Introduction"
    h_explain = "Maelezo na Uchambuzi wa Kina" if is_swahili else "Main Lesson Content & Explanation"
    h_summary = "Muhtasari" if is_swahili else "Summary"
    h_homework = "Kazi ya Nyumbani" if is_swahili else "Homework Assignment"

    # Dynamic translation mapping for user learning styles
    style_translation = {
        "Visual": "Mwanafunzi wa Kielelezo (Visual Learner)",
        "Auditory": "Mwanafunzi wa Kusikia (Auditory Learner)",
        "Kinesthetic": "Mwanafunzi wa Kitendo (Kinesthetic Learner)",
        "Reading/Writing": "Mwanafunzi wa Kusoma na Kuandika"
    }
    local_style = style_translation.get(learning_style, learning_style)
    verified_deck = knowledge_base.get_flashcards_context(subject, topic, sub_topic)
    kicd_data = knowledge_base.get_curriculum_context(subject, topic, sub_topic)

    # Extract ground truth context fields
    kicd_data = knowledge_base.get_curriculum_context(subject, topic, sub_topic)
    prompt = f"""
    {SYSTEM_GUARD}
        You are Mwalimu AI, an elite teacher specialized in Kenya's CBC Curriculum design matrix.
    Generate a complete, comprehensive, and highly engaging markdown educational lesson plan.

    LESSON ENVIRONMENT METRICS:
    - Academic Subject: {subject}
    - Main Topic Focus: {topic}
    - Sub-Topic Focus: {sub_topic}
    - Target Learning Outcome: {outcome}
    - Target Grade Level: {grade}
    - Student Learner Profile Style: {learning_style}
    - Assigned Student Name: {name}
    
    =======================================================
    🚨 CRITICAL LANGUAGE MANDATE (ABSOLUTE INTERFACE LOCK)
    =======================================================
    - TARGET GENERATION LANGUAGE: {lang}
    - You MUST write the ENTIRE lesson output stream—including all headings, introduction paragraphs, bullet examples, explanations, and action items—strictly and exclusively inside this language script: {lang}.
    
    ⚠️ WARNING: Your sidebar language selection is currently set to "{lang}". Do NOT write or mix Kiswahili content blocks if the requested language value is English. Everything from titles to summary points must match "{lang}" seamlessly.

    REQUIRED MARKDOWN TEMPLATE HEADERS (Keep these exact structural levels and translate them to {lang}):
    # {title_lesson}: {topic} - {sub_topic}
    ## 1. {h_objectives}
    [Provide explicit conceptual goals mapped precisely to target: {outcome}]
    
    ## 2. {h_intro}
    [Hook the student's interest using everyday examples suited for a {learning_style} learner]
    
    ## 3. {h_explain}
    [Provide depth of explanation. Breakdown the core content details of {subject} in an interactive narrative form]
    
    ## 4. {h_summary}
    [Wrap up the lesson takeaways clearly]
    
    ## 5. {h_homework}
    [Include structured tasks to practice active recall]
You are Mwalimu AI, an inspiring and expert Senior School Teacher specializing in the Kenyan KICD Competency-Based Curriculum (CBC). 
Your task is to generate a comprehensive, highly engaging, and structured lesson text for a student based on their profile and selected curriculum pathway.

=== CBC KNOWLEDGE LAYER INJECTION ===
You MUST build your lesson around this verified ground-truth data payload:
- Target Concept Definition: {kicd_data['definition']}
- Verified Step-by-Step Worked Examples: {json.dumps(kicd_data['worked_examples'])}

=== STUDENT PROFILE ===
- Name: {student.get('name', 'Student')}
- Grade: {student.get('grade', 'General')}
- Age: {student.get('age', '10')}
- Learning Style: {student.get('learning_style', 'Interactive')}
- Preferred Language: {student.get('language', 'English')}

LESSON TARGET:
- Topic: {topic}
- Subject Domain: {student.get('subject')} | Strand Focus: {student.get('strand')} | Target Outcome: {student.get('learning_outcome')}

=== ACTIVE CBC CURRICULUM CONTEXT ===
Subject: {student.get("subject", "General")}
Topic: {student.get("topic", "General")}
Sub-topic: {student.get("sub_topic", "General")}
Learning Outcome Target: {student.get("learning_outcome", "General")}

=== LESSON ARCHITECTURE RULES ===
Please construct the lesson using clean Markdown headers. The lesson MUST include the following 9 numbered sections in order:

## 1. Lesson Title
- Create an exciting and clear title incorporating the active topic.

## 2. Learning Objectives
- State 3 or 4 clear bullet points outlining what the student will be able to do after completing this lesson, directly matching the Learning Outcome Target.

## 3. Introduction
- Hook the student's interest using a friendly greeting using Kenyan phrases (e.g., "Mambo!", "Habari!", or welcoming them by name: {student.get("name")}) and relate the topic to everyday life.

## 4. Main Explanation
- Breakdown the core concepts clearly. Use simple language and vocabulary appropriate for a {student.get('grade')} student.
- Adapt the explanation explicitly to a {student.get('learning_style')} learning style.

## 5. Real-life Kenyan Examples
- Ground the concept with relatable Kenyan contextual examples (e.g., matatus, market scenarios like Mama Mboga, local food like ugali/sukuma wiki, M-Pesa, or athletics/running tracking).

## 6. Worked Examples
- Provide step-by-step solutions to 1 or 2 practical problems or case scenarios illustrating the concept.

## 7. Practice Questions
- Provide 3 progressive questions matching the difficulty of the lesson to encourage active recall and critical thinking. Do not provide the answers immediately.

## 8. Summary & Fun Fact
- Bullet points summarizing the main takeaways of the lesson, followed by an interesting, mind-blowing fun fact relating to the topic.

## 9. Homework
- Create an engaging practical activity or mini-assignment that the student can perform at home or around the house to observe the concept in action.

=== STRICT GUIDELINES ===
- Always match the vocabulary to {student.get('grade')} expectations.
- Write primarily in the preferred language: {student.get('language')}.
- Do not append any meta-commentary, safety labels ("User Safety: safe"), or extra prompt diagnostics. Output only the complete lesson content starting directly from the Lesson Title.
"""

    try:
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://mwalimu-ai.streamlit.app",
                "X-Title": "Mwalimu AI Lesson Plan Engine",
            },
            model="openrouter/free",  # 👈 DIRECT SPEED ROUTING BYPASS
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2900  # 👈 GENEROUS ROOM FOR EXTENSIVE CBC LESSON STEPS & SCHEMES
        )
        # CRITICAL FIX: Safe indexing using standard array retrieval syntax
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenRouter Lesson Generation Error: {e}")
        return f"Mwalimu encountered an issue preparing your lesson roadmap: {e}. Please click generate again!"

def ask_mwalimu_voice(question, student, messages, adaptive_context):
    """Dedicated text-driven voice streaming engine with pre-emptive credit ceilings."""
    preferred_language = student.get("preferred_language", student.get("language", "English"))
    subject = student.get('subject', 'Science')
    topic = student.get('topic', 'Living Things')
    sub_topic = student.get('sub_topic', 'Plants')
    learning_style = student.get("learning_style", "General")
    
    # Safely look up curriculum details from your knowledge base
    kicd_data = knowledge_base.get_curriculum_context(subject, topic, sub_topic)
    
    language_rules = {
        "English": "Respond naturally and directly in grammatically correct English like an empathetic Kenyan classroom teacher.",
        "Kiswahili": "Andika majibu yako yote kwa Kiswahili sanifu, fasaha, na safi kabisa kinachofaa mazingira ya shule za Kenya. Usitumie Kiingereza.",
        "Sheng": "Tumia lugha ya kirafiki ya Sheng iliyochanganywa na maelezo ya kimasomo ili kumfanya mwanafunzi achangamke, lakini hakikisha ukweli wa kimasomo unabaki sahihi."
    }
    
    # Get the language instruction string based on student choice
    selected_language_rule = language_rules.get(preferred_language, language_rules["English"])
    
    # 🏎️ CRITICAL OPTIMIZATION: Tight sliding window. Never send more than the last 4 messages to save tokens!
    recent_messages = messages[-4:] if messages else []
    
    # Build history string strictly using the recent_messages slice
    voice_history_string = ""
    for msg in recent_messages:
        role_label = "Mwanafunzi" if msg.get("role") in ["user", "student", "voice_student"] else "Mwalimu"
        voice_history_string += f"{role_label}: {msg.get('content')}\n"

    # Assemble the final, isolated prompt string
    prompt = f"""
{SYSTEM_GUARD}

=== CRITICAL CONTEXT CONFLICT PROTECTION WALL ===
- THIS IS A COMPLETELY SEPARATE, INDEPENDENT VOICE LEARNING SESSION.
- NEVER read, reference, or use information from the student's normal text chat window history.
- Treat this voice session as its own isolated classroom environment.
- Ignore any text chat messages that are not present in the Voice Tutor history block below.

=== VOICE TUTOR RULES (STRICT CAP) ===
- YOU ARE SPEAKING ALOUD. NEVER EXCEED 50 WORDS TOTAL.
- Keep answers brief, conversational, warm, and highly snackable.
- Avoid asterisks, bolding markdown, or symbols completely.
- Language Instruction: {selected_language_rule}

=== EXCLUSIVE VOICE TUTOR INTERACTION HISTORY ===
{voice_history_string}
================================================

=== STUDENT PROFILE & CURRENT SUBJECT CONTEXT ===
- **Student Name**: {student.get('name', 'Student')}
- **Subject**: {subject} | **Topic**: {topic} ({sub_topic})
- **Learning Style**: {learning_style}

=== CURRENT STUDENT SPOKEN INQUIRY ===
Student Spoken Question: {question}
Mwalimu AI verbal response:
"""

    api_messages = [{"role": "user", "content": prompt}]

    try:
        # 🚀 PRE-EMPTIVE CEILING: Lower voice max_tokens to 350 to provide super-fast text chunks and stay well within your 812 budget
        response_stream = client.chat.completions.create(
            model="openrouter/free",
            messages=api_messages,  # type: ignore
            max_tokens=350,  
            stream=True  
        )
        return response_stream  
        
    except Exception as api_err:
        error_diagnostic_string = str(api_err)
        print(f"[Terminal Log] Voice Tutor API Fault: {error_diagnostic_string}")
        
        # 🛡️ SYSTEM GUARD: Catch 402/Credit errors explicitly before returning to prevent SSE/JSON pipeline crashes
        if "402" in error_diagnostic_string or "credits" in error_diagnostic_string.lower():
            def error_generator():
                yield "Mwalimu's voice box is currently offline due to low OpenRouter credits. Please add a small credit top-up to your API wallet dashboard!"
            return error_generator()

        def fallback_generator():
            yield f"Mwalimu Voice Engine encountered a stutter. Details: {error_diagnostic_string}"
        return fallback_generator()
