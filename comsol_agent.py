import os
import mph
import pprint
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv('env.local')
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("Error: OPENAI_API_KEY not found in env.local")
    exit(1)

# Initialize OpenAI Client
client = OpenAI(api_key=api_key)

# ------------------------------------------------------------------------------
# Tool Definitions
# ------------------------------------------------------------------------------

def get_model_context(model):
    """Refreshes and returns the model context string."""
    context = []
    context.append("=== Model Overview ===")
    context.append(f"Modules: {model.modules()}")
    context.append(f"Components: {model.components()}")
    context.append(f"Geometries: {model.geometries()}")
    context.append(f"Physics: {model.physics()}")
    context.append(f"Studies: {model.studies()}")
    
    context.append("\n=== Parameters (User Defined) ===")
    try:
        params = model.parameters()
        for k, v in params.items():
            context.append(f"{k} = {v}")
    except Exception as e:
        context.append(f"Could not load parameters: {e}")

    context.append("\n=== Dependent Variables (Solutions) ===")
    try:
        context.append(str(model.solutions()))
    except:
        pass

    return "\n".join(context)

def set_parameter(model, name, value):
    """Sets a global parameter."""
    print(f"[Tool] Setting parameter '{name}' to '{value}'...")
    try:
        model.parameter(name, value)
        return f"Parameter '{name}' set to '{value}'."
    except Exception as e:
        return f"Error setting parameter: {e}"

def build_geometry(model):
    """Builds all geometries."""
    print("[Tool] Building active geometries...")
    try:
        model.build()
        return "Geometry built successfully."
    except Exception as e:
        return f"Error building geometry: {e}"

def build_mesh(model):
    """Builds all meshes."""
    print("[Tool] Building active meshes...")
    try:
        model.mesh()
        return "Mesh built successfully."
    except Exception as e:
        return f"Error building mesh: {e}"

def solve_study(model, study_name):
    """Solves the specified study."""
    print(f"[Tool] Solving study '{study_name}' (this may take time)...")
    try:
        model.solve(study_name)
        return f"Study '{study_name}' execution completed."
    except Exception as e:
        return f"Error solving study: {e}"

def evaluate_expression(model, expression, unit):
    """Evaluates an expression and returns the result."""
    print(f"[Tool] Evaluating '{expression}' in unit '{unit}'...")
    try:
        # We need a solution to evaluate. Usually uses the latest.
        # Check if there are solutions
        if not model.solutions():
             return "Error: No solutions available to evaluate. Run a study first."
        
        # Taking the last solution usually
        result = model.evaluate(expression, unit)
        return f"Result of '{expression}': {result} [{unit}]"
    except Exception as e:
        return f"Error evaluating expression: {e}"

def save_model(model, filename):
    """Saves the model to a file."""
    print(f"[Tool] Saving model to '{filename}'...")
    try:
        model.save(filename)
        return f"Model saved to '{filename}'."
    except Exception as e:
        return f"Error saving model: {e}"

# ------------------------------------------------------------------------------
# Tool Schema for OpenAI
# ------------------------------------------------------------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "set_parameter",
            "description": "Sets a global parameter in the COMSOL model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the parameter."},
                    "value": {"type": "string", "description": "The value/expression (e.g., '10[m/s]')."}
                },
                "required": ["name", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "build_geometry",
            "description": "Builds the model geometry. Run this after changing geometric parameters.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "build_mesh",
            "description": "Builds the mesh. Run this after geometry changes or mesh setting changes.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "solve_study",
            "description": "Runs a study to solve the physics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "study_name": {"type": "string", "description": "The name of the study to run (e.g., 'Study 1')."}
                },
                "required": ["study_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_expression",
            "description": "Evaluates a numerical expression from the results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "The expression to evaluate (e.g., 'spf.U', 'T')."},
                    "unit": {"type": "string", "description": "The unit to evaluate in (e.g., 'm/s', 'degC')."}
                },
                "required": ["expression", "unit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_model",
            "description": "Saves the model to disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "The filename to save as (e.g., 'Test_v2.mph')."}
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "refresh_context",
            "description": "Refreshes the model context (parameters, list of studies) in the prompt. Call this after making changes.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

def chat_loop(model):
    print("Extracting model context...")
    model_context = get_model_context(model)
    print("Context loaded.")
    
    system_prompt_template = (
        "You are an expert COMSOL Multiphysics assistant. "
        "You have control over the model via tools. "
        "When asked to change parameters, always offer to build geometry/mesh and solve/save as well.\n\n"
        "Current Model Context:\n{context}"
    )

    messages = [
        {"role": "system", "content": system_prompt_template.format(context=model_context)}
    ]

    print("\n--- COMSOL Active Agent Started (Type 'quit' to exit) ---\n")
    
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['quit', 'exit']:
                break
            
            messages.append({"role": "user", "content": user_input})
            
            # Request Loop (Handle potential tool calls)
            while True:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=tools,
                    tool_choice="auto"
                )
                
                msg = response.choices[0].message
                messages.append(msg)
                
                if msg.tool_calls:
                    # Execute tools
                    for tool_call in msg.tool_calls:
                        func_name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)
                        
                        tool_output = "Unknown tool"
                        
                        if func_name == "set_parameter":
                            tool_output = set_parameter(model, **args)
                        elif func_name == "build_geometry":
                            tool_output = build_geometry(model)
                        elif func_name == "build_mesh":
                            tool_output = build_mesh(model)
                        elif func_name == "solve_study":
                            tool_output = solve_study(model, **args)
                        elif func_name == "evaluate_expression":
                            tool_output = evaluate_expression(model, **args)
                        elif func_name == "save_model":
                            tool_output = save_model(model, **args)
                        elif func_name == "refresh_context":
                            # Special case: update the system prompt with new context
                            new_context = get_model_context(model)
                            # Update the system prompt (index 0)
                            messages[0]["content"] = system_prompt_template.format(context=new_context)
                            tool_output = "Model context refreshed in system prompt."
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(tool_output)
                        })
                    # Loop back to OpenAI with tool outputs
                    continue
                else:
                    # No more tools, just text response
                    print(f"\nAI: {msg.content}\n")
                    break
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    print("Starting COMSOL Client...")
    # Use cores=1 to be lightweight
    mph_client = mph.start(cores=1)
    
    model_path = 'Test.1.mph'
    if not os.path.exists(model_path):
        print(f"Error: Model file '{model_path}' not found.")
        return

    print(f"Loading model: {model_path}...")
    model = mph_client.load(model_path)
    print("Model loaded.")

    try:
        chat_loop(model)
    finally:
        print("Shutting down COMSOL client...")
        pass

if __name__ == "__main__":
    main()
