import sqlite3

# Function to create the 'analysis' table if it doesn't exist
def create_analysis_table():
    conn = sqlite3.connect("data/users.db")  # Adjust path as necessary
    cursor = conn.cursor()

    # Create the analysis table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sentiment TEXT NOT NULL,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()
    print("Analysis table created successfully!")

# Function to insert sample data into the 'analysis' table
def insert_sample_data():
    conn = sqlite3.connect("data/users.db")  # Adjust path as necessary
    cursor = conn.cursor()

    # Insert some sample data
    cursor.execute("""
    INSERT INTO analysis (sentiment, content)
    VALUES ('positive', 'This is a positive post about well-being.')
    """)
    cursor.execute("""
    INSERT INTO analysis (sentiment, content)
    VALUES ('negative', 'This post expresses sadness and despair.')
    """)
    cursor.execute("""
    INSERT INTO analysis (sentiment, content)
    VALUES ('neutral', 'This post is neutral and without emotion.')
    """)

    conn.commit()
    conn.close()
    print("Sample data inserted successfully!")

# Call the functions to create the table and insert data
create_analysis_table()
insert_sample_data()
