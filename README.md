# AI Workflow Automation & Reporting Assistant

A Streamlit application for converting unstructured workflow notes into structured fields, draft outputs, validation checks, and a final workflow report.

The project demonstrates a practical automation pattern: collect scattered inputs, extract key workflow details, generate useful first drafts, identify missing information, and create a review-ready report. It is designed to run locally and remain reliable even when an external model is unavailable.

## Features

- Unstructured workflow note intake
- Basic input-quality validation
- Structured data extraction
- Automation assessment based on detected outputs and missing fields
- AI-assisted draft generation with Ollama Cloud
- Deterministic fallback generation when the API is unavailable
- Validation and human-review checkpoint
- Downloadable workflow report

## Tech Stack

- Python
- Streamlit
- Ollama Cloud API

## Setup

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
cp .env.example .env
```

Then add your Ollama API key:

```bash
OLLAMA_API_KEY=your_api_key_here
OLLAMA_HOST=https://ollama.com
OLLAMA_MODEL=gpt-oss:120b-cloud
```

4. Run the app:

```bash
streamlit run app.py
```

## Usage

1. Load an example or paste workflow notes.
2. Click **Analyze Workflow**.
3. Review the extracted fields and automation assessment.
4. Review generated drafts, action items, and validation checks.
5. Download the final workflow report.

## Reliability

The app validates input before generating outputs. If the notes are too vague or do not contain a recognizable workflow, the app stops and asks for clearer information.

When Ollama Cloud is configured, the app uses it for draft generation. If the API key is missing, the API request fails, or the model response cannot be parsed, the app automatically uses deterministic fallback generation so the workflow remains available.

## Data

The included examples are illustrative workflow scenarios. No private or internal documents are required to run the app.
