import { PDFDocument, PDFTextField, PDFCheckBox } from 'pdf-lib'

// Helper function to detect blank lines and form fields in PDF
export const scanPDFStructure = async (file) => {
  try {
    const arrayBuffer = await file.arrayBuffer()
    
    // Try different loading methods
    let pdfDoc
    try {
      pdfDoc = await PDFDocument.load(arrayBuffer, { ignoreEncryption: true })
    } catch (error) {
      try {
        pdfDoc = await PDFDocument.load(arrayBuffer)
      } catch (error2) {
        pdfDoc = await PDFDocument.load(arrayBuffer, { 
          ignoreEncryption: true,
          updateMetadata: false 
        })
      }
    }

    const pages = pdfDoc.getPages()
    if (pages.length === 0) {
      throw new Error('No pages found in PDF')
    }

    const page = pages[0]
    const { width, height } = page.getSize()
    
    // Get form fields
    const form = pdfDoc.getForm()
    const fields = form.getFields()
    
    const formFields = fields.map(field => ({
      name: field.getName(),
      type: field.constructor.name,
      value: field instanceof PDFTextField ? field.getText() : null,
      isTextField: field instanceof PDFTextField,
      isCheckBox: field instanceof PDFCheckBox
    }))

    // Analyze text content and positions
    const textContent = await extractTextContent(pdfDoc)
    
    // Detect potential signature areas (blank lines, underlines, etc.)
    const signatureAreas = detectSignatureAreas(textContent, width, height)
    
    // Detect date areas
    const dateAreas = detectDateAreas(textContent, width, height)
    
    return {
      success: true,
      pageCount: pages.length,
      pageSize: { width, height },
      formFields,
      textContent,
      signatureAreas,
      dateAreas,
      recommendations: generateRecommendations(formFields, signatureAreas, dateAreas)
    }
    
  } catch (error) {
    console.error('Error scanning PDF:', error)
    return {
      success: false,
      error: error.message
    }
  }
}

// Extract text content from PDF
const extractTextContent = async (pdfDoc) => {
  // This is a simplified text extraction
  // In a real implementation, you'd use a more sophisticated PDF text extraction library
  const pages = pdfDoc.getPages()
  const page = pages[0]
  const { width, height } = page.getSize()
  
  // For now, we'll return a basic structure
  // In practice, you'd extract actual text content
  return {
    lines: [
      { text: 'Sample text line 1', y: height - 100 },
      { text: 'Sample text line 2', y: height - 150 },
      { text: 'Signature: ___________', y: height - 200 },
      { text: 'Date: before the ___ day of ___ ___', y: height - 250 }
    ],
    width,
    height
  }
}

// Detect potential signature areas
const detectSignatureAreas = (textContent, width, height) => {
  const areas = []
  
  // Look for common signature indicators
  const signatureKeywords = ['signature', 'signed', 'name', 'blank', 'line', 'underscore']
  
  textContent.lines.forEach(line => {
    const lowerText = line.text.toLowerCase()
    
    // Check if line contains signature-related keywords
    const hasSignatureKeyword = signatureKeywords.some(keyword => 
      lowerText.includes(keyword)
    )
    
    // Check if line has underscores or blank spaces (potential signature line)
    const hasUnderscores = line.text.includes('_') || line.text.includes('___')
    const hasBlankSpaces = line.text.includes(' ') && line.text.trim().length < 10
    
    if (hasSignatureKeyword || hasUnderscores || hasBlankSpaces) {
      areas.push({
        type: 'signature',
        x: width * 0.3,
        y: line.y,
        width: width * 0.4,
        height: 20,
        confidence: hasSignatureKeyword ? 'high' : 'medium',
        text: line.text
      })
    }
  })
  
  return areas
}

// Detect potential date areas
const detectDateAreas = (textContent, width, height) => {
  const areas = []
  
  // Look for date-related patterns
  const dateKeywords = ['date', 'before', 'day', 'month', 'year']
  
  textContent.lines.forEach(line => {
    const lowerText = line.text.toLowerCase()
    
    // Check if line contains date-related keywords
    const hasDateKeyword = dateKeywords.some(keyword => 
      lowerText.includes(keyword)
    )
    
    // Check for date patterns like "before the ___ day of ___ ___"
    const hasDatePattern = /before the.*day of.*/.test(line.text)
    
    if (hasDateKeyword || hasDatePattern) {
      areas.push({
        type: 'date',
        x: width * 0.2,
        y: line.y,
        width: width * 0.6,
        height: 20,
        confidence: hasDatePattern ? 'high' : 'medium',
        text: line.text
      })
    }
  })
  
  return areas
}

// Generate recommendations based on analysis
const generateRecommendations = (formFields, signatureAreas, dateAreas) => {
  const recommendations = []
  
  // Analyze form fields
  const textFields = formFields.filter(f => f.isTextField)
  const checkBoxes = formFields.filter(f => f.isCheckBox)
  
  if (textFields.length > 0) {
    recommendations.push(`Found ${textFields.length} text fields that can be filled automatically`)
  }
  
  if (checkBoxes.length > 0) {
    recommendations.push(`Found ${checkBoxes.length} checkboxes that can be checked automatically`)
  }
  
  if (signatureAreas.length > 0) {
    recommendations.push(`Detected ${signatureAreas.length} potential signature areas`)
  }
  
  if (dateAreas.length > 0) {
    recommendations.push(`Detected ${dateAreas.length} potential date areas`)
  }
  
  if (formFields.length === 0 && signatureAreas.length === 0) {
    recommendations.push('No form fields or signature areas detected. Will use overlay approach.')
  }
  
  return recommendations
}

// Get detailed analysis for a specific PDF
export const analyzePDF = async (file) => {
  console.log('Starting PDF analysis...')
  
  const result = await scanPDFStructure(file)
  
  if (result.success) {
    console.log('PDF Analysis Results:')
    console.log(`- Page count: ${result.pageCount}`)
    console.log(`- Page size: ${result.pageSize.width} x ${result.pageSize.height}`)
    console.log(`- Form fields: ${result.formFields.length}`)
    console.log(`- Signature areas: ${result.signatureAreas.length}`)
    console.log(`- Date areas: ${result.dateAreas.length}`)
    console.log('Recommendations:', result.recommendations)
  } else {
    console.error('PDF analysis failed:', result.error)
  }
  
  return result
} 