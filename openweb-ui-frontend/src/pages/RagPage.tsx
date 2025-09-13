import { useState } from 'react'
import { Upload, FileText, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { RagFile } from '@/lib/types'

const RagPage = () => {
  const [files, setFiles] = useState<RagFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    try {
      const response = await api.uploadFile(file)
      const newFile: RagFile = {
        id: response.id,
        filename: response.filename,
        size: file.size,
        uploaded_at: new Date(),
      }
      setFiles(prev => [...prev, newFile])
    } catch (error) {
      console.error('Upload failed:', error)
    } finally {
      setIsUploading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    try {
      const results = await api.search(searchQuery)
      console.log('Search results:', results)
    } catch (error) {
      console.error('Search failed:', error)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b bg-background p-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold">RAG (Retrieval-Augmented Generation)</h1>
          <p className="text-muted-foreground">
            Upload documents and search through your knowledge base
          </p>
        </div>
      </div>

      {/* Upload Section */}
      <div className="p-6 border-b">
        <div className="max-w-4xl mx-auto">
          <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-8 text-center">
            <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">Upload Documents</h3>
            <p className="text-muted-foreground mb-4">
              Drag and drop files or click to browse
            </p>
            <input
              type="file"
              onChange={handleFileUpload}
              className="hidden"
              id="file-upload"
              accept=".pdf,.txt,.md,.doc,.docx"
            />
            <label htmlFor="file-upload">
              <Button disabled={isUploading} asChild>
                <span>
                  {isUploading ? 'Uploading...' : 'Choose File'}
                </span>
              </Button>
            </label>
          </div>
        </div>
      </div>

      {/* Search and Files */}
      <div className="flex-1 p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Search */}
          <div className="flex space-x-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search documents..."
              className="flex-1 px-3 py-2 border rounded-md"
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button onClick={handleSearch}>Search</Button>
          </div>

          {/* File List */}
          <div>
            <h3 className="text-lg font-medium mb-4">Uploaded Files</h3>
            {files.length === 0 ? (
              <p className="text-muted-foreground">No files uploaded yet</p>
            ) : (
              <div className="space-y-2">
                {files.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between p-3 bg-muted rounded-md"
                  >
                    <div className="flex items-center space-x-3">
                      <FileText className="h-5 w-5" />
                      <div>
                        <p className="font-medium">{file.filename}</p>
                        <p className="text-sm text-muted-foreground">
                          {(file.size / 1024).toFixed(1)} KB • {file.uploaded_at.toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default RagPage