import re
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import streamlit as st


APP_TITLE = "AI Workflow Automation & Reporting Assistant"
APP_SUBTITLE = "Workflow intake, structured extraction, draft generation, and validation"
DISCLAIMER = (
    "This prototype uses example data only. It demonstrates a workflow automation pattern "
    "without exposing internal documents, screenshots, or private information."
)

SAMPLES = {
    "Event Workflow Example": (
        "We are planning a stakeholder briefing next Friday in San Diego. Guest speaker "
        "is Rachel Cohen. Need a newsletter blurb, website update, and internal summary. "
        "Audience is partners and team members. Registration link is not ready yet. "
        "Time still needs to be confirmed. Jana asked to keep the tone clear and "
        "professional."
    ),
    "Newsletter Workflow Example": (
        "Newsletter needs a short update about upcoming training sessions, a reminder "
        "about stakeholder support, and a note about the documentation project. Need "
        "to summarize in a friendly tone. Some dates are still missing. Include an action "
        "item to confirm the training schedule before sending."
    ),
    "Website Update Example": (
        "Website team needs updated text for the programs page. Add short description "
        "for upcoming workshops and team events. Need to make it concise and clear. "
        "Missing final event dates and registration details. Should be reviewed before "
        "publishing."
    ),
}

DEFAULT_OLLAMA_HOST = "https://ollama.com"
DEFAULT_OLLAMA_MODEL = "gpt-oss:120b-cloud"
APP_DIR = Path(__file__).resolve().parent


