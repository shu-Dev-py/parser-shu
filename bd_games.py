import sqlite3
import pandas as pd

def create_bd():
    try:
        df = pd.read_excel('funpay_games_structure.xlsx')
    except FileNotFoundError:
        print("файл не найден")
        return

    conn = sqlite3.connect('funpay.db')
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_name TEXT NOT NULL,
            category_name TEXT NOT NULL,
            url TEXT NOT NULL,
            game_id TEXT NOT NULL)
    """)
    cursor.execute("DELETE FROM game_sections")

    for index,row in df.iterrows():
        cursor.execute("""
            INSERT INTO game_sections (game_name, category_name,url,game_id)
            VALUES (?, ?, ?, ?)
        """, (row["Game_Name"], row["Category_Name"], row["URL"], row["Game_ID"]))
    conn.commit()
    conn.close()

    print("база данных создана^^")

if __name__=="__main__":
    create_bd()
