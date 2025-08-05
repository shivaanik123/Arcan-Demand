import React, { useState } from 'react'
import { Upload, FileText, Calendar, User, Download, CheckCircle, AlertCircle } from 'lucide-react'
import FileUpload from './components/FileUpload'
import SignatureForm from './components/SignatureForm'
import DocumentPreview from './components/DocumentPreview'
import { processDocuments } from './utils/documentProcessor'

function App() {
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [signatureData, setSignatureData] = useState({
    name: '',
    date: new Date().toISOString().split('T')[0],
    useCurrentDate: true
  })
  const [processedDocuments, setProcessedDocuments] = useState([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState('')

  const handleFileUpload = (files) => {
    setUploadedFiles(files)
    setError('')
  }

  const handleSignatureChange = (data) => {
    setSignatureData(data)
  }

  const handleGenerateLetters = async () => {
    if (uploadedFiles.length === 0) {
      setError('Please upload at least one file')
      return
    }

    if (!signatureData.name.trim()) {
      setError('Please enter a signature name')
      return
    }

    setIsProcessing(true)
    setError('')

    try {
      const processed = await processDocuments(uploadedFiles, signatureData)
      setProcessedDocuments(processed)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Signature Letter Generator
          </h1>
          <p className="text-gray-600 text-lg">
            Upload documents and generate letters with custom signatures
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
            <AlertCircle className="text-red-500" size={20} />
            <span className="text-red-700">{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Upload and Form */}
          <div className="space-y-6">
            {/* File Upload */}
            <div className="card">
              <div className="flex items-center gap-2 mb-4">
                <Upload className="text-primary-600" size={24} />
                <h2 className="text-xl font-semibold">Upload Documents</h2>
              </div>
              <FileUpload onFilesUploaded={handleFileUpload} />
              {uploadedFiles.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm text-gray-600 mb-2">
                    {uploadedFiles.length} file(s) uploaded
                  </p>
                  <div className="space-y-1">
                    {uploadedFiles.map((file, index) => (
                      <div key={index} className="flex items-center gap-2 text-sm">
                        <FileText size={16} className="text-gray-500" />
                        <span className="text-gray-700">{file.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Signature Form */}
            <div className="card">
              <div className="flex items-center gap-2 mb-4">
                <User className="text-primary-600" size={24} />
                <h2 className="text-xl font-semibold">Signature Details</h2>
              </div>
              <SignatureForm 
                data={signatureData}
                onChange={handleSignatureChange}
              />
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerateLetters}
              disabled={isProcessing || uploadedFiles.length === 0}
              className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isProcessing ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Processing...
                </>
              ) : (
                <>
                  <CheckCircle size={20} />
                  Generate Letters
                </>
              )}
            </button>
          </div>

          {/* Right Column - Preview */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="text-primary-600" size={24} />
              <h2 className="text-xl font-semibold">Generated Documents</h2>
            </div>
            
            {processedDocuments.length > 0 ? (
              <DocumentPreview 
                documents={processedDocuments}
                signatureData={signatureData}
              />
            ) : (
              <div className="text-center py-12 text-gray-500">
                <FileText size={48} className="mx-auto mb-4 opacity-50" />
                <p>Upload files and generate letters to see previews here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App 