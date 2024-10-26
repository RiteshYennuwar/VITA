# VITA - Virtual Insight for Tailored Academics

VITA is an educational platform that provides personalized learning experiences by utilizing AI-powered tools to generate study plans, quizzes, notes, and real-time assistance. VITA (Virtual Insight for Tailored Academics) is an advanced learning platform designed to revolutionize education through personalized and adaptive learning experiences.

It leverages Large Language Models (LLMs) to create customized study plans and educational content that aligns with individual students' needs, learning preferences, and pace



## Features
- *Document Processing*: Extracts text from uploaded documents for further analysis.
- *Embedding and Vector Management*: Uses embeddings for semantic search and document matching.
- *Query Handling*: Processes user queries and provides contextual answers.
- *Study Planning*: Generates personalized study plans based on analyzed content.
- *Notes Generation*: Automatically creates concise notes from the uploaded study material.
- *Real-Time Assistance*: Provides a chatbot interface for on-demand help.

## Project Structure

```plaintext
.
├── src
│   ├── _init_.py                # Package initialization
│   ├── document_processor.py      # Handles document parsing and text extraction
│   ├── embedding_handler.py       # Manages embedding creation and similarity checks
│   ├── pinecone_manager.py        # Interface with Pinecone for vector storage
│   ├── query_handler.py           # Processes and responds to user queries
│   ├── study_planner.py           # Generates study plans based on user needs
│   ├── utils.py                   # Utility functions for various tasks
├── static                         # Static files (CSS, JS, images)
├── templates                      # HTML templates for the web interface
├── .gitignore                     # Git ignore file
├── PyPDF2-1.26.0.tar.gz           # PDF processing library
├── README.md                      # Project documentation
├── app.py                         # Main application entry point
├── config.py                      # Configuration file for environment variables
├── dockerfile                     # Docker setup for containerization
├── requirements.txt               # Python dependencies
└── setup.py                       # Setup script for package distribution
