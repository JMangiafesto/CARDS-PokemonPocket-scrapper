import requests
from bs4 import BeautifulSoup
import re
import json
import time
import os

BASE_URL = "https://pocket.limitlesstcg.com/cards/"

# Define all available sets
available_sets = ["A1", "P-A", "A1a", "A2", "A2a", "A2b", "A3", "A3A", "A3B"]

# Modify this list to scrape only specific sets
sets = ["A1", "P-A", "A1a", "A2", "A2a", "A2b", "A3", "A3A", "A3B"]  # All available sets

# Set code to descriptive filename mapping
set_filename_mapping = {
    "A1": "a1-genetic-apex.json",
    "P-A": "promo.json", 
    "A1a": "a1a-mythical-island.json",
    "A1b": "a1b-unknown.json",  # Add if needed
    "A2": "a2-space-time-smackdown.json",
    "A2a": "a2a-triumphant-light.json",
    "A2b": "a2b-shining-revelry.json", 
    "A3": "a3-celestial-guardians.json",
    "A3A": "a3a-extradimensional-crisis.json",
    "A3B": "a3b-eevee-grove.json",
    "A4": "a4-datamine.json"
}

# Rarity symbol to human-readable name mapping
rarity_mapping = {
    "◊": "Common",
    "◊◊": "Uncommon", 
    "◊◊◊": "Rare",
    "◊◊◊◊": "Rare EX",
    "☆": "Full Art",
    "☆☆": "Full Art EX/Support",
    "☆☆☆": "Immersive",
    "♛": "Gold Crown",
    "Crown Rare": "Gold Crown",  # Alternative name for ♛
    "Promo": "Promo",
    # Additional mappings for edge cases
    "One shiny star": "Full Art",
    "Two shiny stars": "Full Art EX/Support", 
    "Two shiny star": "Full Art EX/Support",  # Handle typo in user request
    "Unknown": "Unknown"
}

type_mapping = {
    "G": "Grass",
    "R": "Fire",
    "W": "Water",
    "L": "Lightning",
    "P": "Psychic",
    "F": "Fighting",
    "D": "Darkness",
    "M": "Metal",
    "Y": "Fairy",
    "C": "Colorless",
}

probabilitys_per_row = rate_by_rarity = {
    "1-3 card": {
        "◊": "100.000%",
        "◊◊": "0.000%",
        "◊◊◊": "0.000%",
        "◊◊◊◊": "0.000%",
        "☆": "0.000%",
        "☆☆": "0.000%",
        "☆☆☆": "0.000%",
        "♛": "0.000%",
    },
    "4 card": {
        "◊": "0.000%",
        "◊◊": "90.000%",
        "◊◊◊": "5.000%",
        "◊◊◊◊": "1.666%",
        "☆": "2.572%",
        "☆☆": "0.500%",
        "☆☆☆": "0.222%",
        "♛": "0.040%",
    },
    "5 card": {
        "◊": "0.000%",
        "◊◊": "60.000%",
        "◊◊◊": "20.000%",
        "◊◊◊◊": "6.664%",
        "☆": "10.288%",
        "☆☆": "2.000%",
        "☆☆☆": "0.888%",
        "♛": "0.160%",
    },
}

crafting_cost = {
    "◊": 35,
    "◊◊": 70,
    "◊◊◊": 150,
    "◊◊◊◊": 500,
    "☆": 400,
    "☆☆": 1250,
    "☆☆☆": 1500,
    "♛": 2500,
}

FullArt_Rarities = ["☆", "☆☆", "☆☆☆", "Crown Rare"]

packs = [
    "Pikachu pack",
    "Charizard pack",
    "Mewtwo pack",
    "Mew pack",
    "Dialga pack",
    "Palkia pack",
]

def convert_rarity_to_readable(rarity_symbol):
    """Convert rarity symbol to human-readable format."""
    return rarity_mapping.get(rarity_symbol, rarity_symbol)


def map_attack_cost(cost_elements):
    cost_list = []

    for cost in cost_elements:
        cost_symbol = cost.text.strip()

        if len(cost_symbol) > 1:
            for letter in cost_symbol:
                cost_type = type_mapping.get(letter, "Unknown")
                if cost_type == "Unknown":
                    print(f"Warning: unrecognized symbol '{letter}'.")
                cost_list.append(cost_type)
        else:
            cost_type = type_mapping.get(cost_symbol, "Unknown")
            if cost_type == "Unknown":
                print(f"Warning: unrecognized symbol '{cost_symbol}'.")
            cost_list.append(cost_type)

    return cost_list if cost_list else ["No Cost"]


