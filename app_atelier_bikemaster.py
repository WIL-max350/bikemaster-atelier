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

# --- ARCHITECTURE ET CONFIGURATION DES FICHIERS ---
os.makedirs("Archives_Clients", exist_ok=True)
REGISTRE_PATH = "registre_devis.csv"
DATA_CSV_PATH = "universal_bikes_master_database_fr.csv"

# --- COMPILATION INITIALE DE LA BASE COMPLÈTE EN CAS D'ABSENCE ---
if not os.path.exists(DATA_CSV_PATH):
    marques = ["Trek", "Specialized", "Canyon", "Giant", "Scott", "Cannondale", "Orbea", "Cube", "Pinarello", "BMC",
               "Winspace", "Quickpro", "Elves", "Pardus", "Look", "Origine", "Lapierre", "Adris", "Gir's", "Superior"]
    categories = {
        "Route Performance": {"base_standover": 740, "base_stack": 530, "base_reach": 380, "prix": 5400, "elec": False},
        "Gravel": {"base_standover": 750, "base_stack": 560, "base_reach": 375, "prix": 3200, "elec": False},
        "Cyclo-cross": {"base_standover": 765, "base_stack": 545, "base_reach": 382, "prix": 3900, "elec": False},
        "VTT Trail": {"base_standover": 720, "base_stack": 610, "base_reach": 445, "prix": 4500, "elec": False}
    }
    rows = []
    for m in marques:
        for cat, specs in categories.items():
            mod_name = f"{m} Cross-X" if cat == "Cyclo-cross" else f"{m} Élite"
            tailles = ["S", "M", "L", "XL"]
            for i, t in enumerate(tailles):
                rows.append({
                    "Marque": m, "Modele": mod_name, "Categorie": cat, "Taille_Cadre": t,
                    "Taille_Pilote_Min_cm": 155 + (i * 10), "Taille_Pilote_Max_cm": 168 + (i * 10),
                    "Entrejambe_Min_cm": 70 + (i * 6), "Entrejambe_Max_cm": 78 + (i * 6),
                    "Top_Tube_mm": 520 + (i * 20), "Standover_mm": specs["base_standover"] + (i * 25),
                    "Reach_mm": specs["base_reach"] + (i * 15), "Stack_mm": specs["base_stack"] + (i * 20),
                    "Head_Angle_deg": 71.5 if cat == "Cyclo-cross" else (66.0 if "VTT" in cat else 72.0),
                    "Chainstay_mm": 425 if cat == "Cyclo-cross" else 435, 
                    "BB_Drop_mm": 62 if cat == "Cyclo-cross" else 68,
                    "Est_Electrique": specs["elec"], "Moteur_Marque_Modele": "N/A", "Batterie_Wh": 0, "Couple_Nm": 0,
                    "Prix_Base_HT": specs["prix"]
                })
    pd.DataFrame(rows).to_csv(DATA_CSV_PATH, index=False, encoding='utf-8')

@st.cache_data
def charger_base_universelle_reelle():
    try:
        return pd.read_csv(DATA_CSV_PATH, encoding='utf-8')
    except Exception:
        return pd.read_csv(DATA_CSV_PATH, encoding='latin-1')

# --- FONCTIONS LOGIQUES METIER ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔒 Accès Sécurisé - Atelier Bike Master")
        password = st.text_input("Saisissez le code d'accès magasin :", type="password", key="sec_pass_mag_final")
        if st.button("Se connecter"):
            if password == "Atelier2026":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Code d'accès incorrect.")
        return False
    return True

def normaliser_nom_dossier(nom):
    return re.sub(r'[^A-Z0-9_]', '', nom.upper().replace(" ", "_").replace("-", "_"))

def determiner_peripheriques(taille_pilote_cm, largeur_epaules_cm, categorie_velo):
    if "vtt" in categorie_velo.lower():
        largeur_cintre = 760 if taille_pilote_cm < 170 else (780 if taille_pilote_cm <= 180 else 800)
        potence = 40
    else:
        largeur_cintre = largeur_epaules_cm * 10 if largeur_epaules_cm else (380 if taille_pilote_cm < 165 else (400 if taille_pilote_cm <= 178 else 420))
        potence = 90 if taille_pilote_cm < 165 else (100 if taille_pilote_cm <= 178 else 110)
    return largeur_cintre, potence

def inscrire_dans_registre(nom_client, marque, modele, categorie, taille, total_ht, total_ttc, acompte, solde, chemin_pdf):
    nouvelle_ligne = {
        "Date_Emission": datetime.now().strftime("%Y-%m-%d"), "Nom_Client": nom_client,
        "Marque": marque, "Modele": modele, "Categorie": categorie, "Taille_Cadre": taille,
        "Total_HT_Euros": round(total_ht, 2), "Total_TTC_Euros": round(total_ttc, 2),
        "Acompte_TTC_Euros": round(acompte, 2), "Solde_TTC_Euros": round(solde, 2),
        "Statut": "Émis", "Fichier_PDF": chemin_pdf
    }
    df_ligne = pd.DataFrame([nouvelle_ligne])
    if os.path.exists(REGISTRE_PATH):
        try:
            df_existant = pd.read_csv(REGISTRE_PATH, encoding='utf-8')
            df_final = pd.concat([df_existant, df_ligne], ignore_index=True)
        except: df_final = df_ligne
    else: df_final = df_ligne
    df_final.to_csv(REGISTRE_PATH, index=False, encoding='utf-8')

