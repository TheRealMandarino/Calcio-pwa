import sqlite3
import soccerdata as sd
import pandas as pd

def init_db(db_path="data/database.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            home_goals INTEGER,
            away_goals INTEGER,
            home_xg REAL,
            away_xg REAL,
            status TEXT,
            season TEXT
        )
    """)
    conn.commit()
    conn.close()

def update_soccer_data(league="ITA-Serie A"):
    seasons = ["2021", "2022", "2023", "2024", "2025", "2026"]
    
    print(f"Scraping delle partite per {league} (stagioni {seasons[0]} - {seasons[-1]})...")
    fbref = sd.FBref(leagues=league, seasons=seasons)
    schedule = fbref.read_schedule()
    
    matches_data = []
    for idx, row in schedule.iterrows():
        # Cerca il punteggio tra le varie colonne possibili di soccerdata
        h_score = row.get('home_score')
        a_score = row.get('away_score')
        
        if pd.isna(h_score) or h_score == '':
            h_score = row.get('home_goals')
        if pd.isna(a_score) or a_score == '':
            a_score = row.get('away_goals')
            
        # Se ancora assente, prova a leggere dalla colonna 'score' (es. "2–1")
        score_col = row.get('score')
        if (pd.isna(h_score) or pd.isna(a_score)) and isinstance(score_col, str) and ('-' in score_col or '–' in score_col):
            sep = '-' if '-' in score_col else '–'
            parts = score_col.split(sep)
            try:
                h_score = int(parts[0].strip())
                a_score = int(parts[1].strip())
            except:
                pass

        # Conversione sicura in interi
        try:
            h_goals = int(float(h_score)) if not pd.isna(h_score) and str(h_score) != '' else None
        except:
            h_goals = None
            
        try:
            a_goals = int(float(a_score)) if not pd.isna(a_score) and str(a_score) != '' else None
        except:
            a_goals = None

        h_xg = row.get('home_xg', 0.0)
        if pd.isna(h_xg): h_xg = 0.0
        
        a_xg = row.get('away_xg', 0.0)
        if pd.isna(a_xg): a_xg = 0.0

        matches_data.append({
            'date': str(row.get('date', '')),
            'home_team': row.get('home_team'),
            'away_team': row.get('away_team'),
            'home_goals': h_goals,
            'away_goals': a_goals,
            'home_xg': float(h_xg),
            'away_xg': float(a_xg),
            'status': str(row.get('status', 'scheduled')),
            'season': str(row.get('season', ''))
        })
    
    df = pd.DataFrame(matches_data)
    completed_count = df['home_goals'].notna().sum()
    print(f"Totale match scaricati: {len(df)} | Match con gol registrati correttamente: {completed_count}")
    
    conn = sqlite3.connect("data/database.db")
    df.to_sql("matches", conn, if_exists="replace", index=False)
    conn.close()
    print("Database aggiornato con successo.")

if __name__ == "__main__":
    init_db()
    update_soccer_data()