
# Mapping of colloquial/display names to (COMSOL Interface ID, Default Tag)
PHYSICS_MAP = {
    # Fluid Flow
    "Laminar Flow": ("LaminarFlow", "spf"),
    "Turbulent Flow, k-e": ("TurbulentFlowKE", "spf"),
    "Turbulent Flow, k-w": ("TurbulentFlowKO", "spf"),
    "Rotating Machinery, Laminar Flow": ("RotatingMachineryLaminarFlow", "rml"),
    "Multiphase Flow, Level Set": ("MultiphaseLevelSet", "mls"),
    "Two-Phase Flow, Phase Field": ("TwoPhaseFlowPhaseField", "tpf"),

    # Heat Transfer
    "Heat Transfer in Solids": ("HeatTransfer", "ht"),
    "Heat Transfer in Fluids": ("HeatTransferFluids", "ht"),
    "Nonisothermal Flow": ("NonisothermalFlow", "nitf"),

    # Structural Mechanics
    "Solid Mechanics": ("SolidMechanics", "solid"),
    "Shell": ("Shell", "shell"),
    "Beam": ("Beam", "beam"),
    "Multibody Dynamics": ("MultibodyDynamics", "mbd"),

    # AC/DC
    "Magnetic Fields": ("MagneticFields", "mf"),
    "Electric Currents": ("ElectricCurrents", "ec"),
    "Electrostatics": ("Electrostatics", "es"),
    "Magnetic and Electric Fields": ("MagneticElectricFields", "mef"),

    # RF / Optics
    "Electromagnetic Waves, Frequency Domain": ("ElectromagneticWavesFrequencyDomain", "ewfd"),
    "Electromagnetic Waves, Transient": ("ElectromagneticWavesTransient", "ewft"),
    "Ray Optics": ("RayOptics", "ro"),

    # Chemical
    "Transport of Diluted Species": ("TransportDilutedSpecies", "tds"),
    "Transport of Concentrated Species": ("TransportConcentratedSpecies", "tcs"),

    # Other
    "Electrochemistry": ("Electrochemistry", "echem"),
    "Plasma": ("Plasma", "plas"),
    "Pressure Acoustics": ("PressureAcoustics", "acpr"),
    "Coefficient Form PDE": ("CoefficientFormPDE", "c")
}

def get_physics_info(name):
    """
    Returns (interface_id, default_tag) for a given name.
    Tries case-insensitive matching against keys, then exact match against IDs.
    Returns (name, None) if not found (fallback to raw usage).
    """
    # Direct Key Match
    if name in PHYSICS_MAP:
        return PHYSICS_MAP[name]
    
    # Case insensitive key match
    name_lower = name.lower()
    for k, v in PHYSICS_MAP.items():
        if k.lower() == name_lower:
            return v
            
    # Check if name is already an ID (Value match)
    for k, v in PHYSICS_MAP.items():
        if v[0] == name:
            return v
    
    # Fallback
    return name, None