def get_probabilities_by_rarity(rarity):
    probabilities = {}
    for row, rates in rate_by_rarity.items():
        if rarity in rates:
            probabilities[row] = rates[rarity]
    return probabilities


def extract_card_info(soup, set_name=None):
    card_info = {}
    base_id = extract_id(soup)
    # Pad ID to 3 digits with leading zeros
    padded_id = base_id.zfill(3)
    # Remove dashes from set_name but keep the dash separator
    clean_set_name = set_name.replace("-", "") if set_name else ""
    card_info["id"] = f"{clean_set_name}-{padded_id}" if set_name else padded_id
    card_info["name"] = extract_name(soup)
    card_info["hp"] = extract_hp(soup)
    card_info["Element"] = extract_type(soup)
    card_info["type"], card_info["subtype"] = extract_card_and_evolution_type(soup)
    card_info["image"] = extract_image(soup)
    card_info["attacks"] = extract_attacks(soup)
    card_info["ability"] = extract_ability(soup, card_info["type"])
    card_info["weakness"], card_info["retreat"] = extract_weakness_and_retreat(soup)
    card_info["rarity_symbol"], card_info["fullart"] = extract_rarity_and_fullart(soup)
    card_info["rarity"] = convert_rarity_to_readable(card_info["rarity_symbol"])
    card_info["ex"] = extract_ex_status(card_info["name"])
    card_info["set"], card_info["pack"] = extract_set_and_pack_info(soup)
    card_info["alternate_versions"] = extract_alternate_versions(soup)
    card_info["artist"] = extract_artist(soup)
    card_info["probability"] = get_probabilities_by_rarity(card_info["rarity"])
    card_info["crafting_cost"] = extract_crafting_cost(card_info["rarity"])
    return card_info


def extract_id(soup):
    title = soup.find("p", class_="card-text-title")
    return title.find("a")["href"].split("/")[-1]


def extract_name(soup):
    title = soup.find("p", class_="card-text-title")
    return title.find("a").text.strip()

def extract_type(soup):
    title_element = soup.find("p", class_="card-text-title")
    if title_element and title_element.text:
        # Dividir el texto por " - "
        parts = title_element.text.split(" - ")

        # Obtener la lista de nombres de tipo válidos (ej: ["Grass", "Fire", ...])
        known_type_names = type_mapping.values()

        # Buscar en las partes si alguna coincide con un nombre de tipo conocido
        for part in parts:
            cleaned_part = part.strip() # Limpiar espacios
            if cleaned_part in known_type_names:
                return cleaned_part # Devolver el nombre completo encontrado

        # Si ninguna parte coincide con un tipo conocido, devolver "Unknown Type"
        # Puedes descomentar la siguiente línea para depurar qué partes se encontraron
        # print(f"DEBUG: No se encontró un tipo conocido en las partes: {parts}")
        return "Unknown Type"

    # Devolver un valor por defecto si no se encontró el elemento o texto
    return "Unknown Type"

def extract_hp(soup):
    title = soup.find("p", class_="card-text-title")
    return re.sub(r"\D", "", title.text.split(" - ")[-1])


def extract_card_and_evolution_type(soup):
    card_type = re.sub(
        r"\s+", " ", soup.find("p", class_="card-text-type").text.strip()
    )
    
    # Normalize card type
    if "Pokémon" in card_type or "Pokemon" in card_type:
        normalized_type = "Pokemon"
    elif "Trainer" in card_type:
        normalized_type = "Trainer"
    else:
        normalized_type = "Pokemon"  # Default fallback
    
    # Extract evolution type (subtype) - keep original logic
    evolution_info = card_type.split("-")
    evolution_type = evolution_info[1].strip() if len(evolution_info) > 1 else "Basic"
    
    return normalized_type, evolution_type


def extract_image(soup):
    return soup.find("div", class_="card-image").find("img")["src"]