def load_env_file(path: str | Path = APP_DIR / ".env") -> dict[str, str]:
    """Load simple KEY=value entries without requiring an extra dependency."""
    path = Path(path)
    values = {}
    if not path.exists():
        return values

    with path.open("r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and not os.environ.get(key):
                os.environ[key] = value
            values[key] = value
    return values


def configure_page() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="⚙️",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            :root {
                --primary: #1d4f73;
                --accent: #2f7d6d;
                --ink: #1f2937;
                --muted: #6b7280;
                --soft: #f5f7fa;
                --line: #d9e2ec;
                --warn-bg: #fff7ed;
                --warn: #b45309;
                --ok-bg: #ecfdf5;
                --ok: #047857;
                --review-bg: #eff6ff;
                --review: #1d4ed8;
            }

            .main .block-container {
                padding-top: 1.35rem;
                padding-bottom: 3rem;
            }

            header[data-testid="stHeader"],
            div[data-testid="stToolbar"],
            div[data-testid="stDecoration"],
            div[data-testid="stStatusWidget"] {
                display: none;
            }

            h1, h2, h3 {
                letter-spacing: 0;
            }

            .hero {
                border: 1px solid rgba(148, 163, 184, 0.28);
                border-left: 5px solid #38bdf8;
                background: rgba(15, 23, 42, 0.74);
                padding: 1rem 1.15rem;
                border-radius: 8px;
                margin-bottom: 1.35rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.12);
            }

            .hero h1 {
                color: #f9fafb;
                font-size: 2rem;
                line-height: 1.16;
                margin: 0 0 0.35rem;
            }

            .subtitle {
                color: #cbd5e1;
                font-size: 1rem;
                margin: 0 0 0.7rem;
            }

            .disclaimer {
                color: #e5e7eb;
                font-size: 0.92rem;
                line-height: 1.45;
                border-top: 1px solid rgba(148, 163, 184, 0.25);
                padding-top: 0.7rem;
            }

            .card {
                border: 1px solid var(--line);
                background: #ffffff;
                padding: 1rem;
                border-radius: 8px;
                min-height: 142px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
            }

            .card-label {
                color: var(--muted);
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                margin-bottom: 0.5rem;
            }

            .card-value {
                color: var(--ink);
                font-size: 1.02rem;
                font-weight: 650;
                line-height: 1.35;
            }

            .badge {
                display: inline-block;
                padding: 0.18rem 0.5rem;
                border-radius: 999px;
                font-size: 0.78rem;
                font-weight: 700;
                margin-top: 0.65rem;
            }

            .badge-ok {
                color: var(--ok);
                background: var(--ok-bg);
                border: 1px solid #a7f3d0;
            }

            .badge-warn {
                color: var(--warn);
                background: var(--warn-bg);
                border: 1px solid #fed7aa;
            }

            .badge-review {
                color: var(--review);
                background: var(--review-bg);
                border: 1px solid #bfdbfe;
            }

            .flow {
                display: flex;
                flex-wrap: wrap;
                gap: 0.55rem;
                align-items: center;
                margin: 0.5rem 0 1rem;
            }

            .flow-box {
                border: 1px solid var(--line);
                background: #ffffff;
                border-radius: 8px;
                padding: 0.7rem 0.85rem;
                font-weight: 700;
                color: var(--ink);
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }

            .flow-arrow {
                color: var(--primary);
                font-weight: 900;
            }

            .report-box {
                background: #fbfcfe;
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 1rem;
                white-space: pre-wrap;
                font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
                font-size: 0.92rem;
                color: #273244;
            }

            div[data-testid="stMetric"] {
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 0.75rem 0.9rem;
                background: #ffffff;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.35rem;
            }

            .validation-row {
                display: grid;
                grid-template-columns: minmax(220px, 1.1fr) 150px minmax(260px, 1.4fr);
                gap: 0.75rem;
                align-items: center;
                border-bottom: 1px solid var(--line);
                padding: 0.72rem 0;
            }

            .validation-row:first-child {
                border-top: 1px solid var(--line);
            }

            .validation-name {
                font-weight: 650;
                color: #f9fafb;
            }

            .validation-note {
                color: #e5e7eb;
                font-size: 0.9rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Project Overview")
        st.write(
            "A Streamlit prototype showing how messy workflow notes can be "
            "converted into structured data, draft communications, validation checks, "
            "and a final workflow report."
        )

        # st.header("Demo Steps")
        # steps = [
        #     "Load or paste raw workflow notes",
        #     "Extract structured data",
        #     "Detect automation opportunities",
        #     "Generate draft outputs",
        #     "Validate results",
        #     "Create final report",
        # ]
        # for index, step in enumerate(steps, start=1):
        #     st.write(f"{index}. {step}")

        st.header("Workflow Pattern")
        st.write(
            "This workflow assistant shows a repeatable process: collect scattered inputs, "
            "structure the data, generate summaries, validate outputs, and document the result."
        )


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def contains_any(text: str, keywords: list[str]) -> bool:
    lower_text = text.lower()
    return any(keyword in lower_text for keyword in keywords)


def assess_input_quality(raw_notes: str) -> dict:
    text = normalize_text(raw_notes)
    lower_text = text.lower()
    words = re.findall(r"[A-Za-z]{3,}", lower_text)
    unique_words = set(words)

    workflow_keywords = {
        "meeting",
        "appointment",
        "session",
        "invite",
        "booking",
        "book",
        "gym",
        "swimming",
        "tomorrow",
        "tommorow",
        "today",
        "pm",
        "am",
        "event",
        "newsletter",
        "website",
        "summary",
        "report",
        "update",
        "program",
        "class",
        "workshop",
        "registration",
        "audience",
        "speaker",
        "publish",
        "review",
        "schedule",
        "draft",
        "action",
        "support",
        "documentation",
    }
    task_keywords = {
        "need",
        "needs",
        "create",
        "draft",
        "write",
        "summarize",
        "confirm",
        "review",
        "publish",
        "update",
        "add",
        "include",
        "prepare",
        "planning",
        "book",
        "invite",
    }

    matched_workflow = sorted(unique_words & workflow_keywords)
    matched_tasks = sorted(unique_words & task_keywords)
    reasons = []

    if len(words) < 5:
        reasons.append("The note is too short to analyze reliably.")
    if len(unique_words) < 4:
        reasons.append("The note does not contain enough distinct workflow details.")
    has_time_signal = bool(re.search(r"\b\d{1,2}\s*(?::\d{2})?\s*(am|pm)\b", lower_text))
    has_date_signal = contains_any(lower_text, ["today", "tomorrow", "tommorow", "next week", "next friday"])
    has_named_people = len(re.findall(r"\b[A-Z][a-z]{2,}\b", text)) >= 1

    if not matched_workflow and not (has_time_signal or has_date_signal or has_named_people):
        reasons.append("No recognizable workflow topic was found.")
    if not matched_tasks:
        reasons.append("No clear task, request, or next step was found.")

    return {
        "is_valid": not reasons,
        "reasons": reasons,
        "matched_workflow": matched_workflow,
        "matched_tasks": matched_tasks,
    }


def extract_between(text: str, start_pattern: str, end_patterns: list[str]) -> str | None:
    match = re.search(start_pattern, text, flags=re.IGNORECASE)
    if not match:
        return None

    start_index = match.end()
    remainder = text[start_index:]
    end_indexes = [
        match.start()
        for pattern in end_patterns
        if (match := re.search(pattern, remainder, flags=re.IGNORECASE))
    ]
    end_index = min(end_indexes) if end_indexes else len(remainder)
    value = remainder[:end_index].strip(" .,:;-")
    return value or None


def title_case_phrase(value: str) -> str:
    small_words = {"and", "or", "of", "for", "the", "a", "an", "in", "to"}
    words = value.split()
    return " ".join(
        word.lower() if index > 0 and word.lower() in small_words else word.capitalize()
        for index, word in enumerate(words)
    )


def infer_workflow_type(text: str) -> str:
    if contains_any(text, ["stakeholder briefing", "guest speaker", "seminars"]):
        return "Event Communication"
    if contains_any(text, ["website", "programs page", "publishing"]):
        return "Website Content Update"
    if contains_any(text, ["newsletter", "stakeholder support"]):
        return "Newsletter Planning"
    if contains_any(text, ["report", "reporting", "summary"]):
        return "Reporting Summary"
    if contains_any(text, ["invite", "book", "booking", "appointment", "session", "gym", "swimming"]):
        return "Task Planning"
    return "General Workflow Intake"


def infer_topic(text: str, workflow_type: str) -> str:
    lower_text = text.lower()
    if "stakeholder briefing" in lower_text:
        return "Stakeholder Briefing"
    if "training sessions" in lower_text:
        return "Training Sessions, Stakeholder Support, and Documentation Project"
    if "programs page" in lower_text:
        return "Programs Page Updates"
    if "workshops" in lower_text and "team events" in lower_text:
        return "Workshops and Team Events"
    if workflow_type == "Task Planning":
        first_sentence = re.split(r"[.!?]", text)[0].strip()
        return first_sentence.capitalize() if first_sentence else "Task Plan"
    if workflow_type == "Event Communication":
        return "Upcoming Community Event"
    return "Not specified"


def infer_audience(text: str) -> str:
    audience = extract_between(text, r"audience is", [r"\.", r"registration", r"time"])
    if audience:
        return audience[0].upper() + audience[1:]
    if contains_any(text, ["team members", "partners"]):
        return "Partners and team members"
    if contains_any(text, ["support"]):
        return "Stakeholders and supporters"
    if contains_any(text, ["invite"]):
        invite_match = re.search(
            r"invite\s+(.+?)(?:\.|,|\band\b\s+need\b|\bneed\b|$)",
            text,
            flags=re.IGNORECASE,
        )
        if invite_match:
            invitees = re.split(r"\s+and\s+|,", invite_match.group(1), flags=re.IGNORECASE)
            cleaned_invitees = [
                name.strip().title()
                for name in invitees
                if name.strip() and name.strip().lower() not in {"need", "to"}
            ]
            if cleaned_invitees:
                return ", ".join(cleaned_invitees)
    return "Not specified"


def infer_location(text: str) -> str:
    match = re.search(r"\bin\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)", text)
    if match:
        return match.group(1)
    return "Not specified"


def infer_speaker(text: str) -> str:
    speaker = extract_between(text, r"guest speaker is", [r"\.", r"need", r"audience"])
    if speaker:
        return speaker
    return "Not specified"


def infer_outputs(text: str, workflow_type: str) -> list[str]:
    output_map = {
        "newsletter": "Newsletter Draft",
        "blurb": "Newsletter Blurb",
        "website": "Website Update",
        "internal summary": "Internal Summary",
        "summary": "Internal Summary",
        "action item": "Action Items",
        "invite": "Invitation Message",
        "book": "Booking Task",
        "booking": "Booking Task",
        "programs page": "Website Update",
    }
    outputs = []
    lower_text = text.lower()
    for keyword, output in output_map.items():
        if keyword in lower_text and output not in outputs:
            outputs.append(output)

    if not outputs:
        defaults = {
            "Event Communication": ["Newsletter Draft", "Website Update", "Internal Summary"],
            "Newsletter Planning": ["Newsletter Draft", "Action Items"],
            "Website Content Update": ["Website Update", "Internal Summary"],
            "Task Planning": ["Action Items"],
        }
        outputs = defaults.get(workflow_type, [])

    return outputs


def infer_missing_information(text: str) -> list[str]:
    lower_text = text.lower()
    missing = []

    if contains_any(lower_text, ["registration link is not ready", "registration details", "registration"]):
        missing.append("Registration link/details")
    if contains_any(lower_text, ["time still needs", "time needs", "confirmed timing"]):
        missing.append("Event time")
    if contains_any(lower_text, ["dates are still missing", "missing final event dates", "dates"]):
        missing.append("Final dates")
    if contains_any(lower_text, ["confirm class schedule", "class schedule"]):
        missing.append("Class schedule")

    return list(dict.fromkeys(missing))


def infer_tone(text: str) -> str:
    lower_text = text.lower()
    if "clear and professional" in lower_text:
        return "Clear and professional"
    if "friendly" in lower_text:
        return "Friendly"
    if "concise and clear" in lower_text:
        return "Concise and clear"
    return "Not specified"


def infer_priority(missing_info: list[str], outputs: list[str]) -> str:
    if len(missing_info) >= 3:
        return "High"
    if len(outputs) >= 3 or missing_info:
        return "Medium"
    return "Low"


def analyze_workflow(raw_notes: str) -> dict:
    text = normalize_text(raw_notes)
    workflow_type = infer_workflow_type(text)
    topic = infer_topic(text, workflow_type)
    audience = infer_audience(text)
    location = infer_location(text)
    speaker = infer_speaker(text)
    outputs = infer_outputs(text, workflow_type)
    missing_info = infer_missing_information(text)
    tone = infer_tone(text)
    if topic == "Not specified":
        missing_info.append("Workflow topic")
    if audience == "Not specified":
        missing_info.append("Audience")
    if not outputs:
        missing_info.append("Requested output")
    if tone == "Not specified":
        missing_info.append("Tone")
    missing_info = list(dict.fromkeys(missing_info))
    priority = infer_priority(missing_info, outputs)
    review_status = "Human review required" if missing_info else "Ready for review"

    return {
        "raw_notes": text,
        "workflow_type": workflow_type,
        "topic": topic,
        "audience": audience,
        "location": location,
        "speaker": speaker,
        "outputs": outputs,
        "missing_info": missing_info,
        "tone": tone,
        "priority": priority,
        "review_status": review_status,
    }


def status_for_field(field: str, value: str, analysis: dict) -> str:
    if value in {"Not specified", "None identified"}:
        return "Missing"
    if field in {"Missing Information", "Review Status"} and analysis["missing_info"]:
        return "Review required"
    if field in {"Location", "Speaker"} and value == "Not specified":
        return "Needs confirmation"
    if field == "Priority" and value in {"Medium", "High"}:
        return "Needs confirmation"
    return "Complete"


def structured_rows(analysis: dict) -> list[dict]:
    rows = [
        ("Workflow Type", analysis["workflow_type"]),
        ("Event/Content Topic", analysis["topic"]),
        ("Audience", analysis["audience"]),
        ("Location", analysis["location"]),
        ("Speaker", analysis["speaker"]),
        ("Output Needed", ", ".join(analysis["outputs"])),
        (
            "Missing Information",
            ", ".join(analysis["missing_info"]) if analysis["missing_info"] else "None identified",
        ),
        ("Tone", analysis["tone"]),
        ("Priority", analysis["priority"]),
        ("Review Status", analysis["review_status"]),
    ]
    return [
        {
            "Field": field,
            "Extracted Value": value,
            "Status": status_for_field(field, value, analysis),
        }
        for field, value in rows
    ]


def sentence_list(items: list[str]) -> str:
    if not items:
        return "none identified"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def build_fallback_drafts(analysis: dict) -> dict:
    topic = analysis["topic"]
    location = analysis["location"]
    speaker = analysis["speaker"]
    audience = analysis["audience"]
    missing = analysis["missing_info"]
    tone = analysis["tone"].lower()

    location_phrase = f" in {location}" if location != "Not specified" else ""
    speaker_phrase = f" featuring guest speaker {speaker}" if speaker != "Not specified" else ""
    missing_sentence = (
        f" Final details still needing confirmation include {sentence_list(missing).lower()}."
        if missing
        else " Details have been reviewed and are ready for final approval."
    )

    newsletter = (
        f"Join us for an upcoming {topic.lower()}{location_phrase}{speaker_phrase}. "
        f"This {tone} update is intended for {audience.lower()} and highlights the next step "
        f"in the workflow.{missing_sentence}"
    )

    website = (
        f"{topic} is being prepared as part of upcoming team programming"
        f"{location_phrase}{speaker_phrase}. Please check back soon for confirmed timing, "
        "registration details, and final participation information."
    )

    internal_summary = (
        f"The team is preparing materials for {topic.lower()}. Current outputs include "
        f"{sentence_list(analysis['outputs']).lower()}. Key missing items are "
        f"{sentence_list(missing).lower()}. {analysis['review_status']} before publishing "
        "or sharing externally."
    )

    action_items = []
    raw_notes = analysis["raw_notes"]
    task_sentences = [
        sentence.strip(" .")
        for sentence in re.split(r"[.!?]", raw_notes)
        if sentence.strip()
    ]
    for sentence in task_sentences:
        lowered = sentence.lower()
        if lowered.startswith("need to "):
            action_items.append(sentence[0].upper() + sentence[1:])
        elif lowered.startswith("need "):
            action_items.append(sentence[0].upper() + sentence[1:])
        elif lowered.startswith(("confirm", "book", "invite", "review", "send", "update")):
            action_items.append(sentence[0].upper() + sentence[1:])

    if any("time" in item.lower() for item in missing):
        action_items.append("Confirm final event time")
    if any("date" in item.lower() for item in missing):
        action_items.append("Confirm final dates")
    if any("registration" in item.lower() for item in missing):
        action_items.append("Add registration link or registration details")
    if any("class schedule" in item.lower() for item in missing):
        action_items.append("Confirm class schedule before sending")
    action_items.extend(
        ["Review generated text for tone and accuracy"]
    )
    if analysis["workflow_type"] == "Task Planning":
        action_items.append("Confirm tasks are complete after follow-up")
    else:
        action_items.extend(
            [
                "Approve website or newsletter copy before publishing",
                "Save final version for reporting and documentation",
            ]
        )
    action_items = list(dict.fromkeys(action_items))

    return {
        "Newsletter Draft": newsletter,
        "Website Update": website,
        "Internal Summary": internal_summary,
        "Action Items": action_items,
    }


def parse_ollama_response(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content)

    if not content.startswith("{"):
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            content = content[start : end + 1]

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {}

    required_keys = {"Newsletter Draft", "Website Update", "Internal Summary", "Action Items"}
    if not required_keys.issubset(parsed):
        return {}
    if not isinstance(parsed["Action Items"], list):
        parsed["Action Items"] = [str(parsed["Action Items"])]
    return parsed


def call_ollama_cloud(
    analysis: dict,
    api_key: str,
    model: str,
    host: str,
) -> tuple[dict | None, str | None]:
    prompt = f"""
Create concise draft workflow outputs for an internal workflow automation prototype.
Use only the provided workflow information. Do not invent final dates, times, or registration links.
Return only valid JSON. Do not include markdown, commentary, or code fences.
Use this exact schema:
{{
  "Newsletter Draft": "string",
  "Website Update": "string",
  "Internal Summary": "string",
  "Action Items": ["string"]
}}

Structured input:
Workflow Type: {analysis["workflow_type"]}
Topic: {analysis["topic"]}
Audience: {analysis["audience"]}
Location: {analysis["location"]}
Speaker: {analysis["speaker"]}
Outputs Needed: {", ".join(analysis["outputs"])}
Missing Information: {sentence_list(analysis["missing_info"])}
Tone: {analysis["tone"]}
Review Status: {analysis["review_status"]}
Raw Notes: {analysis["raw_notes"]}
""".strip()

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You create practical workflow drafts from structured workflow notes.",
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2},
    }
    endpoint = host.rstrip("/") + "/api/chat"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return None, f"Ollama Cloud API error. Fallback activated. Details: {error}"

    try:
        content = data["message"]["content"]
    except (KeyError, TypeError):
        return None, "Ollama Cloud API error. Fallback activated. Unexpected response format."

    parsed = parse_ollama_response(content)
    if not parsed:
        return None, "Ollama Cloud API error. Fallback activated. Output was not valid structured JSON."
    return parsed, None


