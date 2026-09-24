# Nigeria FEM Survey — Analysis Pipeline

This repository contains the Nigeria Streamlit app and its regional processing
pipeline. Raw participant CSVs are supplied through command-line paths and are
not committed to the repository. The app reads only the pre-aggregated CSVs
written to the regional `data/` folders.

```
fem_app/
├── processing/                  <- raw regional CSV cleaning
├── processing_output/           <- cleaned regional CSVs and manifests
├── pipeline_output/pipeline/    <- regional ETL modules and runner
├── data/                        <- generated aggregate CSVs, one folder per region
├── src/                         <- Streamlit pages and data loaders
└── app.py                       <- Streamlit entry point
```

## Setup

```bash
pip install -r requirements.txt
```

## Running the full Nigeria pipeline

Run all commands from the `fem_app/` project root. The raw CSV files can be
stored anywhere on your machine; do not commit them to the repository.

### 1. Clean the three regional exports

Replace the three input paths with the actual downloaded filenames:

```bash
python -m processing.run_processing \
  --north /path/to/north.csv \
  --south /path/to/south.csv \
  --south-west /path/to/south_west.csv \
  --output-dir ./processing_output \
  --form-definition "./2023+Northern+Nigeria_+Survey+Data+Collection.xlsx"
```

This creates one cleaned file per region and `processing_output/manifest.json`.

### 2. Run every ETL for every region

The runner automatically processes `north`, `south`, and `south_west`.
It reads the cleaned files from `processing_output/` and writes aggregates to
`data/<region>/`.

```bash
python pipeline_output/pipeline/run_pipeline.py
```

To run only selected pages:

```bash
python pipeline_output/pipeline/run_pipeline.py \
  --pages respondents access statements family_planning personality personas radio
```

### 3. Validate generated outputs

```bash
python pipeline_output/pipeline/validate_pipeline.py --outputs
```

### 4. Launch the Streamlit app

```bash
streamlit run app.py
```

The app's region selector reads the corresponding files from `data/<region>/`.

### Processing one region manually

For a single regional run, set the cleaned input and output directory explicitly:

```bash
FEM_MAPPED_DATA="$PWD/processing_output/nigeria_north_cleaned.csv" \
FEM_APP_DATA_DIR="$PWD/data/north" \
FEM_SURVEY_REGION=north \
python pipeline_output/pipeline/run_pipeline.py --region north
```

### Legacy path overrides

The ETL paths can also be overridden with environment variables:

```bash
FEM_MAPPED_DATA=/path/to/nigeria_cleaned.csv \
FEM_APP_DATA_DIR=/path/to/app/data \
python pipeline_output/pipeline/run_pipeline.py --region north
```

## What each ETL produces

| Page | ETL file | Outputs |
|------|----------|---------|
| Access & Supply | `etl_access.py` | stockout rates, travel times, costs, composite barriers |
| Statements | `etl_statements.py` | weighted agreement scores per statement x split |
| Family Planning | `etl_family_planning.py` | funnel, methods, timing, intent, non-use reasons |
| Personality | `etl_personality.py` | life goals, role models, traits, beliefs, wellbeing |
| Personas | `etl_personas.py` | cluster centroids + per-persona profiles |

`fp_unmet.csv` reports a Nigeria-specific spacing-demand proxy based on the
XLSForm question `Spacing_desire` plus current use. The form does not include
the preferred-pregnancy timing question needed for a standard timing-based
unmet-need estimate, so these values must not be described as the standard
FP2030/DHS unmet-need measure.

The radio ETL is currently skipped for Nigeria. Its existing implementation
uses Benin station metadata and French/Fon bilingual mappings; it must be given
Nigeria-specific Hausa/English question and station mappings before radio
outputs can be generated.

## Updating the app pages

Each affected page (`page_access.py`, `page_statements.py`, `page_family_planning.py`,
`page_personality_traits.py`, `page_personas.py`) should be updated to:

1. Import the relevant loader from `src/data_loader.py` instead of `load_raw_data()`
2. Use `pipeline/agg_helpers.py:get_overall_series()` and `get_split_series()` to
   extract the right slice for the selected split

The app loaders are in `src/data_loader.py` and automatically select the
generated `data/<region>/` folder for the region selected in the app.

## PII guarantee

- The pipeline reads `DIR_MAPPED_DATA` (PII) and writes only aggregated statistics
- Minimum cell sizes are not currently enforced — add a `min_cell=5` filter in
  `utils.py:split_weighted_counts()` if needed for additional protection
- `fp_nonuse_reasons.csv` contains free-text responses — review before publishing
  to ensure no names or identifying details appear in those answers
- The `data/` folder contains aggregate outputs only; review any free-text output
  before publishing it


## Validation

### ETL Pipeline Validation
```
# Check the cleaned regional data only (before running ETL)
python pipeline_output/pipeline/validate_pipeline.py --raw

# Check generated CSVs only (after running pipeline)
python pipeline_output/pipeline/validate_pipeline.py --outputs

# Both (default if no flag given)
python pipeline_output/pipeline/validate_pipeline.py
```

| Check                                                                     | What it catches                                                                                      |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Weight column exists, no nulls/zeros/negatives                            | Silent corruption of all weighted stats                                                              |
| use column values vs ALL_USE_GROUPS                                       | Spelling mismatches (non-user vs non_user) that silently drop rows                                   |
| age_group dash style                                                      | En-dash (–) vs hyphen (-) mixing → duplicate age bands in outputs                                    |
| Statement columns exist + contain "Agree"/"Disagree"                      | All-zero heatmap                                                                                     |
| Funnel columns (birth_spacing, ever_use, current_use) value distributions | Your all-zero funnel — prints the actual raw values so you can see immediately what encoding is used |
| Stockout/sought columns, checks str.contains("yes") will work             | Your all-zero sought_contraceptives — detects 0/1 or Oui/Non encoding                                |
| WTT_MAP coverage                                                          | NaN travel times from unmapped willingness values                                                    |
| Wellbeing columns + flags known frame bug in etl_personality.py           | Blank wellbeing charts                                                                               |



| Check                                                             | What it catches                                                                           |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Every expected file exists                                        | Missing pipeline runs                                                                     |
| Required columns present (including n, weighted_n for statements) | Schema drift                                                                              |
| All-zero value detection per metric                               | Silent ETL failures                                                                       |
| non_user present in sought_contraceptives groups                  | The specific missing group bug                                                            |
| stockout_nonusers_sought metric exists                            | Missing ETL branch                                                                        |
| age_group en-dash/hyphen duplicates in funnel output              | Duplicate funnel rows                                                                     |
| Wellbeing question column has both "happiness" and "satisfaction" | The undefined frame variable bug in etl_personality.py — prints the corrected code inline |
| Proportion range check (warns if > 1.0)                           | Weighted sums mistakenly used as proportions                                              |


### Weights Validation

`python pipeline/validate_weights.py`

| Section                         | What it catches |
|---------------------------------|-----------------|
| **Input integrity**             | Missing columns, null GPS coords (→ colliding household IDs), population dtype |
| **Location code alignment**     | The direct cause of your 20 null weights — finds location codes in data that don't match any `sample_number` in `settlements_chosen`, prints the exact unmatched values and their respondent counts, detects dtype mismatches (int vs string) |
| **Stage 1**                     | Chosen settlements not in eligible list, within-stratum proportions don't sum to 1, extreme weight ratios |
| **Stage 2**                     | Clusters with very few households (→ huge weights), missing population data |
| **Stage 3**                     | `eligible_adults_in_hh == 0` (from `parse_n` subtracting 1 from a trailing "1" digit) |
| **Combined weight nulls**       | Identifies which stage introduced each null and prints the guilty location codes |
| **Normalised weight diagnostics** | DEFF, effective n, CV, extreme weight percentiles, weighted vs unweighted stratum proportions |
