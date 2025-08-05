import { PDFDocument, rgb, StandardFonts } from 'pdf-lib'

// Helper function to get current date components
const getCurrentDateComponents = () => {
  const now = new Date()
  return {
    day: now.getDate(),
    month: now.toLocaleDateString('en-US', { month: 'long' }),
    year: now.getFullYear(),
    fullDate: now.toLocaleDateString()
  }
}

// Helper function to get custom date components
const getCustomDateComponents = (dateString) => {
  const date = new Date(dateString)
  return {
    day: date.getDate(),
    month: date.toLocaleDateString('en-US', { month: 'long' }),
    year: date.getFullYear(),
    fullDate: date.toLocaleDateString()
  }
}

// Create a new PDF with original as background and signatures/dates as overlays
const createPDFWithOverlays = async (file, signatureData) => {
  const arrayBuffer = await file.arrayBuffer()
  
  // Create a new PDF document
  const newPdfDoc = await PDFDocument.create()
  
  // Try to embed the original PDF as a background
  let originalPdfEmbedded = false
  
  try {
    // Try different methods to load the original PDF
    const loadingMethods = [
      { name: 'Standard', options: {} },
      { name: 'Ignore Encryption', options: { ignoreEncryption: true } },
      { name: 'Update Metadata False', options: { ignoreEncryption: true, updateMetadata: false } }
    ]
    
    for (const method of loadingMethods) {
      try {
        console.log(`Trying to embed original PDF with ${method.name} method`)
        const originalPdfDoc = await PDFDocument.load(arrayBuffer, method.options)
        const [embeddedPdf] = await newPdfDoc.embedPdf(originalPdfDoc)
        
        // Create a new page with the same size as the original
        const originalPages = originalPdfDoc.getPages()
        if (originalPages.length > 0) {
          const originalPage = originalPages[0]
          const { width, height } = originalPage.getSize()
          
          const page = newPdfDoc.addPage([width, height])
          page.drawPage(embeddedPdf)
          
          // Add signature and date overlays
          const font = await newPdfDoc.embedFont(StandardFonts.Helvetica)
          const signatureText = signatureData.name
          
          const dateComponents = signatureData.useCurrentDate 
            ? getCurrentDateComponents()
            : getCustomDateComponents(signatureData.date)
          
          const dateText = `before the ${dateComponents.day} day of ${dateComponents.month} ${dateComponents.year}`
          
          // Add signature at multiple positions
          const signaturePositions = [
            { x: width * 0.3, y: height * 0.7 },
            { x: width * 0.6, y: height * 0.7 },
            { x: width * 0.45, y: height * 0.3 },
            { x: width - 200, y: 100 },
            { x: 100, y: height - 150 },
            { x: width * 0.2, y: height * 0.5 },
            { x: width * 0.5, y: height * 0.8 },
            { x: width * 0.1, y: height * 0.2 }
          ]
          
          signaturePositions.forEach((pos, index) => {
            page.drawText(signatureText, {
              x: pos.x,
              y: pos.y,
              size: 14,
              font: font,
              color: rgb(0, 0, 0)
            })
          })
          
          // Add date at multiple positions
          const datePositions = [
            { x: width * 0.2, y: height * 0.8 },
            { x: width * 0.2, y: height * 0.6 },
            { x: width * 0.2, y: height * 0.4 },
            { x: 100, y: height - 200 },
            { x: width * 0.3, y: height * 0.5 },
            { x: width * 0.1, y: height * 0.3 },
            { x: width * 0.4, y: height * 0.9 }
          ]
          
          datePositions.forEach((pos, index) => {
            page.drawText(dateText, {
              x: pos.x,
              y: pos.y,
              size: 12,
              font: font,
              color: rgb(0, 0, 0)
            })
          })
          
          originalPdfEmbedded = true
          console.log(`Successfully embedded original PDF with ${method.name} method`)
          break
        }
      } catch (error) {
        console.log(`${method.name} method failed:`, error.message)
      }
    }
  } catch (error) {
    console.log('Could not embed original PDF:', error.message)
  }
  
  // If we couldn't embed the original, create a template with the same name
  if (!originalPdfEmbedded) {
    console.log('Creating template with original filename')
    const page = newPdfDoc.addPage([612, 792])
    
    const font = await newPdfDoc.embedFont(StandardFonts.Helvetica)
    const { width, height } = page.getSize()
    
    // Add title
    page.drawText(`Signed Document: ${file.name}`, {
      x: 50,
      y: height - 50,
      size: 16,
      font: font,
      color: rgb(0, 0, 0)
    })
    
    // Add signature information
    page.drawText(`Signature: ${signatureData.name}`, {
      x: 50,
      y: height - 100,
      size: 14,
      font: font,
      color: rgb(0, 0, 0)
    })
    
    // Add date information
    const dateComponents = signatureData.useCurrentDate 
      ? getCurrentDateComponents()
      : getCustomDateComponents(signatureData.date)
    
    const dateText = `Date: before the ${dateComponents.day} day of ${dateComponents.month} ${dateComponents.year}`
    page.drawText(dateText, {
      x: 50,
      y: height - 130,
      size: 12,
      font: font,
      color: rgb(0, 0, 0)
    })
    
    // Add note
    page.drawText('Note: Original PDF could not be embedded due to security restrictions.', {
      x: 50,
      y: height - 200,
      size: 10,
      font: font,
      color: rgb(0.5, 0.5, 0.5)
    })
  }
  
  const pdfBytes = await newPdfDoc.save()
  
  return {
    originalName: file.name,
    data: pdfBytes,
    size: pdfBytes.length,
    method: originalPdfEmbedded ? 'Overlay' : 'Template',
    success: true
  }
}