def extract_attacks(soup):
    attack_section = soup.find_all("div", class_="card-text-attack")
    attacks = []
    for attack in attack_section:
        attack_info_section = attack.find("p", class_="card-text-attack-info")
        attack_effect_section = attack.find("p", class_="card-text-attack-effect")

        if attack_info_section:
            cost_elements = attack_info_section.find_all("span", class_="ptcg-symbol")
            attack_cost = map_attack_cost(cost_elements)

            attack_text = attack_info_section.text.strip()
            for cost_element in cost_elements:
                attack_text = attack_text.replace(cost_element.text, "").strip()

            attack_parts = attack_text.rsplit(" ", 1)
            attack_name = (
                attack_parts[0].strip() if len(attack_parts) > 1 else "Unknown"
            )
            attack_damage = attack_parts[1].strip() if len(attack_parts) > 1 else "0"
            attack_effect = (
                attack_effect_section.text.strip()
                if attack_effect_section
                else "No effect"
            )

            attacks.append(
                {
                    "cost": attack_cost,
                    "name": attack_name,
                    "damage": attack_damage,
                    "effect": attack_effect,
                }
            )
    return attacks


def extract_ability(soup, card_type):
    if card_type.startswith("Trainer"):
        ability_section = soup.find("div", class_="card-text-section")
        if ability_section:
            next_section = ability_section.find_next("div", class_="card-text-section")
            return next_section.text.strip() if next_section else "No effect"
        return "No effect"
    else:
        ability_section = soup.find("div", class_="card-text-ability")
        if ability_section:
            ability_name_section = ability_section.find(
                "p", class_="card-text-ability-info"
            )
            ability_effect_section = ability_section.find(
                "p", class_="card-text-ability-effect"
            )
            ability_name = (
                ability_name_section.text.replace("Ability:", "").strip()
                if ability_name_section
                else "Unknown"
            )
            ability_effect = (
                re.sub(r"\[.*?\]", "", ability_effect_section.text).strip()
                if ability_effect_section
                else "No effect"
            )
            return {"name": ability_name, "effect": ability_effect}
        return {"name": "No ability", "effect": "N/A"}


def extract_weakness_and_retreat(soup):
    weakness_retreat_section = soup.find("p", class_="card-text-wrr")
    if weakness_retreat_section:
        text = [
            line.strip() for line in weakness_retreat_section.text.strip().split("\n")
        ]
        weakness = (
            text[0].split(": ")[1].strip()
            if len(text) > 0 and ": " in text[0]
            else "N/A"
        )
        retreat = (
            text[1].split(": ")[1].strip()
            if len(text) > 1 and ": " in text[1]
            else "N/A"
        )
        return weakness, retreat
    return "N/A", "N/A"


def extract_rarity_and_fullart(soup):
    rarity_section = soup.find("table", class_="card-prints-versions")
    if rarity_section:
        current_version = rarity_section.find("tr", class_="current")
        rarity = (
            current_version.find_all("td")[-1].text.strip()
            if current_version
            else "Unknown"
        )
    else:
        rarity = "Unknown"
    fullart = "Yes" if rarity in FullArt_Rarities else "No"
    return rarity, fullart


def extract_ex_status(name):
    return "Yes" if "ex" in name.split(" ") else "No"


def extract_set_and_pack_info(soup):
    set_info = soup.find("div", class_="card-prints-current")
    if set_info:
        set_details = set_info.find("span", class_="text-lg")
        set_number = set_info.find("span").next_sibling
        set_details = set_details.text.strip() if set_details else "Unknown"
        pack_temp = set_info.find_all("span")[-1].text.strip()
        pack_info = " ".join(pack_temp.split("·")[-1].split())
        return set_details, pack_info if pack_info in packs else "Every pack"
    return "Unknown", "Unknown"


def extract_alternate_versions(soup):
    alternate_versions = []
    versions = soup.find_all("tr")
    for version in versions:
        version_name = version.find("a")
        rarity_cell = version.find_all("td")[-1] if version.find_all("td") else None
        version_text = (
            version_name.text.replace("\n", "").strip() if version_name else None
        )
        rarity_text = rarity_cell.text.strip() if rarity_cell else None
        if version_text and rarity_text:
            version_text = " ".join(version_text.split())
            rarity_symbol = rarity_text if rarity_text != "Crown Rare" else "♛"
            alternate_versions.append(
                {
                    "version": version_text,
                    #"rarity_symbol": rarity_symbol,
                    "rarity": convert_rarity_to_readable(rarity_symbol),
                }
            )
    if not alternate_versions:
        alternate_versions.append({
            "version": "Unknown", 
            #"rarity_symbol": "Unknown",
            "rarity": "Unknown"
        })
    return alternate_versions


