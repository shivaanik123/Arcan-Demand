import React from 'react'
import { Download, FileText, Eye, CheckCircle } from 'lucide-react'
import { saveAs } from 'file-saver'

const DocumentPreview = ({ documents, signatureData }) => {
  const handleDownload = (document, index) => {
    const blob = new Blob([document.data], { type: 'application/pdf' })
    const filename = `signed_${document.originalName.replace('.pdf', '')}_${signatureData.name.replace(/\s+/g, '_')}.pdf`
    saveAs(blob, filename)
  }

  const handleDownloadAll = () => {
    documents.forEach((document, index) => {
      setTimeout(() => {
        handleDownload(document, index)
      }, index * 500) // Stagger downloads
    })
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle className="text-green-600" size={20} />
          <span className="font-medium text-green-800">
            Successfully processed {documents.length} document(s)
          </span>
        </div>
        <p className="text-sm text-green-700">
          Signature: <span className="font-medium">{signatureData.name}</span> | 
          Date: <span className="font-medium">{signatureData.useCurrentDate ? 'Current Date' : signatureData.date}</span>
        </p>
      </div>

      {/* Download All Button */}
      <button
        onClick={handleDownloadAll}
        className="w-full btn-primary flex items-center justify-center gap-2"
      >
        <Download size={20} />
        Download All Documents
      </button>

      {/* Document List */}
      <div className="space-y-3">
        <h4 className="font-medium text-gray-700">Processed Documents:</h4>
        
        {documents.map((document, index) => (
          <div
            key={index}
            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
          >
            <div className="flex items-center gap-3">
              <FileText size={20} className="text-gray-500" />
              <div>
                <p className="font-medium text-gray-900">
                  {document.originalName}
                </p>
                <p className="text-sm text-gray-600">
                  Signed by {signatureData.name}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleDownload(document, index)}
                className="btn-secondary text-sm px-3 py-1"
              >
                <Download size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Processing Details */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h4 className="font-medium text-blue-800 mb-2">What was processed:</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• Added signature: {signatureData.name}</li>
          <li>• Applied date: {signatureData.useCurrentDate ? 'Current date' : signatureData.date}</li>
          <li>• Filled in blank fields automatically</li>
          <li>• Added checkboxes where applicable</li>
          <li>• Maintained original document formatting</li>
        </ul>
      </div>
    </div>
  )
}

export default DocumentPreview 