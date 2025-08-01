from datetime import datetime
import streamlit as st
import torch
from transformers import pipeline
from logic.chat_history import ChatHistory
from logic.ui_components import (
    chat_message_ui,
    sidebar_chat_history_ui, user_input_ui
)
from logic.utils import extract_text_from_image, extract_text_from_pdf
import uuid

# --- Init ---
ChatHistory.init_db()
st.set_page_config(page_title="EduMate", layout="wide", page_icon="📚")

# --- Load Models Once ---
def load_models():
    if "models_loaded" not in st.session_state:
        with st.spinner("Preparing your EduMate Assistant..."):
            device = -1  
            st.session_state.qa_pipeline = pipeline(
                "question-answering",
                model="deepset/tinyroberta-squad2",
                device=device
            )
            st.session_state.summarizer = pipeline(
                "summarization",
                model="t5-small",
                device=device
            )
        st.session_state.models_loaded = True

# --- Prompt Logic ---
def get_context_prompt(level):
    return {
        "Basic": "Explain simply like to a 10-year-old: ",
        "SHS": "Explain for high school level: ",
        "Tertiary": "Provide detailed academic explanation: "
    }.get(level, "")

# --- Answer ---
def answer_question(question, context="", level="Basic"):
    prompt = get_context_prompt(level) + question
    result = st.session_state.qa_pipeline(
        question=prompt,
        context=context or prompt,
        max_length=512
    )
    return result["answer"]

# --- Summarize ---
def summarize_text(text, level="Basic"):
    prompt = f"summarize: {text}"
    summary = st.session_state.summarizer(
        prompt,
        max_length=130 if level == "Basic" else 200,
        min_length=30
    )
    return summary[0]["summary_text"]


def cleanup_models():
    st.session_state.pop("qa_pipeline", None)
    st.session_state.pop("summarizer", None)
    torch.cuda.empty_cache()


# sourcery skip: 
for key, val in {
    "history": ChatHistory.load_history(),
    "active_chat_id": None,
    "education_level": "Basic",
    "search_query": "",
    "dark_mode": False,
    "main_dark_mode": False,
    "paused": False,
    "smart_context": ""
}.items():
    st.session_state.setdefault(key, val)

load_models()


st.markdown("""
    <style>
    .stChatMessage { padding: 12px; }
    .stButton button {
        transition: all 0.2s ease-in-out;
        border-radius: 6px;
    }
    .stButton button:hover {
        background-color: #ffeb3b20;
        transform: scale(1.05);
    }
    @media only screen and (max-width: 768px) {
        section[data-testid="stSidebar"] { display: none; }
        .mobile-sidebar-toggle { display: block; margin-bottom: 10px; }
    }
    @media only screen and (min-width: 769px) {
        .mobile-sidebar-toggle { display: none; }
    }
    </style>
""", unsafe_allow_html=True)


if st.session_state.main_dark_mode:
    st.markdown("""
        <style>
        body { background-color: #121212; color: white; }
        .stTextInput input, .stSelectbox div { background-color: #222; color: white; }
        </style>
    """, unsafe_allow_html=True)

