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
# OPENROUTER CONFIGURATION
# ============================================================

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    print("WARNING: OPENROUTER_API_KEY is not configured.")


client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)


MODEL = "openrouter/free"


# ============================================================
# AI SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are Nova AI, a helpful AI assistant and coding assistant.

For normal questions, answer naturally and clearly.

When the user asks you to CREATE FILES or a PROJECT, return ONLY
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

For file-generation requests:

- Return valid JSON.
- Do not use Markdown code fences around the JSON.
- Never execute terminal commands.
- Never create executable binaries.
- Only create text/code files.
- Never use ../ in filenames.
- Never use absolute paths.
- Use supported file extensions.
- Include complete file contents.
- Create all required project files.

For normal questions:

- DO NOT return JSON.
- Answer naturally.
- Be helpful and clear.
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
                "OpenRouter API key is not configured. "
                "Add OPENROUTER_API_KEY in Render Environment Variables."
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

            model=MODEL,

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

            max_tokens=8192
        )


        ai_text = (
            response.choices[0].message.content
            or ""
        ).strip()


        if not ai_text:

            raise ValueError(
                "OpenRouter returned an empty response."
            )


        # ====================================================
        # TRY TO PARSE JSON
        # ====================================================

        try:

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


        except json.JSONDecodeError:

            # Normal AI response.
            # Do NOT treat it as an error.

            return jsonify({

                "success": True,

                "reply": ai_text,

                "files": []

            })


    except Exception as error:

        print(
            "OPENROUTER ERROR:",
            repr(error)
        )


        return jsonify({

            "success": False,

            "reply":
                f"OpenRouter error: {error}"

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
# START SERVER
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
