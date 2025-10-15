#!/usr/bin/env python3
"""
Web Brand Color Scraper
Extracts primary, secondary, and tertiary brand colors from a given URL
Focuses on brand elements like logos, headers, buttons, and key UI components
"""

import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
import argparse
from urllib.parse import urljoin, urlparse
import json
import os
from datetime import datetime
from typing import Dict, Optional

class WebColorScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def is_valid_color(self, color):
        """Check if color is valid and not white/black/gray"""
        if not color:
            return False
            
        # Convert to lowercase for comparison
        color_lower = color.lower()
        
        # Skip common neutral colors
        neutral_colors = {
            'white', 'black', 'gray', 'grey', '#ffffff', '#000000', 
            '#fff', '#000', 'rgb(255,255,255)', 'rgb(0,0,0)',
            'rgba(255,255,255,1)', 'rgba(0,0,0,1)',
            'transparent', 'inherit', 'initial', 'unset'
        }
        
        if color_lower in neutral_colors:
            return False
            
        # Check for grayscale colors (RGB values are close to each other)
        rgb_match = re.search(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', color_lower)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            # If RGB values are close (within 30), it's likely gray
            if abs(r - g) <= 30 and abs(g - b) <= 30 and abs(r - b) <= 30:
                return False
                
        return True
    
    def is_brand_color(self, color):
        """Check if color is likely a brand color (distinctive, not neutral)"""
        if not self.is_valid_color(color):
            return False
            
        # Convert to RGB for analysis
        normalized = self.normalize_color(color)
        if not normalized or not normalized.startswith('#'):
            return False
            
        # Extract RGB values from hex
        hex_color = normalized[1:]  # Remove #
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Check if it's a distinctive color (not too close to grayscale)
            max_val = max(r, g, b)
            min_val = min(r, g, b)
            
            # If the difference between max and min is significant, it's distinctive
            if max_val - min_val > 50:
                return True
                
            # Also check for specific brand color ranges
            # Bright colors, saturated colors, etc.
            if max_val > 200 and min_val < 100:  # High contrast
                return True
                
        return False
    
    def normalize_color(self, color):
        """Normalize color to HEX format"""
        if not color:
            return None
            
        color = color.strip().lower()
        
        # Handle hex colors
        if color.startswith('#'):
            # Convert 3-digit hex to 6-digit
            if len(color) == 4:
                return f"#{color[1]}{color[1]}{color[2]}{color[2]}{color[3]}{color[3]}"
            return color if len(color) == 7 else None
            
        # Handle rgb/rgba colors
        rgb_match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            return f"#{r:02x}{g:02x}{b:02x}"
            
        # Handle named colors (basic mapping)
        named_colors = {
            'red': '#ff0000', 'green': '#008000', 'blue': '#0000ff',
            'yellow': '#ffff00', 'orange': '#ffa500', 'purple': '#800080',
            'pink': '#ffc0cb', 'brown': '#a52a2a', 'cyan': '#00ffff',
            'magenta': '#ff00ff', 'lime': '#00ff00', 'navy': '#000080',
            'maroon': '#800000', 'olive': '#808000', 'teal': '#008080',
            'silver': '#c0c0c0', 'gold': '#ffd700'
        }
        
        return named_colors.get(color)
    
    def extract_colors_from_css(self, css_content, base_url):
        """Extract colors from CSS content with focus on :root and CSS variables"""
        root_colors = []
        css_variable_colors = []
        brand_colors = []
        general_colors = []
        
        # First, look for :root selector specifically
        root_pattern = r':root\s*\{([^}]+)\}'
        root_matches = re.findall(root_pattern, css_content, re.IGNORECASE | re.DOTALL)
        
        for root_content in root_matches:
            # Extract CSS custom properties (variables) from :root
            # Look for color-specific variable names
            css_var_pattern = r'--(?:color|primary|secondary|tertiary|accent|brand|theme|background|text|border)[a-zA-Z0-9-]*\s*:\s*([^;]+)'
            css_vars = re.findall(css_var_pattern, root_content, re.IGNORECASE)
            
            # Also look for any CSS variable that contains color values
            general_css_var_pattern = r'--[a-zA-Z0-9-]+\s*:\s*([^;]+)'
            general_css_vars = re.findall(general_css_var_pattern, root_content, re.IGNORECASE)
            
            # Filter general variables to only include those with color values
            for var_value in general_css_vars:
                if re.search(r'#[a-fA-F0-9]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)|\b(red|green|blue|yellow|orange|purple|pink|brown|cyan|magenta|lime|navy|maroon|olive|teal|silver|gold|white|black|gray|grey)\b', var_value.lower()):
                    css_vars.append(var_value)
            
            for var_value in css_vars:
                # Extract colors from CSS variable values (be more specific)
                color_values = re.findall(r'#[a-fA-F0-9]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)', var_value)
                # Also check for named colors that are likely to be colors
                named_colors = re.findall(r'\b(red|green|blue|yellow|orange|purple|pink|brown|cyan|magenta|lime|navy|maroon|olive|teal|silver|gold|white|black|gray|grey)\b', var_value.lower())
                css_variable_colors.extend(color_values)
                css_variable_colors.extend(named_colors)
            
            # Also extract any direct color properties in :root
            color_patterns = [
                r'color\s*:\s*([^;]+)',
                r'background-color\s*:\s*([^;]+)',
                r'border-color\s*:\s*([^;]+)',
                r'background\s*:\s*([^;]+)',
                r'border\s*:\s*([^;]+)',
            ]
            
            for pattern in color_patterns:
                matches = re.findall(pattern, root_content, re.IGNORECASE)
                for match in matches:
                    color_values = re.findall(r'#[a-fA-F0-9]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)|[a-zA-Z]+', match)
                    root_colors.extend(color_values)
        
        # Brand-specific CSS selectors to prioritize (simplified approach)
        brand_keywords = [
            'logo', 'brand', 'header', 'nav', 'navbar', 'hero', 'cta', 
            'btn-primary', 'primary', 'main', 'title', 'heading'
        ]
        
        # Split CSS into rules (excluding :root which we already processed)
        css_rules = re.split(r'\{|\}', css_content)
        
        for i in range(0, len(css_rules) - 1, 2):
            selector = css_rules[i].strip()
            properties = css_rules[i + 1].strip()
            
            # Skip :root as we already processed it
            if selector.lower().strip() == ':root':
                continue
            
            # Check if this is a brand-related selector
            is_brand_rule = any(keyword in selector.lower() for keyword in brand_keywords)
            
            # Extract colors from properties
            color_patterns = [
                r'color\s*:\s*([^;]+)',
                r'background-color\s*:\s*([^;]+)',
                r'border-color\s*:\s*([^;]+)',
                r'background\s*:\s*([^;]+)',
                r'border\s*:\s*([^;]+)',
            ]
            
            for pattern in color_patterns:
                matches = re.findall(pattern, properties, re.IGNORECASE)
                for match in matches:
                    color_values = re.findall(r'#[a-fA-F0-9]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)|[a-zA-Z]+', match)
                    
                    if is_brand_rule:
                        brand_colors.extend(color_values)
                    else:
                        general_colors.extend(color_values)
        
        return root_colors, css_variable_colors, brand_colors, general_colors
    
    def extract_colors_from_html(self, soup, base_url):
        """Extract colors from HTML elements with brand focus"""
        brand_colors = []
        
        # Priority 1: Logo and brand elements
        logo_selectors = [
            'img[alt*="logo" i]', 'img[class*="logo" i]', 'img[id*="logo" i]',
            '.logo', '#logo', '[class*="brand" i]', '[id*="brand" i]'
        ]
        for selector in logo_selectors:
            for element in soup.select(selector):
                if element.get('style'):
                    style = element['style']
                    color_matches = re.findall(r'#[a-fA-F0-9]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)|[a-zA-Z]+', style)
                    brand_colors.extend([(color, 'logo') for color in color_matches])
        
        # Priority 2: Header and navigation
        header_selectors = ['header', 'nav', '.header', '.navigation', '.navbar', '.nav']
        for selector in header_selectors:
            for element in soup.select(selector):
                if element.get('style'):
                    style = element['style']
                    color_matches = re.findall(r'#[a-fA-F0-9]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)|[a-zA-Z]+', style)
                    brand_colors.extend([(color, 'header') for color in color_matches])
        
        # Priority 3: Primary buttons and CTAs
        button_selectors = [
            'button', '.btn', '.button', '.cta', '.call-to-action',
            'input[type="submit"]', 'input[type="button"]'
        ]
        for selector in button_selectors:
            for element in soup.select(selector):
                if element.get('style'):
                    style = element['style']
                    color_matches = re.findall(r'#[a-fA-F0-9]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)|[a-zA-Z]+', style)
                    brand_colors.extend([(color, 'button') for color in color_matches])
        
        # Priority 4: Main headings
        heading_selectors = ['h1', 'h2', '.main-title', '.hero-title', '.page-title']
        for selector in heading_selectors:
            for element in soup.select(selector):
                if element.get('style'):
                    style = element['style']
                    color_matches = re.findall(r'#[a-fA-F0-9]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)|[a-zA-Z]+', style)
                    brand_colors.extend([(color, 'heading') for color in color_matches])
        
        # Priority 5: Footer and other brand elements
        footer_selectors = ['footer', '.footer', '.site-footer']
        for selector in footer_selectors:
            for element in soup.select(selector):
                if element.get('style'):
                    style = element['style']
                    color_matches = re.findall(r'#[a-fA-F0-9]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)|[a-zA-Z]+', style)
                    brand_colors.extend([(color, 'footer') for color in color_matches])
        
        # Also extract from general inline styles for completeness
        general_colors = []
        for element in soup.find_all(style=True):
            style = element['style']
            color_matches = re.findall(r'#[a-fA-F0-9]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)|[a-zA-Z]+', style)
            general_colors.extend(color_matches)
        
        return brand_colors, general_colors
    
    def fetch_external_css(self, soup, base_url):
        """Fetch external CSS files"""
        root_css_colors = []
        css_var_colors = []
        brand_css_colors = []
        general_css_colors = []
        
        # Find all CSS links
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                css_url = urljoin(base_url, href)
                try:
                    response = self.session.get(css_url, timeout=10)
                    if response.status_code == 200:
                        root_colors, css_vars, brand_colors, general_colors = self.extract_colors_from_css(response.text, base_url)
                        root_css_colors.extend(root_colors)
                        css_var_colors.extend(css_vars)
                        brand_css_colors.extend(brand_colors)
                        general_css_colors.extend(general_colors)
                except:
                    continue
        
        return root_css_colors, css_var_colors, brand_css_colors, general_css_colors
    
    def identify_brand_colors(self, html_brand_colors, root_colors, css_var_colors, css_brand_colors, css_general_colors, inline_css):
        """Identify primary, secondary, and tertiary brand colors"""
        # Priority weights for different brand elements
        priority_weights = {
            'root': 20,        # Highest priority for :root colors
            'css_variables': 18, # CSS custom properties
            'logo': 15,
            'header': 12,
            'button': 10,
            'heading': 8,
            'footer': 6,
            'css_brand': 10,  # Brand-specific CSS
            'css_general': 1  # General CSS
        }
        
        # Combine and score colors
        color_scores = {}
        
        # Score :root colors with highest priority
        for color in root_colors:
            if self.is_valid_color(color):
                normalized = self.normalize_color(color)
                if normalized:
                    weight = priority_weights['root']
                    # Boost score for distinctive brand colors
                    if self.is_brand_color(color):
                        weight *= 2
                    
                    if normalized not in color_scores:
                        color_scores[normalized] = {'score': 0, 'sources': []}
                    color_scores[normalized]['score'] += weight
                    color_scores[normalized]['sources'].append('root')
        
        # Score CSS variable colors with high priority
        for color in css_var_colors:
            if self.is_valid_color(color):
                normalized = self.normalize_color(color)
                if normalized:
                    weight = priority_weights['css_variables']
                    # Boost score for distinctive brand colors
                    if self.is_brand_color(color):
                        weight *= 2
                    
                    if normalized not in color_scores:
                        color_scores[normalized] = {'score': 0, 'sources': []}
                    color_scores[normalized]['score'] += weight
                    color_scores[normalized]['sources'].append('css_variables')
        
        # Score HTML brand colors by element type
        for color, element_type in html_brand_colors:
            if self.is_valid_color(color):
                normalized = self.normalize_color(color)
                if normalized:
                    weight = priority_weights.get(element_type, 1)
                    # Boost score for distinctive brand colors
                    if self.is_brand_color(color):
                        weight *= 2
                    
                    if normalized not in color_scores:
                        color_scores[normalized] = {'score': 0, 'sources': []}
                    color_scores[normalized]['score'] += weight
                    color_scores[normalized]['sources'].append(element_type)
        
        # Score CSS brand colors
        for color in css_brand_colors:
            if self.is_valid_color(color):
                normalized = self.normalize_color(color)
                if normalized:
                    weight = priority_weights['css_brand']
                    # Boost score for distinctive brand colors
                    if self.is_brand_color(color):
                        weight *= 2
                    
                    if normalized not in color_scores:
                        color_scores[normalized] = {'score': 0, 'sources': []}
                    color_scores[normalized]['score'] += weight
                    color_scores[normalized]['sources'].append('css_brand')
        
        # Score general CSS colors with lower weight, but prioritize distinctive colors
        for color in css_general_colors + inline_css:
            if self.is_valid_color(color):
                normalized = self.normalize_color(color)
                if normalized:
                    weight = priority_weights['css_general']
                    # Boost score significantly for distinctive brand colors
                    if self.is_brand_color(color):
                        weight *= 5  # Much higher boost for distinctive colors
                    
                    if normalized not in color_scores:
                        color_scores[normalized] = {'score': 0, 'sources': []}
                    color_scores[normalized]['score'] += weight
                    color_scores[normalized]['sources'].append('css_general')
        
        # Sort by score and return top 3
        sorted_colors = sorted(color_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        return sorted_colors[:3]
    
    def scrape_colors(self, url):
        """Main method to scrape brand colors from URL"""
        try:
            print(f"Scraping brand colors from: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            
            print("Looking for :root CSS rules and CSS variables...")
            
            # Extract brand-focused colors from HTML
            html_brand_colors, html_general_colors = self.extract_colors_from_html(soup, base_url)
            
            # Extract colors from external CSS
            root_css_colors, css_var_colors, css_brand_colors, css_general_colors = self.fetch_external_css(soup, base_url)
            
            # Extract colors from inline CSS
            inline_root_colors = []
            inline_css_var_colors = []
            inline_css_brand = []
            inline_css_general = []
            for style_tag in soup.find_all('style'):
                if style_tag.string:
                    root_colors, css_vars, brand_colors, general_colors = self.extract_colors_from_css(style_tag.string, base_url)
                    inline_root_colors.extend(root_colors)
                    inline_css_var_colors.extend(css_vars)
                    inline_css_brand.extend(brand_colors)
                    inline_css_general.extend(general_colors)
            
            # Combine all CSS colors
            all_root_colors = root_css_colors + inline_root_colors
            all_css_var_colors = css_var_colors + inline_css_var_colors
            all_css_brand = css_brand_colors + inline_css_brand
            all_css_general = css_general_colors + inline_css_general
            
            # Debug output
            print(f"Found {len(all_root_colors)} colors in :root rules")
            print(f"Found {len(all_css_var_colors)} colors in CSS variables")
            if all_root_colors:
                print(f":root colors: {list(set(all_root_colors))[:5]}")  # Show first 5 unique
            if all_css_var_colors:
                print(f"CSS variable colors: {list(set(all_css_var_colors))[:5]}")  # Show first 5 unique
            
            # Identify brand colors using priority scoring
            brand_color_results = self.identify_brand_colors(
                html_brand_colors, all_root_colors, all_css_var_colors, 
                all_css_brand, all_css_general, []
            )
            
            return brand_color_results
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return []
    
    def save_to_json(self, url, colors, output_file="color_results.json"):
        """Save results to JSON file"""
        # Prepare the data structure
        result = {
            "url": url,
            "scraped_at": datetime.now().isoformat(),
            "colors": {
                "primary": None,
                "secondary": None,
                "tertiary": None
            }
        }
        
        # Add colors to result
        if len(colors) >= 1:
            result["colors"]["primary"] = colors[0][0]
        if len(colors) >= 2:
            result["colors"]["secondary"] = colors[1][0]
        if len(colors) >= 3:
            result["colors"]["tertiary"] = colors[2][0]
        
        # Load existing data or create new list
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = []
        else:
            existing_data = []
        
        # Add new result
        existing_data.append(result)
        
        # Save updated data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        return output_file

def main():
    parser = argparse.ArgumentParser(description='Extract primary, secondary, and tertiary brand colors from a website')
    parser.add_argument('url', help='URL to scrape brand colors from')
    parser.add_argument('--output', '-o', default='color_results.json', help='Output JSON file (default: color_results.json)')
    
    args = parser.parse_args()
    
    scraper = WebColorScraper()
    colors = scraper.scrape_colors(args.url)
    
    if colors:
        # Save to JSON
        output_file = scraper.save_to_json(args.url, colors, args.output)
        
        print("\n" + "="*50)
        print("EXTRACTED BRAND COLORS")
        print("="*50)
        
        # Format: url : primary, secondary, tertiary colors
        color_list = []
        if len(colors) >= 1:
            color_list.append(colors[0][0])
        if len(colors) >= 2:
            color_list.append(colors[1][0])
        if len(colors) >= 3:
            color_list.append(colors[2][0])
        
        colors_str = ", ".join(color_list)
        print(f"{args.url} : {colors_str}")
        
        print("="*50)
        print(f"Results saved to: {output_file}")
    else:
        print("No colors found or error occurred.")

async def scrape_institution_colors_async(institution_url: str) -> Dict[str, Optional[str]]:
    """
    Async wrapper for scraping institution colors
    Returns dict with primary, secondary, tertiary colors
    """
    import asyncio

    def _scrape():
        scraper = WebColorScraper()
        colors = scraper.scrape_colors(institution_url)

        result = {
            "primary": None,
            "secondary": None,
            "tertiary": None
        }

        if colors:
            if len(colors) >= 1:
                result["primary"] = colors[0][0]
            if len(colors) >= 2:
                result["secondary"] = colors[1][0]
            if len(colors) >= 3:
                result["tertiary"] = colors[2][0]

        return result

    # Run in thread pool to avoid blocking
    loop = asyncio.get_running_loop()
    result: Dict[str, Optional[str]] = await loop.run_in_executor(None, _scrape)  # type: ignore
    return result

if __name__ == "__main__":
    main()