# --- Mobile Sidebar Toggle ---
with st.container():
    st.markdown(
        """
        <style>
        @media only screen and (min-width: 769px) {
            .mobile-sidebar-toggle { display: none !important; }
        }
        @media only screen and (max-width: 768px) {
            .mobile-sidebar-toggle { display: block !important; margin-bottom: 10px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    

# --- Sidebar ---
with st.sidebar:
    st.title("📚 EduMate")
    st.session_state.education_level = st.selectbox(
        "🎓 Education Level", ["Basic", "SHS", "Tertiary"]
    )
    # Learning style selector in a collapsible expander
    with st.expander("🎯 Preferred Learning Style", expanded=False):
        st.session_state.learning_style = st.radio(
            "Select your learning style:",
            ["Visual (videos/images)", "Auditory (audio/podcasts)", "Reading/Writing (articles/text)", "Kinesthetic (hands-on)"],
            key="learning_style_radio"
        )
    st.markdown("---")
    # Study Plan Generator
    st.subheader("📝 Study Plan Generator")
    with st.form("study_plan_form"):
        study_goal = st.text_input("What do you want to study? (e.g., Algebra, Photosynthesis, World War II)")
        study_duration = st.number_input("How many weeks do you want to study?", min_value=1, max_value=52, value=1)
        submit_plan = st.form_submit_button("Generate Study Plan")
    st.markdown("---")
    # Chat History
    filtered_history = [
        c for c in st.session_state.history
        if st.session_state.search_query.lower() in c["title"].lower()
    ]
    sidebar_chat_history_ui(filtered_history)
    
    if st.button("🧹 Free Up Memory", help="Clear loaded models from memory"):
        cleanup_models()
        st.success("Memory freed!")
    st.markdown("---")


if 'study_plan' not in st.session_state:
    st.session_state['study_plan'] = None

if submit_plan and study_goal:
    subtopics = []
    n = int(study_duration)
    
    if 'quiz_gen_pipeline' in st.session_state and st.session_state.quiz_gen_pipeline:
        try:
            prompt = f"List {n} important subtopics to study for {study_goal}."
            result = st.session_state.quiz_gen_pipeline(prompt, max_length=128, num_return_sequences=1)[0]["generated_text"]
            
            if '\n' in result:
                subtopics = [line.strip('- ').strip() for line in result.split('\n') if line.strip()]
            else:
                subtopics = [s.strip() for s in result.split(',') if s.strip()]
            if len(subtopics) < n:
                raise Exception("Not enough subtopics")
        except Exception:
            subtopics = []
            
    # Fallback to template
    if not subtopics or len(subtopics) < n:
        subtopics = [f"Subtopic {i+1} of {study_goal}" for i in range(n)]
    plan = [f"Week {i+1}: Study {subtopics[i]}" for i in range(n)]
    st.session_state['study_plan'] = plan
    st.success("Study plan generated!")


if 'show_mobile_sidebar_modal' not in st.session_state:
    st.session_state['show_mobile_sidebar_modal'] = False
if 'mobile_sidebar_feature' not in st.session_state:
    st.session_state['mobile_sidebar_feature'] = None

mobile_sidebar_features = [
    "None",
    "Education Level",
    "Learning Style",
    "Study Plan Generator",
    "Chat History"
]
selected_sidebar_feature = st.selectbox(
    "Sidebar Features on Mobile:",
    mobile_sidebar_features,
    key="mobile_sidebar_dropdown",
    index=0,
    help="Access sidebar features on mobile"
)
if selected_sidebar_feature and selected_sidebar_feature != "None":
    st.session_state['show_mobile_sidebar_modal'] = True
    st.session_state['mobile_sidebar_feature'] = selected_sidebar_feature
else:
    st.session_state['show_mobile_sidebar_modal'] = False
    st.session_state['mobile_sidebar_feature'] = None

# Streamlit-native expander for selected sidebar feature 
if st.session_state.get('show_mobile_sidebar_modal') and st.session_state.get('mobile_sidebar_feature'):
    with st.expander(f"{st.session_state['mobile_sidebar_feature']} (Mobile)", expanded=True):
        if st.button("✖️ Close", key="close_mobile_sidebar_modal"):
            st.session_state['show_mobile_sidebar_modal'] = False
            st.session_state['mobile_sidebar_feature'] = None
        # Render the selected sidebar feature's controls
        if st.session_state['mobile_sidebar_feature'] == "Education Level":
            st.session_state.education_level = st.selectbox(
                "Education Level (Mobile)", ["Basic", "SHS", "Tertiary"], key="mobile_edu_level"
            )
        elif st.session_state['mobile_sidebar_feature'] == "Learning Style":
            st.session_state.learning_style = st.radio(
                "Learning Style (Mobile)",
                ["Visual (videos/images)", "Auditory (audio/podcasts)", "Reading/Writing (articles/text)", "Kinesthetic (hands-on)"],
                key="mobile_learning_style_radio"
            )
        elif st.session_state['mobile_sidebar_feature'] == "Study Plan Generator":
            with st.form("mobile_study_plan_form"):
                study_goal = st.text_input("What do you want to study? (e.g., Algebra, Photosynthesis, World War II)", key="mobile_study_goal")
                study_duration = st.number_input("How many weeks do you want to study?", min_value=1, max_value=52, value=1, key="mobile_study_duration")
                submit_plan = st.form_submit_button("Generate Study Plan (Mobile)")
            if submit_plan and study_goal:
                subtopics = []
                n = int(study_duration)
                if 'quiz_gen_pipeline' in st.session_state and st.session_state.quiz_gen_pipeline:
                    try:
                        prompt = f"List {n} important subtopics to study for {study_goal}."
                        result = st.session_state.quiz_gen_pipeline(prompt, max_length=128, num_return_sequences=1)[0]["generated_text"]
                        if '\n' in result:
                            subtopics = [line.strip('- ').strip() for line in result.split('\n') if line.strip()]
                        else:
                            subtopics = [s.strip() for s in result.split(',') if s.strip()]
                        if len(subtopics) < n:
                            raise Exception("Not enough subtopics")
                    except Exception:
                        subtopics = []
                if not subtopics or len(subtopics) < n:
                    subtopics = [f"Subtopic {i+1} of {study_goal}" for i in range(n)]
                plan = [f"Week {i+1}: Study {subtopics[i]}" for i in range(n)]
                st.session_state['study_plan'] = plan
                st.success("Study plan generated!")
        elif st.session_state['mobile_sidebar_feature'] == "Chat History":
            filtered_history = [
                c for c in st.session_state.history
                if st.session_state.search_query.lower() in c["title"].lower()
            ]
            sidebar_chat_history_ui(filtered_history)
# --- App Description Card ---
st.info(
    """
    **Welcome to EduMate!**
    
    EduMate is your AI-powered personal learning assistant. Use the sidebar to:
    - Select your education level and learning style
    - Generate a personalized study plan for any topic
    - Get curated articles and videos
    - Take auto-generated quizzes and track your progress
    - **Search your previous chats and summaries using the chat history search box**
    
    On mobile, use the dropdown menu at the top to access sidebar features.
    Use the main feature selector below to switch between core features. Happy learning!
    """,
    icon="🎓"
)

# --- Main Area Feature Selector ---
main_feature = st.selectbox(
    "Select a feature to view:",
    [
        "Study Plan",
        "Curated Learning Resources",
        "Auto-Generated Quiz",
        "Progress Dashboard"
    ],
    index=0,
    key="main_feature_selector"
)

if main_feature == "Study Plan":
    if st.session_state.get('study_plan'):
        st.markdown("## 📅 Your Personalized Study Plan")
        for item in st.session_state['study_plan']:
            st.markdown(f"- {item}")
    else:
        st.info("No study plan generated yet. Use the sidebar to create one.")

elif main_feature == "Curated Learning Resources":
    st.header("🔗 Curated Learning Resources")
    resource_topic = st.text_input("Enter a topic to get articles and videos:", key="resource_topic")
    if st.button("Get Resources", key="get_resources"):
        if resource_topic.strip():
            with st.spinner("Fetching resources..."):
                import requests
                wiki_results = []
                try:
                    resp = requests.get(f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={resource_topic}&format=json")
                    for item in resp.json()["query"]["search"][:2]:
                        title = item["title"]
                        url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                        wiki_results.append((title, url))
                except Exception:
                    wiki_results = []
                yt_results = [
                    ("YouTube Search", f"https://www.youtube.com/results?search_query={resource_topic.replace(' ', '+')}")
                ]
            style = st.session_state.get("learning_style", "Reading/Writing (articles/text)")
            if "Visual" in style:
                st.subheader("YouTube Videos (Visual)")
                for title, url in yt_results:
                    st.markdown(f"- [{title}]({url})")
                st.subheader("Wikipedia Articles")
                for title, url in wiki_results:
                    st.markdown(f"- [{title}]({url})")
            elif "Auditory" in style:
                st.subheader("YouTube Videos (for audio)")
                for title, url in yt_results:
                    st.markdown(f"- [{title}]({url})")
                st.info("Audio/podcast resources coming soon!")
            elif "Reading/Writing" in style:
                st.subheader("Wikipedia Articles (Reading/Writing)")
                for title, url in wiki_results:
                    st.markdown(f"- [{title}]({url})")
                st.subheader("YouTube Videos")
                for title, url in yt_results:
                    st.markdown(f"- [{title}]({url})")
            elif "Kinesthetic" in style:
                st.subheader("Practical Activities (Kinesthetic)")
                st.markdown(f"- Try to find a hands-on project or experiment about **{resource_topic}**.")
                st.subheader("Wikipedia Articles")
                for title, url in wiki_results:
                    st.markdown(f"- [{title}]({url})")
                st.subheader("YouTube Videos")
                for title, url in yt_results:
                    st.markdown(f"- [{title}]({url})")

elif main_feature == "Auto-Generated Quiz":
    st.header("📝 Auto-Generated Quiz")
    quiz_topic = st.text_input("Enter a topic to generate a quiz:", key="quiz_topic")
    num_questions = st.selectbox("Number of questions:", [5, 10, 15, 20], index=0, key="num_questions")
    if st.button("Generate Quiz", key="generate_quiz"):
        if quiz_topic.strip():
            questions = []
            options = []
            correct_indices = []
            n = num_questions
            if st.session_state.quiz_gen_pipeline:
                try:
                    prompt = f"Generate {n} multiple choice quiz questions about {quiz_topic} with 1 correct answer and 2 distractors for each. Format: Q: ...\nA) ...\nB) ...\nC) ...\nCorrect: ..."
                    result = st.session_state.quiz_gen_pipeline(prompt, max_length=512, num_return_sequences=1)[0]["generated_text"]
                    for block in result.split("Q:"):
                        lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
                        if len(lines) >= 4:
                            q = lines[0]
                            opts = [l[3:].strip() if l.startswith(('A)', 'B)', 'C)')) else l for l in lines[1:4]]
                            correct = lines[4].replace("Correct:", "").strip()
                            if correct in opts:
                                correct_idx = opts.index(correct)
                            else:
                                correct_idx = 0
                            questions.append(q)
                            options.append(opts)
                            correct_indices.append(correct_idx)
                        if len(questions) >= n:
                            break
                    if not questions:
                        raise Exception("Parsing failed")
                except Exception:
                    questions = []
                    options = []
                    correct_indices = []
            if not questions or len(questions) < n:
                fallback_qs = [
                    f"What is the main idea of {quiz_topic}?",
                    f"List one important fact about {quiz_topic}.",
                    f"Why is {quiz_topic} important?"
                ]
                fallback_opts = [
                    ["It is a key concept.", "It is a random topic.", "It is not important."],
                    ["It is widely studied.", "It is rarely discussed.", "It is a new discovery."],
                    ["It has a big impact.", "It is not useful.", "It is only for fun."]
                ]
                fallback_correct = [0, 0, 0]
                while len(questions) < n:
                    idx = len(questions) % 3
                    questions.append(fallback_qs[idx])
                    options.append(fallback_opts[idx])
                    correct_indices.append(fallback_correct[idx])
            st.session_state["quiz_questions"] = questions[:n]
            st.session_state["quiz_options"] = options[:n]
            st.session_state["quiz_correct_indices"] = correct_indices[:n]
            st.session_state["quiz_mc_answers"] = [None for _ in questions[:n]]
            st.session_state["quiz_mc_feedback"] = None
            st.session_state["quiz_score"] = None
            if "quiz_progress" not in st.session_state:
                st.session_state["quiz_progress"] = {"taken": 0, "correct": 0}
    if "quiz_questions" in st.session_state and "quiz_options" in st.session_state:
        with st.form("quiz_form_mc"):
            user_mc_answers = []
            for i, (q, opts) in enumerate(zip(st.session_state["quiz_questions"], st.session_state["quiz_options"])):
                user_mc_answers.append(st.radio(f"Q{i+1}: {q}", opts, index=st.session_state["quiz_mc_answers"][i] if st.session_state["quiz_mc_answers"][i] is not None else 0, key=f"quiz_mc_answer_{i}"))
            submit_mc_quiz = st.form_submit_button("Submit Answers")
        if submit_mc_quiz:
            st.session_state["quiz_mc_answers"] = [opts.index(ans) for ans, opts in zip(user_mc_answers, st.session_state["quiz_options"])]
            score = 0
            feedback = []
            for i, (user_idx, correct_idx, opts) in enumerate(zip(st.session_state["quiz_mc_answers"], st.session_state["quiz_correct_indices"], st.session_state["quiz_options"])):
                if user_idx == correct_idx:
                    feedback.append(f"✅ Correct! The answer is: {opts[correct_idx]}")
                    score += 1
                else:
                    feedback.append(f"❌ Not quite. You chose: {opts[user_idx]}\nCorrect answer: {opts[correct_idx]}")
            st.session_state["quiz_mc_feedback"] = feedback
            st.session_state["quiz_score"] = score
            st.session_state["quiz_progress"]["taken"] += 1
            st.session_state["quiz_progress"]["correct"] += score
        if st.session_state.get("quiz_mc_feedback"):
            st.subheader("Quiz Feedback")
            for i, feedback in enumerate(st.session_state["quiz_mc_feedback"]):
                st.markdown(f"**Q{i+1}:** {feedback}")
            st.markdown(f"**Score:** {st.session_state['quiz_score']} / {len(st.session_state['quiz_questions'])}")

elif main_feature == "Progress Dashboard":
    with st.expander("📊 Progress Dashboard", expanded=True):
        quizzes_taken = st.session_state.get("quiz_progress", {}).get("taken", 0)
        total_correct = st.session_state.get("quiz_progress", {}).get("correct", 0)
        avg_score = (total_correct / quizzes_taken) if quizzes_taken else 0
        st.markdown(f"**Quizzes Taken:** {quizzes_taken}")
        st.markdown(f"**Total Correct Answers:** {total_correct}")
        st.markdown(f"**Average Score:** {avg_score:.2f}")
        if st.session_state.get('study_plan'):
            st.markdown("---")
            st.markdown("**Study Plan Steps:**")
            if 'study_plan_completed' not in st.session_state:
                st.session_state['study_plan_completed'] = [False] * len(st.session_state['study_plan'])
            for i, step in enumerate(st.session_state['study_plan']):
                st.session_state['study_plan_completed'][i] = st.checkbox(step, value=st.session_state['study_plan_completed'][i], key=f'study_step_{i}')
            completed = sum(st.session_state['study_plan_completed'])
            st.markdown(f"**Completed:** {completed} / {len(st.session_state['study_plan'])}")

# --- Chat Options Modal ---
if st.session_state.get("show_menu_for"):
    
    pass 


st.header("🤖 EduMate Assistant")

# --- Upload & Summarize ---
uploaded_file = st.file_uploader("📎 Upload PDF/Image", type=["pdf", "jpg", "png", "jpeg"])
if uploaded_file:
    text = extract_text_from_pdf(uploaded_file) if uploaded_file.type == "application/pdf" else extract_text_from_image(uploaded_file)
    st.session_state.smart_context = text  

    if st.button("📝 Summarize"):
        with st.spinner("🔍 Analyzing document..."):
            summary = summarize_text(text, st.session_state.education_level)
            # Prevent duplicate summary chats
            exists = any(
                c["question"] == f"Summarize this document ({st.session_state.education_level})" and c["answer"] == summary
                for c in st.session_state.history
            )
            if not exists:
                chat = {
                    "id": str(uuid.uuid4()),
                    "title": f"Summary ({st.session_state.education_level})",
                    "question": f"Summarize this document ({st.session_state.education_level})",
                    "answer": summary,
                    "pinned": False
                }
                ChatHistory.save_chat(chat)
                chat_id = chat["id"]
                st.session_state.history = ChatHistory.load_history()
                st.session_state.active_chat_id = chat_id
                st.toast("Summary generated!", icon="✅")
                st.rerun()
            else:
                st.toast("Summary already exists!", icon="ℹ️")

# --- Smart Suggestions ---
if st.session_state.smart_context and not st.session_state.get("active_chat_id"):
    st.subheader("🪄 Smart Suggestions from Upload")
    suggestions = [
        "What is the main idea of the text?",
        "Summarize in 3 key points",
        "What is the tone or mood?",
        "Who is the audience?"
    ]
    for s in suggestions:
        if st.button(s, key=f"suggestion-{s}"):
            with st.spinner("💡 Thinking..."):
                response = answer_question(
                    s,
                    context=st.session_state.smart_context,
                    level=st.session_state.education_level
                )
                chat = {
                    "id": str(uuid.uuid4()),
                    "title": s,
                    "question": s,
                    "answer": response,
                    "pinned": False
                }
                ChatHistory.save_chat(chat)
                chat_id = chat["id"]
                st.session_state.history = ChatHistory.load_history()
                st.session_state.active_chat_id = chat_id
                st.toast("Suggestion answered!", icon="💡")
                st.rerun()

# --- Chat Display ---
if st.session_state.active_chat_id:
    chat = ChatHistory.get_chat(st.session_state.active_chat_id)
    if chat:
        chat_message_ui({"id": chat["id"], "message": chat["question"], "timestamp": chat["created_at"]}, is_user=True)
        chat_message_ui({"id": chat["id"], "message": chat["answer"], "timestamp": chat["updated_at"]}, is_user=False)

# --- Chat Input ---
user_input = user_input_ui()
if user_input:
    with st.spinner("💭 Processing..."):
        response = answer_question(user_input, level=st.session_state.education_level)
        chat = {
            "id": str(uuid.uuid4()),
            "title": f"{st.session_state.education_level} - {user_input[:25]}{'...' if len(user_input) > 25 else ''}",
            "question": user_input,
            "answer": response,
            "pinned": False
        }
        ChatHistory.save_chat(chat)
        chat_id = chat["id"]
        st.session_state.history = ChatHistory.load_history()
        st.session_state.active_chat_id = chat_id
        st.toast("Response saved!", icon="💾")
        st.rerun()

# --- Chat Deletion ---
if st.session_state.get("delete_chat"):
    ChatHistory.delete_chat(st.session_state["delete_chat"])
    st.session_state.history = ChatHistory.load_history()
    st.session_state.active_chat_id = None
    st.session_state.delete_chat = None
    st.toast("Chat deleted!", icon="🗑️")
