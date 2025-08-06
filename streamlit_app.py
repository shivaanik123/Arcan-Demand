import streamlit as st
import pdfplumber
import fitz  # PyMuPDF
import io
import zipfile
from datetime import datetime
import tempfile
import os
import re
import base64

# Template definitions with exact file paths
TEMPLATES = {
    "Florida Template": {
        "file_path": "templates/Florida Template.pdf",
        "description": "Florida demand letter template with signature and date fields",
        "placeholders": ["SIGN HERE", "DATE HERE", "<<SIGNATURE>>", "<<DATE>>"],
        "include_date": True
    },
    "Georgia Template": {
        "file_path": "templates/Georgia Template.pdf", 
        "description": "Georgia demand letter template with signature fields",
        "placeholders": ["SIGN HERE", "<<SIGNATURE>>"],
        "include_date": False
    },
    "Alabama Template": {
        "file_path": "templates/Alabama Template.pdf",
        "description": "Alabama demand letter template with signature and service fields", 
        "placeholders": ["SIGN HERE", "<<SIGNATURE>>", "SERVICE METHOD"],
        "include_date": True
    }
}

def analyze_pdf_structure(pdf_path_or_bytes):
    """Analyze PDF structure to extract key features for matching"""
    try:
        # Handle both file paths and bytes
        if isinstance(pdf_path_or_bytes, str):
            # It's a file path
            with pdfplumber.open(pdf_path_or_bytes) as pdf:
                return _extract_pdf_features(pdf)
        else:
            # It's bytes - handle BytesIO properly without consuming the stream
            if isinstance(pdf_path_or_bytes, io.BytesIO):
                # Create a copy of the BytesIO to avoid consuming the original
                pdf_bytes = pdf_path_or_bytes.getvalue()
            else:
                # It's raw bytes
                pdf_bytes = pdf_path_or_bytes
            
            # Create a fresh BytesIO and ensure .seek(0) before reading
            file_buffer = io.BytesIO(pdf_bytes)
            file_buffer.seek(0)  # 🔑 this is crucial
            with pdfplumber.open(file_buffer) as pdf:
                return _extract_pdf_features(pdf)
    except Exception as e:
        st.error(f"Error analyzing PDF structure: {str(e)}")
        return None

def _extract_pdf_features(pdf):
    """Extract key features from PDF for template matching"""
    features = {
        'page_count': len(pdf.pages),
        'text_content': [],
        'key_phrases': [],
        'word_count': 0,
        'has_demand_letter_keywords': False,
        'state_indicators': []
    }
    
    # Keywords that indicate this is a demand letter
    demand_keywords = [
        'demand', 'notice', 'letter', 'payment', 'due', 'balance', 'amount',
        'outstanding', 'past due', 'collection', 'legal', 'action', 'attorney',
        'law firm', 'settlement', 'resolution', 'compliance', 'breach', 'contract'
    ]
    
    # State-specific keywords
    florida_keywords = ['florida', 'fl', 'miami', 'orlando', 'tampa', 'jacksonville', 'fort lauderdale']
    georgia_keywords = ['georgia', 'ga', 'atlanta', 'savannah', 'augusta', 'columbus', 'macon']
    alabama_keywords = ['alabama', 'al', 'birmingham', 'montgomery', 'mobile', 'huntsville', 'hoover', 'tuscaloosa']
    
    all_text = ""
    
    for page_num, page in enumerate(pdf.pages):
        try:
            text = page.extract_text()
            if text:
                all_text += text.lower()
                features['text_content'].append(text)
                features['word_count'] += len(text.split())
                
                # Check for demand letter keywords
                for keyword in demand_keywords:
                    if keyword in text.lower():
                        features['has_demand_letter_keywords'] = True
                        break
                
                # Check for state indicators
                for keyword in florida_keywords:
                    if keyword in text.lower():
                        features['state_indicators'].append('florida')
                        break
                
                for keyword in georgia_keywords:
                    if keyword in text.lower():
                        features['state_indicators'].append('georgia')
                        break
                
                for keyword in alabama_keywords:
                    if keyword in text.lower():
                        features['state_indicators'].append('alabama')
                        break
                
        except Exception as e:
            st.warning(f"Error processing page {page_num}: {str(e)}")
            continue
    
    # Extract key phrases (longer text segments that might indicate document type)
    words = all_text.split()
    for i in range(len(words) - 2):
        phrase = ' '.join(words[i:i+3])
        if any(keyword in phrase for keyword in demand_keywords):
            features['key_phrases'].append(phrase)
    
    return features

def match_pdf_to_template(uploaded_pdf_features):
    """Match uploaded PDF features to the best template"""
    try:
        # Analyze template features
        template_features = {}
        
        for template_name, template_info in TEMPLATES.items():
            template_path = template_info['file_path']
            if os.path.exists(template_path):
                template_features[template_name] = analyze_pdf_structure(template_path)
        
        # Scoring system for matching
        best_match = None
        best_score = 0
        
        for template_name, template_feat in template_features.items():
            if template_feat is None:
                continue
                
            score = 0
            
            # State matching (highest weight)
            if 'florida' in uploaded_pdf_features['state_indicators'] and 'florida' in template_name.lower():
                score += 50
            elif 'georgia' in uploaded_pdf_features['state_indicators'] and 'georgia' in template_name.lower():
                score += 50
            
            # Document type matching
            if uploaded_pdf_features['has_demand_letter_keywords'] and template_name.lower().find('template') != -1:
                score += 30
            
            # Page count similarity
            page_diff = abs(uploaded_pdf_features['page_count'] - template_feat['page_count'])
            if page_diff == 0:
                score += 20
            elif page_diff == 1:
                score += 10
            elif page_diff <= 2:
                score += 5
            
            # Word count similarity
            word_diff = abs(uploaded_pdf_features['word_count'] - template_feat['word_count'])
            if word_diff < 100:
                score += 15
            elif word_diff < 500:
                score += 10
            elif word_diff < 1000:
                score += 5
            
            # Key phrase matching
            uploaded_phrases = set(uploaded_pdf_features['key_phrases'])
            template_phrases = set(template_feat['key_phrases'])
            common_phrases = uploaded_phrases.intersection(template_phrases)
            score += len(common_phrases) * 5
            
            if score > best_score:
                best_score = score
                best_match = template_name
        
        return best_match, best_score
        
    except Exception as e:
        st.error(f"Error matching PDF to template: {str(e)}")
        return None, 0

