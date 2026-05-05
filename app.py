import os
import json
from flask import Flask, render_template, request, jsonify, stream_with_context, Response
import anthropic

app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


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
        "You are a senior drilling estimator at Forged Drill Co., a North American drilling contractor "
        "headquartered in Pilot Butte, Saskatchewan, with offices in San Antonio TX and Denver CO. "
        "Forged Drill Co. offers: Environmental Drilling, Resource Coring, Hydrogeological Drilling, "
        "Geotechnical Drilling, Geothermal Drilling, Oil Sands, Pipeline Services, and Dewatering Systems. "
        "Extract key information from RFPs and produce concise internal job briefs. "
        "Identify the applicable drilling discipline(s) and focus on rig requirements, metreage, "
        "hole specifications, formation context, safety requirements, and commercial terms. "
        "Be factual and structured. Use plain text only, no markdown symbols."
    )
    prompt = f"""From this RFP, produce a structured internal job brief for Forged Drill Co. with these sections:
PROJECT OVERVIEW, CLIENT, LOCATION, DRILLING DISCIPLINE (which Forged service applies), SCOPE SUMMARY,
RIG REQUIREMENTS, KEY QUANTITIES (metres / hole count / diameters / depths), DURATION & PROGRAMME,
SUBMISSION DEADLINE, MOBILISATION REQUIREMENTS, SAFETY & REGULATORY REQUIREMENTS, SPECIAL REQUIREMENTS,
KNOWN RISKS & HAZARDS, and INITIAL OBSERVATIONS.

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
        "You are a drilling operations manager at Forged Drill Co., a North American drilling contractor "
        "offering Environmental Drilling, Resource Coring, Hydrogeological Drilling, Geotechnical Drilling, "
        "Geothermal Drilling, Oil Sands, Pipeline Services, and Dewatering Systems. "
        "Generate targeted questions for the operations team to answer so the estimator can build a cost and proposal. "
        "Tailor questions to the specific drilling discipline identified in the brief. "
        "Always include safety and HSE compliance questions — safety is Forged Drill Co.'s core value. "
        "Return ONLY a JSON array, no markdown, no preamble. "
        'Each item: {"id":"q1","category":"Crew & Personnel","question":"Full question text",'
        '"hint":"Brief guidance for ops","type":"text"}. '
        "Categories: Crew & Personnel, Rig Selection & Equipment, Drilling Programme, "
        "Production Rates, Schedule & Mobilisation, Formation & Ground Conditions, "
        "Fluids & Consumables, Health Safety & Environment, Subcontractors & Suppliers, "
        "Risks & Assumptions, Margin & Commercials."
    )
    prompt = f"Based on this drilling job brief, generate 14-18 targeted operations questions for estimating:\n\n{brief}"

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2500,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        start = raw.find('[')
        end = raw.rfind(']')
        if start == -1 or end == -1:
            return jsonify({"error": "No JSON array found in AI response", "raw": raw[:1000]}), 500
        questions = json.loads(raw[start:end + 1])
        return jsonify({"questions": questions})
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Failed to parse questions: {e}", "raw": raw[:1000]}), 500
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
        "You are a senior drilling estimator at Forged Drill Co., a North American drilling contractor "
        "offering Environmental Drilling, Resource Coring, Hydrogeological Drilling, Geotechnical Drilling, "
        "Geothermal Drilling, Oil Sands, Pipeline Services, and Dewatering Systems. "
        "Produce a structured cost estimate and proposal outline in plain text only — "
        "no markdown symbols, just clear section headings in CAPS. "
        "Use drilling industry terminology appropriate to the discipline. "
        "Always include a safety and compliance cost line — safety is Forged Drill Co.'s core value ('Forged in Safety'). "
        "Be specific with numbers where ops data allows; flag gaps clearly."
    )
    prompt = f"""Using this job brief and operations team input, produce a draft drilling estimate and proposal outline for Forged Drill Co.

JOB BRIEF:
{brief}

OPERATIONS TEAM INPUT:
{qa_text}

Structure your output with these sections:
SCOPE SUMMARY
DRILLING DISCIPLINE & APPLICABLE SERVICES
CREW & PERSONNEL ESTIMATE
RIG & EQUIPMENT COSTS
DRILLING PRODUCTION ASSUMPTIONS
FLUIDS & CONSUMABLES ESTIMATE
MOBILISATION & DEMOBILISATION
HEALTH SAFETY & ENVIRONMENT (HSE) COSTS
PROGRAMME SUMMARY
SUBCONTRACTOR & SPECIALIST ALLOWANCES
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
