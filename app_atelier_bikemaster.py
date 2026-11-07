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
os.makedirs("Archives_Clients", exist_ok=True)
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
    try:
        return pd.read_csv(DATA_CSV_PATH, encoding='utf-8')
    except Exception:
        return pd.read_csv(DATA_CSV_PATH, encoding='latin-1')

def determiner_peripheriques(taille_cm, buste_cm, bras_cm, epaules_cm, categorie):
    if "vtt" in categorie.lower(): return 780, 40
    return (epaules_cm * 10 if epaules_cm else 420), (100 if taille_cm <= 178 else 110)

def normaliser_nom_dossier(nom):
    return re.sub(r'[^A-Z0-9_]', '', nom.upper().replace(" ", "_").replace("-", "_"))

def inscrire_dans_registre(nom, prenom, tel, mail, h, ej, buste, bras, epaules, poids, pointure, marque, modele, cat, taille_c, total_ht, total_ttc, acompte, solde, chemin_pdf):
    nouvelle_ligne = {
        "Date": datetime.now().strftime("%Y-%m-%d"), "Nom": str(nom).upper(), "Prenom": str(prenom).capitalize(),
        "Telephone": tel, "Courriel": mail, "Taille_cm": h, "Entrejambe_cm": ej, "Buste_cm": buste, "Bras_cm": bras, "Epaule_cm": epaules,
        "Poids_kg": poids, "Pointure_cm": pointure, "Marque": marque, "Modele": modele, "Categorie": cat, "Taille_Cadre": taille_c,
        "Total_HT": round(total_ht, 2), "Total_TTC": round(total_ttc, 2), "Acompte_TTC": round(acompte, 2), "Solde_TTC": round(solde, 2), "Fichier_PDF": chemin_pdf
    }
    df_line = pd.DataFrame([nouvelle_ligne])
    if os.path.exists(REGISTRE_PATH):
        try:
            df_ext = pd.read_csv(REGISTRE_PATH, encoding='utf-8')
            df_final = pd.concat([df_ext, df_line], ignore_index=True)
        except: df_final = df_line
    else: df_final = df_line
    df_final.to_csv(REGISTRE_PATH, index=False, encoding='utf-8')

def generer_pdf_devis(chemin_complet, client, velo_info, cintre_mm, potence_mm, prix, pct):
    doc = SimpleDocTemplate(chemin_complet, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    style_text = ParagraphStyle('Txt', fontSize=9, leading=13)
    style_dr = ParagraphStyle('Dr', parent=style_text, alignment=2)
    logo = Drawing(120, 35)
    logo.add(Rect(0, 0, 120, 35, fillColor=colors.HexColor("#1A365D"), strokeColor=None))
    logo.add(String(12, 12, "BIKE MASTER", fontSize=13, fontName="Helvetica-Bold", fillColor=colors.white))
    
    elements = [
        Table([[logo, Paragraph("<b>BIKE MASTER ATELIER</b><br/>75017 Paris", style_dr)]], colWidths=[150, 380]),
        Spacer(1, 15),
        Table([
            [Paragraph("<b>Émetteur :</b> Bike Master Paris", style_text), Paragraph(f"<b>Client :</b> {client['nom']} {client['prenom']}<br/>Tél: {client['tel']} | Mail: {client['mail']}<br/>Adresse : {client['adresse']}", style_text)],
            [Paragraph(f"<b>Date :</b> {datetime.now().strftime('%d/%m/%Y')}", style_text), Paragraph(f"<b>Mensurations :</b> {client['taille']}cm | EJ: {client['entrejambe']}cm | Poids: {client['poids']}kg", style_text)]
        ], colWidths=[260, 270]),
        Spacer(1, 15),
        Paragraph("<b>1. Spécifications Configuration Atelier & Cadre</b>", styles['Heading3']),
        Table([
            ["Marque", "Modèle", "Cadre Prévu", "Largeur Cintre", "Longueur Potence", "Arbitrage"],
            [velo_info['Marque'], velo_info['Modele'], velo_info['Taille_Cadre'], f"{cintre_mm} mm", f"{potence_mm} mm", "Ajusté sur-mesure"]
        ], colWidths=[80, 100, 80, 80, 90, 100]),
        Spacer(1, 15),
        Paragraph("<b>2. Détail Commercial Chiffré</b>", styles['Heading3'])
    ]
    ts = TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")), ('PADDING', (0,0), (-1,-1), 5), ('FONTSIZE', (0,0), (-1,-1), 8)])
    elements[-2].setStyle(ts)
    
    lignes = [
        ["Désignation des Équipements", "Qté", "Montant HT"],
        [f"Kit Châssis Professionnel : {velo_info['Marque']} {velo_info['Modele']}", "1", f"{prix['velo']:.2f} €"],
        [f"Poste de Pilotage Monobloc sélectionné", "1", f"{prix['combo']:.2f} €"],
        ["Forfait Main d'œuvre Atelier & Posture", "1", f"{prix['mo']:.2f} €"],
        ["", "Sous-Total HT :", f"{prix['net_ht']:.2f} €"],
        ["", "TVA (20%) :", f"{prix['tva']:.2f} €"],
        ["", "TOTAL COMMANDÉ TTC :", f"{prix['ttc']:.2f} €"],
        ["", f"ACOMPTE REQUIS ({pct}%) :", f"{prix['acompte']:.2f} €"],
        ["", "SOLDE À LA LIVRAISON :", f"{prix['solde']:.2f} €"]
    ]
    tf = Table(lignes, colWidths=[310, 110, 110])
    tf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")), ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-6), 0.5, colors.HexColor("#E2E8F0")), ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('PADDING', (0,0), (-1,-1), 5), ('FONTNAME', (1,-5), (2,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1,-2), (2,-2), colors.HexColor("#C53030")), ('BACKGROUND', (1,-2), (2,-2), colors.HexColor("#FEF2F2"))
    ]))
    elements.append(tf)
    doc.build(elements)

