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

def find_signature_placeholders_simple(pdf_path_or_bytes):
    """Find signature placeholders with simple, robust approach"""
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
            return _extract_placeholders(pdf)
    except Exception as e:
        st.error(f"Error finding placeholders: {str(e)}")
        return []

def _extract_placeholders(pdf):
    """Extract placeholders from PDF object"""
    signature_locations = []
    
    for page_num, page in enumerate(pdf.pages):
        try:
            words = page.extract_words()
            
            for word_data in words:
                word_text = word_data['text'].strip()
                
                # Look for signature placeholders - "Signature" and "SIGN" (only bottom ones)
                if word_text.lower() == "signature" or word_text.lower() == "sign":
                    # Only add signatures that are in the bottom section (y > 500)
                    if word_data['top'] > 500:
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
                
                # Check for long underscore lines (signature lines) - only bottom ones
                if len(word_text) > 15 and all(c in '_' for c in word_text):
                    # Only add signature lines that are in the bottom section (y > 500)
                    if word_data['top'] > 500:
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
                
                # Check for Florida template specific patterns - ONLY the main date fields
                # Only detect the specific patterns we want, not generic day/month text
                if '______day' in word_text:
                    signature_locations.append({
                        'page': page_num,
                        'text': word_text,
                        'x': word_data['x0'],
                        'y': word_data['top'],
                        'width': word_data['x1'] - word_data['x0'],
                        'height': word_data['bottom'] - word_data['top'],
                        'font_size': word_data.get('size', 12),
                        'placeholder_type': 'day_blank'
                    })
                elif 'of___________,' in word_text:
                    signature_locations.append({
                        'page': page_num,
                        'text': word_text,
                        'x': word_data['x0'],
                        'y': word_data['top'],
                        'width': word_data['x1'] - word_data['x0'],
                        'height': word_data['bottom'] - word_data['top'],
                        'font_size': word_data.get('size', 12),
                        'placeholder_type': 'month_blank'
                    })
                elif '20______.' in word_text or '20____' in word_text:
                    signature_locations.append({
                        'page': page_num,
                        'text': word_text,
                        'x': word_data['x0'],
                        'y': word_data['top'],
                        'width': word_data['x1'] - word_data['x0'],
                        'height': word_data['bottom'] - word_data['top'],
                        'font_size': word_data.get('size', 12),
                        'placeholder_type': 'year_blank'
                    })
                # Check for second section date patterns - in correct order: day, month, year
                elif word_text == '__________' and word_data['top'] > 400:
                    # First underscore pattern in second section - DAY field
                    signature_locations.append({
                        'page': page_num,
                        'text': word_text,
                        'x': word_data['x0'],
                        'y': word_data['top'],
                        'width': word_data['x1'] - word_data['x0'],
                        'height': word_data['bottom'] - word_data['top'],
                        'font_size': word_data.get('size', 12),
                        'placeholder_type': 'day_blank'
                    })
                elif word_text == '__________________,' and word_data['top'] > 400:
                    # Second underscore pattern in second section - MONTH field
                    signature_locations.append({
                        'page': page_num,
                        'text': word_text,
                        'x': word_data['x0'],
                        'y': word_data['top'],
                        'width': word_data['x1'] - word_data['x0'],
                        'height': word_data['bottom'] - word_data['top'],
                        'font_size': word_data.get('size', 12),
                        'placeholder_type': 'month_blank'
                    })
                elif word_text.lower() == 'month' and word_data['top'] > 400:
                    signature_locations.append({
                        'page': page_num,
                        'text': word_text,
                        'x': word_data['x0'],
                        'y': word_data['top'],
                        'width': word_data['x1'] - word_data['x0'],
                        'height': word_data['bottom'] - word_data['top'],
                        'font_size': word_data.get('size', 12),
                        'placeholder_type': 'month_blank'
                    })
                
                # Check for checkbox patterns (for "By posting same at the above described premises")
                if 'posting' in word_text.lower() and 'premises' in word_text.lower():
                    # Look for checkbox near this text
                    signature_locations.append({
                        'page': page_num,
                        'text': word_text,
                        'x': word_data['x0'] - 20,  # Position checkbox to the left
                        'y': word_data['top'],
                        'width': 15,
                        'height': 15,
                        'font_size': word_data.get('size', 12),
                        'placeholder_type': 'checkbox'
                    })
        except Exception as e:
            st.warning(f"Error processing page {page_num}: {str(e)}")
            continue
    
    return signature_locations



