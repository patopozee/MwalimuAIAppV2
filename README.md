# 🎓 Mwalimu AI App

<p align="center">
  <img src="assets/logo.png" alt="Mwalimu AI Logo" width="180">
</p>

<p align="center">
  <strong>Shaping Minds, Shifting Futures.</strong><br>
  An AI-powered learning platform built for Kenya's Competency-Based Curriculum (CBC).
</p>

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-Latest-red.svg)
![Firestore](https://img.shields.io/badge/Database-Firestore-orange.svg)
![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-blueviolet.svg)
![OpenRouter](https://img.shields.io/badge/OpenRouter-AI%20Gateway-success.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

</p>

---

# 📖 About

**Mwalimu AI** is an intelligent educational assistant designed specifically for Kenyan learners following the **Competency-Based Curriculum (CBC)**.

The platform combines Artificial Intelligence, adaptive learning, analytics, and personalized tutoring into one modern learning environment.

Unlike traditional e-learning systems, Mwalimu AI adapts to each student's:

- Grade
- Age
- Learning style
- Academic strengths
- Weak topics
- Learning history

to deliver a truly personalized learning experience.

---

# ✨ Key Features

## 🤖 AI Tutor (Ask Mwalimu)

- Personalized AI teacher
- Context-aware conversations
- Remembers previous discussions
- Explains concepts according to:
  - Grade
  - Age
  - Learning style
  - Preferred language
- Supports:
  - English
  - Kiswahili
  - Sheng

---

## 📝 AI Quiz Generator

Generate competency-based quizzes instantly.

Features:

- Multiple Choice Questions
- Automatic Marking
- Instant Feedback
- Adaptive Difficulty
- Performance Tracking

---

## 📚 AI Lesson Generator

Generate complete textbook-style lessons including:

- Learning Objectives
- Introduction
- Detailed Explanations
- Kenyan Examples
- Worked Examples
- Practice Activities
- Summary
- Homework

---

## 🃏 Smart Flashcards

- Active Recall
- Revision Cards
- Personalized Questions
- Exam Preparation

---

## 📅 Personalized Study Planner

Automatically generates daily study schedules based on:

- Student profile
- Weak subjects
- Previous performance
- Learning preferences

---

## 📊 Student Analytics

Monitor learning progress through:

- Questions asked
- Quiz attempts
- Average score
- Weak topic detection
- Strong topic identification
- Learning history
- Performance trends

---

## 🧠 Adaptive Learning

Mwalimu AI continuously improves recommendations using:

- Quiz performance
- Previous conversations
- Learning style
- Weak topics
- Study habits

---

## 💳 Premium Subscription

Integrated M-Pesa STK Push payments allow learners to upgrade without leaving the application.

Features include:

- Secure M-Pesa Express Checkout
- Premium subscriptions
- Tier-based access
- Automatic usage tracking

---

# 👑 Subscription Plans

| Feature | Free | Mwalimu AI Plus | Premium |
|----------|------|-----------------|----------|
| AI Questions | Limited | Higher Daily Limit | Unlimited |
| Quizzes | Limited | Extended Access | Unlimited |
| Flashcards | ✅ | ✅ | Unlimited |
| Study Plans | Limited | Unlimited | Unlimited |
| AI Lessons | Limited | Unlimited | Unlimited |

---

# 🏗 Technology Stack

| Technology | Purpose |
|------------|----------|
| Python | Backend |
| Streamlit | User Interface |
| Google Gemini | AI Model |
| OpenRouter | AI Gateway |
| Firebase Authentication | User Authentication |
| Google Firestore | Cloud Database |
| SQLite | Local Analytics Cache |
| M-Pesa Daraja API | Payments |
| Plotly | Analytics |
| Pillow | Image Processing |
| Pandas | Data Analysis |

---

# 📂 Project Structure

```text
Mwalimu-AI/
│
├── assets/
│   ├── logo.png
│   ├── mpesa_logo.png
│   └── icons/
│
├── services/
│   ├── auth_service.py
│   ├── db_service.py
│   ├── payment_service.py
│   ├── tier_guard.py
│   ├── ui_components.py
│   ├── analytics.py
│   └── database.py
│
├── curriculum/
│   ├── grade10/
│   ├── grade11/
│   └── grade12/
│
├── main.py
├── requirements.txt
├── .streamlit/
│   └── secrets.toml
└── README.md
```

---

# 🚀 Installation

## Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/Mwalimu-AI.git

cd Mwalimu-AI
```

---

## Create Virtual Environment

### Windows

```bash
python -m venv venv

venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv venv

source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Secrets

Create:

```text
.streamlit/secrets.toml
```

Example:

```toml
[firebase]

...

[openrouter]

...

[google_oauth]

...

[mpesa]

consumer_key=""

consumer_secret=""

shortcode=""

passkey=""

callback_url=""
```

---

# ▶ Run Application

```bash
streamlit run main.py
```

Open:

```
http://localhost:8501
```

---

# 📸 Screenshots

Add screenshots here:

- Home Dashboard
- AI Tutor
- Quiz Generator
- Lesson Generator
- Flashcards
- Analytics Dashboard
- M-Pesa Payment Dialog

---

# 🔐 Security

- Firebase Authentication
- Google OAuth Login
- Firestore Security Rules
- Tier Guard Protection
- Daily Usage Tracking
- Secure M-Pesa STK Push
- Environment Secrets

---

# 📈 Roadmap

## Completed

- AI Tutor
- Adaptive Learning
- Quiz Generator
- Lesson Generator
- Flashcards
- Personalized Study Plans
- Firestore Migration
- Tier Guard
- M-Pesa Payments
- Professional UI

## Upcoming

- Voice Tutor
- Parent Dashboard
- Teacher Dashboard
- Android App
- PDF Export
- Offline Learning
- Gamification
- AI Revision Coach

---

# 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create your feature branch

```bash
git checkout -b feature-name
```

3. Commit changes

```bash
git commit -m "Added new feature"
```

4. Push

```bash
git push origin feature-name
```

5. Open a Pull Request

---

# 📄 License

Licensed under the **MIT License**.

---

# 👨‍💻 Developer

**JP Cyber Services**

### 🎓 Mwalimu AI App

**Shaping Minds, Shifting Futures.**

Built with ❤️ for Kenyan learners.