# COMSOL Agent

Chat with an AI assistant that controls your COMSOL model. Change parameters, build geometry, run studies, evaluate results—all via natural language.

**Setup**

- Put your OpenAI API key in `env.local` as `OPENAI_API_KEY`
- Add a `.mph` file (e.g. `Demo_file.mph`) in the project folder
- `pip install -r requirements.txt`

**Run**

- Terminal: `python comsol_agent.py`
- Web UI: `python webchat.py` then open http://127.0.0.1:5000

COMSOL must be installed. The mph Python package talks to it in the background.
