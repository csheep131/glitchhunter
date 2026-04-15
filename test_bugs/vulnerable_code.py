#!/usr/bin/env python3
"""
Test-Datei mit absichtlichen Sicherheitslücken für GlitchHunter-Tests.

Diese Datei enthält bekannte Schwachstellen die von GlitchHunter
erkannt werden sollten.
"""

import sqlite3
import os
import pickle
import requests
from typing import Optional


class VulnerableExamples:
    """Beispiele für häufige Sicherheitslücken."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
    
    # BUG 1: SQL Injection via f-string (KRITISCH)
    def sql_injection_fstring(self, user_id: str) -> Optional[dict]:
        """SQL Injection durch f-string Formatierung."""
        query = f"SELECT * FROM users WHERE id = '{user_id}'"
        cursor = self.conn.execute(query)
        return cursor.fetchone()
    
    # BUG 2: SQL Injection via .format() (KRITISCH)
    def sql_injection_format(self, username: str, password: str) -> bool:
        """SQL Injection durch .format() Methode."""
        query = "SELECT * FROM users WHERE username = '{}' AND password = '{}'".format(
            username, password
        )
        cursor = self.conn.execute(query)
        return cursor.fetchone() is not None
    
    # BUG 3: Command Injection (KRITISCH)
    def command_injection(self, filename: str) -> str:
        """Command Injection via os.system."""
        os.system(f"cat {filename}")
        return "Done"
    
    # BUG 4: Path Traversal (HOCH)
    def path_traversal(self, user_path: str) -> str:
        """Path Traversal durch nicht validierte Dateipfade."""
        base_dir = "/var/data"
        full_path = os.path.join(base_dir, user_path)
        with open(full_path, 'r') as f:
            return f.read()
    
    # BUG 5: Insecure Deserialization (KRITISCH)
    def insecure_deserialization(self, data: bytes) -> object:
        """Unsichere Deserialization mit pickle."""
        return pickle.loads(data)
    
    # BUG 6: Hardcoded Credentials (MITTEL)
    def authenticate_with_hardcoded_key(self, api_endpoint: str) -> dict:
        """Authentifizierung mit hardcoded API-Key."""
        api_key = "sk-1234567890abcdef"  # Hardcoded credential!
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(api_endpoint, headers=headers)
        return response.json()
    
    # BUG 7: Weak Hash (MD5) (MITTEL)
    def hash_password_md5(self, password: str) -> str:
        """Passwort-Hashing mit schwachem MD5."""
        import hashlib
        return hashlib.md5(password.encode()).hexdigest()
    
    # BUG 8: Missing Error Handling (NIEDRIG)
    def silent_exception(self, data: str) -> int:
        """Verschweigt Exceptions durch leeren except-Block."""
        try:
            return int(data)
        except ValueError:
            pass  # Exception wird stillschweigend ignoriert!
        return 0
    
    # BUG 9: Resource Not Closed (NIEDRIG)
    def file_not_closed(self, filepath: str) -> str:
        """Datei wird nicht richtig geschlossen."""
        f = open(filepath, 'r')  # Kein context manager!
        content = f.read()
        # f.close() wird vergessen!
        return content
    
    # BUG 10: Mutable Default Argument (NIEDRIG)
    def mutable_default(self, items: list = []) -> list:
        """Mutable default argument führt zu unerwartetem Verhalten."""
        items.append(len(items))
        return items
    
    # BUG 11: Uninitialized Variable (MITTEL)
    def uninitialized_var(self, condition: bool) -> str:
        """Variable wird möglicherweise nicht initialisiert."""
        if condition:
            result = "yes"
        # result wird nicht initialisiert wenn condition=False
        return result
    
    # BUG 12: TOCTOU Race Condition (MITTEL)
    def toctou_race(self, filepath: str) -> bool:
        """Time-of-check-time-of-use race condition."""
        if os.path.exists(filepath):
            # Zwischen Check und Open kann sich die Datei ändern
            with open(filepath, 'r') as f:
                return True
        return False
    
    # BUG 13: Weak Random für Security (MITTEL)
    def weak_random_token(self) -> str:
        """Schwacher Zufallsgenerator für Security-Token."""
        import random
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return ''.join(random.choice(chars) for _ in range(32))
    
    # BUG 14: Eval mit User Input (KRITISCH)
    def dangerous_eval(self, user_expression: str) -> any:
        """Gefährliche eval() mit User Input."""
        return eval(user_expression)
    
    # BUG 15: Debug Mode in Production (MITTEL)
    def run_flask_debug(self):
        """Flask mit Debug=True in Production."""
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            return "Hello World"
        
        # Debug mode enabled!
        app.run(host='0.0.0.0', port=5000, debug=True)


# Global examples für direkte Tests

# BUG 16: Direct SQL Injection (KRITISCH)
def get_user_by_email(email: str) -> Optional[dict]:
    """SQL Injection in globaler Funktion."""
    conn = sqlite3.connect(':memory:')
    query = f"SELECT * FROM users WHERE email = '{email}'"
    cursor = conn.execute(query)
    return cursor.fetchone()


# BUG 17: SSRF Potential (HOCH)
def fetch_url(user_url: str) -> str:
    """SSRF wenn user_url nicht validiert."""
    response = requests.get(user_url, timeout=5)
    return response.text


if __name__ == "__main__":
    # Demo usage
    vuln = VulnerableExamples(":memory:")
    
    # Create table for testing
    vuln.conn.execute("CREATE TABLE users (id TEXT, username TEXT, password TEXT)")
    vuln.conn.execute("INSERT INTO users VALUES ('1', 'admin', 'password123')")
    vuln.conn.commit()
    
    print("Test-Datei mit Sicherheitslücken geladen.")
    print("Diese Datei sollte von GlitchHunter scanbar sein.")
