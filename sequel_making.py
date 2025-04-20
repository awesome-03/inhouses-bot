import sqlite3

connection = sqlite3.connect("data.db")
cursor = connection.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS text_commands (
    command TEXT,
    command_content TEXT,
    adder_username TEXT,
    added_date INT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS ranks (
    username TEXT,
    ign TEXT,
    rank TEXT,
    last_update INT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS ping_logs (
    pinged_by TEXT,
    ping_time INT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS auto_reacts (
    reaction TEXT,
    user_id INT,
    user_name TEXT,
    added_by TEXT,
    added_date INT
)""")

connection.commit()

cursor.close()
connection.close()
