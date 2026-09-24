# FEM brand colour palette -- same 5 official brand hexes as niger_app.
# Only the *role assignment* (which colour leads, which marks "priority",
# which anchors the heatmap) differs here, so Benin's charts read as
# visually distinct from Niger's at a glance rather than as reskins.
FEM_ORANGE = "#C1693A"
FEM_BROWN  = "#8B5E45"
FEM_TAUPE  = "#7A7068"
FEM_STEEL  = "#5A6E7F"
FEM_NAVY   = "#2E3F52"

# Ordered palette for charts (5 colours). niger_app leads warm
# (orange -> brown -> taupe -> steel -> navy); Benin leads cool instead.
FEM_PALETTE = [FEM_STEEL, FEM_NAVY, FEM_ORANGE, FEM_BROWN, FEM_TAUPE]

# Priority colours -- navy (not orange) reads as "most urgent" here
PRIORITY_COLORS = {
    "Very high": FEM_NAVY,
    "High":      FEM_STEEL,
    "Medium":    FEM_BROWN,
    "Low":       FEM_TAUPE,
}

# Heatmap ramp: cool pale -> steel -> navy -> orange, so high values read
# as a warm accent against a cool base (niger_app ramps cream -> tan ->
# orange -> brown -> navy, ending cool; this ends warm instead).
FEM_SCALE = [
    [0.0,  "#eef2f5"],
    [0.25, "#aebfc9"],
    [0.5,  FEM_STEEL],
    [0.75, FEM_NAVY],
    [1.0,  FEM_ORANGE],
]
