# Nigeria processing

`processing.run_processing` cleans the North, South, and South West raw SurveyCTO exports independently. It removes fully empty columns, optionally removes unfinished/short submissions, derives the canonical fields used by the shared ETL, and writes one CSV plus a JSON manifest per region.

Raw participant data is supplied through command-line paths and is never written to the Streamlit app output. A unit weight is used only when the input has no `normalized_weight`; the manifest records that limitation so production survey weights are not mistaken for design weights.