def create_handwritten_signature(name):
    """Create a beautiful cursive signature"""
    parts = name.split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = parts[-1]
        
        # Create a flowing cursive signature with full first and last name
        signature = f"{first_name} {last_name}"
    else:
        # Single name - add flourish
        signature = f"{name}"
    
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



def create_signed_pdf_simple(pdf_path_or_bytes, signature_name, signature_locations, use_current_date, custom_date):
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
        
        # 📌 3.5. EMBED CUSTOM FONT IF AVAILABLE
        custom_font_available = False
        font_path = "fonts/Playwrite_AU_QLD/PlaywriteAUQLD-VariableFont_wght.ttf"
        if os.path.exists(font_path):
            try:
                # Try to embed the custom font at document level
                font_buffer = open(font_path, "rb").read()
                custom_font_available = True
                print(f"✅ Custom font loaded: {font_path}")
            except Exception as e:
                custom_font_available = False
                print(f"❌ Failed to load custom font: {e}")
        else:
            print(f"❌ Font file not found: {font_path}")

        # 📌 4. PROCESS EACH PAGE
        processed_pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_signatures = [loc for loc in signature_locations if loc['page'] == page_num]

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
                        # Handle Florida template day blanks (______day pattern)
                        text_to_insert = day_text
                        
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
                        # Handle Florida template month blanks (of___________, pattern)
                        text_to_insert = month_text
                        
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
                        # Handle Florida template year blanks (20______. pattern)
                        text_to_insert = year_text
                        
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
                        # Handle checkbox for "By posting same at the above described premises"
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
                    else:
                        # Use text-based signature with cursive styling
                        text_to_insert = create_handwritten_signature(signature_name)
                        point = calculate_text_position(x, y, text_to_insert, font_size, placeholder_type)
                        
                        # Use elegant styling for signature with cursive font
                        font_size_adjusted = font_size + 2  # Slightly larger for elegance
                        
                        # Use custom Playwrite font for italic/cursive signature
                        if custom_font_available:
                            try:
                                # Use the embedded custom font
                                page.insert_text(
                                    point,
                                    text_to_insert,
                                    fontsize=font_size_adjusted,
                                    color=(0, 0, 0),
                                    fontname="playwrite",
                                    fontfile=font_buffer,
                                    render_mode=0
                                )
                                print(f"✅ Used custom font for signature: {text_to_insert}")
                            except Exception as e:
                                print(f"❌ Custom font failed: {e}")
                                # If custom font fails, try Times Italic
                                try:
                                    page.insert_text(
                                        point,
                                        text_to_insert,
                                        fontsize=font_size_adjusted,
                                        color=(0, 0, 0),
                                        fontname="tiro",
                                        render_mode=0
                                    )
                                    print(f"✅ Used Times Italic fallback for signature: {text_to_insert}")
                                except:
                                    # Final fallback to helvetica
                                    page.insert_text(
                                        point,
                                        text_to_insert,
                                        fontsize=font_size_adjusted,
                                        color=(0, 0, 0),
                                        fontname="helv",
                                        render_mode=0
                                    )
                                    print(f"✅ Used Helvetica fallback for signature: {text_to_insert}")
                        else:
                            # Try Times Italic if custom font not available
                            try:
                                page.insert_text(
                                    point,
                                    text_to_insert,
                                    fontsize=font_size_adjusted,
                                    color=(0, 0, 0),
                                    fontname="tiro",
                                    render_mode=0
                                )
                                print(f"✅ Used Times Italic (no custom font): {text_to_insert}")
                            except:
                                # Final fallback to helvetica
                                page.insert_text(
                                    point,
                                    text_to_insert,
                                    fontsize=font_size_adjusted,
                                    color=(0, 0, 0),
                                    fontname="helv",
                                    render_mode=0
                                )
                                print(f"✅ Used Helvetica (no custom font): {text_to_insert}")

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
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Demand Letter Generator")
    st.markdown("Upload PDFs or generate from templates with signatures and dates")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Mode selection
        mode = st.radio(
            "Choose Mode",
            ["Upload PDFs", "Generate from Templates"],
            help="Upload your own PDFs or generate from our templates"
        )
        
        signature_name = st.text_input(
            "Signer Name",
            placeholder="Enter the name to use as signature"
        )
        
        # Text signature info and preview
        st.info("Using text-based signature")
        signature_image = None
        
        # Show signature preview
        if signature_name:
            st.subheader("📝 Signature Preview")
            preview_signature = create_handwritten_signature(signature_name)
            st.markdown(f"**Preview:** `{preview_signature}`")
            st.markdown("*Beautiful cursive signature using Playwrite font*")
        
        # Date options
        use_current_date = st.checkbox("Use Current Date", value=True)
        
        if not use_current_date:
            custom_date = st.date_input("Select Custom Date")
        else:
            custom_date = None
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if mode == "Upload PDFs":
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
                                
                                # Get template info and find placeholders
                                template_info = TEMPLATES[matched_template]
                                template_path = template_info['file_path']
                                
                                # Find signature placeholders in the template
                                signature_locations = find_signature_placeholders_simple(template_path)
                                
                                if signature_locations:
                                    st.write(f"Found {len(signature_locations)} signature location(s) in template")
                                    
                                    # Add signatures at the found locations using the uploaded PDF
                                    processed_pages = create_signed_pdf_simple(
                                        pdf_bytes,  # Pass BytesIO object directly
                                        signature_name,
                                        signature_locations,
                                        use_current_date,
                                        custom_date
                                    )
                                    
                                    if processed_pages:
                                        # Add each individual page as a separate file
                                        for page_info in processed_pages:
                                            processed_files.append({
                                                'name': f"{uploaded_file.name.replace('.pdf', '')}_page_{page_info['page_num']}.pdf",
                                                'data': page_info['data'],
                                                'locations_found': len(signature_locations),
                                                'matched_template': matched_template,
                                                'match_score': match_score,
                                                'page_num': page_info['page_num']
                                            })
                                else:
                                    st.warning(f"No signature placeholders found in {matched_template}")
                            else:
                                st.warning(f"Could not confidently match {uploaded_file.name} to any template (best score: {match_score})")
                                
                                # Show analysis details for debugging
                                with st.expander("Analysis Details"):
                                    st.write(f"Page count: {uploaded_features['page_count']}")
                                    st.write(f"Word count: {uploaded_features['word_count']}")
                                    st.write(f"State indicators: {uploaded_features['state_indicators']}")
                                    st.write(f"Has demand letter keywords: {uploaded_features['has_demand_letter_keywords']}")
                                    st.write(f"Key phrases found: {uploaded_features['key_phrases'][:5]}")  # Show first 5
                    
                    # Display results
                    if processed_files:
                        st.success(f"Successfully processed {len(processed_files)} file(s)")
                        
                        # Create zip file for batch download
                        if len(processed_files) > 1:
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
                                with zipfile.ZipFile(tmp_zip.name, 'w') as zip_file:
                                    for file_info in processed_files:
                                        zip_file.writestr(f"signed_{file_info['name']}", file_info['data'])
                                
                                # Read the zip file
                                with open(tmp_zip.name, 'rb') as f:
                                    zip_bytes = f.read()
                                
                                # Clean up
                                os.unlink(tmp_zip.name)
                            
                            # Download button for zip file
                            st.download_button(
                                label="📦 Download All Signed PDFs (ZIP)",
                                data=zip_bytes,
                                file_name=f"signed_pdfs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                                mime="application/zip"
                            )
                        
                        # Individual download buttons
                        with col2:
                            st.header("Results")
                            
                            for file_info in processed_files:
                                st.write(f"**{file_info['name']}**")
                                st.write(f"Signature locations: {file_info['locations_found']}")
                                
                                # Show page number if available
                                if 'page_num' in file_info:
                                    st.write(f"Page: {file_info['page_num']}")
                                
                                # Show template matching info if available
                                if 'matched_template' in file_info:
                                    st.write(f"Matched template: {file_info['matched_template']}")
                                    st.write(f"Match confidence: {file_info['match_score']}")
                                
                                # Create download button
                                st.download_button(
                                    label=f"Download {file_info['name']}",
                                    data=file_info['data'],
                                    file_name=file_info['name'],
                                    mime="application/pdf"
                                )
                                st.divider()
                    else:
                        st.error("No files were successfully processed")
        
        else:  # Generate from Templates
            st.header("Generate from Templates")
            
            # Template selection
            selected_template = st.selectbox(
                "Select Template",
                options=list(TEMPLATES.keys()),
                help="Choose the template to use for generating demand letters"
            )
            
            # Show template description
            if selected_template in TEMPLATES:
                template_info = TEMPLATES[selected_template]
                st.info(f"**{selected_template}**: {template_info['description']}")
                
                if template_info['include_date']:
                    st.success("✅ This template includes date fields")
                else:
                    st.info("ℹ️ This template only includes signature fields")
            
            # Number of letters to generate
            num_letters = st.number_input(
                "Number of Letters to Generate",
                min_value=1,
                max_value=50,
                value=1,
                help="How many demand letters to generate"
            )
            
            # Generate letters
            if st.button("Generate Demand Letters", type="primary"):
                if not signature_name:
                    st.error("Please enter a signer name")
                    return
                
                template_info = TEMPLATES[selected_template]
                template_path = template_info['file_path']
                
                # Check if template file exists
                if not os.path.exists(template_path):
                    st.error(f"Template file not found: {template_path}")
                    return
                
                # Find signature placeholders in template
                with st.spinner("Analyzing template..."):
                    signature_locations = find_signature_placeholders_simple(template_path)
                    
                    if signature_locations:
                        st.success(f"Found {len(signature_locations)} signature location(s) in template")
                    else:
                        st.warning("No signature placeholders found in template")
                
                # Generate letters
                processed_files = []
                
                with st.spinner(f"Generating {num_letters} demand letter(s)..."):
                    for i in range(num_letters):
                        st.write(f"Generating letter {i+1}/{num_letters}...")
                        
                        # Generate PDF from template
                        processed_pages = create_signed_pdf_simple(
                            template_path,
                            signature_name,
                            signature_locations,
                            use_current_date,
                            custom_date
                        )
                        
                        if processed_pages:
                            # Add each individual page as a separate file
                            for page_info in processed_pages:
                                processed_files.append({
                                    'name': f"{selected_template.replace(' ', '_')}_Letter_{i+1}_page_{page_info['page_num']}.pdf",
                                    'data': page_info['data'],
                                    'locations_found': len(signature_locations),
                                    'page_num': page_info['page_num']
                                })
                
                # Display results
                if processed_files:
                    st.success(f"Successfully generated {len(processed_files)} demand letter(s)")
                    
                    # Create zip file for batch download
                    if len(processed_files) > 1:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
                            with zipfile.ZipFile(tmp_zip.name, 'w') as zip_file:
                                for file_info in processed_files:
                                    zip_file.writestr(file_info['name'], file_info['data'])
                            
                            # Read the zip file
                            with open(tmp_zip.name, 'rb') as f:
                                zip_bytes = f.read()
                            
                            # Clean up
                            os.unlink(tmp_zip.name)
                        
                        # Download button for zip file
                        st.download_button(
                            label="📦 Download All Letters (ZIP)",
                            data=zip_bytes,
                            file_name=f"demand_letters_{selected_template.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                            mime="application/zip"
                        )
                    
                    # Individual download buttons
                    with col2:
                        st.header("Results")
                        
                        for file_info in processed_files:
                            st.write(f"**{file_info['name']}**")
                            st.write(f"Signature locations: {file_info['locations_found']}")
                            
                            # Show page number if available
                            if 'page_num' in file_info:
                                st.write(f"Page: {file_info['page_num']}")
                            
                            # Create download button
                            st.download_button(
                                label=f"Download {file_info['name']}",
                                data=file_info['data'],
                                file_name=file_info['name'],
                                mime="application/pdf"
                            )
                            st.divider()
                else:
                    st.error("No letters were successfully generated")
    
    with col2:
        st.header("Instructions")
        st.markdown("""
        **Upload PDFs Mode:**
        1. **Upload your PDFs** (with or without placeholders)
        2. **Enter signer name** in the sidebar
        3. **Click Generate** to match to templates and add signatures
        4. **Download** signed PDFs (split into individual pages)
        
        **Generate from Templates Mode:**
        1. **Select template** (Florida or Georgia)
        2. **Enter signer name** in the sidebar
        3. **Choose number of letters** to generate
        4. **Click Generate** to create demand letters
        5. **Download** letters individually or as ZIP
        
        The system will:
        - **Analyze uploaded PDFs** and match to appropriate templates
        - **Find signature placeholders** in templates
        - **Add signatures** in correct locations
        - **Add dates** where appropriate
        - **Split multi-page PDFs into individual pages**
        - **Preserve PDF formatting**
        - **Show matching confidence** for each file
        """)
        
        st.header("Supported Placeholders")
        st.markdown("""
        - `SIGN HERE`
        - `SIGNATURE`
        - `<<SIGNATURE>>`
        - `<<SIGN>>`
        - `DATE HERE`
        - `<<DATE>>`
        - `___` (underscore lines)
        - `...` (dotted lines)
        """)

if __name__ == "__main__":
    main() 