# --- SÉCURISATION ET VARIABLES DE SESSION ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if "s_nom" not in st.session_state:
    st.session_state["s_nom"], st.session_state["s_prenom"] = "CLAVEL", "Jean-Pierre"
    st.session_state["s_tel"], st.session_state["s_mail"] = "06 12 34 56 78", "jp.clavel@mail.com"
    st.session_state["s_adresse"], st.session_state["s_fact"] = "45 Rue de la République, Lyon", "Identique"
    st.session_state["s_taille"], st.session_state["s_ej"] = 175, 81
    st.session_state["s_bu"], st.session_state["s_br"] = 62, 64
    st.session_state["s_ep"], st.session_state["s_po"], st.session_state["s_pt"] = 40, 75, 27.0

# --- ÉCRAN DE VERROUILLAGE INITIAL ---
if not st.session_state.authenticated:
    st.title("🔒 Accès Sécurisé - Atelier Bike Master")
    password = st.text_input("Saisissez le code d'accès magasin :", type="password", key="p_final_v11_prod")
    if st.button("Se connecter"):
        if password == "Atelier2026": 
            st.session_state.authenticated = True
            st.rerun()
        else: 
            st.error("Code d'accès incorrect. Veuillez contacter votre responsable d'atelier.")
else:
    # --- INTERFACE EN LIGNE ACTIVE ---
    df_base = charger_base_universelle_reelle()
    
    st.sidebar.title("Compass Navigation")
    page = st.sidebar.radio("Sélectionner un Espace :", [
        "👤 1. Fiche Profil Client", 
        "🚴 2. Univers ROUTE", 
        "🚴 3. Univers CYCLO-CROSS", 
        "🚴 4. Univers GRAVEL", 
        "🚴 5. Univers VTT", 
        "📊 6. Registre & Télémétrie"
    ])
    
    # --- AJOUT STRUCTUREL DU BOUTON DE DECONNEXION EN BAS DE BARRE LATÉRALE ---
    st.sidebar.write("---")
    if st.sidebar.button("🔴 Fin de session (Déconnexion)", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
    
    # --- ESPACE 1 : FICHE PROFIL CLIENT ---
    if page == "👤 1. Fiche Profil Client":
        st.header("👤 Fiche Anthropométrique & Profil Client Central")
        st.write("Saisissez l'identité, les coordonnées de contact et les 7 mensurations anthropométriques.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📝 Coordonnées & Contact")
            st.session_state["s_nom"] = st.text_input("Nom de famille", value=st.session_state["s_nom"]).upper()
            st.session_state["s_prenom"] = st.text_input("Prénom", value=st.session_state["s_prenom"]).capitalize()
            st.session_state["s_tel"] = st.text_input("Numéro de Téléphone mobile", value=st.session_state["s_tel"])
            st.session_state["s_mail"] = st.text_input("Adresse Courriel (Email)", value=st.session_state["s_mail"])
            st.session_state["s_adresse"] = st.text_input("Adresse de résidence", value=st.session_state["s_adresse"])
