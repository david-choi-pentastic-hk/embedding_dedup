# This document illustrates the steps to setup the environment.

1. Install Python 3
2. Create a virtual environment in the source code directory.
  ```sh
  python3 -m venv venv
  ```
3. Activate the virtual environment.
  - MacOSX:
    ```sh
    source venv/bin/activate
    ```
  - Windows Powershell:
    ```sh
    .\venv\Scripts\Activate.ps1
    ```
4. Install the required packages via pip.
  ```sh
  python3 -m pip install -r requirements.txt
  ```
5. Install [ollama](https://ollama.com/download/) and embedding models.
  ```sh
  ollama pull nomic-embed-text
  ```
