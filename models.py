import numpy as np
import math

def probabilita_poisson(lambda_casa, lambda_ospite, max_gol=6):
    """
    Calcola la matrice delle probabilità congiunte dei risultati esatti 
    usando la distribuzione di Poisson.
    """
    matrice = np.zeros((max_gol, max_gol))
    for i in range(max_gol):
        for j in range(max_gol):
            p_casa = (math.exp(-lambda_casa) * (lambda_casa ** i)) / math.factorial(i)
            p_ospite = (math.exp(-lambda_ospite) * (lambda_ospite ** j)) / math.factorial(j)
            matrice[i, j] = p_casa * p_ospite
    return matrice

def correzione_dixon_coles(matrice_prob, lambda_casa, lambda_ospite, rho=-0.13):
    """
    Applica la correzione di Dixon-Coles per correggere le probabilità 
    dei punteggi bassi (0-0, 1-0, 0-1, 1-1).
    """
    matrice = matrice_prob.copy()
    max_gol = matrice.shape[0]
    
    # Fattori di correzione per i punteggi bassi
    if max_gol > 1:
        # 0-0
        matrice[0, 0] *= (1 - lambda_casa * lambda_ospite * rho)
        # 1-0
        matrice[1, 0] *= (1 + lambda_ospite * rho)
        # 0-1
        matrice[0, 1] *= (1 + lambda_casa * rho)
        # 1-1
        matrice[1, 1] *= (1 - rho)
        
    # Riornormalizzazione della matrice
    totale = np.sum(matrice)
    if totale > 0:
        matrice = matrice / totale
        
    return matrice

def estrai_esiti_1x2(matrice_prob):
    """
    Estrae le percentuali di 1, X, 2 dalla matrice delle probabilità.
    """
    p_1 = 0.0
    p_x = 0.0
    p_2 = 0.0
    
    max_gol = matrice_prob.shape[0]
    for i in range(max_gol):
        for j in range(max_gol):
            if i > j:
                p_1 += matrice_prob[i, j]
            elif i == j:
                p_x += matrice_prob[i, j]
            else:
                p_2 += matrice_prob[i, j]
                
    return {
        "1": round(p_1 * 100, 2),
        "X": round(p_x * 100, 2),
        "2": round(p_2 * 100, 2)
    }

def estrai_under_over(matrice_prob, linea=2.5):
    """
    Calcola le percentuali di Under e Over (default 2.5) dalla matrice delle probabilità.
    """
    p_under = 0.0
    max_gol = matrice_prob.shape[0]
    
    for i in range(max_gol):
        for j in range(max_gol):
            if (i + j) < linea:
                p_under += matrice_prob[i, j]
                
    p_over = 1.0 - p_under
    
    return {
        "under": round(p_under * 100, 2),
        "over": round(p_over * 100, 2)
    }

def applica_fattori_correttivi(lambda_c, lambda_o, fattore_fatica_c=1.0, fattore_fatica_o=1.0, boost_c=1.0, boost_o=1.0):
    """
    Modifica i lambda attesi applicando fattori di fatica e boost.
    """
    lam_c_mod = lambda_c * fattore_fatica_c * boost_c
    lam_o_mod = lambda_o * fattore_fatica_o * boost_o
    return max(0.05, lam_c_mod), max(0.05, lam_o_mod)
def calcola_fattore_h2h(df_giocate, squadra_casa, squadra_trasferta, max_precedenti=5):
    """
    Estrae gli ultimi precedenti tra le due squadre e calcola un 
    coefficiente correttivo H2H per i lambda.
    """
    # Filtra le partite giocate tra le due squadre (in casa o in trasferta per entrambe)
    h2h = df_giocate[
        ((df_giocate['squadra_casa'] == squadra_casa) & (df_giocate['squadra_ospite'] == squadra_trasferta)) |
        ((df_giocate['squadra_casa'] == squadra_trasferta) & (df_giocate['squadra_ospite'] == squadra_casa))
    ].copy()
    
    if len(h2h) == 0:
        return 1.0, 1.0  # Nessun precedente trovato, nessun impatto
        
    # Ordiniamo per data (le più recenti in fondo) e prendiamo le ultime N
    h2h = h2h.sort_values('data').tail(max_precedenti)
    
    gol_fatti_casa = 0.0
    gol_subiti_casa = 0.0
    partite_contate = len(h2h)
    
    for _, row in h2h.iterrows():
        if row['squadra_casa'] == squadra_casa:
            gol_fatti_casa += row['squadra_casa_gol']
            gol_subiti_casa += row['squadra_ospite_gol']
        else:
            gol_fatti_casa += row['squadra_ospite_gol']
            gol_subiti_casa += row['squadra_casa_gol']
            
    # Medie nei precedenti diretti
    media_fatti_h2h = gol_fatti_casa / partite_contate
    media_subiti_h2h = gol_subiti_casa / partite_contate
    
    # Creiamo un fattore di spinta moderato (es. ±10% di influenza basata sui precedenti)
    # Se storicamente segna di più negli H2H, il fattore sarà > 1.0
    fattore_h2h_casa = 1.0 + ((media_fatti_h2h - 1.3) * 0.1)  # 1.3 media gol di riferimento
    fattore_h2h_trasferta = 1.0 + ((media_subiti_h2h - 1.3) * 0.1)
    
    # Limitiamo il fattore in un range sicuro (es. da 0.90 a 1.10) per evitare distorsioni eccessive
    fattore_h2h_casa = max(0.90, min(1.10, fattore_h2h_casa))
    fattore_h2h_trasferta = max(0.90, min(1.10, fattore_h2h_trasferta))
    
    return fattore_h2h_casa, fattore_h2h_trasferta