def generate_drafts(
    analysis: dict,
    api_key: str,
    model: str,
    host: str,
) -> tuple[dict, str | None]:
    if not api_key:
        return (
            build_fallback_drafts(analysis),
            "Ollama Cloud API key not found. Fallback activated.",
        )

    ollama_drafts, warning = call_ollama_cloud(analysis, api_key, model, host)
    if ollama_drafts:
        return ollama_drafts, None
    return build_fallback_drafts(analysis), warning or "Ollama Cloud API error. Fallback activated."


def opportunity_data(analysis: dict) -> list[dict]:
    outputs = analysis["outputs"]
    missing = analysis["missing_info"]
    missing_text = sentence_list(missing).capitalize()
    draft_outputs = [output for output in outputs if output != "Action Items"]
    repetitive_task = (
        ", ".join(draft_outputs)
        if draft_outputs
        else "Summary and action-item preparation"
    )
    opportunity = (
        f"Generate {len(outputs)} reusable output types from one structured intake"
        if len(outputs) > 1
        else "Standardize the intake and review process"
    )
    manual_check = missing_text if missing else "Final human approval"
    risk = "High" if len(missing) >= 3 else "Medium" if missing else "Low"
    recommended_action = (
        "Resolve missing fields before publishing"
        if missing
        else "Proceed to human approval"
    )

    return [
        {
            "label": "Repetitive Task Found",
            "value": repetitive_task,
            "badge": "Detected",
            "badge_class": "badge-ok",
        },
        {
            "label": "Automation Opportunity",
            "value": opportunity,
            "badge": "High value",
            "badge_class": "badge-ok",
        },
        {
            "label": "Manual Check Needed",
            "value": manual_check,
            "badge": "Human step",
            "badge_class": "badge-warn",
        },
        {
            "label": "Risk Level",
            "value": risk,
            "badge": "Based on missing fields",
            "badge_class": "badge-review" if risk == "Low" else "badge-warn",
        },
        {
            "label": "Recommended Action",
            "value": recommended_action,
            "badge": "Required",
            "badge_class": "badge-review",
        },
    ]


