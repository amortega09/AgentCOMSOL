import os
import mph
import pprint
import json
from dotenv import load_dotenv
from openai import OpenAI
import physics # Custom mappings

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
    """Refreshes and returns the model context string, including detailed physics/material settings."""
    context = []
    context.append("=== Model Overview ===")
    try:
        # Use Java API to get fresh lists to avoid caching
        comps = [str(t) for t in model.java.component().tags()]
        context.append(f"Components: {comps}")
    except:
         context.append(f"Components: {model.components()}")
         
    context.append(f"Modules: {model.modules()}")
    context.append(f"Geometries: {model.geometries()}")
    context.append(f"Studies: {model.studies()}")
    
    context.append("\n=== Parameters (Global) ===")
    try:
        params = model.parameters()
        for k, v in params.items():
            context.append(f"{k} = {v}")
    except Exception as e:
        context.append(f"Could not load parameters: {e}")

    # --- Physics Inspection ---
    context.append("\n=== Physics & Materials Details ===")
    try:
        physics_names = model.physics()
        for ph_name in physics_names:
            context.append(f"\n[Physics Interface: {ph_name}]")
            node = model / "physics" / ph_name
            if not node.exists():
                continue
            
            # recursive function to list properties
            def list_node_properties(n, indent=2):
                prefix = " " * indent
                try:
                    # Some nodes have 'properties()' which dict-like settings
                    props = n.properties()
                    if props:
                        for pk, pv in props.items():
                            context.append(f"{prefix}{pk}: {pv}")
                except:
                    pass
                
                # Check children (features)
                try:
                    for child in n.children():
                        context.append(f"{prefix}- Feature: {child.name()} ({child.type()})")
                        list_node_properties(child, indent + 4)
                except:
                    pass

            list_node_properties(node)
            
    except Exception as e:
        context.append(f"Error inspecting physics: {e}")

    # --- Materials Inspection ---
    try:
        context.append("\n[Materials]")
        # Mph doesn't have a direct 'materials()' list sometimes, distinct from access
        # Usually found under 'components' -> 'component 1' -> 'materials'
        # We'll try to scan the model tree briefly for materials
        for comp in model.components():
            mat_node_path = model / "components" / comp / "materials"
            if mat_node_path.exists():
                for mat in mat_node_path.children():
                    context.append(f"  - {mat.name()} ({mat.type()})")
                    # Try to see properties like 'rho', 'mu'
                    try:
                        # Materials often have 'property group' -> 'def' -> variables
                        # This is deep, but let's try shallow property listing
                        props = mat.properties()
                        if props:
                            context.append(f"    Properties: {props}")
                    except:
                        pass
    except Exception as e:
        context.append(f"Error inspecting materials: {e}")

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

import traceback

# ... imports ...

def create_model(mph_client, name):
    """Creates a new blank model. Returns (message, model_object)."""
    print(f"[Tool] Creating new model '{name}'...")
    try:
        if name in mph_client.names():
            return (f"Error: Model '{name}' already exists. Please choose a different name or load it.", None)
        new_model = mph_client.create(name)
        return (f"New model '{name}' created successfully.", new_model)
    except Exception as e:
        return (f"Error creating model: {e}", None)

# ... (other tools remain returning strings) ...



def add_component(model, name, dimension):
    """Adds a component to the model."""
    print(f"[Tool] Adding component '{name}' with dimension '{dimension}'...")
    try:
        # Check if component already exists (using Java API to avoid caching issues)
        if name in [str(t) for t in model.java.component().tags()]:
            return f"Error: Component '{name}' already exists."

        # Create component using Java API
        comp = model.java.component().create(name)
        
        # Map dimension string to integer
        dim_map = {"1D": 1, "2D": 2, "3D": 3, "0D": 0}
        dim_val = dim_map.get(str(dimension).upper(), None)
        
        if dim_val is not None:
             geom_name = "geom1"
             try:
                 comp.geom().create(geom_name, dim_val)
                 return f"Created component '{name}' and geometry '{geom_name}' ({dimension})."
             except Exception as ge:
                 return f"Created component '{name}', but failed to create geometry: {ge}"
        
        return f"Created component '{name}'. (Warning: No geometry created, dimension '{dimension}' unknown)"
    except Exception as e:
        return f"Error adding component: {e}"

