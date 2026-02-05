"""
COMSOL Agent - Web UI
Serves a ChatGPT-like chat interface for the COMSOL agent.
"""
import os
import mph

from flask import Flask, render_template, request, jsonify

# Load agent module (must be after dotenv is loaded)
from dotenv import load_dotenv
load_dotenv("env.local")

from comsol_agent import (
    get_model_context,
    process_user_message,
)

app = Flask(__name__)

# Global model and conversation state (single-user dev tool)
model = None
messages = []
system_prompt_template = None


def init_model():
    """Load COMSOL model at startup."""
    global model, messages, system_prompt_template

    model_path = os.environ.get("COMSOL_MODEL", "Demo_file.mph")
    if not os.path.exists(model_path):
        # Fallback for original agent's default
        model_path = "Demo_file.mph"
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"No .mph file found. Expected: Demo_file.mph")

    print("Starting COMSOL client...")
    mph_client = mph.start(cores=1)
    print(f"Loading model: {model_path}...")
    model = mph_client.load(model_path)
    print("Model loaded.")

    model_context = get_model_context(model)
    system_prompt_template = (
        "You are an expert COMSOL Multiphysics assistant. "
        "You have control over the model via tools. "
        "When asked to change parameters, always offer to build geometry/mesh and solve/save as well.\n\n"
        "Current Model Context:\n{context}"
    )
    messages.clear()
    messages.append({"role": "system", "content": system_prompt_template.format(context=model_context)})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    if model is None:
        return jsonify({"error": "Model not loaded"}), 500

    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' in request body"}), 400

    user_content = data["message"].strip()
    if not user_content:
        return jsonify({"content": ""})

    try:
        reply = process_user_message(model, messages, user_content, system_prompt_template)
        return jsonify({"content": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    init_model()
    print("\n--- COMSOL Agent Web UI ---")
    print("Open http://127.0.0.1:5000 in your browser\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