def generer_pdf_devis(chemin_complet, nom_client, adresse_client, velo_info, cintre, potence, prix_totaux, pct_acompte):
    doc = SimpleDocTemplate(chemin_complet, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    style_text = ParagraphStyle('Txt', fontSize=9, leading=13)
    style_dr = ParagraphStyle('Dr', parent=style_text, alignment=2)
    
    logo = Drawing(120, 35)
    logo.add(Rect(0, 0, 120, 35, fillColor=colors.HexColor("#1A365D"), strokeColor=None))
    logo.add(String(12, 12, "BIKE MASTER", fontSize=13, fontName="Helvetica-Bold", fillColor=colors.white))
    
    elements = [
        Table([[logo, Paragraph("<b>BIKE MASTER ATELIER</b><br/>75017 Paris", style_dr)]], colWidths=[150, 370]),
        Spacer(1, 15),
        Table([
            [Paragraph("<b>Émetteur :</b> Bike Master", style_text), Paragraph(f"<b>Client :</b> {nom_client}<br/>{adresse_client}", style_text)],
            [Paragraph(f"<b>Date :</b> {datetime.now().strftime('%d/%m/%Y')}", style_text), Paragraph("", style_text)]
        ], colWidths=[260, 260]),
        Spacer(1, 15),
        Paragraph("<b>1. Spécifications du Poste de Pilotage Analysé (Résultat Automatique)</b>", styles['Heading3']),
        Table([
            ["Marque", "Modèle", "Cadre Prévu", "Cintre", "Potence", "Arbitrage Profil"],
            [velo_info['Marque'], velo_info['Modele'], velo_info['Taille_Cadre'], f"{cintre} mm", f"{potence} mm", velo_info['Profil']]
        ], colWidths=[80, 100, 70, 70, 70, 130]),
        Spacer(1, 15),
        Paragraph("<b>2. Détail Commercial Chiffré & Échéances</b>", styles['Heading3'])
    ]
    
    ts = TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")), ('PADDING', (0,0), (-1,-1), 5), ('FONTSIZE', (0,0), (-1,-1), 8)])
    elements[0].setStyle(ts)
    elements[2].setStyle(ts)
    elements[5].setStyle(ts)
    
    lignes_facture = [
        ["Désignation", "Qté", "Total HT"],
        [f"Configuration Châssis : {velo_info['Marque']} {velo_info['Modele']}", "1", f"{prix_totaux['velo']:.2f} €"],
        ["Composants Périphériques Élite (Cintre + Potence)", "1", f"{(prix_totaux['cintre'] + prix_totaux['potence']):.2f} €"],
        ["Main d'œuvre Atelier & Posture Professionnelle", "1", f"{prix_totaux['mo']:.2f} €"]
    ]
    if prix_totaux['remise'] > 0:
        lignes_facture.append([f"Remise Commerciale Appliquée", "1", f"-{prix_totaux['remise']:.2f} €"])
        
    lignes_facture.extend([
        ["", "Total Net HT :", f"{prix_totaux['net_ht']:.2f} €"],
        ["", "TVA (20%) :", f"{prix_totaux['tva']:.2f} €"],
        ["", "Total TTC :", f"{prix_totaux['ttc']:.2f} €"],
        ["", f"ACOMPTE REQUIS ({pct_acompte}%) :", f"{prix_totaux['acompte']:.2f} €"],
        ["", "SOLDE À LA LIVRAISON :", f"{prix_totaux['solde']:.2f} €"]
    ])
    
    tf = Table(lignes_facture, colWidths=[280, 140, 100])
    tf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")), ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-6), 0.5, colors.HexColor("#E2E8F0")), ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('PADDING', (0,0), (-1,-1), 5), ('FONTNAME', (1,-5), (2,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1,-2), (2,-2), colors.HexColor("#C53030")), ('BACKGROUND', (1,-2), (2,-2), colors.HexColor("#FEF2F2")),
        ('TEXTCOLOR', (1,-1), (2,-1), colors.HexColor("#2B6CB0"))
    ]))
    elements.append(tf)
    
    elements.append(Spacer(1, 15))
    t_sig = Table([
        ["Mentions de commande & Acompte :", "Validation Client :"],
        [f"Le montage débutera dès réception de l'acompte.\nLe solde sera dû le jour de l'ajustement final.", "Bon pour accord, Lu et approuvé\nDate et Signature :"]
    ], colWidths=[260, 260])
    t_sig.setStyle(TableStyle([('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")), ('BOTTOMPADDING', (1,1), (1,1), 30)]))
    elements.append(t_sig)
    
    doc.build(elements)

# --- EXECUTION APPLI ---
if check_password():
    df_base = charger_base_universelle_reelle()
    
    st.sidebar.title("🔬 Profils de Test Rapide")
    scenario = st.sidebar.selectbox("Charger un profil type :", ["Manuel (Saisie libre)", "Route Buste Long", "VTT Grandes Jambes", "Cyclo-cross Standard", "Gravel Standard"])
    
    def_nom, def_h, def_in, def_brand, def_cat = "Jean-Pierre Clavel", 175, 81, "Look", "Route Performance"
    if scenario == "Route Buste Long": def_nom, def_h, def_in, def_brand, def_cat = "Lucas Buste Long", 182, 82, "Look", "Route Performance"
