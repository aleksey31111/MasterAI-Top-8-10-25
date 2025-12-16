class WorkflowManager:
    def __init__(self, bot, database):
        self.bot = bot
        self.db = database
        self.workflows = {}

    def start_workflow(self, message, action_type):
        chat_id = message.chat.id
        self.workflows[chat_id] = {"action": action_type}
        self.ask_next_question(chat_id)

    def ask_next_question(self, chat_id):
        action = self.workflows[chat_id]["action"]
        questions = {
            "generate_text": "Какой тип текста хотите сгенерировать?",
            "generate_ideas": "По какой теме нужны идеи?"
        }
        question = questions.get(action, "")
        self.bot.send_message(chat_id, question)

    def handle_step(self, message):
        chat_id = message.chat.id
        if chat_id in self.workflows:
            answer = message.text
            action = self.workflows[chat_id]["action"]
            if action == "generate_text":
                type_ = answer
                self.bot.send_message(chat_id, "Введите тему текста:")
                self.workflows[chat_id]["type"] = type_
            elif action == "generate_ideas":
                topic = answer
                ideas = generate_ideas(topic)
                formatted_output = "\n".join([f"- {idea}" for idea in ideas])
                self.bot.send_message(chat_id, f"Идеи по теме \"{topic}\":\n{formatted_output}")
                del self.workflows[chat_id]