// Create a signature template as fallback
const createSignatureTemplate = async (originalFileName, signatureData) => {
  const pdfDoc = await PDFDocument.create()
  const page = pdfDoc.addPage([612, 792])
  
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica)
  const { width, height } = page.getSize()
  
  // Get date components
  const dateComponents = signatureData.useCurrentDate 
    ? getCurrentDateComponents()
    : getCustomDateComponents(signatureData.date)
  
  // Add title
  page.drawText(`Signature Template for: ${originalFileName}`, {
    x: 50,
    y: height - 50,
    size: 16,
    font: font,
    color: rgb(0, 0, 0)
  })
  
  // Add signature information
  page.drawText(`Signature: ${signatureData.name}`, {
    x: 50,
    y: height - 100,
    size: 14,
    font: font,
    color: rgb(0, 0, 0)
  })
  
  // Add date information
  const dateText = `Date: before the ${dateComponents.day} day of ${dateComponents.month} ${dateComponents.year}`
  page.drawText(dateText, {
    x: 50,
    y: height - 130,
    size: 12,
    font: font,
    color: rgb(0, 0, 0)
  })
  
  const pdfBytes = await pdfDoc.save()
  
  return {
    originalName: originalFileName,
    data: pdfBytes,
    size: pdfBytes.length,
    method: 'Template',
    success: true
  }
}

export const processDocuments = async (files, signatureData) => {
  const processedDocuments = []

  for (const file of files) {
    console.log(`Processing file: ${file.name}`)
    
    try {
      // Create PDF with overlays
      const result = await createPDFWithOverlays(file, signatureData)
      processedDocuments.push(result)
      
      console.log(`Successfully processed ${file.name} using ${result.method} method`)
      
    } catch (error) {
      console.error(`Failed to process ${file.name}:`, error)
      
      // Create template as absolute last resort
      const templateDoc = await createSignatureTemplate(file.name, signatureData)
      processedDocuments.push(templateDoc)
      console.log(`Created template for ${file.name}`)
    }
  }

  return processedDocuments
}

// Helper function to create a simple signature image
export const createSignatureImage = (name, fontSize = 24) => {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  
  canvas.width = 200
  canvas.height = 60
  
  ctx.font = `${fontSize}px cursive`
  ctx.fillStyle = '#000000'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  
  ctx.fillText(name, 10, 30)
  
  return canvas.toDataURL()
} 