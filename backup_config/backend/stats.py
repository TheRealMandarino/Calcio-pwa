import sqlite3
import pandas as pd

def compute_team_stats(db_path="data/database.db"):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM matches WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL", conn)
    conn.close()
    
    if df.empty:
        print("ATTENZIONE: Nessuna partita completata trovata nel database!")
        return {}, {}, 1.0, 1.0

    avg_home_goals = df['home_goals'].mean()
    avg_away_goals = df['away_goals'].mean()
    
    home_stats = df.groupby('home_team').agg(
        home_matches=('home_goals', 'count'),
        goals_scored=('home_goals', 'sum'),
        goals_conceded=('away_goals', 'sum')
    ).reset_index()  # CORRETTO DA .reset() A .reset_index()
    
    away_stats = df.groupby('away_team').agg(
        away_matches=('away_goals', 'count'),
        goals_scored=('away_goals', 'sum'),
        goals_conceded=('home_goals', 'sum')
    ).reset_index()  # CORRETTO DA .reset() A .reset_index()
    
    teams = pd.merge(home_stats, away_stats, left_on='home_team', right_on='away_team', suffixes=('_home', '_away'))
    teams['total_matches'] = teams['home_matches'] + teams['away_matches']
    teams['total_scored'] = teams['goals_scored_home'] + teams['goals_scored_away']
    teams['total_conceded'] = teams['goals_conceded_home'] + teams['goals_conceded_away']
    
    league_avg_scored_home = avg_home_goals if avg_home_goals > 0 else 1.0
    league_avg_conceded_away = avg_away_goals if avg_away_goals > 0 else 1.0

    attack_strength = {}
    defense_strength = {}
    
    for _, row in teams.iterrows():
        team = row['home_team']
        att_rate = (row['total_scored'] / row['total_matches']) if row['total_matches'] > 0 else league_avg_scored_home
        attack_strength[team] = att_rate / league_avg_scored_home
        
        def_rate = (row['total_conceded'] / row['total_matches']) if row['total_matches'] > 0 else league_avg_conceded_away
        defense_strength[team] = def_rate / league_avg_conceded_away

    return attack_strength, defense_strength, avg_home_goals, avg_away_goals