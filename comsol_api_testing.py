import mph
import pprint  # For nicer printing of dicts/lists

# Start COMSOL server (use cores=1 for lighter usage if needed)
client = mph.start(cores=1)  # or mph.start() for default

# Load your model (make sure the file exists in current dir or provide full path)
model = client.load('Demo_file.mph')

# --- Model inspection ---
print("=== Parameters (expressions) ===")
params = model.parameters()          # dict: name → expression (str)
pprint.pprint(params)

print("\n=== Parameters (evaluated/numeric) ===")
params_num = model.parameters(evaluate=True)  # dict: name → numeric value (float or complex)
pprint.pprint(params_num)

# List of key model tree components
print("\n=== Model Structure ===")
print("Modules:", model.modules())
print("Components:", model.components())
print("Geometries:", model.geometries())
print("Meshes:", model.meshes())
print("Physics:", model.physics())
print("Multiphysics:", model.multiphysics())
print("Materials:", model.materials())
print("Selections:", model.selections())
print("Studies:", model.studies())
print("Solutions:", model.solutions())
print("Datasets:", model.datasets())
print("Plots:", model.plots())
print("Exports:", model.exports())
print("Functions:", model.functions())

# --- Physics: editable parameters (node properties) ---
# model.physics() only gives interface names; actual editable settings are node "properties"
print("\n=== Physics – editable parameters (node properties) ===")
physics_names = model.physics()
if not physics_names:
    print("(No physics interfaces in this model.)")
else:
    for ph_name in physics_names:
        node = model / "physics" / ph_name
        if not node.exists():
            continue
        print(f"\n--- Physics: {ph_name} ---")
        try:
            props = node.properties()
            if props:
                pprint.pprint(props)
            else:
                print("  (no top-level properties)")
        except Exception as e:
            print(f"  Error reading properties: {e}")
        # Child features (e.g. PDEs, boundary conditions) have their own editable properties
        try:
            for child in node.children():
                try:
                    child_props = child.properties()
                    if child_props:
                        print(f"\n  [{child.name()}] (type: {child.type()})")
                        pprint.pprint(child_props)
                except Exception:
                    pass
        except Exception:
            pass

