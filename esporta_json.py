import json
import pandas as pd
from models import probabilita_poisson, correzione_dixon_coles, estrai_esiti_1x2, estrai_under_over, calcola_fattore_h2h

def genera_feed_pwa():
    try:
        with open('partite.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Errore: partite.json non trovato. Esegui prima update_data.py!")
        return

    df = pd.DataFrame(data)
    
    df['squadra_casa_gol'] = pd.to_numeric(df['squadra_casa_gol'], errors='coerce')
    df['squadra_ospite_gol'] = pd.to_numeric(df['squadra_ospite_gol'], errors='coerce')

    df_giocate = df.dropna(subset=['squadra_casa_gol', 'squadra_ospite_gol']).copy()
    media_casa = df_giocate['squadra_casa_gol'].mean()
    media_ospite = df_giocate['squadra_ospite_gol'].mean()

    squadre = pd.unique(df_giocate[['squadra_casa', 'squadra_ospite']].values.ravel())
    forze = {}
    for sq in squadre:
        c_giocate = df_giocate[df_giocate['squadra_casa'] == sq]
        f_c = c_giocate['squadra_casa_gol'].mean() if len(c_giocate) > 0 else media_casa
        s_c = c_giocate['squadra_ospite_gol'].mean() if len(c_giocate) > 0 else media_ospite
        
        t_giocate = df_giocate[df_giocate['squadra_ospite'] == sq]
        f_t = t_giocate['squadra_ospite_gol'].mean() if len(t_giocate) > 0 else media_ospite
        s_t = t_giocate['squadra_casa_gol'].mean() if len(t_giocate) > 0 else media_casa

        forze[sq] = {
            'attacco_c': f_c / media_casa,
            'difesa_t': s_t / media_casa,
            'attacco_t': f_t / media_ospite,
            'difesa_c': s_c / media_ospite
        }

    df_future = df[df['squadra_casa_gol'].isna() & df['squadra_ospite_gol'].isna()].copy()
    
    partite_pwa = []
    for idx, row in df_future.iterrows():
        c = row['squadra_casa']
        o = row['squadra_ospite']
        
        if c not in forze or o not in forze:
            continue
            
        # Lambda base
        lam_c = forze[c]['attacco_c'] * forze[o]['difesa_t'] * media_casa
        lam_o = forze[o]['attacco_t'] * forze[c]['difesa_c'] * media_ospite
        
        # Integrazione Testa a Testa (H2H)
        h2h_c, h2h_o = calcola_fattore_h2h(df_giocate, c, o)
        lam_c = lam_c * h2h_c
        lam_o = lam_o * h2h_o
        
        # Modello statistico
        matrice = probabilita_poisson(lam_c, lam_o)
        matrice_corr = correzione_dixon_coles(matrice, lam_c, lam_o)
        esiti = estrai_esiti_1x2(matrice_corr)
        uo = estrai_under_over(matrice_corr, linea=2.5)

        q1 = round(100 / max(esiti['1'], 1.0), 2)
        qx = round(100 / max(esiti['X'], 1.0), 2)
        q2 = round(100 / max(esiti['2'], 1.0), 2)
        q_over = round(100 / max(uo['over'], 1.0), 2)
        q_under = round(100 / max(uo['under'], 1.0), 2)

        match_id = f"2026-{c}-{o}".lower().replace(" ", "-")
        data_match = row['data']
        if len(str(data_match)) == 10:
            data_match += "T15:00:00Z"

        partite_pwa.append({
            "id": match_id,
            "campionato": "Serie A",
            "casa": c,
            "trasferta": o,
            "data": data_match,
            "quote": {"1": q1, "X": qx, "2": q2},
            "lambdaBase": {"casa": round(float(lam_c), 2), "trasferta": round(float(lam_o), 2)},
            "mercati": {
                "goalNoGoal": {"goal": 1.85, "noGoal": 1.95},
                "overUnder25": {"over": q_over, "under": q_under}
            }
        })

    with open('pwa_feed.json', 'w', encoding='utf-8') as f:
        json.dump(partite_pwa, f, ensure_ascii=False, indent=2)

    print(f"Esportate {len(partite_pwa)} partite con H2H in pwa_feed.json!")

if __name__ == "__main__":
    genera_feed_pwa()