def card(label: str, value: str, badge: str, badge_class: str) -> None:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-label">{label}</div>
            <div class="card-value">{value}</div>
            <span class="badge {badge_class}">{badge}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def validation_rows(analysis: dict) -> list[dict]:
    has_missing = bool(analysis["missing_info"])
    tone_missing = analysis["tone"] == "Not specified"
    return [
        {
            "check": "Source information reviewed",
            "status": "Complete",
            "badge_class": "badge-ok",
            "note": "Input notes were processed into structured fields.",
        },
        {
            "check": "Missing fields identified",
            "status": "Gaps found" if has_missing else "No gaps found",
            "badge_class": "badge-warn" if has_missing else "badge-ok",
            "note": sentence_list(analysis["missing_info"]).capitalize() if has_missing else "No missing fields detected.",
        },
        {
            "check": "Generated output checked against input",
            "status": "Review required",
            "badge_class": "badge-review",
            "note": "Drafts must be checked before use.",
        },
        {
            "check": "Tone reviewed",
            "status": "Needs confirmation" if tone_missing else "Complete",
            "badge_class": "badge-warn" if tone_missing else "badge-ok",
            "note": "Tone was not specified." if tone_missing else f"Detected tone: {analysis['tone']}.",
        },
        {
            "check": "Privacy/internal data check",
            "status": "Complete",
            "badge_class": "badge-ok",
            "note": "Example data only; no private documents are used.",
        },
        {
            "check": "Human approval before publishing",
            "status": "Required",
            "badge_class": "badge-review",
            "note": "Final approval remains a human responsibility.",
        },
        {
            "check": "Final document readiness",
            "status": "Ready for review",
            "badge_class": "badge-review",
            "note": "Review package is prepared; publishing depends on approval.",
        },
    ]


