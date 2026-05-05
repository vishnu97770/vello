import random

class ResponseGenerator:
    """
    Generates fun, human-like responses with slight variations.
    """

    RESPONSES = {
        "open_chrome": [
            "Alright, let’s explore the web 🌐",
            "Opening Chrome. Time to surf! 🏄‍♂️"
        ],
        "open_terminal": [
            "Let’s open the terminal 💻",
            "Powering up the command line! 💻"
        ],
        "open_vscode": [
            "Time to build something awesome 🚀",
            "VS Code is ready. Let's write some code! 💻"
        ],
        "open_libreoffice": [
            "Let’s get productive 📄",
            "Opening LibreOffice. Time to work! 📝"
        ],
        "execute_command": [
            "Watch this magic happen ⚡",
            "Running that for you right now! ⚡"
        ],
        "search_ask": [
            "What should I search?",
            "What are we looking for today? 🔍"
        ],
        "terminal_ask": [
            "What should I run? 💻",
            "Ready to execute. What's the command? 💻"
        ],
        "vscode_greet": [
            "What are we coding today? 🚀",
            "Ready to build the future? 🛠️"
        ],
        "libreoffice_greet": [
            "What would you like to work on? 📄",
            "Ready for some document magic? ✍️"
        ],
        "generic_success": [
            "Done! Anything else? 😊",
            "Task complete! ✅"
        ],
        "goodbye": [
            "Goodbye! Have an awesome day! 👋",
            "See you later! 👋"
        ]
    }

    def get_response(self, key):
        if key in self.RESPONSES:
            return random.choice(self.RESPONSES[key])
        return "Task completed!"
