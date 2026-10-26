import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import poisson
from backend.stats import compute_team_stats

def get_h2h_factor(home_team, away_team, db_path="data/database.db"):
    """
    Considera gli ultimi 5 precedenti con variazione controllata tra 0.95 e 1.05 (±5%).
    """
    conn = sqlite3.connect(db_path)
    query = """
        SELECT home_team, away_team, home_goals, away_goals 
        FROM matches 
        WHERE status = 'complete' 
        AND ((home_team = ? AND away_team = ?) OR (home_team = ? AND away_team = ?))
        ORDER BY date DESC LIMIT 5
    """
    df = pd.read_sql(query, conn, params=(home_team, away_team, away_team, home_team))
    conn.close()
    
    if len(df) < 2:
        return 1.0
    
    home_points = 0
    total_games = len(df)
    
    for _, row in df.iterrows():
        if row['home_team'] == home_team:
            if row['home_goals'] > row['away_goals']: home_points += 3
            elif row['home_goals'] == row['away_goals']: home_points += 1
        else:
            if row['away_goals'] > row['home_goals']: home_points += 3
            elif row['away_goals'] == row['home_goals']: home_points += 1
            
    max_pts = total_games * 3
    performance_ratio = home_points / max_pts if max_pts > 0 else 0.5
    
    h2h_factor = 0.95 + (performance_ratio * 0.10)
    return float(np.clip(h2h_factor, 0.95, 1.05))

def dixon_coles_adjustment(i, j, lam_h, lam_a, rho=-0.11):
    """
    Correzione di Dixon-Coles per i punteggi bassi (0-0, 1-0, 0-1, 1-1).
    """
    if i == 0 and j == 0:
        return 1.0 - (lam_h * lam_a * rho)
    elif i == 0 and j == 1:
        return 1.0 + (lam_h * rho)
    elif i == 1 and j == 0:
        return 1.0 + (lam_a * rho)
    elif i == 1 and j == 1:
        return 1.0 - rho
    return 1.0

def calculate_match_probabilities(home_team, away_team, max_goals=6):
    attack, defense, avg_h, avg_a = compute_team_stats()
    
    att_h = attack.get(home_team, 1.0)
    def_h = defense.get(home_team, 1.0)
    att_a = attack.get(away_team, 1.0)
    def_a = defense.get(away_team, 1.0)
    
    h2h = get_h2h_factor(home_team, away_team)
    
    # Lambda con fattore campo (+4%) e H2H smorzato
    lam_h = att_h * def_a * avg_h * 1.04 * h2h
    lam_a = att_a * def_h * avg_a
    
    # Soglie minime di sicurezza sui gol attesi lambda
    lam_h = max(lam_h, 0.70)
    lam_a = max(lam_a, 0.65)
    
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            base_prob = poisson.pmf(i, lam_h) * poisson.pmf(j, lam_a)
            correction = dixon_coles_adjustment(i, j, lam_h, lam_a)
            matrix[i, j] = max(0, base_prob * correction)
            
    matrix /= matrix.sum()
    
    p_home = np.sum(np.tril(matrix, -1))
    p_draw = np.sum(np.diag(matrix))
    p_away = np.sum(np.triu(matrix, 1))
    
    return {
        "lambda_home": round(lam_h, 2),
        "lambda_away": round(lam_a, 2),
        "prob_1": float(p_home),
        "prob_X": float(p_draw),
        "prob_2": float(p_away)
    }