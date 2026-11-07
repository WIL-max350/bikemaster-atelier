# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, String

# --- ARCHITECTURE DES FICHIERS ---
REGISTRE_PATH = "registre_devis.csv"
DATA_CSV_PATH = "universal_bikes_master_database_fr.csv"

# --- GENERATION EN MEMOIRE DIRECTE SANS ATTENTE ---
if not os.path.exists(DATA_CSV_PATH):
    marques = ["Trek", "Specialized", "Canyon", "Giant", "Scott", "Cannondale", "Orbea", "Cube", "Pinarello", "BMC",
               "Winspace", "Quickpro", "Elves", "Pardus", "Look", "Origine", "Lapierre", "Adris", "Gir's", "Superior"]
    categories = {
        "Route Performance": {"base_standover": 740, "base_stack": 530, "base_reach": 380, "prix": 5400},
        "Gravel": {"base_standover": 750, "base_stack": 560, "base_reach": 375, "prix": 3200},
        "Cyclo-cross": {"base_standover": 765, "base_stack": 545, "base_reach": 382, "prix": 3900},
        "VTT Trail": {"base_standover": 720, "base_stack": 610, "base_reach": 445, "prix": 4500}
    }
    rows = []
    for m in marques:
        for cat, specs in categories.items():
            mod_name = f"{m} Cross-X" if cat == "Cyclo-cross" else f"{m} Élite"
            for i, t in enumerate(["S", "M", "L", "XL"]):
                rows.append({
                    "Marque": m, "Modele": mod_name, "Categorie": cat, "Taille_Cadre": t,
                    "Taille_Pilote_Min_cm": 150 + (i * 12), "Taille_Pilote_Max_cm": 168 + (i * 12),
                    "Entrejambe_Min_cm": 68 + (i * 6), "Entrejambe_Max_cm": 78 + (i * 6),
                    "Standover_mm": specs["base_standover"] + (i * 25), "Prix_Base_HT": specs["prix"]
                })
    pd.DataFrame(rows).to_csv(DATA_CSV_PATH, index=False, encoding='utf-8')

@st.cache_data
def charger_base_universelle_reelle():
    """Charge la base universelle de données."""
    try:
        return pd.read_csv(DATA_CSV_PATH, encoding='utf-8')
    except Exception:
        return pd.read_csv(DATA_CSV_PATH, encoding='latin-1')

def determiner_peripheriques(taille_cm, buste_cm, bras_cm, epaules_cm, categorie):
    if "vtt" in categorie.lower(): return 780, 40
    return (epaules_cm * 10 if epaules_cm else 420), (100 if taille_cm <= 178 else 110)

# --- LOCK DE SÉCURITÉ MAGASIN ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "s_nom" not in st.session_state:
    st.session_state["s_nom"], st.session_state["s_prenom"] = "CLAVEL", "Jean-Pierre"
    st.session_state["s_adresse"], st.session_state["s_fact"] = "Lyon", "Identique"
    st.session_state["s_taille"], st.session_state["s_ej"] = 175, 81
    st.session_state["s_bu"], st.session_state["s_br"] = 62, 64
    st.session_state["s_ep"], st.session_state["s_po"], st.session_state["s_pt"] = 40, 75, 27.0

if not st.session_state.authenticated:
    st.title("🔒 Accès Sécurisé - Atelier Bike Master")
    password = st.text_input("Saisissez le code d'accès magasin :", type="password", key="p_final_v7_stable")
    if st.button("Se connecter"):
        if password == "Atelier2026": st.session_state.authenticated = True; st.rerun()
        else: st.error("Code d'accès incorrect.")