def find_signature_placeholders_simple(pdf_path_or_bytes, template_name=None):
    """Find signature placeholders with simple, robust approach and template-specific positioning"""
    try:
        # Handle both file paths and bytes
        if isinstance(pdf_path_or_bytes, io.BytesIO):
            pdf_path_or_bytes.seek(0)
            pdf_bytes = pdf_path_or_bytes.getvalue()
        elif isinstance(pdf_path_or_bytes, bytes):
            pdf_bytes = pdf_path_or_bytes
        elif isinstance(pdf_path_or_bytes, str) and os.path.exists(pdf_path_or_bytes):
            with open(pdf_path_or_bytes, 'rb') as f:
                pdf_bytes = f.read()
        
        # Create a fresh BytesIO and ensure .seek(0) before reading
        file_buffer = io.BytesIO(pdf_bytes)
        file_buffer.seek(0)  # 🔑 this is crucial
        with pdfplumber.open(file_buffer) as pdf:
            return _extract_placeholders(pdf, template_name)
    except Exception as e:
        st.error(f"Error finding placeholders: {str(e)}")
        return []

def _extract_placeholders(pdf, template_name=None):
    """Extract placeholders from PDF object with template-specific positioning"""
    print(f"🔍 Template detection: Processing with template_name='{template_name}'")
    print(f"📄 Total pages in PDF: {len(pdf.pages)}")
    signature_locations = []
    
    for page_num, page in enumerate(pdf.pages):
        # Track detected parentheses to avoid duplicates
        detected_parentheses = set()
        try:
            words = page.extract_words()
            
            # Debug: Print all words to understand page structure
            print(f"📄 Page {page_num + 1} - All words with y-coordinates:")
            for word_data in words:
                if len(word_data['text'].strip()) > 0:  # Only show non-empty words
                    print(f"  '{word_data['text']}' at y: {word_data['top']}")
            print("---")
            
            for word_data in words:
                word_text = word_data['text'].strip()
                
                # Look for signature placeholders - "Signature", "SIGN", and "SIGN HERE" (only top section)
                if (word_text.lower() == "signature" or word_text.lower() == "sign" or 
                    word_text.lower() == "sign here"):
                    # Only add signatures that are in the top section (y < 350) for "Signature of Agent for Landlord"
                    # Based on debug output: "Signature of Agent for Landlord" is at y: 329.24, "SIGN HERE" is at y: 311.58
                    if word_data['top'] < 345:
                        signature_locations.append({
                            'page': page_num,
                            'text': word_text,
                            'x': word_data['x0'],
                            'y': word_data['top'],
                            'width': word_data['x1'] - word_data['x0'],
                            'height': word_data['bottom'] - word_data['top'],
                            'font_size': word_data.get('size', 12),
                            'placeholder_type': 'signature'
                        })
                
                # Check for LONG underscore lines (signature lines) - template-specific positioning
                # Use length > 20 to avoid catching date underscores (which are shorter)
                if len(word_text) > 20 and all(c in '_' for c in word_text):
                    print(f"🔍 Found underscore line: '{word_text}' at y: {word_data['top']}")
                    should_add = False
                    
                    if template_name == "Georgia Template":
                        # Georgia Template: Add signatures for both underscore lines
                        # Based on debug: first at y: 480.3, second at y: 675.8
                        if word_data['top'] < 500 or word_data['top'] > 600:  # Include first (480.3) and second (675.8)
                            should_add = True
                            print(f"✅ Georgia Template: Adding signature at y: {word_data['top']}")
                        else:
                            print(f"⏭️ Georgia Template: Skipping underscore at y: {word_data['top']} (not in target range)")
                    elif template_name == "Alabama Template":
                        # Alabama Template: Only sign first TWO signature lines (where SIGN HERE would be)
                        # Based on analysis: y: 513.079 (first), y: 610.213 (second) - skip y: 688.768 (third)
                        if (500 <= word_data['top'] <= 520 or    # First signature around 513
                            600 <= word_data['top'] <= 620):     # Second signature around 610
                            should_add = True
                            print(f"✅ Alabama Template: Adding signature at y: {word_data['top']}")
                        else:
                            print(f"⏭️ Alabama Template: Skipping underscore at y: {word_data['top']} (only signing first two lines)")
                    else:
                        # Florida Template: Only add signature lines that are in the bottom section (y > 500)
                        if word_data['top'] > 500:
                            should_add = True
                            print(f"✅ Florida Template: Adding signature at y: {word_data['top']}")
                        else:
                            print(f"⏭️ Florida Template: Skipping underscore at y: {word_data['top']} (not in target range)")
                    
                    if should_add:
                        signature_locations.append({
                            'page': page_num,
                            'text': word_text,
                            'x': word_data['x0'],
                            'y': word_data['top'],
                            'width': word_data['x1'] - word_data['x0'],
                            'height': word_data['bottom'] - word_data['top'],
                            'font_size': word_data.get('size', 12),
                            'placeholder_type': 'signature'
                        })
                
                # FLEXIBLE underscore detection - find underscores within text
                # Look for patterns like "____day", "of____", "20____", etc.
                if '___' in word_text and len([c for c in word_text if c == '_']) >= 3:
                    print(f"🔍 CHECKING underscore '{word_text}' at y: {word_data['top']}")
                    
                    # Quick check: skip signature underscores (long lines near signature words)
                    nearby_words = []
                    for other_word in words:
                        if (abs(other_word['top'] - word_data['top']) < 20 and  # Same line
                            abs(other_word['x0'] - word_data['x0']) < 150):     # Close by
                            nearby_words.append(other_word['text'].lower())
                    
                    nearby_text = ' '.join(nearby_words)
                    print(f"🔍 Nearby text: '{nearby_text}'")
                    
                    # Skip signature underscores (long lines near signature-related words)
                    if (len(word_text) > 15 and 
                        any(sig_word in nearby_text for sig_word in ['signature', 'agent', 'landlord', 'shivaani'])):
                        print(f"⏭️ Skipped signature underscore at y: {word_data['top']}")
                    else:
                        # Add as date underscore
                        signature_locations.append({
                            'page': page_num,
                            'text': word_text,
                            'x': word_data['x0'],
                            'y': word_data['top'],
                            'width': word_data['x1'] - word_data['x0'],
                            'height': word_data['bottom'] - word_data['top'],
                            'font_size': word_data.get('size', 12),
                            'placeholder_type': 'underscore_blank'
                        })
                        print(f"✅ Found DATE underscore at y: {word_data['top']}")



                
                # ENHANCED PARENTHESES DETECTION - Focus on "Proof of Service" pattern
                # Handle both complete patterns and individual opening parentheses
                if word_text.strip() in ['( )', '()', '(.)', '(']:
                    # For individual '(', also check if there's a matching ')' on the same line
                    is_valid_checkbox = True
                    if word_text.strip() == '(':
                        # Look for matching ')' on the same line
                        has_matching_paren = False
                        for other_word in words:
                            if (other_word['text'].strip() == ')' and
                                abs(other_word['top'] - word_data['top']) < 10 and  # Same line
                                other_word['x0'] > word_data['x0']):  # To the right
                                has_matching_paren = True
                                break
                        is_valid_checkbox = has_matching_paren
                    
                    if not is_valid_checkbox:
                        continue
                        
                    # Check if we've already detected this parentheses (avoid duplicates)
                    parentheses_key = f"{word_data['x0']}_{word_data['top']}"
                    if parentheses_key in detected_parentheses:
                        print(f"⏭️ Skipping duplicate parentheses: '{word_text}' at ({word_data['x0']}, {word_data['top']})")
                        continue
                    
                    print(f"🔍 Found parentheses pattern: '{word_text}' at ({word_data['x0']}, {word_data['top']})")
                    
                    # Look for service method text nearby
                    nearby_text = ""
                    service_type = "unknown"
                    
                    # Search for service method text ONLY to the right of the parenthesis (very focused)
                    for other_word in words:
                        if (abs(other_word['top'] - word_data['top']) < 10 and  # Same line
                            other_word['x0'] > word_data['x0'] and  # Only words to the right
                            other_word['x0'] - word_data['x0'] < 200):  # Within 200px to the right
                            nearby_text += other_word['text'] + " "
                    
                    # Check for service method patterns (very specific - only look at immediate text)
                    nearby_lower = nearby_text.lower()
                    
                    # Check for exact patterns - look at the first few words after the parenthesis
                    if 'by personally delivering' in nearby_lower:
                        service_type = "personally_delivering"
                    elif 'by posting' in nearby_lower:
                        service_type = "posting"
                    
                    print(f"🔍 Service type for '{word_text}': {service_type} (nearby: '{nearby_text.strip()}')")
                    
                    # Mark this parentheses as detected
                    detected_parentheses.add(parentheses_key)
                    
                    # Add the parentheses checkbox (even if type is unknown - we'll handle it in checking logic)
                    signature_locations.append({
                        'page': page_num,
                        'text': word_text,
                        'x': word_data['x0'],
                        'y': word_data['top'],
                        'width': word_data['x1'] - word_data['x0'],
                        'height': word_data['bottom'] - word_data['top'],
                        'font_size': word_data.get('size', 12),
                        'placeholder_type': 'existing_checkbox',
                        'checkbox_type': service_type,
                        'nearby_text': nearby_text.strip()
                    })
                # Handle individual periods that might be part of (.) pattern
                elif word_text.strip() == '.':
                    # Only add if it's likely part of a checkbox pattern (check for nearby parentheses)
                    has_nearby_parentheses = False
                    for other_word in words:
                        if (other_word['text'].strip() in ['(', ')'] and
                            abs(other_word['x0'] - word_data['x0']) < 30 and 
                            abs(other_word['top'] - word_data['top']) < 20):
                            has_nearby_parentheses = True
                            break
                    
                    if has_nearby_parentheses:
                        # Check if we've already detected this period (avoid duplicates)
                        period_key = f"{word_data['x0']}_{word_data['top']}"
                        if period_key in detected_parentheses:
                            print(f"⏭️ Skipping duplicate period: '{word_text}' at ({word_data['x0']}, {word_data['top']})")
                            continue
                        
                        print(f"🔍 Found period with nearby parentheses: '{word_text}' at ({word_data['x0']}, {word_data['top']})")
                        
                        # Look for service method text nearby
                        nearby_text = ""
                        service_type = "unknown"
                        
                        for other_word in words:
                            if (abs(other_word['top'] - word_data['top']) < 100 and 
                                abs(other_word['x0'] - word_data['x0']) < 800):
                                nearby_text += other_word['text'] + " "
                        
                        nearby_lower = nearby_text.lower()
                        if any(phrase in nearby_lower for phrase in [
                            'personally delivering same upon said tenant',
                            'personally delivering',
                            'personally delivered'
                        ]):
                            service_type = "personally_delivering"
                        elif any(phrase in nearby_lower for phrase in [
                            'posting same at the above described premises',
                            'posting same at the above described',
                            'posting same at',
                            'posting'
                        ]):
                            service_type = "posting"
                        
                        print(f"🔍 Period service type: {service_type} (nearby: '{nearby_text.strip()}')")
                        
                        # Mark this period as detected
                        detected_parentheses.add(period_key)
                        
                        signature_locations.append({
                            'page': page_num,
                            'text': word_text,
                            'x': word_data['x0'],
                            'y': word_data['top'],
                            'width': word_data['x1'] - word_data['x0'],
                            'height': word_data['bottom'] - word_data['top'],
                            'font_size': word_data.get('size', 12),
                            'placeholder_type': 'existing_checkbox',
                            'checkbox_type': service_type,
                            'nearby_text': nearby_text.strip()
                        })
                

        except Exception as e:
            st.warning(f"Error processing page {page_num}: {str(e)}")
            continue
    
    # Debug: Show final signature locations summary
    print(f"\n📊 FINAL SUMMARY: Found {len(signature_locations)} signature locations:")
    checkbox_count = 0
    for i, loc in enumerate(signature_locations):
        loc_type = loc['placeholder_type']
        if loc_type == 'existing_checkbox':
            checkbox_count += 1
            print(f"  {i+1}. Type: {loc_type}, Y: {loc['y']}, Text: '{loc['text']}', Checkbox Type: {loc.get('checkbox_type', 'unknown')}")
        else:
            print(f"  {i+1}. Type: {loc_type}, Y: {loc['y']}, Text: '{loc['text']}'")
    print(f"📋 Checkboxes found: {checkbox_count}")
    print("---\n")
    
    # Post-process underscore_blank placeholders to assign them to day, month, year, signature based on template
    underscore_blanks = [loc for loc in signature_locations if loc.get('placeholder_type') == 'underscore_blank']
    if underscore_blanks:
        # Sort by Y position (top to bottom) to determine order
        underscore_blanks.sort(key=lambda x: x['y'])
        print(f"🔄 Processing {len(underscore_blanks)} underscore blanks for template '{template_name}'...")
        
        # Template-specific underscore patterns
        if template_name and 'florida' in template_name.lower():
            # Florida: day, month, year, signature (repeating every 4)
            type_pattern = ['day_blank', 'month_blank', 'year_blank', 'signature']
            print(f"📋 Florida pattern: day, month, year, signature (repeating)")
        elif template_name and 'alabama' in template_name.lower():
            # Alabama: signature, day, month, year, signature (5 total, rest blank)
            type_pattern = ['signature', 'day_blank', 'month_blank', 'year_blank', 'signature']
            print(f"📋 Alabama pattern: signature, day, month, year, signature")
        else:
            # Georgia (default): first 3 are day, month, year
            type_pattern = ['day_blank', 'month_blank', 'year_blank']
            print(f"📋 Georgia/default pattern: day, month, year")
        
        print(f"📋 Found {len(underscore_blanks)} underscore blanks to assign:")
        for i, blank in enumerate(underscore_blanks):
            print(f"  {i+1}. Underscore at y:{blank['y']}, x:{blank['x']}")
            
        # Assign types based on content analysis, not just position
        for i, blank in enumerate(underscore_blanks):
            if template_name and 'florida' in template_name.lower():
                # Florida: Smart assignment based on text content
                text = blank['text'].lower()
                if 'day' in text:
                    assigned_type = 'day_blank'
                elif 'of' in text and ',' in text:  # "of___________,"
                    assigned_type = 'month_blank'
                elif ',' in text and len(text) > 10:  # Month fields often have commas: "__________________, "
                    assigned_type = 'month_blank'
                elif text.startswith('20'):  # "20____"
                    assigned_type = 'year_blank'
                elif len(text) > 25:  # Very long underscore = signature (raised threshold)
                    assigned_type = 'signature'
                else:
                    # For remaining short underscores, cycle through day/month/year
                    remaining_pattern = ['day_blank', 'month_blank', 'year_blank']
                    assigned_type = remaining_pattern[i % 3]
            elif template_name and 'alabama' in template_name.lower():
                # Alabama: first 5 follow pattern, rest are blank
                if i < len(type_pattern):
                    assigned_type = type_pattern[i]
                else:
                    print(f"⏭️ Alabama: Skipping extra underscore #{i+1} (leaving blank)")
                    continue
            else:
                # Georgia: first 3 follow pattern, rest are blank
                if i < len(type_pattern):
                    assigned_type = type_pattern[i]
                else:
                    print(f"⏭️ Georgia: Skipping extra underscore #{i+1} (leaving blank)")
                    continue
            
            # Find this blank in signature_locations and update its type
            assignment_made = False
            for loc in signature_locations:
                if (loc.get('placeholder_type') == 'underscore_blank' and 
                    loc['x'] == blank['x'] and loc['y'] == blank['y']):
                    loc['placeholder_type'] = assigned_type
                    print(f"✅ Assigned underscore #{i+1} at y:{blank['y']} as {assigned_type}")
                    assignment_made = True
                    break
            if not assignment_made:
                print(f"❌ Failed to assign underscore #{i+1} at y:{blank['y']} as {assigned_type}")
    
    return signature_locations



