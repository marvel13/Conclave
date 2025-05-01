import asyncio
import json
import re
import time

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


async def check_and_extract_where_he_stands(profile_data):
    """
    Check if a cardinal profile has a 'where he stands' section and extract the data

    Args:
        profile_data: Dictionary containing cardinal profile information

    Returns:
        Updated profile_data with attributes if applicable
    """
    url = profile_data["profile_url"]
    cardinal_name = profile_data["name"]

    print(f"\nProcessing {cardinal_name} at {url}")

    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()

            # Navigate to the URL
            await page.goto(url, wait_until="domcontentloaded")

            # Check if the page has a 'where he stands' section
            has_where_he_stands = await page.locator("#wherehestands").count() > 0

            if not has_where_he_stands:
                print(f"No 'where he stands' section found for {cardinal_name}")
                await browser.close()
                return profile_data

            print(
                f"Found 'where he stands' section for {cardinal_name}, extracting data..."
            )

            # Keep clicking "load more issues" button until it's no longer visible or available
            load_more_selector = "a.accrodin-btn.button-secondary"
            more_content_available = True
            click_count = 0

            while more_content_available:
                try:
                    # Check if button exists and is visible
                    is_visible = await page.locator(load_more_selector).is_visible()
                    if not is_visible:
                        more_content_available = False
                        continue

                    # Click the button
                    await page.locator(load_more_selector).click()
                    click_count += 1
                    print(f"Clicked 'load more issues' button ({click_count} times)")

                    # Wait for network to be idle (content to load)
                    await page.wait_for_load_state("networkidle")

                    # Add a small delay to ensure content is fully loaded
                    await asyncio.sleep(1)

                except Exception as e:
                    print(
                        f"No more 'load more issues' buttons found or error occurred: {e}"
                    )
                    more_content_available = False

            # Get the full page content after all dynamic content is loaded
            content = await page.content()

            # Close browser
            await browser.close()

            # Extract issues using BeautifulSoup
            attributes = extract_issues_from_html(content)

            # Add attributes to profile data
            if attributes:
                profile_data["attributes"] = attributes
                print(f"Added {len(attributes)} attributes to {cardinal_name}")
            else:
                print(
                    f"No attributes extracted for {cardinal_name} despite having 'where he stands' section"
                )

            return profile_data

    except Exception as e:
        print(f"Error processing {cardinal_name}: {e}")
        return profile_data


def extract_issues_from_html(html_content):
    """
    Extract issues from HTML content

    Args:
        html_content: HTML content of the page

    Returns:
        List of issues with title, value, and label
    """
    soup = BeautifulSoup(html_content, "html.parser")
    attributes = []

    # Find the div with id="wherehestands"
    where_he_stands = soup.find("div", id="wherehestands")

    if not where_he_stands:
        return attributes

    # Find all accordion items
    accordion_items = where_he_stands.find_all("div", class_="accordion-heading")

    # Process each accordion item
    for item in accordion_items:
        # Extract issue title
        issue_title_element = item.find("h3")
        if issue_title_element:
            # Get just the span containing the main title text, if it exists
            title_span = issue_title_element.find("span", class_="accordion-title")
            if title_span:
                issue_title = title_span.get_text(strip=True)
            else:
                # Fallback to text cleaning method
                issue_title = (
                    issue_title_element.get_text(strip=True)
                    .split("See evidence")[0]
                    .strip()
                )
        else:
            issue_title = "Unknown Issue"

        # Try to find the associated details section
        heading_parent = item.parent
        details_section = heading_parent.find("div", class_="accordion-details")

        if details_section:
            # Find content sections within the details
            content_sections = details_section.find_all(
                "div", class_="accordion-content"
            )

            for content in content_sections:
                # Extract the sub-title
                title_elem = content.find("p", class_="accordion-sub-title")
                subtitle = title_elem.text.strip() if title_elem else "No title found"

                # Extract the value and label from hidden div with a="b"
                hidden_div = content.find("div", attrs={"a": "b"})
                value = "Unknown"
                label = "Unknown"

                if hidden_div:
                    array_text = hidden_div.text.strip()
                    # Extract value using regex
                    value_match = re.search(r"\[value\] =>\s*(\d+)", array_text)
                    value = value_match.group(1) if value_match else "Unknown"

                    # Extract label using regex
                    label_match = re.search(r"\[label\] =>\s*([^\)]+)", array_text)
                    label = label_match.group(1).strip() if label_match else "Unknown"

                attributes.append(
                    {
                        "issue_title": issue_title,
                        "subtitle": subtitle,
                        "value": value,
                        "label": label,
                    }
                )

    return attributes


async def process_all_cardinals(json_data):
    """
    Process all cardinals in the JSON data

    Args:
        json_data: List of cardinal profile data

    Returns:
        Updated JSON data with attributes
    """
    updated_data = []

    # For each cardinal profile
    for profile in json_data:
        # Process the profile
        updated_profile = await check_and_extract_where_he_stands(profile)
        updated_data.append(updated_profile)

        # Add a short delay between profiles to avoid rate limiting
        await asyncio.sleep(1)

    return updated_data


async def main():
    # Load the JSON data
    with open("college_of_cardinals_data.json", "r") as f:
        cardinals_data = json.load(f)

    # If the JSON data is not a list, make it a list
    if not isinstance(cardinals_data, list):
        cardinals_data = [cardinals_data]

    # For testing with a small subset
    # cardinals_data = cardinals_data[:3]  # Uncomment to test with first 3 entries

    # Process all cardinals
    updated_data = await process_all_cardinals(cardinals_data)

    # Save the updated data
    with open("cardinals_with_attributes.json", "w") as f:
        json.dump(updated_data, f, indent=2)

    print(f"\nProcessed {len(updated_data)} cardinal profiles")
    print("Results saved to cardinals_with_attributes.json")


if __name__ == "__main__":
    asyncio.run(main())
