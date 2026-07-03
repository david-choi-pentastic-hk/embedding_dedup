import ollama
import pandas as pd
import numpy as np
from typing import Callable

def get_embedding(text: str, model: str = "nomic-embed-text") -> list[float]:
    """
    Generate an embedding vector for the given text using Ollama.

    Args:
        text (str): The input string to embed.
        model (str): The embedding model to use (default: 'nomic-embed-text').

    Returns:
        list: The embedding vector as a list of floats.
    """
    # Input validation
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Text must be a non-empty string.")

    try:
        # Request embedding from Ollama
        response = ollama.embeddings(model=model, prompt=text)

        # Extract the embedding vector
        embedding = response.get("embedding")
        if embedding is None:
            raise RuntimeError("No embedding returned from Ollama.")

        return embedding

    except Exception as e:
        raise RuntimeError(f"Failed to get embedding: {e}")

# Function to compute cosine similarity
def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    Returns a value between -1 (opposite) and 1 (identical).
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have the same dimensions")
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))

def import_csv(csv_filepath) -> pd.DataFrame:
    df = pd.read_csv(csv_filepath, quotechar='"')
    return df

def convert_cells_to_set(cells: pd.DataFrame) -> set[str]:
    if cells.dtype == "object":
        return set.union(*cells)
    return set(cells.apply(str))

def groupby_column(df: pd.DataFrame, column_name: str, aux_column_names: list[str] = []) -> pd.DataFrame:
    aux_column_names.append(column_name)

    agg: dict[str, Callable[[pd.DataFrame], set[str]] | str] = dict.fromkeys(
        df.columns.difference(aux_column_names), convert_cells_to_set
    )

    for aux_column_name in aux_column_names:
        agg[aux_column_name] = "first"

    df = df.groupby(column_name, as_index=False).agg(func=agg)

    return df

def derive_embedding(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Create a new column that holds the embedding of a text column.

    Args:
        df: The Pandas DataFrame.
        column_name: The name of the column being derived. This column should hold text.
    """
    embedding_column_name = f"{column_name}_embedding"
    df[embedding_column_name] = df[column_name].apply(lambda x: get_embedding(str(x)))
    return df

def join_df_cell_sets_to_strings(df: pd.DataFrame, separator: str = "; ") -> pd.DataFrame:
    def join_by_separator(cell):
        return separator.join(cell) if isinstance(cell, set) else cell
    return df.map(join_by_separator)


# Example usage
if __name__ == "__main__":
    df = import_csv(".sample/t735q2.csv")
    df = groupby_column(df, "Name")
    df = join_df_cell_sets_to_strings(df)
    df = derive_embedding(df, "Name")

    # df.to_csv("output.csv", quotechar='"', encoding="utf-8")
    df.to_excel("output.xlsx")

    print(df)

    # df["NameVector"] = df.apply(lambda row: get_embedding(row["Name"]), axis=1)
    # print(df)
    # str1 = input("string 1: ")
    # str2 = input("string 2: ")
    # vec1 = get_embedding(str1)
    # vec2 = get_embedding(str2)
    # sim = cosine_similarity(vec1, vec2)
    # print("Similarity:", sim)