def extract_unit_info(pdf_path_or_bytes, template_name):
    """Extract unit number from PDF for file naming"""
    return extract_unit_info_from_page(pdf_path_or_bytes, template_name, 0)

def extract_unit_info_from_page(pdf_path_or_bytes, template_name, page_number=0):
    """Extract unit number from a specific page of PDF for file naming"""
    try:
        # Handle both file paths and bytes
        if isinstance(pdf_path_or_bytes, io.BytesIO):
            pdf_path_or_bytes.seek(0)
            pdf_bytes = pdf_path_or_bytes.getvalue()
        elif isinstance(pdf_path_or_bytes, bytes):
            pdf_bytes = pdf_path_or_bytes
        elif isinstance(pdf_path_or_bytes, str) and os.path.exists(pdf_path_or_bytes):
            with open(pdf_path_or_bytes, 'rb') as f:
                pdf_bytes = f.read()
        else:
            return "0000"
        
        # Create a fresh BytesIO and analyze
        file_buffer = io.BytesIO(pdf_bytes)
        file_buffer.seek(0)
        
        with pdfplumber.open(file_buffer) as pdf:
            # Use the specified page number, default to page 0 if out of range
            if page_number >= len(pdf.pages):
                page_number = 0
            
            page = pdf.pages[page_number]
            words = page.extract_words()
            
            unit_number = "0000"
            
            if template_name == "Florida Template":
                # Extract unit number from address
                all_units = []  # Collect all potential unit numbers
                
                for i, word_data in enumerate(words):
                    word_text = word_data['text'].strip()
                    
                    # Look for 4-digit numbers that could be unit numbers
                    if (len(word_text) == 4 and word_text.isdigit()):
                        all_units.append((word_text, word_data['top']))
                
                # Use the second 4-digit number found (skip 8890 which is the address)
                if len(all_units) >= 2:
                    unit_number = all_units[1][0]  # Take the second 4-digit number (actual unit)
                elif len(all_units) == 1:
                    unit_number = all_units[0][0]  # Fallback to first if only one found
                        
            elif template_name == "Georgia Template":
                # Extract apartment number
                all_units = []  # Collect all potential unit numbers
                
                for i, word_data in enumerate(words):
                    word_text = word_data['text'].strip()
                    
                    # Look for apartment number pattern
                    if word_text.lower() == 'apartment' and i + 2 < len(words):
                        if words[i + 1]['text'].strip().lower() == 'number:':
                            unit_number = words[i + 2]['text'].strip()
                            break
                    # Collect all 4-digit numbers as backup
                    elif len(word_text) == 4 and word_text.isdigit():
                        all_units.append((word_text, word_data['top']))
                
                # If no "Apartment Number:" pattern found, use second 4-digit number (skip address)
                if unit_number == "0000" and all_units:
                    if len(all_units) >= 2:
                        unit_number = all_units[1][0]  # Take the second 4-digit number (actual unit)
                    else:
                        unit_number = all_units[0][0]  # Fallback to first if only one found
                            
            elif template_name == "Alabama Template":
                # Extract unit from address patterns
                all_units = []  # Collect all potential unit numbers
                
                for i, word_data in enumerate(words):
                    word_text = word_data['text'].strip()
                    
                    # Pattern 2: Look for "Apt #" followed by unit number (highest priority)
                    if word_text.lower() == 'apt' and i + 2 < len(words):
                        if words[i + 1]['text'].strip() == '#':
                            potential_unit = words[i + 2]['text'].strip()
                            if potential_unit.isdigit():
                                unit_number = potential_unit
                                print(f"✅ Found Apt # pattern: {unit_number}")
                                break
                    
                    # Pattern 1: Collect all 4-digit numbers in tenant address area
                    elif len(word_text) == 4 and word_text.isdigit():
                        all_units.append((word_text, word_data['top']))
                
                # If no "Apt #" pattern found, use second 4-digit number (skip address)
                if unit_number == "0000" and all_units:
                    if len(all_units) >= 2:
                        unit_number = all_units[1][0]  # Take the second 4-digit number (actual unit)
                        print(f"✅ Found second 4-digit number: {unit_number}")
                    else:
                        unit_number = all_units[0][0]  # Fallback to first if only one found
                        print(f"✅ Found only one 4-digit number: {unit_number}")
            
            # Debug: Show what we found on this page
            print(f"🏢 Extracted from page {page_number + 1}: Unit='{unit_number}'")
            return unit_number
            
    except Exception as e:
        print(f"⚠️ Error extracting unit info from page {page_number + 1}: {e}")
        return "0000"

