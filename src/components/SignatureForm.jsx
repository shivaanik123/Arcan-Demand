import React from 'react'
import { User, Calendar, CheckSquare } from 'lucide-react'

const SignatureForm = ({ data, onChange }) => {
  const handleInputChange = (field, value) => {
    onChange({
      ...data,
      [field]: value
    })
  }

  const handleUseCurrentDateChange = (checked) => {
    onChange({
      ...data,
      useCurrentDate: checked,
      date: checked ? new Date().toISOString().split('T')[0] : data.date
    })
  }

  return (
    <div className="space-y-4">
      {/* Signature Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <div className="flex items-center gap-2">
            <User size={16} />
            Signature Name
          </div>
        </label>
        <input
          type="text"
          value={data.name}
          onChange={(e) => handleInputChange('name', e.target.value)}
          placeholder="Enter the name for the signature"
          className="input-field"
        />
      </div>

      {/* Date Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <div className="flex items-center gap-2">
            <Calendar size={16} />
            Date Format
          </div>
        </label>
        
        <div className="space-y-3">
          {/* Use Current Date Checkbox */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={data.useCurrentDate}
              onChange={(e) => handleUseCurrentDateChange(e.target.checked)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <CheckSquare size={16} className="text-gray-500" />
            <span className="text-sm text-gray-700">Use current date</span>
          </label>

          {/* Custom Date Input */}
          {!data.useCurrentDate && (
            <input
              type="date"
              value={data.date}
              onChange={(e) => handleInputChange('date', e.target.value)}
              className="input-field"
            />
          )}
          
          {/* Date Format Preview */}
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-600 mb-1">Date will be formatted as:</p>
            <p className="text-sm font-medium text-gray-800">
              "before the {data.useCurrentDate ? new Date().getDate() : new Date(data.date).getDate()} day of {data.useCurrentDate ? new Date().toLocaleDateString('en-US', { month: 'long' }) : new Date(data.date).toLocaleDateString('en-US', { month: 'long' })} {data.useCurrentDate ? new Date().getFullYear() : new Date(data.date).getFullYear()}"
            </p>
          </div>
        </div>
      </div>

      {/* Additional Options */}
      <div className="pt-4 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Additional Options</h4>
        
        <div className="space-y-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              defaultChecked
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700">Auto-fill blank fields</span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              defaultChecked
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700">Include checkboxes where applicable</span>
          </label>
        </div>
      </div>
    </div>
  )
}

export default SignatureForm 