else:
    df_base = charger_base_universelle_reelle()
    st.sidebar.title("Compass Navigation")
    page = st.sidebar.radio("Sélectionner un Espace :", ["👤 1. Fiche Profil Client", "🚴 2. Univers ROUTE", "🚴 3. Univers CYCLO-CROSS", "🚴 4. Univers GRAVEL", "🚴 5. Univers VTT", "📊 6. Registre & Télémétrie"])
    
    if page == "👤 1. Fiche Profil Client":
        st.header("👤 Fiche Anthropométrique & Profil Client Central")
        st.session_state["s_nom"] = st.text_input("Nom de famille", value=st.session_state["s_nom"]).upper()
        st.session_state["s_prenom"] = st.text_input("Prénom", value=st.session_state["s_prenom"]).capitalize()
        st.session_state["s_adresse"] = st.text_input("Adresse principale", value=st.session_state["s_adresse"])
        st.session_state["s_fact"] = st.text_input("Adresse de facturation", value=st.session_state["s_fact"])
        
        st.write("---")
        st.subheader("📏 Les 7 Mensurations Clients (Saisie Manuelle au Clavier)")
        st.session_state["s_taille"] = st.number_input("1. Taille Globale du corps (cm)", value=st.session_state["s_taille"])
        st.session_state["s_ej"] = st.number_input("2. Hauteur de l'Entrejambe (cm)", value=st.session_state["s_ej"])
        st.session_state["s_bu"] = st.number_input("3. Taille du Buste (cm)", value=st.session_state["s_bu"])
        st.session_state["s_br"] = st.number_input("4. Taille de Bras (cm)", value=st.session_state["s_br"])
        st.session_state["s_ep"] = st.number_input("5. Largeur d'Épaules (cm)", value=st.session_state["s_ep"])
        st.session_state["s_po"] = st.number_input("6. Poids Corporel (kg)", value=st.session_state["s_po"])
        st.session_state["s_pt"] = st.number_input("7. Pointure de pied (cm)", value=st.session_state["s_pt"])
        st.success("✔️ Données enregistrées en direct.")

    elif page in ["🚴 2. Univers ROUTE", "🚴 3. Univers CYCLO-CROSS", "🚴 4. Univers GRAVEL", "🚴 5. Univers VTT"]:
        cat_map = {"🚴 2. Univers ROUTE": "Route Performance", "🚴 3. Univers CYCLO-CROSS": "Cyclo-cross", "🚴 4. Univers GRAVEL": "Gravel", "🚴 5. Univers VTT": "VTT Trail"}
        univers_actuel = cat_map[page]
        st.header(f"⚙️ Calcul Automatique & Devis : {univers_actuel.upper()}")
        
        st.info(f"👤 Client chargé : {st.session_state['s_prenom']} {st.session_state['s_nom']} ({st.session_state['s_taille']} cm | EJ: {st.session_state['s_ej']} cm)")
        df_m = df_base[df_base["Categorie"] == univers_actuel]
        
        marque = st.selectbox("Sélectionner la Marque", sorted(df_m["Marque"].unique()))
        df_mc = df_m[df_m["Marque"] == marque]
        
        col_l, col_r = st.columns(2)
        
        # --- BASE DE DONNÉES DU COMBO Cockpit Intégré ---
        combos_disponibles = {
            "Combo Carbone 380mm x 90mm (Tarif: 390€ HT)": {"largeur": 380, "potence": 90, "prix": 390.0},
            "Combo Carbone 400mm x 90mm (Tarif: 390€ HT)": {"largeur": 400, "potence": 90, "prix": 390.0},
            "Combo Carbone 400mm x 100mm (Tarif: 420€ HT)": {"largeur": 400, "potence": 100, "prix": 420.0},
            "Combo Carbone 420mm x 100mm (Tarif: 420€ HT)": {"largeur": 420, "potence": 100, "prix": 420.0},
            "Combo Carbone 420mm x 110mm (Tarif: 450€ HT)": {"largeur": 420, "potence": 110, "prix": 450.0},
            "Combo Carbone 440mm x 110mm (Tarif: 450€ HT)": {"largeur": 440, "potence": 110, "prix": 450.0},
            "Combo VTT Standard 780mm x 40mm (Tarif: 250€ HT)": {"largeur": 780, "potence": 40, "prix": 250.0}
        }
        
        with col_l:
            st.subheader("⚙️ Configuration Technique & Atelier")
            candidats = df_mc[(st.session_state["s_taille"] >= df_mc["Taille_Pilote_Min_cm"]) & (st.session_state["s_taille"] <= df_mc["Taille_Pilote_Max_cm"])]
            
            if not candidats.empty: sel_row = candidats.iloc
            elif not df_mc.empty: sel_row = df_mc.iloc
            else: sel_row = None
            
            if sel_row is not None:
                cintre_auto, potence_auto = determiner_peripheriques(st.session_state["s_taille"], st.session_state["s_bu"], st.session_state["s_br"], st.session_state["s_ep"], univers_actuel)
                t_cadre = st.text_input("Taille du Cadre assignée Atelier", value=str(sel_row["Taille_Cadre"]))
                
                st.write("---")
                st.markdown("**🎛️ Sélection du Combo Cintre / Potence Intégré**")
                
                # Détermination de la clé par défaut la plus proche
                nom_par_defaut = "Combo Carbone 420mm x 100mm (Tarif: 420€ HT)"
                if "vtt" in univers_actuel.lower():
                    nom_par_defaut = "Combo VTT Standard 780mm x 40mm (Tarif: 250€ HT)"
                else:
                    for nom_combo, specs in combos_disponibles.items():
                        if specs["largeur"] == int(cintre_auto) and specs["potence"] == int(potence_auto):
                            nom_par_defaut = nom_combo
                            break
                            
                combo_choisi = st.selectbox("Sélectionner la taille et tarification du Combo :", list(combos_disponibles.keys()), index=list(combos_disponibles.keys()).index(nom_par_defaut))
                specs_combo = combos_disponibles[combo_choisi]
            else:
                st.error("Aucune donnée de catalogue disponible.")
                st.stop()
                
        with col_r:
            st.subheader("💶 Tarification Libre & Devis Avant Acompte")
            prix_defaut = float(sel_row["Prix_Base_HT"]) if sel_row is not None else 5400.0
            p_velo = st.number_input("Prix du kit Cadre & Groupe HT (€)", 0.0, 30000.0, prix_defaut)
            
            # Injection automatique du prix du combo sélectionné à gauche
            p_combo = st.number_input("Prix du Combo Cintre/Potence sélectionné HT (€)", 0.0, 2000.0, float(specs_combo["prix"]))
            p_mo = st.number_input("Forfait Montage Atelier HT (€)", 0.0, 1000.0, 150.0)
            
            st.write(" ")
            pct_acompte = st.slider("Acompte obligatoire à la commande (%)", 10, 100, 30, step=5)
        
        # --- CALCULS ECONOMIQUES EN DIRECT ---
        brut_ht = p_velo + p_combo + p_mo
        ttc = brut_ht * 1.20
        acompte = ttc * (pct_acompte / 100.0)
        solde = ttc - acompte
        
        st.write("---")
        st.markdown("### 🛠️ Fiche de Préparation Finale Atelier")
        c1, c2, c3 = st.columns(3)
