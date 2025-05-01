import requests
from bs4 import BeautifulSoup
import json
import groq
import os
import time
from typing import Dict, List, Any

# Extract cardinal data from a URL
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
        
        # Return the data
        return {
            "summary": summary,
            "profile": profile
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the website: {e}")
        return None

# Configure Groq client
groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    print("Error: GROQ_API_KEY environment variable not set")
    exit(1)
    
client = groq.Client(api_key=groq_api_key)

# Analyze cardinal profile data
def analyze_cardinal_profile(cardinal_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze cardinal profile data using Groq's reasoning models to determine 
    theological stance and issue positions on a scale of 1-5.
    
    Args:
        cardinal_data: Dictionary containing the cardinal's profile information
        
    Returns:
        Dictionary with ratings for theological stance and issue positions
    """
    # Extract and truncate the profile text to avoid token limits
    summary = cardinal_data.get("summary", "")
    profile = cardinal_data.get("profile", "")
    
    # Limit the profile text to approximately 1500 characters
    truncated_profile = profile[:1500] + "..." if len(profile) > 1500 else profile
    
    # Create a prompt for the model to analyze
    prompt = f"""
    Analyze this Catholic Cardinal's profile data and rate them on specific dimensions.
    
    CARDINAL SUMMARY:
    {summary}
    
    CARDINAL PROFILE (truncated):
    {truncated_profile}
    
    For each category below, rate on a scale of 1-5 where:
    1 = Strongly conservative/against
    2 = Moderately conservative/against
    3 = Neutral/balanced
    4 = Moderately progressive/supports
    5 = Strongly progressive/supports
    
    THEOLOGICAL STANCE RATINGS:
    - Conservative: [?]
    - Reform-Leaning: [?]
    
    ISSUE POSITION RATINGS:
    - LGBTQ+ Policies: [?]
    - Environmentalism: [?]
    
    Format your response as a JSON object with this structure:
    {{
      "theological_stance": {{
        "conservative": {{ "rating": X, "explanation": "..." }},
        "reform_leaning": {{ "rating": X, "explanation": "..." }}
      }},
      "issue_positions": {{
        "lgbtq_policies": {{ "rating": X, "explanation": "..." }},
        "environmentalism": {{ "rating": X, "explanation": "..." }}
      }}
    }}
    """
    
    # Call Groq's API with the prompt
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # Use a smaller model to reduce token usage
            messages=[
                {"role": "system", "content": "You are an expert analyst of Catholic Church leadership and their positions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Low temperature for consistent reasoning
            max_tokens=1000
        )
        
        # Parse the response
        analysis_text = response.choices[0].message.content
        
        # Extract the JSON part
        try:
            # Find JSON within the text if not pure JSON
            start_idx = analysis_text.find('{')
            end_idx = analysis_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = analysis_text[start_idx:end_idx]
                analysis_result = json.loads(json_str)
            else:
                analysis_result = json.loads(analysis_text)
                
            return analysis_result
            
        except json.JSONDecodeError:
            return {"error": "Failed to parse model response as JSON", "raw_response": analysis_text}
            
    except Exception as e:
        return {"error": f"API call failed: {str(e)}"}

# Convert analysis results to attributes format
def convert_to_attributes(analysis_results):
    attributes = []
    
    # Add theological stance attributes
    if "theological_stance" in analysis_results:
        theological = analysis_results["theological_stance"]
        
        if "conservative" in theological:
            attributes.append({
                "issue_title": "Theological Conservatism",
                "subtitle": "Level of adherence to traditional theological positions",
                "value": str(theological["conservative"]["rating"]),
                "label": get_label_for_rating(theological["conservative"]["rating"]),
                "explanation": theological["conservative"]["explanation"]
            })
            
        if "reform_leaning" in theological:
            attributes.append({
                "issue_title": "Reform-Leaning Theology",
                "subtitle": "Openness to theological reforms and changes",
                "value": str(theological["reform_leaning"]["rating"]),
                "label": get_label_for_rating(theological["reform_leaning"]["rating"]),
                "explanation": theological["reform_leaning"]["explanation"]
            })
    
    # Add issue position attributes
    if "issue_positions" in analysis_results:
        issues = analysis_results["issue_positions"]
        
        if "lgbtq_policies" in issues:
            attributes.append({
                "issue_title": "LGBTQ+ Policies",
                "subtitle": "Positions on LGBTQ+ inclusion and related policies",
                "value": str(issues["lgbtq_policies"]["rating"]),
                "label": get_label_for_rating(issues["lgbtq_policies"]["rating"]),
                "explanation": issues["lgbtq_policies"]["explanation"]
            })
            
        if "environmentalism" in issues:
            attributes.append({
                "issue_title": "Environmentalism",
                "subtitle": "Positions on environmental issues and climate change",
                "value": str(issues["environmentalism"]["rating"]),
                "label": get_label_for_rating(issues["environmentalism"]["rating"]),
                "explanation": issues["environmentalism"]["explanation"]
            })
    
    return attributes

# Helper function to convert rating to label
def get_label_for_rating(rating):
    try:
        rating_num = int(rating)
        labels = {
            1: "Strongly Conservative/Against",
            2: "Moderately Conservative/Against",
            3: "Neutral/Balanced",
            4: "Moderately Progressive/Supports",
            5: "Strongly Progressive/Supports"
        }
        return labels.get(rating_num, "Unknown")
    except (ValueError, TypeError):
        return "Unknown"

# Process a list of cardinals
def process_cardinals(cardinals_data):
    for i, cardinal in enumerate(cardinals_data):
        print(f"\nProcessing {i+1}/{len(cardinals_data)}: {cardinal.get('name', 'Unknown Cardinal')}")
        
        # Skip if no profile URL
        if "profile_url" not in cardinal:
            print("No profile URL found, skipping")
            continue
            
        profile_url = cardinal["profile_url"]
        print(f"Extracting data from {profile_url}...")
        
        # Extract data from the cardinal's profile
        profile_data = extract_cardinal_data(profile_url)
        if not profile_data:
            print("Failed to extract profile data, skipping")
            continue
            
        print("Analyzing cardinal profile with Groq...")
        # Analyze the profile data
        analysis_results = analyze_cardinal_profile(profile_data)
        
        if "error" in analysis_results:
            print(f"Error in analysis: {analysis_results['error']}")
            if "raw_response" in analysis_results:
                print(f"Raw response: {analysis_results['raw_response']}")
            continue
            
        # Convert analysis results to attributes format
        new_attributes = convert_to_attributes(analysis_results)
        
        # Add or merge attributes
        if "attributes" not in cardinal:
            cardinal["attributes"] = []
            
        cardinal["attributes"].extend(new_attributes)
        
        print(f"Successfully added {len(new_attributes)} attributes")
        
        # Add raw analysis for reference
        cardinal["analysis_results"] = analysis_results
        
        # Sleep to avoid hitting API rate limits
        if i < len(cardinals_data) - 1:
            print("Waiting 2 seconds before processing next cardinal...")
            time.sleep(2)
    
    return cardinals_data

# Main function
def main():
    # Load the JSON file containing cardinals data
    input_file = "cardinals_with_attributes.json"
    output_file = "cardinals_with_attributes_attributes.json"
    
    with open(input_file, 'r', encoding='utf-8') as f:
        cardinals_data = json.load(f)
    
    # Process the cardinals data
    enhanced_data = process_cardinals(cardinals_data)
    
    # Save the enhanced data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nEnhanced data saved to {output_file}")

if __name__ == "__main__":
    main()