def add_physics(model, component, interface, tag=None):
    """Adds a physics interface to a component."""
    print(f"[Tool] Adding physics '{interface}' to component '{component}' with tag '{tag}'...")
    try:
        # Using Java API for lookup
        current_components = [str(t) for t in model.java.component().tags()]
        if component not in current_components:
            return f"Error: Component '{component}' not found. Available: {current_components}"

        comp_java = model.java.component(component)
        
        # Physics interfaces are usually associated with a geometry.
        # Try to find an existing geometry in the component.
        geoms = comp_java.geom().tags()
        if not geoms:
             return f"Error: No geometry found in component '{component}'. Create geometry first."
        geom_tag = geoms[0] # Use the first geometry found

        # Resolve physics interface and tag using physics module
        phys_id, default_tag = physics.get_physics_info(interface)
        final_interface = phys_id if phys_id else interface # Fallback to input if not found
        
        if not tag:
             tag = default_tag if default_tag else final_interface.lower().replace(" ", "")
             
        # Check if physics with this tag already exists in this component
        # model.physics(component) might be stale too.
        # Use Java: comp_java.physics().tags()
        if tag in [str(t) for t in comp_java.physics().tags()]:
             return f"Error: Physics '{tag}' already exists in component '{component}'."
             
        comp_java.physics().create(tag, final_interface, geom_tag)
        return f"Created physics '{final_interface}' (requested '{interface}') with tag '{tag}' assigned to geometry '{geom_tag}' in component '{component}'."
    except Exception as e:
        return f"Error adding physics: {e}"


def add_physics_feature(model, component, physics, name, type, dimension=None):
    """Adds a feature to a physics interface."""
    print(f"[Tool] Adding physics feature '{name}' ({type}) to '{physics}' in '{component}'...")
    try:
        # Get component
        if component not in model.java.component().tags():
             return f"Error: Component '{component}' not found."
        comp_java = model.java.component(component)

        # Get physics
        if physics not in comp_java.physics().tags():
             return f"Error: Physics '{physics}' not found in component '{component}'."
        phys_java = comp_java.physics(physics)
        
        # Check if feature exists
        if name in [str(t) for t in phys_java.feature().tags()]:
             return f"Error: Feature '{name}' already exists in physics '{physics}'."

        # Create feature
        # If dimension is provided, use it. Otherwise let COMSOL infer (usually 2nd arg is type, 3rd is dim?)
        # User snippet: create("fp1", "FluidProperties", 2) -> name, type, dim
        if dimension is not None:
             phys_java.feature().create(name, type, int(dimension))
        else:
             # Try without dimension if allowed, or assume based on physics?
             # COMSOL Java API usually requires dimension for some features.
             # Let's try to infer or require it. For now, assume user/agent provides it if strictly needed.
             # Actually, creating without dimension might fail for geometric features.
             # Let's default to create(name, type) and see if it works for global features, 
             # but strictly warn about geometric ones.
             try:
                phys_java.feature().create(name, type)
             except Exception:
                return f"Error: Dimension required for feature '{type}'. Please specify 'dimension'."
        
        return f"Created physics feature '{name}' ({type}) in '{physics}'."
    except Exception as e:
        return f"Error adding physics feature: {e}"


def set_physics_selection(model, component, physics, feature, selection):
    """Sets the geometric selection for a physics feature."""
    print(f"[Tool] Setting selection for '{feature}' in '{physics}' to {selection}...")
    try:
        # Resolve path
        feat_java = model.java.component(component).physics(physics).feature(feature)
        
        # Selection is passed as list of integers. Ensure correct type.
        # COMSOL Java expects int[] array.
        # Need to handle if selection is [1, 2, 3] or "1 2 3" or "all"
        if isinstance(selection, str):
            if selection.lower() == "all":
                feat_java.selection().all()
                return f"Set selection for '{feature}' to ALL."
            else:
                 # Try splitting space separated
                 sel_list = [int(x) for x in selection.split() if x.strip().isdigit()]
        elif isinstance(selection, list):
             sel_list = [int(x) for x in selection]
        else:
             return f"Error: Invalid selection format '{selection}'."
             
        feat_java.selection().set(sel_list)
        return f"Set selection for '{feature}' to {sel_list}."
    except Exception as e:
        return f"Error setting selection: {e}"