def create_handwritten_signature(name, style="elegant"):
    """Create a realistic handwritten signature with multiple style options"""
    parts = name.split()
    
    if style == "elegant":
        # Elegant full name signature
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = parts[-1]
            signature = f"{first_name} {last_name}"
        else:
            signature = name
            
    elif style == "stylized":
        # Stylized signature with flourishes
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = parts[-1]
            if len(last_name) > 4:
                signature = f"{first_name} {last_name[:2]}{'~' * (len(last_name) - 2)}"
            else:
                signature = f"{first_name} ~ {last_name}"
        else:
            if len(name) > 4:
                signature = f"{name[:3]}{'~' * (len(name) - 3)}"
            else:
                signature = f"{name}~"
                
    elif style == "initials":
        # Initial-based signature
        if len(parts) >= 2:
            first_initial = parts[0][0].upper()
            last_initial = parts[-1][0].upper()
            signature = f"{first_initial}. {last_initial}."
        else:
            signature = f"{name[0].upper()}."
            
    elif style == "professional":
        # Professional full signature
        if len(parts) >= 2:
            # Use full name with middle initial if available
            if len(parts) == 3:
                signature = f"{parts[0]} {parts[1][0]}. {parts[2]}"
            else:
                signature = f"{parts[0]} {parts[-1]}"
        else:
            signature = name
    else:
        # Default elegant style
        signature = name
    
    return signature