def render_validation(analysis: dict) -> None:
    left, right = st.columns([1.25, 1])

    with left:
        for row in validation_rows(analysis):
            st.markdown(
                f"""
                <div class="validation-row">
                    <div class="validation-name">{row["check"]}</div>
                    <div><span class="badge {row["badge_class"]}">{row["status"]}</span></div>
                    <div class="validation-note">{row["note"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with right:
        if analysis["missing_info"]:
            st.warning("Missing fields or confirmation points were found.")
            for item in analysis["missing_info"]:
                st.write(f"- {item} needs confirmation")
            st.info("Human review required before publishing.")
        else:
            st.success("No missing fields detected in the example notes.")
            st.info("Human approval is still recommended before publication.")


def build_report(analysis: dict, drafts: dict) -> str:
    input_summary = (
        analysis["raw_notes"][:260] + "..."
        if len(analysis["raw_notes"]) > 260
        else analysis["raw_notes"]
    )
    missing = sentence_list(analysis["missing_info"]).capitalize()
    final_status = (
        "Ready for review, not ready for publishing"
        if analysis["missing_info"]
        else "Ready for final approval"
    )
    next_steps = (
        "Confirm missing details, review generated content, approve final version, "
        "then publish or share internally."
        if analysis["missing_info"]
        else "Complete final human approval, then publish or share internally."
    )

    return f"""Workflow Automation Report

Processed Workflow Type: {analysis["workflow_type"]}
Input Summary: {input_summary}
Generated Outputs: {", ".join(drafts.keys())}
Missing Information: {missing}
Validation Status: {analysis["review_status"]}
Final Status: {final_status}
Recommended Next Steps: {next_steps}

Data Note: This report was generated from the workflow notes provided in the app."""


def initialize_session_state() -> None:
    if "raw_notes" not in st.session_state:
        st.session_state.raw_notes = ""
    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if "drafts" not in st.session_state:
        st.session_state.drafts = None
    if "ai_warning" not in st.session_state:
        st.session_state.ai_warning = None
    if "last_analyzed_text" not in st.session_state:
        st.session_state.last_analyzed_text = ""


def main() -> None:
    load_env_file()
    configure_page()
    inject_styles()
    render_sidebar()
    initialize_session_state()

    st.markdown(
        f"""
        <div class="hero">
            <h1>{APP_TITLE}</h1>
            <div class="subtitle">{APP_SUBTITLE}</div>
            <div class="disclaimer">{DISCLAIMER}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.header("1. Load or Paste Workflow Notes")
    example_col, button_col = st.columns([2, 1])
    with example_col:
        selected_example = st.selectbox("Choose an example workflow", list(SAMPLES.keys()))
    with button_col:
        st.write("")
        st.write("")
        if st.button("Load Example", use_container_width=True):
            st.session_state.raw_notes = SAMPLES[selected_example]
            st.session_state.analysis = None
            st.session_state.drafts = None
            st.session_state.ai_warning = None

    raw_notes = st.text_area(
        "Paste raw internal notes, event details, newsletter notes, or reporting updates.",
        key="raw_notes",
        height=170,
        placeholder="Paste notes here or load one of the examples above.",
    )

    analyze_clicked = st.button("Analyze Workflow", type="primary", use_container_width=True)

    if analyze_clicked:
        if not raw_notes.strip():
            st.warning("Please load an example or paste workflow notes before analyzing.")
            st.session_state.analysis = None
            st.session_state.drafts = None
            st.session_state.ai_warning = None
        else:
            input_quality = assess_input_quality(raw_notes)
            if not input_quality["is_valid"]:
                st.error(
                    "This does not look like enough workflow information to analyze. "
                    "Please add a clear topic, requested output, task, audience, date, "
                    "owner, or missing detail."
                )
                for reason in input_quality["reasons"]:
                    st.write(f"- {reason}")
                st.session_state.analysis = None
                st.session_state.drafts = None
                st.session_state.ai_warning = None
            else:
                with st.status("Generating workflow analysis...", expanded=True) as status:
                    st.write("Cleaning notes and extracting structured fields.")
                    analysis_result = analyze_workflow(raw_notes)
                    st.write("Generating draft outputs and action items.")
                    api_key = os.getenv("OLLAMA_API_KEY", "")
                    model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
                    host = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
                    drafts_result, ai_warning = generate_drafts(analysis_result, api_key, model, host)
                    st.write("Preparing validation checks and final report.")
                    status.update(label="Workflow analysis ready.", state="complete", expanded=False)

                st.session_state.analysis = analysis_result
                st.session_state.drafts = drafts_result
                st.session_state.ai_warning = ai_warning
                st.session_state.last_analyzed_text = raw_notes

    analysis = st.session_state.analysis
    drafts = st.session_state.drafts
    if analysis is None or drafts is None:
        st.info("Load an example or paste notes, then click Analyze Workflow to generate the output.")
        st.stop()

    if st.session_state.ai_warning:
        st.warning(st.session_state.ai_warning)

    st.header("2. Structured Data Extraction")
    st.dataframe(structured_rows(analysis), use_container_width=True, hide_index=True)

    st.header("3. Automation Assessment")
    opportunities = opportunity_data(analysis)
    cols = st.columns(len(opportunities))
    for col, item in zip(cols, opportunities):
        with col:
            card(item["label"], item["value"], item["badge"], item["badge_class"])

    st.header("4. AI-Assisted Draft Outputs")
    newsletter_tab, website_tab, summary_tab, actions_tab = st.tabs(
        ["Newsletter Draft", "Website Update", "Internal Summary", "Action Items"]
    )
    with newsletter_tab:
        st.write(drafts["Newsletter Draft"])
    with website_tab:
        st.write(drafts["Website Update"])
    with summary_tab:
        st.write(drafts["Internal Summary"])
    with actions_tab:
        for item in drafts["Action Items"]:
            st.write(f"- {item}")

    st.header("5. Validation and Reliability")
    render_validation(analysis)

    st.header("6. Final Workflow Report")
    report = build_report(analysis, drafts)
    with st.expander("View generated report", expanded=True):
        st.markdown(f'<div class="report-box">{report}</div>', unsafe_allow_html=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    st.download_button(
        "Download Report",
        data=report,
        file_name=f"workflow-automation-report-{timestamp}.txt",
        mime="text/plain",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
