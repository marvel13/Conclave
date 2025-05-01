import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time

def scrape_cardinals():
    url = "https://collegeofcardinalsreport.com/cardinals/?_voting_status=voting"
    
    # Send request with headers to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to retrieve data: Status code {response.status_code}")
        return None
    
    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the table with cardinals data
    table = soup.find('table')
    if not table:
        print("Could not find the cardinals table")
        return None
    
    # Extract data from each row
    cardinals_data = []
    rows = table.find('tbody').find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        
        # Extract cardinal name
        name_cell = cells[0]
        name_element = name_cell.find('h6', {'class': 'cardinal-item-cardinal-name'})
        if name_element and name_element.find('a'):
            name = name_element.find('a').text.strip()
            profile_url = name_element.find('a')['href']
        else:
            name = "Name not found"
            profile_url = ""
        
        # Extract image URL if available
        img_element = name_cell.find('img')
        img_url = img_element['src'] if img_element else ""
        
        # Extract voting status
        voting_status_cell = cells[1]
        voting_status = voting_status_cell.text.strip() if voting_status_cell else ""
        
        # Extract created by
        created_by_cell = cells[2]
        created_by = created_by_cell.text.strip() if created_by_cell else ""
        
        # Extract age
        age_cell = cells[3]
        age = age_cell.text.strip() if age_cell else ""
        
        # Extract nation
        nation_cell = cells[4]
        nation = nation_cell.text.strip() if nation_cell else ""
        
        # Extract continent
        continent_cell = cells[5]
        continent = continent_cell.text.strip() if continent_cell else ""
        
        # Extract position
        position_cell = cells[6]
        position = position_cell.text.strip() if position_cell else ""
        
        cardinal_data = {
            'name': name,
            'profile_url': profile_url,
            'image_url': img_url,
            'voting_status': voting_status,
            'created_by': created_by,
            'age': age,
            'nation': nation,
            'continent': continent,
            'position': position
        }
        
        cardinals_data.append(cardinal_data)
    
    return cardinals_data

def main():
    print("Starting to scrape cardinal data...")
    cardinals = scrape_cardinals()
    
    if cardinals:
        print(f"Successfully scraped data for {len(cardinals)} cardinals")
        
        # Save to JSON file
        with open('college_of_cardinals_data.json', 'w', encoding='utf-8') as json_file:
            json.dump(cardinals, json_file, ensure_ascii=False, indent=4)
        
        print("Data saved to 'college_of_cardinals_data.json'")
        
        # Print sample of the data (first 2 entries)
        print("\nSample of scraped data (first 2 entries):")
        print(json.dumps(cardinals[:2], indent=4, ensure_ascii=False))
    else:
        print("Failed to scrape cardinal data")

if __name__ == "__main__":
    main()