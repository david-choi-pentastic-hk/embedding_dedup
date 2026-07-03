"""
@file embedding_dedup.py
A python script that uses embeddings
to identify and remove duplicated findings
in the CSV output of Nessus Professional - a vulnerability scanner.

@copyright
Copyright (c) 2026 Pentastic Security Limited

@author
David Choi <david.choi@pentastic.hk>

Model:
Gemini

Prompt:
Write me a python program, using numpy, pandas and ollama packages,
which first imports a CSV file "input.csv" as a pandas dataframe,
then merges all rows with the same string content in the "Name" column and
store every merged subset of columns as a set of strings,
then use ollama to calculate the embeddings for the "Name" column and
store them in a newly created column "Name_embedding",
then perform cosine similarity on any 2 pairs of rows on their "Name_embedding" vectors,
then merge all rows that have similarity greater than 0.80 with complete linkage
(this feels like hierarchical clustering),
then save the resultant dataframe as an MS excel file.
"""

import pandas as pd
import numpy as np
import ollama
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist, squareform

# 1. Load the dataset
input_file = ".sample/input.csv"
try:
    df = pd.read_csv(input_file)
except FileNotFoundError:
    # Creating a dummy dataframe for demonstration if the file doesn't exist
    print(f"'{input_file}' not found. Creating a dummy DataFrame for demonstration.")
    data = {
        "Name": ["John Doe", "John Doe", "Jon Doe", "Jane Smith", "Jane S."],
        "City": ["New York", "NYC", "New York", "London", "London"],
        "Job": ["Engineer", "Software Engineer", "Developer", "Doctor", "Surgeon"]
    }
    df = pd.DataFrame(data)

print("Original DataFrame:")
print(df, "\n")

# 2. Merge rows with identical "Name" and store other column values as sets
# We group by 'Name' and aggregate every other column into a set of unique strings
agg_dict = {col: lambda x: set(x.dropna().astype(str)) for col in df.columns if col != "Name"}
df_merged = df.groupby("Name", as_index=False).agg(agg_dict)

print("DataFrame after merging identical names:")
print(df_merged, "\n")

# 3. Generate embeddings using Ollama
EMBED_MODEL = "nomic-embed-text" # You can change this to your preferred embedding model

def get_ollama_embedding(text):
    try:
        response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
        return response["embedding"]
    except Exception as e:
        print(f"Error generating embedding for '{text}': {e}")
        # Return a zero vector fallback depending on model dimensions (e.g., 768 for nomic)
        return []

print(f"Generating embeddings using Ollama model '{EMBED_MODEL}'...")
df_merged["Name_embedding"] = df_merged["Name"].apply(get_ollama_embedding)

# Convert embedding column to a 2D numpy array for distance calculations
embeddings_matrix = np.array(df_merged["Name_embedding"].tolist())

# 4 & 5. Perform Cosine Similarity & Hierarchical Clustering (Complete Linkage)
# Cosine distance = 1 - Cosine Similarity. 
# A similarity threshold > 0.80 means a distance threshold < 0.20.
similarity_threshold = 0.80
distance_threshold = 1.0 - similarity_threshold

print("Calculating cosine similarities and clustering closely related names...")
# 'pdist' computes pairwise distances efficiently. 'cosine' metric is used.
pairwise_distances = pdist(embeddings_matrix, metric="cosine")

# Complete linkage clustering
Z = linkage(pairwise_distances, method="complete")

# Form flat clusters based on our distance threshold
df_merged["Cluster_ID"] = fcluster(Z, t=distance_threshold, criterion="distance")

# 6. Merge rows belonging to the same cluster
# Define how to aggregate columns when merging clusters
final_agg = {"Name": lambda x: " / ".join(sorted(list(set(x))))} # Combine names in the cluster
for col in df_merged.columns:
    if col not in ["Name", "Name_embedding", "Cluster_ID"]:
        # Union the existing sets together
        final_agg[col] = lambda x: set().union(*x)

# Group by the Cluster_ID to finalize the hierarchical merge
df_final = df_merged.groupby("Cluster_ID").agg(final_agg).reset_index(drop=True)

print("Final Clustered and Merged DataFrame:")
print(df_final, "\n")

# 7. Save the resultant dataframe to an MS Excel file
output_file = ".sample/output.xlsx"
# We convert sets to strings so they look clean in Excel
df_excel = df_final.copy()
for col in df_excel.columns:
    if col != "Name":
        df_excel[col] = df_excel[col].apply(lambda s: ", ".join(list(s)))

df_excel.to_excel(output_file, index=False)
print(f"Successfully saved final results to {output_file}")
