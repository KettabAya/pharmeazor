import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import time
from pathlib import Path


df = pd.read_excel("config/Projet2_Liste_40_medicaments.xlsx")
medicines = (
    df["DCI (nom de la substance)"]
    .dropna()
    .astype(str)
    .str.strip()
    .tolist()
)
result = []
for medicine in medicines:
    result.append(medicine)
    if "+" in medicine:
        match = re.search(r"\((.*?)\)", medicine)

        if match:
            main_name = medicine[:match.start()].strip()

            if main_name:
                result.append(main_name)

            components = match.group(1).split("+")

            result.extend([
                component.strip()
                for component in components
                if component.strip()
            ])

        else:
            result.extend([
                part.strip()
                for part in medicine.split("+")
                if part.strip()
            ])
DRUG = list(dict.fromkeys(result))
BASE_URL = "https://www.dzair-pharma.net"
SEARCH_URL = f"{BASE_URL}/recherche"
HEADERS = {
    "User-Agent": "MedicationResearchBot/1.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9"
}
def extract_medication_interactions(url):
    
    interaction_url = url.split("#")[0] + "#interactions"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "fr-FR,fr;q=0.9"
    }

    try:
        response = requests.get(
            interaction_url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

    except requests.exceptions.RequestException as error:
        print(f"Interaction request error: {error}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    interactions = []

    # Find each severity group
    groups = soup.select(
        'div[id^="interactions-"]'
    )

    for group in groups:

        # Find group heading using aria-controls
        group_id = group.get("id")

        heading_button = soup.find(
            "button",
            attrs={"aria-controls": group_id}
        )

        severity = None

        if heading_button:
            heading = heading_button.find_all(
                "span",
                recursive=False
            )

            for span in heading:
                text = span.get_text(" ", strip=True)

                if text in [
                    "Association déconseillée",
                    "Précaution d'emploi",
                    "Contre-indication",
                    "À prendre en compte"
                ]:
                    severity = text
                    break

        # Extract all interactions
        for article in group.select("article"):

            header = article.find("header")
            footer = article.find("footer")

            substance = None
            substance_type = None
            availability = None

            if header:

                title = header.find("h4")

                if title:
                    substance = title.get_text(
                        " ", strip=True
                    )

                spans = header.find_all(
                    "span",
                    recursive=False
                )

                if len(spans) >= 1:
                    substance_type = spans[0].get_text(
                        " ", strip=True
                    )

                if len(spans) >= 2:
                    availability = spans[-1].get_text(
                        " ", strip=True
                    )

            risks = None
            recommendations = None

            for p in article.find_all("p"):

                label = p.get_text(" ", strip=True)

                if label == "Risques":

                    next_p = p.find_next_sibling("p")

                    if next_p:
                        risks = next_p.get_text(
                            " ", strip=True
                        )

                elif label == "Conduite à tenir":

                    next_p = p.find_next_sibling("p")

                    if next_p:
                        recommendations = next_p.get_text(
                            " ", strip=True
                        )

            source = None

            if footer:
                text = footer.get_text(
                    " ", strip=True
                )

                if "Source :" in text:
                    source = text.split(
                        "Source :", 1
                    )[1].strip()

            interactions.append({
                "substance": substance,
                "type": substance_type,
                "gravite": severity,
                "risques": risks,
                "conduite_a_tenir": recommendations,
                "disponibilite": availability,
                "source": source
            })

    if not groups:
        print(
            "Interaction HTML not found. "
            "The website may load it using JavaScript."
        )
        return None

    return interactions
def extract_medication_links(medication_name):

    params = {
        "q": medication_name,
        "mode": "dci"
    }

    try:
        response = requests.get(
            SEARCH_URL,
            params=params,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as error:
        print(f"Error searching {medication_name}: {error}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    medications = []
    seen_urls = set()

    for card in soup.select(".drug-card"):

        link_tag = card.select_one("a.drug-detail-btn[href]")

        if not link_tag:
            continue

        url = urljoin(BASE_URL, link_tag["href"])

      
        card_classes = card.get("class", [])

        if "retrait" in card_classes:
            status = "Retiré"

        elif "non_renouvele" in card_classes:
            status = "Non renouvelé"

        elif "enregistrement" in card_classes:
            status = "Enregistré"

        else:
  
            badges = card.select(".drug-badges .badge")

            badge_text = " ".join(
                badge.get_text(" ", strip=True).lower()
                for badge in badges
            )

            if "retiré" in badge_text:
                status = "Retiré"

            elif "non renouvelé" in badge_text:
                status = "Non renouvelé"

            elif "enregistré" in badge_text or "enreg." in badge_text:
                status = "Enregistré"

            else:
                status = "Inconnu"

        medications.append({
            "url": url,
            "status": status
        })

    print(f"{medication_name}: {len(medications)} results")

    if not medications:
        print(
            "Warning: No medication cards found. "
            "The page may have no results or use dynamic rendering."
        )

    return medications
def extract_medication_info(url, status="Inconnu"):

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()

    except requests.exceptions.RequestException as error:
        print(f"Error fetching {url}: {error}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    panel = soup.select_one("#fs-panneau-essentiel")

    if panel is None:
        print(f"Medication information not found: {url}")
        return None

    def get_text(element):
        return element.get_text(" ", strip=True) if element else None

    # All expected fields
    medication = {
        "url": url,
        "status": status,

        # Identification
        "DCI (Substance active)": None,
        "Nom de marque": None,
        "N° d'enregistrement": None,
        "Code produit": None,
        "Code ATC": None,
        "Type de produit": None,
        "Origine de fabrication": None,

        # Conditionnement
        "Forme pharmaceutique": None,
        "Voie d'administration": None,
        "Méthode d'administration": None,
        "Dosage": None,
        "Conditionnement": None,
        "Prescription": None,
        "Stabilité": None,

        # Fabricant
        "Laboratoire": None,
        "Pays d'origine": None,

        # Registration
        "Date d'enregistrement": None,
        "Date de fin de validité": None,
        "Année de nomenclature": None,
        "Version source": None,

        # Additional information
        "description": None,
        "medicament_en_algerie": None,
        "PPA": None,
        "RCP PDF": None,

        # Related medications
        "generiques": [],
        "related_presentations": []
    }

    # ==========================================
    # 1. EXTRACT ALL MAIN TABLE FIELDS
    # ==========================================

    for row in panel.select(
        ".fiche-main table.fiche-table tr"
    ):
        th = row.find("th")
        td = row.find("td")

        if not th or not td:
            continue

        field = get_text(th)

        # Copy the HTML before removing
        # supplementary EDQM and UCUM codes
        td_copy = BeautifulSoup(
            str(td),
            "html.parser"
        )

        for code in td_copy.select(".fiche-code"):
            code.decompose()

        value = get_text(td_copy)

        if field:
            medication[field] = value

    # ==========================================
    # 2. DESCRIPTION
    # ==========================================

    layout = panel.select_one(".fiche-layout")

    if layout:
        paragraph = layout.find_previous_sibling("p")

        if paragraph:
            text = get_text(paragraph)

            if text and "est un médicament" in text:
                medication["description"] = text

    # ==========================================
    # 3. MEDICATION IN ALGERIA
    # ==========================================

    for heading in panel.select(".section-title"):

        heading_text = get_text(heading) or ""

        if (
            "en Algérie" in heading_text
            and "équivalents" in heading_text
            and "validité" in heading_text
        ):
            content_div = heading.find_next_sibling("div")

            if content_div:
                paragraphs = content_div.find_all(
                    "p",
                    recursive=False
                )

                medication["medicament_en_algerie"] = (
                    "\n".join(
                        get_text(p)
                        for p in paragraphs
                        if get_text(p)
                    ) or None
                )

            break

    # ==========================================
    # 4. OTHER MEDICATIONS WITH SAME DCI
    # ==========================================

    same_dci_section = panel.select_one("#meme-dci")

    if same_dci_section:

        for card in same_dci_section.select(
            "a.detail-alt-card[href]"
        ):

            name = get_text(
card.select_one(".detail-alt-name")
            )

            meta = [
                get_text(tag)
                for tag in card.select(".detail-alt-meta")
            ]

            form_dosage = (
                meta[0] if len(meta) > 0 else None
            )

            laboratory = (
                meta[1] if len(meta) > 1 else None
            )

            forme = None
            dosage = None

            if form_dosage:
                parts = re.split(
                    r"\s+[—–]\s+",
                    form_dosage,
                    maxsplit=1
                )

                forme = parts[0]

                if len(parts) > 1:
                    dosage = parts[1]

            badges = [
                get_text(badge)
                for badge in card.select(".badge")
            ]

            product_type = None
            year = None

            for badge in badges:
                if not badge:
                    continue

                if re.fullmatch(r"\d{4}", badge):
                    year = badge

                elif badge not in ("🇩🇿", "🇫🇷"):
                    product_type = badge

            medication["generiques"].append({
                "nom": name,
                "forme": forme,
                "dosage": dosage,
                "laboratoire": laboratory,
                "type": product_type,
                "annee": year,
                "url": urljoin(
                    BASE_URL,
                    card["href"]
                )
            })

    # ==========================================
    # 5. RELATED PRESENTATIONS
    # ==========================================

    for heading in panel.find_all(["h2", "h3"]):

        heading_text = get_text(heading) or ""

        if not heading_text.startswith("Présentations de "):
            continue

        section = heading.parent
        table = section.find("table") if section else None

        if not table:
            continue

        for row in table.select("tbody tr"):

            cells = row.find_all("td")

            if len(cells) < 4:
                continue

            link = cells[0].find("a", href=True)

            medication["related_presentations"].append({
                "nom": get_text(cells[0]),
                "forme": get_text(cells[1]),
                "dosage": get_text(cells[2]),
                "conditionnement": get_text(cells[3]),
                "url": (
                    urljoin(BASE_URL, link["href"])
                    if link else url
                )
            })

        break

    # ==========================================
    # 6. PRICE (PPA)
    # ==========================================

    aside = panel.select_one(".fiche-aside")

    if aside:

        for label in aside.select(".fiche-aside-label"):

            if get_text(label) == "PPA":

                price_element = label.find_next_sibling()

                if price_element:
                    price = get_text(price_element)

                    if (
                        price
                        and "non disponible" not in price.lower()
                    ):
                        medication["PPA"] = price

                break

    # ==========================================
    # 7. OFFICIAL RCP PDF
    # ==========================================

    rcp_section = panel.select_one("#rcp")

    if rcp_section:

        pdf_link = rcp_section.select_one(
            'a[href*=".pdf"]'
        )

        if pdf_link:
            medication["RCP PDF"] = urljoin(
                BASE_URL,
                pdf_link["href"]
            )

    return medication
RAW_DIR = Path("data/row_data/json")
RAW_DIR.mkdir(parents=True, exist_ok=True)
saved_count = 0
for drug in DRUG:
    
    print(f"\nSearching for: {drug}")

    try:
        medications = extract_medication_links(drug)
    except Exception as error:
        print(f"Search error for {drug}: {error}")
        continue

    if not medications:
        print(f"No medications found for: {drug}")
        continue

    all_info = []
  

    for med in medications:

        url = med["url"]



        try:
            info = extract_medication_info(
                url,
                med.get("status", "Inconnu")
            )

            if not info:
                print(f"Failed to extract: {url}")
                continue

            info["status"] = med.get("status", "Inconnu")

            info["interactions"] = extract_medication_interactions(
                url
            )

            all_info.append(info)

            print(f"Extracted: {info.get('Nom de marque')}")

        except Exception as error:
            print(f"Error processing {url}: {error}")

        time.sleep(2)

    # Save one JSON file per searched drug
    if all_info:

        safe_drug_name = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            str(drug)
        ).strip("_")

        filename = f"{safe_drug_name}.json"
        filepath = RAW_DIR / filename

        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(
                all_info,
                file,
                ensure_ascii=False,
                indent=4
            )

        saved_count += len(all_info)

        print(f"Saved {len(all_info)} medications to {filepath}")

print("\nExtraction completed!")
print(f"Total medications saved: {saved_count}")
print(f"Output folder: {RAW_DIR.resolve()}")