def extract_artist(soup):
    artist_section = soup.find("div", class_="card-text-section card-text-artist")
    return artist_section.find("a").text.strip() if artist_section else "Unknown"


def extract_crafting_cost(rarity):
    return crafting_cost[rarity] if rarity in crafting_cost else "Unknown"


def scrape_all_sets(start_id=1, end_id=286):
    """
    Main function to scrape all Pokemon card sets and create individual + combined files.
    """
    all_cards = []
    set_card_counts = {}
    init_time = time.time()
    
    # Create output directory if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory '{output_dir}' is ready.")
    
    print("Starting Pokemon card scraping...")
    
    for set_name in sets:
        print(f"Scraping set: {set_name}")
        set_cards = []
        error_tracker = 0
        
        for i in range(start_id, end_id + 1):
            url = f"{BASE_URL}{set_name}/{i}"
            
            # Retry logic for network requests
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = requests.get(url, timeout=10)
                    soup = BeautifulSoup(response.content, "html.parser")
                    card_info = extract_card_info(soup, set_name)
                    set_cards.append(card_info)
                    all_cards.append(card_info)
                    print(f"Card {set_name} - {i} processed.")
                    error_tracker = 0
                    break  # Success, break out of retry loop
                except requests.exceptions.Timeout:
                    retry_count += 1
                    print(f"Timeout for card {set_name}-{i}, retry {retry_count}/{max_retries}")
                    if retry_count >= max_retries:
                        print(f"Max retries reached for card {set_name}-{i}, skipping...")
                        error_tracker += 1
                        break
                    time.sleep(2)  # Wait before retry
                except requests.exceptions.ConnectionError as e:
                    retry_count += 1
                    print(f"Connection error for card {set_name}-{i}, retry {retry_count}/{max_retries}: {e}")
                    if retry_count >= max_retries:
                        print(f"Max retries reached for card {set_name}-{i}, skipping...")
                        error_tracker += 1
                        break
                    time.sleep(5)  # Longer wait for connection errors
                except Exception as e:
                    print(f"Error processing card {set_name}-{i}: {e}")
                    error_tracker += 1
                    break  # Break out of retry loop for non-network errors
                    
            if error_tracker > 4:
                print(f"Finished set {set_name} on card {i}")
                break
        
        # Save individual set file
        set_filename = set_filename_mapping.get(set_name, f"{set_name}_cards.json")
        set_filepath = os.path.join(output_dir, set_filename)
        with open(set_filepath, "w", encoding="utf-8") as file:
            json.dump(set_cards, file, ensure_ascii=False, indent=4)
        
        set_card_counts[set_name] = len(set_cards)
        print(f"Saved {len(set_cards)} cards to {set_filepath}")
    
    # Check if all available sets are being scraped
    all_sets_included = len(sets) == len(available_sets) and set(sets) == set(available_sets)
    
    if all_sets_included:
        # Save combined file only if all sets are included
        combined_filename = "pokemon_cards_all_sets.json"
        combined_filepath = os.path.join(output_dir, combined_filename)
        with open(combined_filepath, "w", encoding="utf-8") as file:
            json.dump(all_cards, file, ensure_ascii=False, indent=4)
        print(f"✅ All sets included - saved combined file: {combined_filepath}")
    else:
        print(f"⚠️  Not all sets included ({len(sets)}/{len(available_sets)}) - skipping combined file")
        print(f"   Current sets: {sets}")
        print(f"   Missing sets: {set(available_sets) - set(sets)}")
    
    end_time = time.time()
    print(f"Completed! Total time: {end_time - init_time:.2f} seconds")
    print(f"Total cards: {len(all_cards)}")
    
    # Print summary of what was saved
    print("\nFiles created:")
    for set_name, count in set_card_counts.items():
        filename = set_filename_mapping.get(set_name, f"{set_name}_cards.json")
        filepath = os.path.join(output_dir, filename)
        print(f"  {filepath}: {count} cards")
    
    if all_sets_included:
        combined_filepath = os.path.join(output_dir, "pokemon_cards_all_sets.json")
        print(f"  {combined_filepath}: {len(all_cards)} cards (COMBINED)")
    else:
        print(f"  Combined file: SKIPPED (not all sets included)")
    
    return all_cards, set_card_counts


# Main execution
if __name__ == "__main__":
    scrape_all_sets()
