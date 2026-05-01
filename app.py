import os
import json
from flask import Flask, render_template, request, jsonify, stream_with_context, Response
import anthropic

app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate-brief", methods=["POST"])
def generate_brief():
    data = request.get_json()
    rfp_text = data.get("rfp_text", "").strip()
    if not rfp_text:
        return jsonify({"error": "No RFP text provided"}), 400

    system = (
        "You are a senior construction estimator. Extract key information from RFPs "
        "and produce concise internal job briefs. Be factual and structured. "
        "Use plain text only, no markdown symbols."
    )
    prompt = f"""From this RFP, produce a structured internal job brief with these sections:
PROJECT OVERVIEW, CLIENT, LOCATION, SCOPE SUMMARY, KEY QUANTITIES, DURATION & PROGRAMME,
SUBMISSION DEADLINE, SPECIAL REQUIREMENTS, KNOWN RISKS, and INITIAL OBSERVATIONS.

RFP:
{rfp_text}"""

    def generate():
        with client.messages.stream(
            model=MODEL,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/generate-questions", methods=["POST"])
def generate_questions():
    data = request.get_json()
    brief = data.get("brief", "").strip()
    if not brief:
        return jsonify({"error": "No brief provided"}), 400

    system = (
        "You are a construction operations manager. Generate targeted questions for "
        "operations teams to fill in for estimating purposes. "
        "Return ONLY a JSON array, no markdown, no preamble. "
        'Each item: {"id":"q1","category":"Crew & Labour","question":"Full question text",'
        '"hint":"Brief guidance for ops","type":"text"}. '
        "Categories: Crew & Labour, Plant & Equipment, Production Rates, "
        "Schedule & Programme, Subcontractors, Site Conditions, Risks & Assumptions, Margin & Commercials."
    )
    prompt = f"Based on this job brief, generate 12-16 targeted operations questions for estimating:\n\n{brief}"

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        clean = raw.replace("```json", "").replace("```", "").strip()
        questions = json.loads(clean)
        return jsonify({"questions": questions})
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse questions from AI response"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate-estimate", methods=["POST"])
def generate_estimate():
    data = request.get_json()
    brief = data.get("brief", "").strip()
    questions = data.get("questions", [])
    answers = data.get("answers", {})

    if not brief:
        return jsonify({"error": "No brief provided"}), 400

    qa_text = "\n\n".join(
        f"{q['question']}\nOps answer: {answers.get(q['id'], '(not provided)')}"
        for q in questions
    )

    system = (
        "You are a senior construction estimator. Produce a structured estimate draft "
        "in plain text only — no markdown symbols, just clear section headings in CAPS. "
        "Be specific with numbers where ops data allows; flag gaps clearly."
    )
    prompt = f"""Using this job brief and operations input, produce a draft estimate and proposal outline.

JOB BRIEF:
{brief}

OPERATIONS TEAM INPUT:
{qa_text}

Structure your output with these sections:
SCOPE SUMMARY
CREW & LABOUR ESTIMATE
PLANT & EQUIPMENT ESTIMATE
PRODUCTION RATE ASSUMPTIONS
PROGRAMME SUMMARY
SUBCONTRACTOR ALLOWANCES
RISK ALLOWANCES & CONTINGENCY
MARGIN & COMMERCIAL SUMMARY
KEY GAPS & ASSUMPTIONS REQUIRING SIGN-OFF
RECOMMENDED NEXT STEPS"""

    def generate():
        with client.messages.stream(
            model=MODEL,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
