import os
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from flask import Flask, render_template, request, jsonify, send_file
from openai import OpenAI


app = Flask(__name__)


# ============================================================
# GENERATED FILE WORKSPACE
# ============================================================

GENERATED = Path("/tmp/nova_generated")
GENERATED.mkdir(parents=True, exist_ok=True)


ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".html",
    ".css",
    ".json",
    ".txt",
    ".md",
    ".gd",
    ".xml",
    ".yml",
    ".yaml"
}


# ============================================================
# DEEPSEEK CONFIGURATION
# ============================================================

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    print("WARNING: DEEPSEEK_API_KEY is not configured.")


client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)


# ============================================================
# AI SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are Nova AI, a helpful AI coding and general-purpose assistant.

You can answer normal questions.

When the user asks you to create a file or project, return ONLY
valid JSON in this exact structure:

{
  "message": "Short explanation",
  "files": [
    {
      "filename": "example.py",
      "content": "complete file contents"
    }
  ]
}

Rules:

- Always return valid JSON.
- Never wrap the JSON in Markdown code fences.
- Never execute terminal commands.
- Never create executable binaries.
- Only create text/code files.
- Never use ../ in filenames.
- Never use absolute paths.
- Keep filenames simple.
- Only create files with supported extensions.
- Put complete file contents inside each content field.
- If the user does not request files, return an empty files array.
- If creating a project, create all required files.
- Make the generated code complete and usable.
"""


# ============================================================
# SAFE FILENAME
# ============================================================

def safe_filename(filename):
    if not isinstance(filename, str):
        raise ValueError("Filename must be text.")

    filename = Path(filename).name

    if not filename:
        raise ValueError("Filename is empty.")

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File type '{extension or 'unknown'}' is not allowed."
        )

    return filename


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/")
def home():
    return render_template("index.html")


# ============================================================
# CHAT API
# ============================================================

@app.post("/api/chat")
def chat():

    if not api_key:
        return jsonify({
            "success": False,
            "reply": (
                "DeepSeek API key is not configured on the server. "
                "Add DEEPSEEK_API_KEY in Render Environment Variables."
            )
        }), 500


    data = request.get_json(silent=True) or {}


    user_message = str(
        data.get("message", "")
    ).strip()


    if not user_message:
        return jsonify({
            "success": False,
            "reply": "Please type a message."
        }), 400


    try:

        response = client.chat.completions.create(

            model="deepseek-chat",

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],

            response_format={
                "type": "json_object"
            },

            max_tokens=8192
        )


        ai_text = response.choices[0].message.content


        if not ai_text:
            raise ValueError(
                "DeepSeek returned an empty response."
            )


        result = json.loads(ai_text)


        reply = str(
            result.get(
                "message",
                "Done."
            )
        )


        created_files = []


        files = result.get(
            "files",
            []
        )


        if not isinstance(files, list):
            files = []


        for item in files:

            if not isinstance(item, dict):
                continue


            filename = safe_filename(
                item.get(
                    "filename",
                    ""
                )
            )


            content = str(
                item.get(
                    "content",
                    ""
                )
            )


            path = GENERATED / filename


            path.write_text(
                content,
                encoding="utf-8"
            )


            created_files.append(
                filename
            )


        return jsonify({

            "success": True,

            "reply": reply,

            "files": created_files

        })


    except json.JSONDecodeError as error:

        print(
            "JSON ERROR:",
            repr(error)
        )

        return jsonify({

            "success": False,

            "reply":
                "DeepSeek returned invalid JSON."

        }), 500


    except Exception as error:

        print(
            "DEEPSEEK ERROR:",
            repr(error)
        )

        return jsonify({

            "success": False,

            "reply":
                f"DeepSeek error: {error}"

        }), 500


# ============================================================
# LIST GENERATED FILES
# ============================================================

@app.get("/api/files")
def list_files():

    files = []


    for file in GENERATED.iterdir():

        if file.is_file():

            files.append(
                file.name
            )


    return jsonify({

        "success": True,

        "files":
            sorted(files)

    })


# ============================================================
# DOWNLOAD FILE
# ============================================================

@app.get("/api/download/<filename>")
def download_file(filename):

    try:

        filename = safe_filename(
            filename
        )


        path = GENERATED / filename


        if not path.exists():

            return jsonify({

                "error":
                    "File not found."

            }), 404


        return send_file(

            path,

            as_attachment=True,

            download_name=filename

        )


    except ValueError as error:

        return jsonify({

            "error":
                str(error)

        }), 400


# ============================================================
# CREATE ZIP
# ============================================================

@app.get("/api/create-zip")
def create_zip():

    files = [

        file

        for file in GENERATED.iterdir()

        if file.is_file()

    ]


    if not files:

        return jsonify({

            "error":
                "There are no generated files."

        }), 400


    memory_file = BytesIO()


    with ZipFile(
        memory_file,
        "w"
    ) as zip_file:

        for file in files:

            zip_file.write(

                file,

                arcname=file.name

            )


    memory_file.seek(0)


    return send_file(

        memory_file,

        as_attachment=True,

        download_name="nova_project.zip",

        mimetype="application/zip"

    )


# ============================================================
# CLEAR GENERATED FILES
# ============================================================

@app.post("/api/clear-files")
def clear_files():

    for file in GENERATED.iterdir():

        if file.is_file():

            file.unlink()


    return jsonify({

        "success": True,

        "message":
            "Generated files cleared."

    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return jsonify({

        "status": "ok"

    })


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(

        host="0.0.0.0",

        port=port

    )
