const messages =
    document.getElementById("messages");

const input =
    document.getElementById("input");

const composer =
    document.getElementById("composer");

const sendButton =
    document.querySelector(".send-button");


function escapeHTML(text) {

    return String(text).replace(
        /[&<>"']/g,
        character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        })[character]
    );
}


function addMessage(
    text,
    type,
    files = []
) {

    const message =
        document.createElement("div");

    message.className =
        "message " + type;


    const bubble =
        document.createElement("div");

    bubble.className =
        "bubble";


    bubble.innerHTML = `
        <div class="message-name">
            ${
                type === "user"
                    ? "You"
                    : "Nova AI"
            }
        </div>

        ${escapeHTML(text)}
    `;


    if (files.length > 0) {

        const card =
            document.createElement("div");

        card.className =
            "file-card";

        const heading =
            document.createElement("strong");

        heading.textContent =
            "Created files";

        card.appendChild(heading);


        files.forEach(file => {

            const row =
                document.createElement("div");

            const link =
                document.createElement("a");

            link.href =
                "/api/download/" +
                encodeURIComponent(file);

            link.textContent =
                file;

            link.download = file;

            row.appendChild(link);

            card.appendChild(row);
        });


        bubble.appendChild(card);
    }


    message.appendChild(bubble);

    messages.appendChild(message);

    messages.scrollTop =
        messages.scrollHeight;
}


function showTyping() {

    const message =
        document.createElement("div");

    message.id =
        "typing-message";

    message.className =
        "message assistant";

    message.innerHTML = `
        <div class="bubble typing">
            Nova AI is thinking...
        </div>
    `;

    messages.appendChild(message);

    messages.scrollTop =
        messages.scrollHeight;
}


function removeTyping() {

    const typing =
        document.getElementById(
            "typing-message"
        );

    if (typing) {
        typing.remove();
    }
}


function usePrompt(prompt) {

    input.value = prompt;

    input.focus();
}


composer.addEventListener(
    "submit",
    async event => {

        event.preventDefault();

        const message =
            input.value.trim();

        if (!message) {
            return;
        }


        addMessage(
            message,
            "user"
        );

        input.value = "";

        sendButton.disabled = true;

        showTyping();


        try {

            const response =
                await fetch(
                    "/api/chat",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            message
                        })
                    }
                );


            const data =
                await response.json();

            removeTyping();


            addMessage(
                data.reply ||
                data.error ||
                "Something went wrong.",
                "assistant",
                data.files || []
            );


        } catch (error) {

            removeTyping();

            addMessage(
                "Could not connect to Nova AI.",
                "assistant"
            );

        } finally {

            sendButton.disabled = false;

            input.focus();
        }
    }
);


input.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            composer.requestSubmit();
        }
    }
);


function newChat() {

    messages.innerHTML = `
        <div class="welcome">

            <div class="welcome-logo">
                N
            </div>

            <h1>
                Build something great.
            </h1>

            <p>
                Start a fresh conversation.
            </p>

        </div>
    `;

    input.focus();
}


function toggleTheme() {

    document.body.classList.toggle(
        "light"
    );
}


async function showFiles() {

    try {

        const response =
            await fetch("/api/files");

        const data =
            await response.json();


        if (!data.files.length) {

            addMessage(
                "There are no generated files yet.",
                "assistant"
            );

            return;
        }


        addMessage(
            "Generated files:\n\n" +
            data.files.join("\n"),
            "assistant"
        );

    } catch {

        addMessage(
            "Could not load generated files.",
            "assistant"
        );
    }
}


function createZip() {

    window.location.href =
        "/api/create-zip";
}


async function clearFiles() {

    if (
        !confirm(
            "Delete all generated files?"
        )
    ) {
        return;
    }


    try {

        const response =
            await fetch(
                "/api/clear-files",
                {
                    method: "POST"
                }
            );


        const data =
            await response.json();


        addMessage(
            data.message ||
            "Files cleared.",
            "assistant"
        );

    } catch {

        addMessage(
            "Could not clear files.",
            "assistant"
        );
    }
          }
