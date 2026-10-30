import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

def compute_team_stats(db_path="data/database.db", half_life_days=90):
    """
    Calcola le statistiche di attacco e difesa separate per Casa e Trasferta,
    applicando un fattore di Time Decay basato sulla data del match.
    """
    conn = sqlite3.connect(db_path)
    query = """
        SELECT date, league, home_team, away_team, home_goals, away_goals 
        FROM matches 
        WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL
        ORDER BY date ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        return {}, {}, {}, {}, {}, {}, 1.3, 1.1

    # Converti la colonna data in datetime per calcolare il time decay
    df['date'] = pd.to_datetime(df['date'])
    max_date = df['date'].max()

    home_attack_sum = {}
    home_attack_count = {}
    home_defense_sum = {}
    home_defense_count = {}

    away_attack_sum = {}
    away_attack_count = {}
    away_defense_sum = {}
    away_defense_count = {}

    league_home_goals = {}
    league_away_goals = {}
    league_matches_count = {}

    for _, row in df.iterrows():
        league = row['league']
        h_team = row['home_team']
        a_team = row['away_team']
        h_goals = float(row['home_goals'])
        a_goals = float(row['away_goals'])
        match_date = row['date']

        # Calcolo Time Decay esponenziale
        days_diff = (max_date - match_date).days
        decay_weight = np.exp(-np.log(2) * days_diff / half_life_days)
        if decay_weight < 0.1:
            decay_weight = 0.1

        if league not in league_home_goals:
            league_home_goals[league] = 0.0
            league_away_goals[league] = 0.0
            league_matches_count[league] = 0.0

        league_home_goals[league] += h_goals * decay_weight
        league_away_goals[league] += a_goals * decay_weight
        league_matches_count[league] += decay_weight

        # Accumula per Squadra Casa
        home_attack_sum[h_team] = home_attack_sum.get(h_team, 0.0) + (h_goals * decay_weight)
        home_attack_count[h_team] = home_attack_count.get(h_team, 0.0) + decay_weight
        home_defense_sum[h_team] = home_defense_sum.get(h_team, 0.0) + (a_goals * decay_weight)
        home_defense_count[h_team] = home_defense_count.get(h_team, 0.0) + decay_weight

        # Accumula per Squadra Trasferta
        away_attack_sum[a_team] = away_attack_sum.get(a_team, 0.0) + (a_goals * decay_weight)
        away_attack_count[a_team] = away_attack_count.get(a_team, 0.0) + decay_weight
        away_defense_sum[a_team] = away_defense_sum.get(a_team, 0.0) + (h_goals * decay_weight)
        away_defense_count[a_team] = away_defense_count.get(a_team, 0.0) + decay_weight

    avg_home_by_league = {lg: league_home_goals[lg] / league_matches_count[lg] for lg in league_home_goals}
    avg_away_by_league = {lg: league_away_goals[lg] / league_matches_count[lg] for lg in league_away_goals}

    global_avg_h = sum(league_home_goals.values()) / sum(league_matches_count.values()) if league_matches_count else 1.3
    global_avg_a = sum(league_away_goals.values()) / sum(league_matches_count.values()) if league_matches_count else 1.1

    home_attack_rating = {team: (home_attack_sum[team] / home_attack_count[team]) for team in home_attack_sum}
    home_defense_rating = {team: (home_defense_sum[team] / home_defense_count[team]) for team in home_defense_sum}
    away_attack_rating = {team: (away_attack_sum[team] / away_attack_count[team]) for team in away_attack_sum}
    away_defense_rating = {team: (away_defense_sum[team] / away_defense_count[team]) for team in away_defense_sum}

    return (
        home_attack_rating, home_defense_rating, 
        away_attack_rating, away_defense_rating, 
        avg_home_by_league, avg_away_by_league, 
        global_avg_h, global_avg_a
    )