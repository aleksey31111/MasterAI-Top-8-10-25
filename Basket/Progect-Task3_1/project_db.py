import sqlite3

class ProjectDatabase:
    def __init__(self):
        self.conn = sqlite3.connect("projects.db")
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT
            );
        """)
        self.conn.commit()

    def add_project(self, title, content):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO projects (title, content) VALUES (?, ?)", (title, content))
        self.conn.commit()