def set_physics_property(model, component, physics, feature, property, value):
    """Sets a property value for a physics feature."""
    print(f"[Tool] Setting property '{property}' of '{feature}' in '{physics}' to '{value}'...")
    try:
         # Resolve path
        feat_java = model.java.component(component).physics(physics).feature(feature)
        
        # Set string/double/int. Python -> Java bridge handles some, but explicit typing helps.
        # Usually setString or setDouble. 'set' is generic in MPH or JNI? 
        # model.java objects usually support .set(name, value)
        feat_java.set(property, value)
        return f"Set property '{property}' of '{feature}' to '{value}'."
    except Exception as e:
        return f"Error setting physics property: {e}"

def add_geometry_feature(model, geometry, type, name=None, properties=None):
    """Adds a geometric feature (Block, Circle, etc.) to a geometry."""
    print(f"[Tool] Adding geometry feature '{type}' to geometry '{geometry}'...")
    try:
        # Find the component that owns this geometry
        found_comp_tag = None
        found_geom_java = None
        for c_tag in model.java.component().tags():
             c_java = model.java.component(c_tag)
             if geometry in c_java.geom().tags():
                 found_comp_tag = c_tag
                 found_geom_java = c_java.geom(geometry)
                 break
        
        if not found_geom_java:
            return f"Error: Geometry '{geometry}' not found in any component."

        if not name:
             name = f"{type.lower()}1" # simplistic auto-naming

        # Check if feature with this name already exists (using Java API)
        # found_geom_java is the geom object. .feature() gets the feature list container. .tags() gets names.
        if name in [str(t) for t in found_geom_java.feature().tags()]:
            return f"Error: Geometry feature '{name}' already exists in geometry '{geometry}'."
             
        feat = found_geom_java.create(name, type)
        
        if properties:
             for key, val in properties.items():
                 try:
                     # Attempt to set property, handling common types
                     if isinstance(val, (int, float)):
                         feat.set(key, val)
                     elif isinstance(val, str):
                         feat.set(key, val)
                     elif isinstance(val, list): # For array properties
                         feat.set(key, val)
                     else:
                         feat.set(key, str(val)) # Fallback to string
                 except Exception as prop_e:
                     print(f"Warning: Could not set property '{key}' to '{val}' for feature '{name}': {prop_e}")
                         
        found_geom_java.run(name) # Build this specific feature
        return f"Created geometry feature '{name}' of type '{type}' in geometry '{geometry}'."
        
    except Exception as e:
        return f"Error adding geometry feature: {e}"

def create_geometry_boolean(model, geometry, type, name, input_objects):
    """Creates a boolean geometry operation (Union, Difference, Intersection)."""
    print(f"[Tool] Creating geometry boolean '{type}' ({name}) in '{geometry}' with inputs {input_objects}...")
    try:
         # Find geometry
        found_geom_java = None
        for c_tag in model.java.component().tags():
             c_java = model.java.component(c_tag)
             if geometry in c_java.geom().tags():
                 found_geom_java = c_java.geom(geometry)
                 break
        
        if not found_geom_java:
            return f"Error: Geometry '{geometry}' not found."

        if name in [str(t) for t in found_geom_java.feature().tags()]:
            return f"Error: Feature '{name}' already exists."

        # Create boolean feature
        # type should be "Uni", "Dif", "Int" (COMSOL tags usually) or "Union", "Difference", "Intersection" -> Map them
        type_map = {
            "Union": "Uni", "union": "Uni",
            "Difference": "Dif", "difference": "Dif",
            "Intersection": "Int", "intersection": "Int"
        }
        comsol_type = type_map.get(type, type) # Fallback to passed type if not in map
        
        feat = found_geom_java.create(name, comsol_type)
        
        # Set input objects
        # input_objects should be a list of feature names
        if isinstance(input_objects, list):
             feat.selection("input").set(input_objects)
        elif isinstance(input_objects, str):
             # Try split
             feat.selection("input").set(input_objects.split())
             
        found_geom_java.run(name)
        return f"Created boolean operation '{name}' ({comsol_type}) on inputs {input_objects}."
    except Exception as e:
        return f"Error creating geometry boolean: {e}"

