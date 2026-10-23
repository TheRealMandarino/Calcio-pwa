import json
import pandas as pd
import numpy as np
from models import probabilita_poisson, correzione_dixon_coles, estrai_esiti_1x2, estrai_under_over, applica_fattori_correttivi, calcola_fattore_h2h

def esegui_pronostici():
    print("Caricamento dati da partite.json...")
    try:
        with open('partite.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Errore: Il file partite.json non è stato trovato. Esegui prima update_data.py!")
        return

    df = pd.DataFrame(data)
    
    # Conversione gol in numerico
    df['squadra_casa_gol'] = pd.to_numeric(df['squadra_casa_gol'], errors='coerce')
    df['squadra_ospite_gol'] = pd.to_numeric(df['squadra_ospite_gol'], errors='coerce')

    # Partite giocate (per calcolare le forze)
    df_giocate = df.dropna(subset=['squadra_casa_gol', 'squadra_ospite_gol']).copy()
    
    if len(df_giocate) == 0:
        print("Nessuna partita giocata trovata nello storico.")
        return

    media_gol_casa_tot = df_giocate['squadra_casa_gol'].mean()
    media_gol_ospite_tot = df_giocate['squadra_ospite_gol'].mean()

    # Calcoliamo le metriche di attacco e difesa per ogni squadra
    squadre = pd.unique(df_giocate[['squadra_casa', 'squadra_ospite']].values.ravel())
    forze = {}

    for sq in squadre:
        c_giocate = df_giocate[df_giocate['squadra_casa'] == sq]
        fatti_c = c_giocate['squadra_casa_gol'].mean() if len(c_giocate) > 0 else media_gol_casa_tot
        subiti_c = c_giocate['squadra_ospite_gol'].mean() if len(c_giocate) > 0 else media_gol_ospite_tot
        
        t_giocate = df_giocate[df_giocate['squadra_ospite'] == sq]
        fatti_t = t_giocate['squadra_ospite_gol'].mean() if len(t_giocate) > 0 else media_gol_ospite_tot
        subiti_t = t_giocate['squadra_casa_gol'].mean() if len(t_giocate) > 0 else media_gol_casa_tot

        forze[sq] = {
            'attacco_casa': fatti_c / media_gol_casa_tot,
            'difesa_casa': subiti_c / media_gol_ospite_tot,
            'attacco_trasferta': fatti_t / media_gol_ospite_tot,
            'difesa_trasferta': subiti_t / media_gol_casa_tot
        }

    # Partite future da pronosticare
    df_future = df[df['squadra_casa_gol'].isna() & df['squadra_ospite_gol'].isna()].copy()
    
    if len(df_future) == 0:
        print("Nessuna partita futura trovata nel calendario corrente.")
        return

    print(f"\nPronostici per le prossime partite (con 1X2 e Under/Over 2.5):\n")
    print("=" * 70)

    count = 0
    for idx, row in df_future.iterrows():
        if count >= 5:
            break
            
        c = row['squadra_casa']
        o = row['squadra_ospite']
        data = row['data']

        if c not in forze or o not in forze:
            continue

        # Lambda base da storico
        lam_c = forze[c]['attacco_casa'] * forze[o]['difesa_trasferta'] * media_gol_casa_tot
        lam_o = forze[o]['attacco_trasferta'] * forze[c]['difesa_casa'] * media_gol_ospite_tot

        # Integrazione Testa a Testa (H2H)
        h2h_c, h2h_o = calcola_fattore_h2h(df_giocate, c, o)
        lam_c_h2h = lam_c * h2h_c
        lam_o_h2h = lam_o * h2h_o

        # Fattori di Fatica e Boost (personalizzabili al volo)
        fatica_casa = 1.0
        fatica_ospite = 1.0   
        boost_casa = 1.0
        boost_ospite = 1.0

        # Applichiamo fatica e boost sui lambda ponderati con l'H2H
        lam_c_fin, lam_o_fin = applica_fattori_correttivi(lam_c_h2h, lam_o_h2h, fatica_casa, fatica_ospite, boost_casa, boost_ospite)

        # Calcoli Statistici
        matrice = probabilita_poisson(lam_c_fin, lam_o_fin)
        matrice_corretta = correzione_dixon_coles(matrice, lam_c_fin, lam_o_fin)
        esiti = estrai_esiti_1x2(matrice_corretta)
        uo = estrai_under_over(matrice_corretta, linea=2.5)

        print(f"Data: {data} | {c} vs {o}")
        print(f"  Lambda Base -> Casa: {lam_c:.2f} | Ospite: {lam_o:.2f}")
        print(f"  Lambda H2H  -> Casa: {lam_c_fin:.2f} | Ospite: {lam_o_fin:.2f}")
        print(f"  [1X2]    1: {esiti['1']}%  |  X: {esiti['X']}%  |  2: {esiti['2']}%")
        print(f"  [U/O]    Under 2.5: {uo['under']}%  |  Over 2.5: {uo['over']}%")
        print("-" * 70)
        count += 1

if __name__ == "__main__":
    esegui_pronostici()