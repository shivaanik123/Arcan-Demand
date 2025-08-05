import React, { useRef, useState } from 'react'
import { Upload, X, FileText, Archive, CheckCircle } from 'lucide-react'
import JSZip from 'jszip'

const FileUpload = ({ onFilesUploaded }) => {
  const fileInputRef = useRef(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [extractedFiles, setExtractedFiles] = useState([])

  const processFiles = async (files) => {
    setIsProcessing(true)
    const allFiles = []
    const extractedFileList = []

    for (const file of files) {
      if (file.type === 'application/zip' || file.name.endsWith('.zip')) {
        // Process ZIP file
        try {
          const zip = new JSZip()
          const zipContent = await zip.loadAsync(file)
          
          for (const [filename, zipEntry] of Object.entries(zipContent.files)) {
            if (!zipEntry.dir && (filename.endsWith('.pdf') || filename.endsWith('.PDF'))) {
              const blob = await zipEntry.async('blob')
              const pdfFile = new File([blob], filename, { type: 'application/pdf' })
              allFiles.push(pdfFile)
              extractedFileList.push({
                name: filename,
                size: blob.size,
                type: 'pdf',
                originalZip: file.name
              })
            }
          }
        } catch (error) {
          console.error('Error processing ZIP file:', error)
        }
      } else if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
        // Direct PDF file
        allFiles.push(file)
        extractedFileList.push({
          name: file.name,
          size: file.size,
          type: 'pdf',
          originalZip: null
        })
      }
    }

    setIsProcessing(false)
    setExtractedFiles(extractedFileList)
    onFilesUploaded(allFiles)
  }

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files)
    if (files.length > 0) {
      processFiles(files)
    }
  }

  const handleDrop = (event) => {
    event.preventDefault()
    setIsDragOver(false)
    
    const files = Array.from(event.dataTransfer.files)
    if (files.length > 0) {
      processFiles(files)
    }
  }

  const handleDragOver = (event) => {
    event.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (event) => {
    event.preventDefault()
    setIsDragOver(false)
  }

  const clearFiles = () => {
    setExtractedFiles([])
    onFilesUploaded([])
  }

  return (
    <div className="space-y-4">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors duration-200 ${
          isDragOver
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div className="flex flex-col items-center gap-4">
          {isProcessing ? (
            <>
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
              <p className="text-gray-600">Processing files...</p>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 text-gray-500">
                <Upload size={24} />
                <Archive size={24} />
                <FileText size={24} />
              </div>
              <div>
                <p className="text-lg font-medium text-gray-900 mb-2">
                  Drop files here or click to browse
                </p>
                <p className="text-sm text-gray-600">
                  Supports ZIP files with PDFs or individual PDF files
                </p>
              </div>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="btn-primary"
              >
                Choose Files
              </button>
            </>
          )}
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".zip,.pdf,.PDF"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Extracted Files List */}
      {extractedFiles.length > 0 && (
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium text-gray-900">
              Extracted PDF Files ({extractedFiles.length})
            </h3>
            <button
              onClick={clearFiles}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear All
            </button>
          </div>
          
          <div className="space-y-2">
            {extractedFiles.map((file, index) => (
              <div key={index} className="flex items-center gap-3 p-2 bg-white rounded border">
                <CheckCircle size={16} className="text-green-500" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(file.size / 1024).toFixed(1)} KB
                    {file.originalZip && ` • From: ${file.originalZip}`}
                  </p>
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-3 p-2 bg-blue-50 rounded border border-blue-200">
            <p className="text-xs text-blue-700">
              Each PDF will be processed individually with signatures and dates.
            </p>
          </div>
        </div>
      )}

      <div className="text-xs text-gray-500 text-center">
        <p>Accepted formats: ZIP files containing PDFs, or individual PDF files</p>
        <p>Maximum file size: 50MB per file</p>
      </div>
    </div>
  )
}

export default FileUpload 