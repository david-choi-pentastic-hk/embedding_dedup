"""
@file server.py
A python script that serves an HTML webpage as a GUI to this tool.

@copyright
Copyright (c) 2026 Pentastic Security Limited

@author
David Choi <david.choi@pentastic.hk>
"""

import time
import os
import argparse
from bottle import get, post, request, run, static_file, abort
from embedding_dedup import merge_csv_rows_by_embeddings

@get("/")
def get_webpage():
    return static_file("index.html", root="./views")

@post("/")
def upload_file():
    # 1. Retrieve the file object using the HTML form's field name
    uploaded_csv_file = request.files.get("uploaded_file")
    similarity_threshold = request.forms.get("similarity_threshold")
    similarity_threshold = min(max(float(similarity_threshold), -1.0), +1.0)

    if not uploaded_csv_file:
        abort(400, "bad request: No file was uploaded.")

    # 2. Reject all non-CSV file uploads to prevent web shells
    #    I know this program runs on localhost only,
    #    but who knows if someone will try to hack us
    input_csv_filename = uploaded_csv_file.filename
    content_type = uploaded_csv_file.content_type

    if not input_csv_filename.endswith(".csv") or content_type != "text/csv":
        abort(400, "bad request: File uploaded is not a CSV file.")

    # 3. Save the file to a specific disk location securely
    input_csv_save_dir = "./input"
    os.makedirs(input_csv_save_dir, exist_ok=True)

    epoch_time_str = str(time.time())

    input_csv_filepath = os.path.join(input_csv_save_dir, f"{epoch_time_str}.csv")
    uploaded_csv_file.save(input_csv_filepath, overwrite=True)

    output_xlsx_dir = "./output"
    os.makedirs(output_xlsx_dir, exist_ok=True)

    output_xlsx_filename = f"{epoch_time_str}.xlsx"
    output_xlsx_filepath = os.path.join(output_xlsx_dir, output_xlsx_filename)

    # perform the merge
    merge_csv_rows_by_embeddings(input_csv_filepath, output_xlsx_filepath)

    # remove the unused CSV file
    os.remove(input_csv_filepath)

    return static_file(output_xlsx_filename, root=output_xlsx_dir, download=True)

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
                    prog="Embedding Dedup Frontend Server",
                    description="Provides a GUI to access the tool.",
                    epilog="Copyright (c) 2026 Pentastic Security Limited")

    parser.add_argument("-p", "--port", default=8080, help="The port to serve the webpage.")

    return parser

def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    run(host="localhost", port=args.port)

if __name__ == "__main__":
    main()