def add_material(model, component, name, material_type="Common", library_path=None):
    """Adds a material to the component."""
    print(f"[Tool] Adding material '{name}' to '{component}' (Source: {library_path})...")
    try:
        comp_java = model.java.component(component)
        if not comp_java:
            return f"Error: Component '{component}' not found."
            
        # If library_path is provided, try to load. 
        # Note: 'Common' is the standard type for blank materials.
        # Loading from library usually involves 'Link' or mimicking the file structure.
        # But 'create(name, "Common", filename)' is supported in some APIs.
        # Let's try basic creation first.
        
        if name in [str(t) for t in comp_java.material().tags()]:
             return f"Error: Material '{name}' already exists."

        if library_path:
             # Try to create from file
             try:
                 mat = comp_java.material().create(name, material_type, library_path)
                 return f"Created material '{name}' from '{library_path}'."
             except Exception as lib_e:
                 return f"Error loading material from library: {lib_e}. Suggestion: Create empty material and set properties."
        
        # Create empty/common material
        comp_java.material().create(name, material_type)
        return f"Created empty material '{name}'. Please set properties."
    except Exception as e:
        return f"Error adding material: {e}"

def add_multiphysics(model, component, type, tag=None):
    """Adds a multiphysics coupling."""
    print(f"[Tool] Adding multiphysics '{type}' to '{component}'...")
    try:
        comp_java = model.java.component(component)
        if not comp_java:
            return f"Error: Component '{component}' not found."
            
        if not tag:
             tag = f"mp{len(comp_java.multiphysics().tags()) + 1}"
             
        comp_java.multiphysics().create(tag, type)
        return f"Created multiphysics coupling '{tag}' of type '{type}'."
    except Exception as e:
        return f"Error adding multiphysics: {e}"

def export_plot(model, plot_group, filename):
    """Exports a plot group to an image file."""
    print(f"[Tool] Exporting plot group '{plot_group}' to '{filename}'...")
    try:
        # Check if plot group exists
        pg_tags = [str(t) for t in model.java.result().tags()]
        if plot_group not in pg_tags:
             return f"Error: Plot group '{plot_group}' not found. Available: {pg_tags}"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Check if an export feature for this file exists, or create a temporary one
        # To avoid clutter, we can create a temporary export tag
        export_tag = "img_export_temp"
        
        # Remove if exists (to reset settings)
        if export_tag in [str(t) for t in model.java.export().tags()]:
             model.java.export().remove(export_tag)
             
        # Create Image export
        exp = model.java.export().create(export_tag, "Image")
        exp.set("sourceobject", plot_group)
        exp.set("filename", os.path.abspath(filename))
        
        # Adjust settings for web view (optional)
        # exp.set("size", "manual")
        # exp.set("unit", "px")
        # exp.set("width", "800")
        
        # Run export
        model.java.export(export_tag).run()
        
        # Cleanup
        model.java.export().remove(export_tag)
        
        return f"Successfully exported '{plot_group}' to '{filename}'. URL: /static/plots/{os.path.basename(filename)}"
    except Exception as e:
        return f"Error exporting plot: {e}"

# ------------------------------------------------------------------------------
# Tool Schema for OpenAI
# ------------------------------------------------------------------------------

def create_mesh(model, geometry, name="mesh1"):
    """Creates a new mesh sequence."""
    print(f"[Tool] Creating mesh '{name}' for geometry '{geometry}'...")
    try:
        # Check if mesh already exists
        if name in [str(t) for t in model.java.mesh().tags()]:
             return f"Error: Mesh '{name}' already exists."

        model.java.mesh().create(name, geometry)
        return f"Created mesh '{name}' for geometry '{geometry}'."
    except Exception as e:
        return f"Error creating mesh: {e}"

