import requests
from bs4 import BeautifulSoup

def extract_cardinal_data(url):
    # Send a request to the website
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract the summary
        summary_div = soup.find('div', class_='cardinals-summary-block')
        summary = summary_div.get_text(strip=True) if summary_div else "Summary not found"
        
        # Extract the full profile description
        profile_div = soup.find('div', class_='dynamic-entry-content')
        profile = profile_div.get_text(strip=True) if profile_div else "Profile not found"
        
        # Return the data if needed elsewhere
        return {
            "summary": summary,
            "profile": profile
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the website: {e}")
        return None

# URL of the Cardinal's page
url = "https://collegeofcardinalsreport.com/cardinals/fridolin-ambongo-besungu/"

# Extract the data
cardinal_data = extract_cardinal_data(url)