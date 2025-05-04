class User:
    def __init__(self, userid, name, email, password, role):
        self.userid = userid  # Unique user ID
        self.name = name  # User's name
        self.email = email  # User's email address
        self.password = password  # User's password (should be hashed in real-world use)
        self.role = role  # User's role (e.g., "user" or "admin")
    
    def __repr__(self):
        return f"User(userid={self.userid}, name={self.name}, email={self.email}, role={self.role})"

    def __str__(self):
        return f"User {self.name} ({self.email}) with role {self.role}"

# Example usage:
# user = User(userid="uuid123", name="John Doe", email="john.doe@example.com", password="password123", role="user")
# print(user)
