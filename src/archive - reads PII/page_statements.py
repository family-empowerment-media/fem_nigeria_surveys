import streamlit as st
import pandas as pd
from src.data_loader import (
    load_raw_data,
    load_statement_labels
)
from src.fem_colours import FEM_SCALE
import plotly.express as px

descriptive_cols = ['age_group', 'gender', 'use', 'combined_weight_adjusted']
def statement_heatmap(df_raw, split_key, use_weights):
    # Read mapped and cleaned survey data
    df_raw = load_raw_data()

    # Read CSV of statement definition linkages (if needed)
    statement_mapping = load_statement_labels()
    statement_labels = statement_mapping.set_index("statement").to_dict()['label_en']

    # Filter survey data to statement columns
    statement_columns = [col for col in df_raw.columns if col.startswith("statement_")]
    df_statements = df_raw[statement_columns + descriptive_cols].copy()
    
    # Step 1: Pivot the dataframe
    # Melt to long format first
    df_melted = df_statements.melt(
        id_vars=descriptive_cols,
        value_vars=statement_columns,
        var_name='statement',
        value_name='response'
    )

    # Map statement_[0-9] number
    df_melted['statement_num'] = df_melted['statement'].str.extract('(\d+)').astype(int)

    # Map statement to descriptive label
    df_melted['label'] = df_melted['statement'].map(statement_labels)

    # Quantify agreement
    df_melted['agreement'] = df_melted.response.fillna("")\
                                    .map(lambda x: 1 if x.__contains__('Agree') else (-1 if x.__contains__('Disagree') else 0))

    

    # Apply weights if specified
    if use_weights:
        df_melted['weighted_agreement'] = df_melted['agreement'] * df_melted['combined_weight_adjusted']
    else:
        df_melted['weighted_agreement'] = df_melted['agreement']

    # Pivot the data: index = statement with label, columns = split_key, values = weighted_agreement
    if split_key != "":
        heatmap_data = df_melted.groupby(['label', split_key])['weighted_agreement'].sum().reset_index()

        # Pivot to wide format for heatmap visualization
        heatmap_pivot = heatmap_data.pivot_table(
            index=['label'],
            columns=split_key,
            values='weighted_agreement',
            fill_value=0
        )


        # Step 4: Visualize the heatmap
        fig = px.imshow(
            heatmap_pivot.values,
            labels=dict(x=split_key, y="Statement", color="Weighted Agreement"),
            x=heatmap_pivot.columns,
            y=[f"{row}" for row in heatmap_pivot.index],
            color_continuous_scale=FEM_SCALE,
        )
        fig.update_layout(
            title="Heatmap of Statement Agreement by Barrier",
            xaxis_title=split_key,
            yaxis_title="Statements",
            height=1400,  
        )
    else:
        heatmap_data = df_melted.groupby(['label'])['weighted_agreement'].sum().reset_index()
        heatmap_pivot = heatmap_data.set_index('label')


        # Step 4: Visualize the heatmap
        fig = px.imshow(
            heatmap_pivot.values,
            labels=dict(y="Statement", color="Weighted Agreement"),
            x=heatmap_pivot.columns,
            y=[f"{row}" for row in heatmap_pivot.index],
            color_continuous_scale=FEM_SCALE,
        )
        fig.update_layout(
            title="Heatmap of Statement Agreement by Barrier",
            # xaxis_title=split_key,
            yaxis_title="Statements",
            height=1400,  
        )
    
    # Display the heatmap in Streamlit
    st.plotly_chart(fig, use_container_width=True)

    # Optionally, display the raw data for reference
    with st.expander("View Processed Data"):
        st.dataframe(heatmap_pivot)


def render():
    # Page title
    st.title("Statement Agreement Heatmap")

    # Load raw data
    df_raw = load_raw_data()

    # Split options for filtering
    split_by = st.radio("Split data by", ["User category", "Gender", "Age group", "None"], horizontal=True)
    split_key = {"User category": "use", "Gender": "gender", "Age group": "age_group", "None": ""}[split_by]

    # Add a checkbox to toggle weights
    use_weights = st.checkbox("Use normalized weights", value=True)

    # Render the heatmap
    statement_heatmap(df_raw, split_key, use_weights)
