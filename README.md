# Personalized Networking Assistant

## Overview

The **Personalized Networking Assistant** is an AI-powered web application designed to help users initiate meaningful conversations during professional and social networking events. The application analyzes event descriptions, identifies relevant themes, and generates personalized conversation starters based on user interests.

Additionally, it provides fact verification using the Wikipedia API and maintains a history of generated responses along with user feedback for future interactions.

---

## Features

- AI-based event theme analysis
- Personalized conversation starter generation
- Fact verification using the Wikipedia API
- Conversation history management
- User feedback collection
- Interactive web interface

---

## Technologies Used

- Python
- FastAPI
- Streamlit
- DistilBERT (Zero-Shot Classification)
- GPT-2
- Hugging Face Transformers
- Wikipedia API
- Pytest

---

## Project Structure

```text
networking-assistant/
├── backend/
│   ├── main.py
│   ├── models/
│   ├── routes/
│   └── services/
├── frontend/
│   └── app.py
├── tests/
├── data/
│   └── history.json
├── requirements.txt
└── README.md
```

---

## Installation

### Clone the Repository

```bash
git clone <repository-url>
cd networking-assistant
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Backend Server

```bash
uvicorn backend.main:app --reload
```

### Run the Frontend Application

```bash
streamlit run frontend/app.py
```

After successful execution:

- **Frontend:** http://localhost:8501
- **API Documentation:** http://localhost:8000/docs

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/generate` | Generate personalized conversation starters |
| GET | `/api/v1/verify` | Verify information using the Wikipedia API |
| GET | `/api/v1/history` | Retrieve conversation history |
| POST | `/api/v1/feedback` | Submit user feedback |
| GET | `/health` | Check application status |

---

## Workflow

1. Enter an event description.
2. Provide a brief user profile or areas of interest.
3. Generate personalized conversation starters.
4. Verify information using the Fact Verification feature.
5. Review previous interactions in the History section.

---

## Testing

Run the following command to execute the test suite:

```bash
pytest
```

---

## Future Scope

- Integration with additional fact verification services
- Enhanced personalization using interaction history
- User authentication and profile management
- Cloud-based storage for conversation history
- Multilingual conversation generation

---

