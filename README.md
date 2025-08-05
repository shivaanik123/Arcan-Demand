# Signature Letter Generator

A modern web platform for generating letters with custom signatures from uploaded PDF documents. Users can upload ZIP files containing multiple PDFs or individual PDF files, specify signature names and dates, and automatically generate signed documents with filled forms and checkboxes.

## Features

- **File Upload**: Support for ZIP files containing PDFs or individual PDF files
- **Signature Customization**: Add custom signature names and dates
- **Form Filling**: Automatically fill in common form fields (signature, date, checkboxes)
- **Batch Processing**: Process multiple documents at once
- **Download**: Download individual files or all processed documents
- **Modern UI**: Beautiful, responsive interface built with React and Tailwind CSS

## Technology Stack

- **Frontend**: React 18 with Vite
- **Styling**: Tailwind CSS
- **PDF Processing**: pdf-lib
- **File Handling**: JSZip for ZIP file processing
- **Icons**: Lucide React
- **Date Handling**: date-fns

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd signature-letter-generator
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```

4. **Open your browser** and navigate to `http://localhost:3000`

## Usage

### Uploading Documents

1. **Drag and drop** files onto the upload area, or click "Choose Files"
2. **Supported formats**:
   - ZIP files containing PDF documents
   - Individual PDF files
3. **File size limit**: 50MB per file

### Setting Signature Details

1. **Enter signature name** in the "Signature Name" field
2. **Choose date option**:
   - Check "Use current date" for today's date
   - Or select a custom date from the date picker

### Generating Letters

1. **Click "Generate Letters"** to process all uploaded documents
2. **Wait for processing** - the system will:
   - Add signatures to each document
   - Fill in date fields
   - Check applicable checkboxes
   - Fill blank form fields

### Downloading Results

1. **Download individual files** by clicking the download button next to each document
2. **Download all files** using the "Download All Documents" button
3. **File naming**: Processed files are named with the pattern `signed_[original-name]_[signature-name].pdf`

## How It Works

### PDF Processing

The application uses the `pdf-lib` library to:

1. **Load PDF documents** from uploaded files
2. **Add signature text** at the bottom right of each page
3. **Add date information** below the signature
4. **Fill form fields** automatically:
   - Signature fields (containing "signature", "name", or "signed")
   - Date fields (containing "date")
   - Checkboxes (containing "agree", "accept", or "confirm")
5. **Save processed PDFs** with all modifications

### ZIP File Handling

For ZIP files containing multiple PDFs:

1. **Extract PDF files** from the ZIP using JSZip
2. **Process each PDF** individually
3. **Maintain original filenames** for easy identification

### Form Field Detection

The system automatically detects and fills common form field types:

- **Text fields**: For signatures and dates
- **Checkboxes**: For agreement/confirmation fields
- **Blank fields**: Auto-filled with appropriate information

## Development

### Project Structure

```
src/
├── components/
│   ├── FileUpload.jsx      # File upload component
│   ├── SignatureForm.jsx   # Signature and date form
│   └── DocumentPreview.jsx # Results preview and download
├── utils/
│   └── documentProcessor.js # PDF processing logic
├── App.jsx                 # Main application component
├── main.jsx               # React entry point
└── index.css              # Global styles
```

### Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

### Customization

#### Adding New Form Field Types

Edit `src/utils/documentProcessor.js` to add support for additional field types:

```javascript
// Add new field detection logic
if (fieldName.includes('your-field-type')) {
  // Handle the new field type
}
```

#### Modifying Signature Position

Change the signature positioning in the `processDocuments` function:

```javascript
const signatureX = width - 150  // Adjust X position
const signatureY = 100          // Adjust Y position
```

## Browser Compatibility

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## License

MIT License - see LICENSE file for details.

## Support

For issues or questions, please create an issue in the repository or contact the development team. 