def create_study(model, name="std1"):
    """Creates a new study."""
    print(f"[Tool] Creating study '{name}'...")
    try:
        # Check if study already exists (Java)
        if name in [str(t) for t in model.java.study().tags()]:
             return f"Error: Study '{name}' already exists."

        model.java.study().create(name)
        model.java.study(name).create("stat", "Stationary") # Default to stationary
        return f"Created study '{name}' (Stationary)."
    except Exception as e:
        return f"Error creating study: {e}"

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
            "name": "create_mesh",
            "description": "Creates a new mesh sequence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "geometry": {"type": "string", "description": "Geometry tag to mesh (e.g. 'geom1')."},
                    "name": {"type": "string", "description": "Mesh tag name (e.g. 'mesh1')."}
                },
                "required": ["geometry"]
            }
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
            "name": "create_study",
            "description": "Creates a new study.",
            "parameters": {
                "type": "object",
                "properties": {
                     "name": {"type": "string", "description": "Study name (e.g. 'std1')."}
                },
                "required": ["name"]
            }
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
            "name": "add_physics_feature",
            "description": "Adds a feature to a physics interface (e.g., Inlet, Wall, Fluid Properties).",
            "parameters": {
                "type": "object",
                "properties": {
                     "component": {"type": "string", "description": "Component tag (e.g. 'comp1')."},
                     "physics": {"type": "string", "description": "Physics tag (e.g. 'spf')."},
                     "name": {"type": "string", "description": "Name for the new feature (e.g. 'inlet1')."},
                     "type": {"type": "string", "description": "Feature type (e.g. 'Inlet', 'Wall', 'FluidProperties')."},
                     "dimension": {"type": "integer", "description": "Geometric dimension of the feature (e.g., 1 for boundaries in 2D, 2 for domains in 2D). Optional, defaults to physics dimension."}
                },
                "required": ["component", "physics", "name", "type"]
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
            "name": "set_physics_selection",
            "description": "Sets the geometric domain/boundary selection for a physics feature.",
            "parameters": {
                "type": "object",
                "properties": {
                     "component": {"type": "string"},
                     "physics": {"type": "string"},
                     "feature": {"type": "string", "description": "Feature name (e.g. 'inlet1')."},
                     "selection": {
                         "type": ["array", "string"], 
                         "items": {"type": "integer"},
                         "description": "List of domain/boundary indices (e.g. [1, 2]) or 'all'."
                     }
                },
                "required": ["component", "physics", "feature", "selection"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_physics_property",
            "description": "Sets a property value for a physics feature (e.g. Setting 'U0' for an Inlet).",
            "parameters": {
                "type": "object",
                "properties": {
                     "component": {"type": "string"},
                     "physics": {"type": "string"},
                     "feature": {"type": "string"},
                     "property": {"type": "string", "description": "Property name (e.g. 'U0', 'p0')."},
                     "value": {"type": ["string", "number", "boolean"], "description": "Value to set."}
                },
                "required": ["component", "physics", "feature", "property", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_model",
            "description": "Creates a new blank model. Use this if the user wants to start from scratch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the new model (e.g. 'Model1')."}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_component",
            "description": "Adds a component to the model. Required before adding geometry or physics.",
            "parameters": {
                "type": "object",
                "properties": {
                     "name": {"type": "string", "description": "Tag name (e.g. 'comp1')."},
                     "dimension": {"type": "string", "description": "Space dimension (e.g. '2D', '3D'). Note: This might require specific implementation details."}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_physics",
            "description": "Adds a physics interface.",
            "parameters": {
                "type": "object",
                "properties": {
                     "component": {"type": "string", "description": "Component tag (e.g. 'comp1')."},
                     "interface": {"type": "string", "description": "Physics interface tag (e.g. 'LaminarFlow', 'Electrostatics')."},
                     "tag": {"type": "string", "description": "Tag for the physics (e.g. 'phys1')."}
                },
                "required": ["component", "interface"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "create_geometry_boolean",
            "description": "Creates a boolean operation (Union, Difference, Intersection).",
            "parameters": {
                "type": "object",
                "properties": {
                     "geometry": {"type": "string", "description": "Geometry tag (e.g. 'geom1')."},
                     "type": {"type": "string", "description": "Type: 'Union', 'Difference', or 'Intersection'."},
                     "name": {"type": "string", "description": "Tag name (e.g. 'uni1')."},
                     "input_objects": {
                         "type": "array", 
                         "items": {"type": "string"},
                         "description": "List of feature names to convert (e.g. ['blk1', 'yl1'])."
                     }
                },
                "required": ["geometry", "type", "name", "input_objects"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_material",
            "description": "Adds a material to the model.",
            "parameters": {
                "type": "object",
                "properties": {
                     "component": {"type": "string", "description": "Component tag (e.g. 'comp1')."},
                     "name": {"type": "string", "description": "Material tag (e.g. 'mat1')."},
                     "library_path": {"type": "string", "description": "Optional path to material library file. Omit for empty material."}
                },
                "required": ["component", "name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_multiphysics",
            "description": "Adds a multiphysics coupling.",
            "parameters": {
                "type": "object",
                "properties": {
                     "component": {"type": "string", "description": "Component tag (e.g. 'comp1')."},
                     "type": {"type": "string", "description": "Coupling type (e.g. 'NonIsothermalFlow')."},
                     "tag": {"type": "string", "description": "Optional tag."}
                },
                "required": ["component", "type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_plot",
            "description": "Exports a plot group to an image file. Returns the image path.",
            "parameters": {
                "type": "object",
                "properties": {
                     "plot_group": {"type": "string", "description": "Plot group tag to export (e.g. 'pg1')."},
                     "filename": {"type": "string", "description": "Output filename (e.g. 'static/plots/velocity.png'). Use 'static/plots/' directory."}
                },
                "required": ["plot_group", "filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_geometry_feature",
            "description": "Adds a geometric feature (Block, Circle, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                     "geometry": {"type": "string", "description": "Geometry tag (e.g. 'geom1')."},
                     "type": {"type": "string", "description": "Feature type (e.g. 'Block', 'Circle', 'Rectangle')."},
                     "name": {"type": "string", "description": "Feature tag name (e.g. 'blk1')."},
                     "properties": {
                         "type": "object", 
                         "description": "Dictionary of properties (e.g. {'size': '1 [m]', 'pos': '0 0'}).",
                         "additionalProperties": True # This works in JSON schema? Python dict here.
                     }
                },
                "required": ["geometry", "type"]
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

def _message_to_dict(msg):
    """Convert OpenAI Message object to dict for API round-trip."""
    d = {"role": msg.role, "content": msg.content or ""}
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]
    return d


def process_user_message(mph_client, model, messages, user_content, system_prompt_template):
    """
    Process one user message through the agent (including any tool calls) and return the final response.
    Mutates messages in place.
    Returns: (final_response_str, current_model_object)
    """
    try:
        # Add user message
        messages.append({"role": "user", "content": user_content})

        while True:
            # API call (using global OpenAI client)
            response = client.chat.completions.create(
                model="gpt-5.2",
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            msg = response.choices[0].message
            messages.append(_message_to_dict(msg))

            # If no tool calls, we are done. Return content.
            if not msg.tool_calls:
                return msg.content, model

            # Handle tool calls
            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                tool_id = tool_call.id
                
                print(f"Tool Call: {name}({args})")
                
                # Execute tool
                result = f"Error: Unknown function {name}"
                
                try:
                    if name == "create_model":
                        # create_model returns (msg, model)
                        creation_msg, new_model_obj = create_model(mph_client, args.get("name"))
                        result = creation_msg
                        
                        if new_model_obj:
                            model = new_model_obj
                            # Force a context refresh immediately on the new model
                            try:
                                print(f"[System] Switched to new model: {args.get('name')}")
                                # Verify we can read from it
                                _ = model.parameters()
                            except Exception as e:
                                print(f"Warning: New model seems unstable: {e}")
                                
                    elif name == "set_parameter":
                        result = set_parameter(model, args["name"], args["value"])
                    elif name == "build_geometry":
                        result = build_geometry(model)
                    elif name == "create_mesh":
                        result = create_mesh(model, args["geometry"], args.get("name", "mesh1"))
                    elif name == "build_mesh":
                        result = build_mesh(model)
                    elif name == "create_study":
                        result = create_study(model, args.get("name", "std1"))
                    elif name == "solve_study":
                        result = solve_study(model, args["study_name"])
                    elif name == "evaluate_expression":
                        result = evaluate_expression(model, args["expression"], args["unit"])
                    elif name == "save_model":
                        result = save_model(model, args["filename"])
                    elif name == "refresh_context":
                        result = "Context refreshed."
                    elif name == "add_component":
                        result = add_component(model, args["name"], args.get("dimension"))
                    elif name == "add_physics":
                        result = add_physics(model, args["component"], args["interface"], args.get("tag"))
                    elif name == "add_physics_feature":
                        result = add_physics_feature(model, args["component"], args["physics"], args["name"], args["type"], args.get("dimension"))
                    elif name == "set_physics_selection":
                        result = set_physics_selection(model, args["component"], args["physics"], args["feature"], args["selection"])
                    elif name == "set_physics_property":
                        result = set_physics_property(model, args["component"], args["physics"], args["feature"], args["property"], args["value"])
                    elif name == "add_geometry_feature":
                        result = add_geometry_feature(model, args["geometry"], args["type"], args.get("name"), args.get("properties"))
                    elif name == "create_geometry_boolean":
                         result = create_geometry_boolean(model, args["geometry"], args["type"], args["name"], args["input_objects"])
                    elif name == "add_material":
                         result = add_material(model, args["component"], args["name"], library_path=args.get("library_path"))
                    elif name == "add_multiphysics":
                         result = add_multiphysics(model, args["component"], args["type"], args.get("tag"))
                    elif name == "export_plot":
                         result = export_plot(model, args["plot_group"], args["filename"])
                        
                except Exception as e:
                    result = f"Tool Execution Error: {e}"
                    traceback.print_exc()
                
                print(f"Tool Result: {str(result)}")
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": str(result)
                })

            # Refresh system prompt with new context before next loop
            if model:
                try:
                    context = get_model_context(model)
                except Exception as e:
                     context = f"Error getting context: {e}"
            else:
                context = "No model loaded."
            messages[0]["content"] = system_prompt_template.format(context=context)

    except Exception as e:
        traceback.print_exc()
        raise e


def chat_loop(mph_client, model):
    """
    Continuous chat loop for the terminal.
    """
    params = {}
    if model:
        params = get_model_context(model)
    else:
        params = "No model loaded. Ask to create one."
        
    system_prompt_template = (
        "You are an expert COMSOL Multiphysics assistant. "
        "You have control over the model via tools. "
        "You can create new models, add components, geometry, and physics. "
        "When asked to change parameters, always offer to build geometry/mesh and solve/save as well.\n\n"
        "Current Model Context:\n{context}"
    )
    
    # Initialize conversation
    messages = [
        {"role": "system", "content": system_prompt_template.format(context=params)}
    ]
    
    print("\n--- COMSOL Active Agent (Type 'exit' to quit) ---")
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            print("Agent: Thinking...")
            reply, model = process_user_message(mph_client, model, messages, user_input, system_prompt_template)
            print(f"Agent: {reply}\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    print("Starting COMSOL...")
    mph_client = mph.start(cores=1)
    
    target = "Demo_file.mph"
    if os.path.exists(target):
        print(f"Loading {target}...")
        try:
            model = mph_client.load(target)
            print("Model loaded.")
        except Exception as e:
            print(f"Error loading model: {e}")
            model = None
    else:
        print(f"'{target}' not found. Starting with empty session.")
        model = None

    chat_loop(mph_client, model)

if __name__ == "__main__":
    main()