def get_ordinal_suffix(day):
    """Get the ordinal suffix for a day number (1st, 2nd, 3rd, etc.)"""
    if 10 <= day % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return suffix

def determine_date_field_type(page, x, y, word_text):
    """Determine which date field type an underscore represents based on context"""
    try:
        # Get words around this position to analyze context
        words = page.extract_words()
        
        # Find words near this position
        nearby_words = []
        for word in words:
            word_x = word['x0']
            word_y = word['top']
            
            # Check if word is near our underscore (within reasonable distance)
            if (abs(word_x - x) < 200 and abs(word_y - y) < 50):
                nearby_words.append(word['text'].lower())
        
        # Analyze context to determine date field type
        context = ' '.join(nearby_words)
        
        # Look for specific patterns
        if 'day of' in context:
            return 'day'
        elif 'month' in context or any(month in context for month in ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']):
            return 'month'
        elif '20' in context or 'year' in context:
            return 'year'
        else:
            # Default based on position or pattern
            return 'day'  # Default to day if context is unclear
            
    except Exception:
        return 'day'  # Default to day if analysis fails

def check_for_overlapping_text(page, x, y, text_to_insert):
    """Check if there's existing text that might overlap with our insertion"""
    try:
        words = page.extract_words()
        
        for word in words:
            word_x = word['x0']
            word_y = word['top']
            word_text = word['text']
            
            # Check if existing text is very close to our insertion point
            if (abs(word_x - x) < 50 and abs(word_y - y) < 20):
                # If there's existing text, adjust our position
                return True
                
        return False
    except Exception:
        return False

def calculate_text_position(x, y, text_to_insert, font_size, placeholder_type):
    """Calculate optimal text position for better alignment"""
    # Base positioning
    if placeholder_type == 'day_blank':
        # For day fields, position slightly to the left (less right offset)
        x_offset = 10  # Reduced from 15 to 10 for day fields
        y_offset = 8  # Position down a little more
    elif placeholder_type in ['month_blank', 'year_blank', 'date_blank']:
        # For month and year fields, keep the current positioning
        x_offset = 15  # Move to the right to align with other text
        y_offset = 8  # Position down a little more
    elif placeholder_type == 'signature':
        # For signatures, position above the signature line
        x_offset = 0
        y_offset = -12  # Closer to the line for better alignment
    else:
        # Default positioning
        x_offset = 0
        y_offset = -3
    
    return fitz.Point(x + x_offset, y + y_offset)



def mark_checkbox(page, center_x, center_y, checkbox_size, mark_type="circle"):
    if mark_type == "circle":
        circle_radius = min(checkbox_size / 4, 3)
        page.draw_circle(
            fitz.Point(center_x, center_y),
            circle_radius,
            color=(0, 0, 0),
            fill=(0, 0, 0),
            width=1
        )
    elif mark_type == "check":
        # Draw a checkmark manually using lines (✓)
        # Adjust length/thickness based on checkbox size
        check_size = min(checkbox_size, 10)
        x, y = center_x, center_y

        # These coordinates create a simple ✓ mark shape
        page.draw_line(fitz.Point(x - check_size * 0.3, y),
                       fitz.Point(x, y + check_size * 0.3),
                       color=(0, 0, 0), width=1.2)
        page.draw_line(fitz.Point(x, y + check_size * 0.3),
                       fitz.Point(x + check_size * 0.5, y - check_size * 0.4),
                       color=(0, 0, 0), width=1.2)

def create_signed_pdf_simple(pdf_path_or_bytes, signature_name, signature_locations, use_current_date, custom_date, service_method=None, signature_style="elegant"):
    """Create signed PDF using PyMuPDF for better stream handling"""
    import traceback

    try:
        # 📌 1. DATE HANDLING
        if use_current_date:
            now = datetime.now()
            day = now.day
            month = now.strftime("%B")
            year = now.year
        else:
            date_obj = datetime.strptime(str(custom_date), "%Y-%m-%d")
            day = date_obj.day
            month = date_obj.strftime("%B")
            year = date_obj.year

        # Create formatted date components
        day_with_suffix = f"{day}{get_ordinal_suffix(day)}"
        year_last_two = str(year)[-2:]  # Last two digits of year
        
        date_text = f"before the {day} day of {month} {year}"
        day_text = day_with_suffix
        month_text = month
        year_text = year_last_two

        # 📌 2. HANDLE INPUT SAFELY
        pdf_bytes = None
        if isinstance(pdf_path_or_bytes, io.BytesIO):
            if pdf_path_or_bytes.closed:
                raise ValueError("Input BytesIO stream is closed")
            pdf_path_or_bytes.seek(0)
            pdf_bytes = pdf_path_or_bytes.getvalue()
        elif isinstance(pdf_path_or_bytes, bytes):
            pdf_bytes = pdf_path_or_bytes
        elif isinstance(pdf_path_or_bytes, str) and os.path.exists(pdf_path_or_bytes):
            with open(pdf_path_or_bytes, 'rb') as f:
                pdf_bytes = f.read()
        else:
            raise ValueError("Invalid input: must be BytesIO, bytes, or a file path")

        # 📌 3. OPEN PDF WITH PYMUPDF
        pdf_buffer = io.BytesIO(pdf_bytes)
        pdf_buffer.seek(0)
        doc = fitz.open(stream=pdf_buffer, filetype="pdf")
        
        # 📌 3.5. SETUP TIMES NEW ROMAN FONT
        # Check what built-in fonts are available
        print("Available built-in fonts in PyMuPDF:")

        # 📌 4. PROCESS EACH PAGE
        processed_pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_signatures = [loc for loc in signature_locations if loc['page'] == page_num]
            
            print(f"🔍 Page {page_num + 1}: Found {len(page_signatures)} signature locations")
            for sig in page_signatures:
                print(f"  - {sig['text']} at ({sig['x']}, {sig['y']}) type: {sig['placeholder_type']}")
            
            # Debug: show what types we have
            types_found = [sig['placeholder_type'] for sig in page_signatures]
            print(f"📋 Types on page {page_num + 1}: {set(types_found)}")

            # Copy signatures (but not date fields) from page 1 if none found on this page
            if not page_signatures and page_num > 0:
                page_0_signatures = [loc for loc in signature_locations if loc['page'] == 0]
                if page_0_signatures:
                    print(f"📋 No signatures found on page {page_num + 1}, copying signatures from page 1...")
                    # Copy ONLY signature and checkbox locations, NOT date fields
                    page_signatures = []
                    for sig in page_0_signatures:
                        # Only copy actual signatures and checkboxes, skip date fields
                        if sig.get('placeholder_type') in ['signature', 'checkbox', 'parentheses_personally_delivering', 'parentheses_posting']:
                            copied_sig = sig.copy()
                            copied_sig['page'] = page_num
                            page_signatures.append(copied_sig)
                    if page_signatures:
                        print(f"✅ Copied {len(page_signatures)} signatures/checkboxes to page {page_num + 1}")
                    else:
                        print(f"📋 No signatures to copy to page {page_num + 1}")

            if page_signatures:
                # Add signatures directly using PyMuPDF text insertion
                for sig_loc in page_signatures:
                    x = sig_loc['x']
                    y = sig_loc['y']  # Keep original coordinate system
                    font_size = sig_loc.get('font_size', 12)
                    placeholder_type = sig_loc.get('placeholder_type', 'signature')
                    
                    # Insert text directly into the PDF
                    if placeholder_type == 'date':
                        # Handle different date field types
                        if sig_loc['text'] == 'Day':
                            text_to_insert = day_text
                        elif sig_loc['text'] == 'Month':
                            text_to_insert = month_text
                        elif sig_loc['text'] == '--':
                            text_to_insert = year_text
                        else:
                            text_to_insert = date_text
                        
                        # Insert date text with better positioning and alignment
                        point = calculate_text_position(x, y, text_to_insert, font_size, placeholder_type)
                        # Use smaller font size for date fields
                        date_font_size = max(font_size - 3, 8)  # Reduce by 3 but minimum 8
                        page.insert_text(
                            point,
                            text_to_insert,
                            fontsize=date_font_size,
                            color=(0, 0, 0),
                            fontname="helv",
                            render_mode=0
                        )
                    elif placeholder_type == 'day_blank':
                        # Handle day blanks - use day with suffix like "6th"
                        text_to_insert = day_text  # Use day_text which includes "th" suffix
                        print(f"🗓️ Inserting day: {text_to_insert}")
                        
                        # Insert date text with better positioning and alignment
                        point = calculate_text_position(x, y, text_to_insert, font_size, placeholder_type)
                        # Use smaller font size for date fields
                        date_font_size = max(font_size - 3, 8)  # Reduce by 3 but minimum 8
                        page.insert_text(
                            point,
                            text_to_insert,
                            fontsize=date_font_size,
                            color=(0, 0, 0),
                            fontname="helv",
                            render_mode=0
                        )
                    elif placeholder_type == 'month_blank':
                        # Handle Florida template month blanks - use full month name
                        text_to_insert = month_text  # Full month like "August"
                        print(f"🗓️ Inserting month: {text_to_insert}")
                        
                        # Insert date text with better positioning and alignment
                        point = calculate_text_position(x, y, text_to_insert, font_size, placeholder_type)
                        # Use smaller font size for date fields
                        date_font_size = max(font_size - 3, 8)  # Reduce by 3 but minimum 8
                        page.insert_text(
                            point,
                            text_to_insert,
                            fontsize=date_font_size,
                            color=(0, 0, 0),
                            fontname="helv",
                            render_mode=0
                        )
                    elif placeholder_type == 'year_blank':
                        # Handle Florida template year blanks (20______. pattern) - use last 2 digits only
                        text_to_insert = year_text  # This is already the last 2 digits (like "25")
                        print(f"🗓️ Inserting year: {text_to_insert}")
                        
                        # Insert date text with better positioning and alignment
                        point = calculate_text_position(x, y, text_to_insert, font_size, placeholder_type)
                        # Use smaller font size for date fields
                        date_font_size = max(font_size - 3, 8)  # Reduce by 3 but minimum 8
                        page.insert_text(
                            point,
                            text_to_insert,
                            fontsize=date_font_size,
                            color=(0, 0, 0),
                            fontname="helv",
                            render_mode=0
                        )
                    elif placeholder_type == 'date_blank':
                        # Handle underscore date blanks - determine which date field based on context
                        date_field_type = determine_date_field_type(page, x, y, sig_loc['text'])
                        
                        if date_field_type == 'day':
                            text_to_insert = day_text
                        elif date_field_type == 'month':
                            text_to_insert = month_text
                        elif date_field_type == 'year':
                            text_to_insert = year_text
                        else:
                            text_to_insert = day_text  # Default to day
                        
                        # Insert date text with better positioning and alignment
                        point = calculate_text_position(x, y, text_to_insert, font_size, placeholder_type)
                        # Use smaller font size for date fields
                        date_font_size = max(font_size - 3, 8)  # Reduce by 3 but minimum 8
                        page.insert_text(
                            point,
                            text_to_insert,
                            fontsize=date_font_size,
                            color=(0, 0, 0),
                            fontname="helv",
                            render_mode=0
                        )
                    elif placeholder_type == 'checkbox':
                        # Handle checkbox for service methods (creating new checkboxes)
                        # Check if this checkbox matches the user's selection
                        checkbox_service_method = sig_loc.get('service_method', '')
                        should_check = False
                        
                        if service_method:  # Only check if user has selected a service method
                            if 'personally delivering' in checkbox_service_method and 'personally delivering' in service_method:
                                should_check = True
                            elif 'posting' in checkbox_service_method and 'posting' in service_method:
                                should_check = True
                        
                        if should_check:
                            # Draw a checked checkbox (X mark)
                            checkbox_size = 12
                            point = fitz.Point(x, y)
                            
                            # Draw checkbox rectangle
                            rect = fitz.Rect(x, y, x + checkbox_size, y + checkbox_size)
                            page.draw_rect(rect, color=(0, 0, 0), width=1)
                            
                            # Draw X mark inside checkbox
                            page.draw_line(
                                fitz.Point(x + 2, y + 2),
                                fitz.Point(x + checkbox_size - 2, y + checkbox_size - 2),
                                color=(0, 0, 0),
                                width=1
                            )
                            page.draw_line(
                                fitz.Point(x + checkbox_size - 2, y + 2),
                                fitz.Point(x + 2, y + checkbox_size - 2),
                                color=(0, 0, 0),
                                width=1
                            )
                            print(f"✅ Created and checked new checkbox for: {checkbox_service_method}")
                        else:
                            print(f"⏭️ Skipped creating checkbox for: {checkbox_service_method} (doesn't match selected service method)")
                    
                    elif placeholder_type == 'existing_checkbox':
                        # Handle existing checkboxes in the PDF
                        checkbox_type = sig_loc.get('checkbox_type', 'unknown')
                        should_check = False
                        
                        nearby_text = sig_loc.get('nearby_text', '')
                        print(f"🔍 Processing parentheses: type={checkbox_type}, service_method='{service_method}'")
                        print(f"🔍 Nearby text: '{nearby_text}'")
                        
                        if service_method:  # Only check if user has selected a service method
                            # Enhanced matching logic
                            service_method_lower = service_method.lower()
                            nearby_text = sig_loc.get('nearby_text', '').lower()
                            
                            # EXCLUSIVE matching - only check the one that matches the user's selection
                            if service_method == "By personally delivering same upon said tenant":
                                # User selected personally delivering - ONLY check that one
                                if checkbox_type == 'personally_delivering':
                                    should_check = True
                                    print(f"✅ MATCHED: User selected personally delivering, checkbox type is {checkbox_type}")
                                else:
                                    print(f"⏭️ SKIPPED: User selected personally delivering, but this checkbox type is {checkbox_type}")
                            elif service_method == "By posting same at the above described premises in the absence of said tenant":
                                # User selected posting - ONLY check that one
                                if checkbox_type == 'posting':
                                    should_check = True
                                    print(f"✅ MATCHED: User selected posting, checkbox type is {checkbox_type}")
                                else:
                                    print(f"⏭️ SKIPPED: User selected posting, but this checkbox type is {checkbox_type}")
                            else:
                                # For any other service method, be very strict about matching
                                print(f"⚠️ Unknown service method: '{service_method}' - not checking any parentheses")
                        
                        if should_check:
                            # Check the parentheses by adding a checkmark symbol (✓)
                            checkbox_text = sig_loc.get('text', '')
                            checkbox_size = max(sig_loc['width'], sig_loc['height'], 12)
                            
                            # Calculate the center of the parentheses
                            center_x = x + checkbox_size / 2
                            center_y = y + checkbox_size / 2
                            
                            # Check if this is a period-based checkbox (.) or regular parentheses
                            if checkbox_text.strip() == '.' or '(.)' in checkbox_text:
                                # For period-based checkboxes, fill in the period with a solid circle
                                mark_checkbox(page, center_x, center_y, checkbox_size, "circle")
                                print(f"✅ Filled period checkbox")
                            else:
                                # For regular parentheses, add checkmark using manual drawing
                                mark_checkbox(page, center_x, center_y, checkbox_size, "check")
                                print(f"✅ Added checkmark to parentheses")
                            
                            print(f"✅ Checked parentheses: {checkbox_type} at position ({x}, {y}) - text: {checkbox_text}")
                        else:
                            print(f"⏭️ Skipped parentheses: {checkbox_type} (doesn't match selected service method)")
                    else:
                        # Use text-based signature with selected styling
                        text_to_insert = create_handwritten_signature(signature_name, signature_style)
                        print(f"🖋️ PROCESSING SIGNATURE: {text_to_insert} at position ({x}, {y})")
                        
                        # Position signature based on location - top signature above line, bottom signature on line
                        # Based on debug output: "SIGN HERE" is at y: 311.58, underscore line is at y: 315.66
                        # Top signature (y < 350) should be above the line, bottom signature (y > 500) should be on the line
                        if y < 350:  # Top signature - position above the line
                            point = fitz.Point(x, y - 13)  # Move up 15 points above the line
                        else:  # Bottom signature - position right on the line
                            point = fitz.Point(x, y)  # Position signature right on the line
                        
                        # Use signature-style formatting with appropriate font size
                        font_size_adjusted = max(font_size + 2, 14)  # Moderate increase, minimum 14pt
                        
                        # Signature color - slightly blue-black like real ink
                        signature_color = (0.1, 0.1, 0.2)  # Dark blue-black
                        
                        # Use Times New Roman font ONLY - try different approaches
                        success = False
                        
                        # Method 1: Try with fontname parameter
                        for font_name in ["times-roman", "times", "serif"]:
                            try:
                                page.insert_text(
                                    point,
                                    text_to_insert,
                                    fontsize=font_size_adjusted,
                                    color=signature_color,
                                    fontname=font_name,
                                    render_mode=0
                                )
                                print(f"✅ Used Times New Roman signature ({font_name}): {text_to_insert}")
                                success = True
                                break
                            except Exception as e:
                                print(f"❌ Failed with fontname '{font_name}': {e}")
                                continue
                        
                        if not success:
                            print(f"❌ ERROR: No Times New Roman font variants worked!")
                            raise Exception("Times New Roman font is required but not available")

        # 📌 5. EXPORT FINAL PDF - SPLIT INTO INDIVIDUAL PAGES
        try:
            # Create individual PDF files for each page
            individual_pdfs = []
            
            for page_num in range(len(doc)):
                # Create a new PDF document for this page
                single_page_doc = fitz.open()
                single_page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                
                # Save the single page to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_output:
                    single_page_path = temp_output.name
                
                try:
                    single_page_doc.save(single_page_path)
                    
                    with open(single_page_path, 'rb') as f:
                        page_bytes = f.read()
                    
                    individual_pdfs.append({
                        'page_num': page_num + 1,
                        'data': page_bytes,
                        'filename': f"page_{page_num + 1}.pdf"
                    })
                    
                finally:
                    if os.path.exists(single_page_path):
                        os.unlink(single_page_path)
                    single_page_doc.close()
            
            # Return the list of individual PDFs
            return individual_pdfs

        finally:
            doc.close()

    except Exception as e:
        st.error(f"Error creating signed PDF: {str(e)}")
        st.code(traceback.format_exc())  # Print the full traceback for debugging
        return None



def main():
    st.set_page_config(
        page_title="Demand Letter Generator",
        layout="wide"
    )
    
    st.title("Demand Letter Generator")
    st.markdown("Upload PDFs with signatures and dates")
    

    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        signature_name = st.text_input(
            "Signer Name",
            placeholder="Enter the name to use as signature",
            key="signature_name"
        )
        
        # Text signature settings
        signature_image = None
        signature_style = "elegant"  # Default to elegant style
        
        # Show signature preview
        if signature_name:
            st.subheader("Signature Preview")
            preview_signature = create_handwritten_signature(signature_name, signature_style)
            st.markdown(f"**Preview:** `{preview_signature}`")
        
        # Date options
        st.subheader("Date Settings")
        
        # Ask user for their preferred date
        date_option = st.radio(
            "Choose Date Option",
            ["Use Current Date", "Select Custom Date"],
            help="Choose whether to use today's date or select a specific date",
            key="date_option"
        )
        
        if date_option == "Use Current Date":
            use_current_date = True
            custom_date = None
            st.info(f"Will use current date: {datetime.now().strftime('%B %d, %Y')}")
        else:
            use_current_date = False
            custom_date = st.date_input(
                "Select Date for Documents",
                value=datetime.now().date(),
                help="Choose the date to appear on all generated documents",
                key="custom_date"
            )
                
            st.info(f"Selected date: {custom_date.strftime('%B %d, %Y')}")
        
        # Checkbox options
        st.subheader("Service Method")
        
        service_method_options = [
            "By personally delivering same upon said tenant",
            "By posting same at the above described premises in the absence of said tenant",
        ]
        
        service_method = st.radio(
            "Choose Service Method",
            service_method_options,
            help="Select which service method checkbox should be checked on the documents",
            key="service_method"
        )
        
        st.info(f"Will check: **{service_method}**")
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Show selected date prominently
        if use_current_date:
            st.success(f"**Using Current Date:** {datetime.now().strftime('%B %d, %Y')}")
        else:
            st.success(f"**Selected Date:** {custom_date.strftime('%B %d, %Y')}")
        
        st.divider()
        st.header("Upload PDFs")
        
        uploaded_files = st.file_uploader(
            "Choose PDF files to add signatures to",
            type=['pdf'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
                st.success(f"Uploaded {len(uploaded_files)} file(s)")
                
                # Process files
                if st.button("Add Signatures to PDFs", type="primary"):
                    if not signature_name:
                        st.error("Please enter a signer name")
                        return
                    
                    processed_files = []
                    
                    with st.spinner("Processing PDFs..."):
                        for uploaded_file in uploaded_files:
                            st.write(f"Processing {uploaded_file.name}...")
                            
                            # Recreate a clean BytesIO buffer for safe re-use
                            raw_bytes = uploaded_file.getvalue()
                            pdf_bytes = io.BytesIO(raw_bytes)
                            pdf_bytes.seek(0)  # 🔑 this is crucial
                            
                            # Analyze the uploaded PDF structure
                            uploaded_features = analyze_pdf_structure(pdf_bytes)
                            
                            if uploaded_features is None:
                                st.error(f"Could not analyze {uploaded_file.name}")
                                continue
                            
                            # Match to best template
                            matched_template, match_score = match_pdf_to_template(uploaded_features)
                            
                            if matched_template and match_score > 20:  # Minimum confidence threshold
                                st.success(f"Matched to {matched_template} (confidence: {match_score})")
                                
                                # Extract unit number for file naming from the UPLOADED PDF
                                unit_number = extract_unit_info(pdf_bytes, matched_template)
                                
                                # Get template info and find placeholders
                                template_info = TEMPLATES[matched_template]
                                template_path = template_info['file_path']
                                
                                # Find signature placeholders in the UPLOADED PDF (not template) with template-specific positioning
                                signature_locations = find_signature_placeholders_simple(pdf_bytes, matched_template)
                                
                                if signature_locations:
                                    
                                    # Add signatures at the found locations using the uploaded PDF
                                    processed_pages = create_signed_pdf_simple(
                                        pdf_bytes,  # Pass BytesIO object directly
                                        signature_name,
                                        signature_locations,
                                        use_current_date,
                                        custom_date,
                                        service_method,
                                        signature_style
                                    )
                                    
                                    if processed_pages:
                                        # Create formatted file name: "Unit{Unit Number} Demand Letter {Current Date}"
                                        current_date = datetime.now().strftime('%m-%d-%Y')
                                        
                                        # Add each individual page as a separate file
                                        for page_info in processed_pages:
                                            # Extract unit number for each individual page if it's a multi-page PDF
                                            if len(processed_pages) > 1:
                                                # For multi-page PDFs, extract unit number from each page separately
                                                page_unit_number = extract_unit_info_from_page(pdf_bytes, matched_template, page_info['page_num'] - 1)
                                            else:
                                                # For single page PDFs, use the already extracted info
                                                page_unit_number = unit_number
                                            
                                            formatted_filename = f"Unit{page_unit_number} Demand Letter {current_date}.pdf"
                                            processed_files.append({
                                                'name': formatted_filename,
                                                'data': page_info['data'],
                                                'locations_found': len(signature_locations),
                                                'matched_template': matched_template,
                                                'match_score': match_score,
                                                'page_num': page_info['page_num'],
                                                'unit_number': page_unit_number
                                            })
                                else:
                                    st.error(f"No signature placeholders found in {matched_template}")
                            else:
                                st.error(f"Could not match {uploaded_file.name} to any template")
                    
                    # Display results
                    if processed_files:
                        st.success(f"Successfully processed {len(processed_files)} file(s)")
                        
                        # Create zip file for batch download - always available
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
                            with zipfile.ZipFile(tmp_zip.name, 'w') as zip_file:
                                for file_info in processed_files:
                                    zip_file.writestr(file_info['name'], file_info['data'])
                                
                            # Read the zip file
                            with open(tmp_zip.name, 'rb') as f:
                                zip_bytes = f.read()
                            
                            # Clean up
                            os.unlink(tmp_zip.name)
                            
                        # Prominent ZIP download button
                        current_date_zip = datetime.now().strftime('%m-%d-%Y')
                        st.subheader("Download Options")
                        
                        # Make ZIP download prominent
                        col_zip, col_info = st.columns([3, 1])
                        with col_zip:
                            st.download_button(
                                label="Download All Files as ZIP",
                                data=zip_bytes,
                                file_name=f"Demand Letters {current_date_zip}.zip",
                                mime="application/zip",
                                type="primary",
                                use_container_width=True,
                                key="download_zip_all"
                            )
                        with col_info:
                            st.info(f"{len(processed_files)} file(s)")
                        
                        st.markdown("---")
                        st.markdown("**Individual Downloads:**")
                        
                        # Individual download buttons
                        with col2:
                            st.header("Results")
                            
                            for i, file_info in enumerate(processed_files):
                                st.write(f"**{file_info['name']}**")
                                
                                # Create download button with unique key
                                st.download_button(
                                    label=f"Download {file_info['name']}",
                                    data=file_info['data'],
                                    file_name=file_info['name'],
                                    mime="application/pdf",
                                    key=f"download_individual_{i}"
                                )
                                st.divider()
                    else:
                        st.error("No files were successfully processed")
    
    with col2:
        st.header("Instructions")
        st.markdown("""
        **Upload PDFs:**
        1. **Upload your PDFs** (with or without placeholders)
        2. **Enter signer name** in the sidebar
        3. **Choose date settings** (current or custom date)
        4. **Select service method** (which checkbox to check)
        5. **Click Add Signatures** to process PDFs
        6. **Download** signed PDFs (split into individual pages)
        
        """)
    

if __name__ == "__main__":
    main() 