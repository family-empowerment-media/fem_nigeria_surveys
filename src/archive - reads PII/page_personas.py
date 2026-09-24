import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.data_loader import (
    load_raw_data
)
from src.fem_colours import PRIORITY_COLORS, FEM_PALETTE
from kmodes.kmodes import KModes
import matplotlib.pyplot as plt


vars_for_clustering=[
                    "age", # Numerical
                    "gender", # Categorical                  
                    "occupation", # Multi-Categorical
                    "religion", # Multi-Categorical
                    "life_goals"  # Multi-Categorical
                    ] 


# def find_optimal_clusters_elbow(data, max_clusters=10):
#     cluster_df = data[vars_for_clustering]
#     costs = []
    
#     for n in range(1, max_clusters + 1):
#         kmode = KModes(n_clusters=n, init='Cao', n_init=5, verbose=0, random_state=42)
#         cost = kmode.fit(cluster_df.to_numpy(), 
#                           categorical=[cluster_df.columns.get_loc(col) for col in vars_for_clustering]).cost_
#         costs.append(cost)
    
#     # Create the plot with controlled size
#     fig, ax = plt.subplots(figsize=(2, 1.5))  # Width=4, Height=3.5
#     ax.plot(range(1, max_clusters + 1), costs, marker='o')
#     ax.set_xlabel('Number of Clusters')
#     ax.set_ylabel('Cost')
#     ax.set_title('Elbow Method for Optimal Clusters (Mixed Data)')
    
#     # Use HTML and CSS to confine the plot width
#     st.markdown(
#         """
#         <div style="display: flex; justify-content: center; width: 200px; margin: 0 auto;">
#             <div style="width: 50%;">
#         """,
#         unsafe_allow_html=True,
#     )
    
#     # Display the plot in Streamlit
#     st.pyplot(fig)
    
#     # Close the HTML div
#     st.markdown("</div></div>", unsafe_allow_html=True)


def create_personas(data):
    cluster_df=data[vars_for_clustering]
    kmode = KModes(n_clusters=3, init='Cao', n_init=5, verbose=0,random_state=42)
    clusters = kmode.fit_predict(cluster_df.to_numpy(), 
                                            categorical = [cluster_df.columns.get_loc(col) for col in vars_for_clustering])
    counts = pd.Series(clusters).value_counts()
    counts.name="Count of People" 
    personas=pd.DataFrame(kmode.cluster_centroids_,columns=cluster_df.columns)
    personas.rename(index={},
                            columns={
                                "index":"Persona",
                                "age": "Age",
                                'religion': "Religion",
                                'occupation': "Occupation",
                                'gender': "Gender",
                                "life_goals": "Life Goals"
                                },
                            inplace=True)
    personas["Age"]=round(personas["Age"].astype(float))
    personas = personas.rename_axis('Persona').rename_axis(columns=None)
    # personas=personas.merge(counts,left_index=True,right_index=True)
    personas["Count of People"] = counts

    return personas,clusters


def render(df_raw=None):
    st.header("Personas")
    st.caption("Cluster-based respondent profiles derived from survey data.")

    if df_raw is None:
        df_raw = load_raw_data()

    st.caption("Missing values in clustering variables:")
    st.dataframe(df_raw[vars_for_clustering].isnull().sum())
    df_raw[vars_for_clustering] = df_raw[vars_for_clustering].fillna("Unemployed / Prefer not to say")

    # st.caption("Find optimal number of clusters using the elbow method:")
    # find_optimal_clusters_elbow(df_raw)
    
    st.subheader("Persona Summary")
    persona_df, cluster_assignments=create_personas(df_raw)
    df_raw["Personas"]=cluster_assignments.astype(str)
    st.dataframe(persona_df.set_index("Age"))
