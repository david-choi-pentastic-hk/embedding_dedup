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
from typing import Callable, Any
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist, squareform

COMPARED_COLUMN_NAME: str = "Name"
COMPARED_COLUMN_EMBEDDING_NAME: str = f"{COMPARED_COLUMN_NAME}_embedding"

CLUSTER_ID_COLUMN_NAME: str = "Cluster_ID"

COMPARED_COLUMN_STRJOIN_SEPARATOR: str = " / "
OTHER_COLUMNS_STRJOIN_SEPARATOR: str = ", "

SIMILARITY_THRESHOLD = 0.80
DISTANCE_THRESHOLD = 1.0 - SIMILARITY_THRESHOLD

# 1. Load the dataset
def import_csv_as_df(csv_filepath: str) -> pd.DataFrame:
    # Force "Risk" column to be a string, so it does not convert Risk: "None" to null.
    df = pd.read_csv(csv_filepath, converters={"Risk": str})
    return df

# 2. Merge rows with identical "Name" and store other column values as sets
# We group by 'Name' and aggregate every other column into a set of unique strings
def merge_rows_with_same_field(df: pd.DataFrame) -> pd.DataFrame:
    agg_dict = {col: lambda x: set(x.dropna().astype(str)) for col in df.columns if col != COMPARED_COLUMN_NAME}
    df_merged = df.groupby(COMPARED_COLUMN_NAME, as_index=False).agg(agg_dict)
    return df_merged

# 3. Generate embeddings using Ollama
# A new column is created to store the embeddings of each name.
def add_embeddings(df: pd.DataFrame) -> pd.DataFrame:
    def get_embedding(text: str) -> list[float]:
        EMBED_MODEL = "nomic-embed-text" # You can change this to your preferred embedding model
        response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
        return response["embedding"]

    df[COMPARED_COLUMN_EMBEDDING_NAME] = df[COMPARED_COLUMN_NAME].apply(get_embedding)
    return df

# 4 & 5. Perform Cosine Similarity & Hierarchical Clustering (Complete Linkage)
# Cosine distance = 1 - Cosine Similarity. 
# A similarity threshold > 0.80 means a distance threshold < 0.20.
# A new column is created to label the cluster each row belongs to.
def add_cluster_labels(df: pd.DataFrame) -> pd.DataFrame:
    # Convert embedding column to a 2D numpy array for distance calculations
    embeddings_matrix = np.array(df[COMPARED_COLUMN_EMBEDDING_NAME].tolist())

    # Calculate cosine similarities and clustering closely related names
    # 'pdist' computes pairwise distances efficiently. 'cosine' metric is used.
    pairwise_distances = pdist(embeddings_matrix, metric="cosine")

    # Complete linkage clustering
    Z = linkage(pairwise_distances, method="complete")

    # Form flat clusters based on our distance threshold
    df[CLUSTER_ID_COLUMN_NAME] = fcluster(Z, t=DISTANCE_THRESHOLD, criterion="distance")

    return df

# 6. Merge rows belonging to the same cluster
# Define how to aggregate columns when merging clusters
def merge_clusters(df: pd.DataFrame) -> pd.DataFrame:
    final_agg: dict[str, Callable[[Any], set[Any] | str]] = {
        COMPARED_COLUMN_NAME: lambda x: COMPARED_COLUMN_STRJOIN_SEPARATOR.join(sorted(list(set(x))))
    } # Combine names in the cluster
    for col in df.columns:
        if col not in [COMPARED_COLUMN_NAME, COMPARED_COLUMN_EMBEDDING_NAME, CLUSTER_ID_COLUMN_NAME]:
            # Union the existing sets together
            final_agg[col] = lambda x: set().union(*x)

    # Group by the Cluster_ID to finalize the hierarchical merge
    df = df.groupby(CLUSTER_ID_COLUMN_NAME).agg(final_agg).reset_index(drop=True)

    return df

# We convert sets to strings so they look clean in Excel
def reduce_sets(df: pd.DataFrame) -> pd.DataFrame:
    df_excel = df.copy()
    for col in df_excel.columns:
        if col != COMPARED_COLUMN_NAME:
            df_excel[col] = df_excel[col].apply(lambda s: OTHER_COLUMNS_STRJOIN_SEPARATOR.join(list(s)))
    return df_excel

# 7. Save the resultant dataframe to an MS Excel file
def save_df_to_excel(df: pd.DataFrame, excel_filepath: str) -> None:
    df.to_excel(excel_filepath, index=False)

def merge_df_rows_by_embeddings(df: pd.DataFrame) -> pd.DataFrame:
    print("Processing...")

    df = merge_rows_with_same_field(df)
    print("Rows with same names are merged.")

    df = add_embeddings(df)
    print("Embeddings are created.")

    df = add_cluster_labels(df)
    print("Clusters are identified.")

    df = merge_clusters(df)
    print("Clusters are merged.")

    df = reduce_sets(df)
    print("Sets are reduced.")

    return df

def merge_csv_rows_by_embeddings(input_csv_filepath: str, output_xlsx_filepath: str) -> None:
    df: pd.DataFrame = import_csv_as_df(input_csv_filepath)
    df = merge_df_rows_by_embeddings(df)
    save_df_to_excel(df, output_xlsx_filepath)

def main() -> None:
    input_file = ".sample/input.csv"
    output_file = ".sample/output.xlsx"

    merge_csv_rows_by_embeddings(input_file, output_file)
    print(f"Successfully saved final results to {output_file}")

if __name__ == "__main__":
    main()
