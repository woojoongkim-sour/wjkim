import { useState } from 'react'
import {
  hybridSearch,
  adaptiveRag,
  uploadDocument,
  listDocuments,
} from '../api/archive-client'
import type { SearchResult, Document } from '../api/archive-client'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: SearchResult[]
}

interface DocumentUploadState {
  file: File | null
  title: string
  description: string
  documentType: string
  tags: string
  isVersioned: boolean
  existingDocumentId?: number
}

export default function DocumentPage() {
  const [activeTab, setActiveTab] = useState<'search' | 'upload' | 'documents'>('search')
  const [customerId] = useState(1)
  
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchMode, setSearchMode] = useState<string>('')
  
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatQuery, setChatQuery] = useState('')
  const [isChatting, setIsChatting] = useState(false)
  const [crossSearch, setCrossSearch] = useState(false)
  
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoadingDocs, setIsLoadingDocs] = useState(false)
  
  const [uploadState, setUploadState] = useState<DocumentUploadState>({
    file: null,
    title: '',
    description: '',
    documentType: 'OPERATION_MANUAL',
    tags: '',
    isVersioned: false,
  })
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState(false)

  const handleSearch = async () => {
    if (!query.trim()) return
    
    setIsSearching(true)
    try {
      const result = await hybridSearch(query, customerId)
      setSearchResults(result.results)
      setSearchMode(result.search_mode)
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setIsSearching(false)
    }
  }

  const handleChat = async () => {
    if (!chatQuery.trim()) return
    
    const userMessage: ChatMessage = { role: 'user', content: chatQuery }
    setChatMessages(prev => [...prev, userMessage])
    setChatQuery('')
    setIsChatting(true)
    
    try {
      const result = await adaptiveRag(chatQuery, customerId, crossSearch)
      
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: result.response,
        sources: result.tool_results?.[0]?.results?.results,
      }
      setChatMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Chat failed:', error)
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: '죄송합니다. 응답 생성 중 오류가 발생했습니다.',
      }])
    } finally {
      setIsChatting(false)
    }
  }

  const loadDocuments = async () => {
    setIsLoadingDocs(true)
    try {
      const docs = await listDocuments(customerId)
      setDocuments(docs)
    } catch (error) {
      console.error('Failed to load documents:', error)
    } finally {
      setIsLoadingDocs(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadState(prev => ({
        ...prev,
        file,
        title: file.name.replace(/\.[^/.]+$/, ''),
      }))
    }
  }

  const handleUpload = async () => {
    if (!uploadState.file || !uploadState.title) {
      setUploadError('파일을 선택하고 제목을 입력해주세요.')
      return
    }
    
    setIsUploading(true)
    setUploadError(null)
    setUploadSuccess(false)
    
    try {
      await uploadDocument(uploadState.file, {
        title: uploadState.title,
        documentType: uploadState.documentType,
        customerId,
        description: uploadState.description,
        tags: uploadState.tags,
        isVersioned: uploadState.isVersioned,
        existingDocumentId: uploadState.existingDocumentId,
      })
      
      setUploadSuccess(true)
      setUploadState({
        file: null,
        title: '',
        description: '',
        documentType: 'OPERATION_MANUAL',
        tags: '',
        isVersioned: false,
      })
    } catch (error: any) {
      if (error.response?.status === 409) {
        setUploadError('동일한 파일이 이미 존재합니다.')
      } else {
        setUploadError('업로드 중 오류가 발생했습니다.')
      }
    } finally {
      setIsUploading(false)
    }
  }

  const renderSearchTab = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">문서 검색</h2>
        
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="검색어를 입력하세요..."
            className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button
            onClick={handleSearch}
            disabled={isSearching}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isSearching ? '검색 중...' : '검색'}
          </button>
        </div>
        
        {searchResults.length > 0 && (
          <div className="mt-4">
            <p className="text-sm text-gray-600 mb-2">
              {searchResults.length}건 검색됨 | 모드: {searchMode}
            </p>
            <div className="space-y-4">
              {searchResults.map((result) => (
                <div key={result.chunk_id} className="border rounded-lg p-4">
                  <h3 className="font-medium text-blue-600">{result.document_title}</h3>
                  {result.section_title && (
                    <p className="text-sm text-gray-500">섹션: {result.section_title}</p>
                  )}
                  <p className="mt-2 text-gray-700">{result.content}</p>
                  <div className="mt-2 flex gap-4 text-xs text-gray-500">
                    <span>Score: {result.score.toFixed(4)}</span>
                    {result.dense_score && <span>Dense: {result.dense_score.toFixed(3)}</span>}
                    {result.keyword_score && <span>Keyword: {result.keyword_score.toFixed(2)}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">AI 채팅</h2>
        
        <div className="flex items-center gap-4 mb-4">
          <input
            type="text"
            value={chatQuery}
            onChange={(e) => setChatQuery(e.target.value)}
            placeholder="질문을 입력하세요..."
            className="flex-1 px-4 py-2 border rounded-lg"
            onKeyDown={(e) => e.key === 'Enter' && handleChat()}
          />
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={crossSearch}
              onChange={(e) => setCrossSearch(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">크로스 검색</span>
          </label>
          <button
            onClick={handleChat}
            disabled={isChatting}
            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {isChatting ? '생성 중...' : '질문'}
          </button>
        </div>
        
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {chatMessages.map((msg, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-lg ${
                msg.role === 'user' ? 'bg-blue-100 ml-8' : 'bg-gray-100 mr-8'
              }`}
            >
              <p className="font-medium text-sm mb-1">
                {msg.role === 'user' ? '사용자' : 'AI 어시스턴트'}
              </p>
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 text-xs text-gray-500">
                  출처: {msg.sources.map(s => s.document_title).join(', ')}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  const renderUploadTab = () => (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold mb-4">문서 업로드</h2>
      
      {uploadError && (
        <div className="mb-4 p-4 bg-red-100 text-red-700 rounded-lg">{uploadError}</div>
      )}
      
      {uploadSuccess && (
        <div className="mb-4 p-4 bg-green-100 text-green-700 rounded-lg">
          문서가 성공적으로 업로드되었습니다.
        </div>
      )}
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">파일 선택</label>
          <input
            type="file"
            onChange={handleFileChange}
            className="w-full px-4 py-2 border rounded-lg"
            accept=".pdf,.docx,.doc,.txt,.pptx,.ppt,.xlsx,.xls,.hwp,.hwpx,.csv"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-1">제목</label>
          <input
            type="text"
            value={uploadState.title}
            onChange={(e) => setUploadState(prev => ({ ...prev, title: e.target.value }))}
            className="w-full px-4 py-2 border rounded-lg"
            placeholder="문서 제목"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-1">설명</label>
          <textarea
            value={uploadState.description}
            onChange={(e) => setUploadState(prev => ({ ...prev, description: e.target.value }))}
            className="w-full px-4 py-2 border rounded-lg"
            rows={3}
            placeholder="문서 설명 (선택사항)"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-1">문서 유형</label>
          <select
            value={uploadState.documentType}
            onChange={(e) => setUploadState(prev => ({ ...prev, documentType: e.target.value }))}
            className="w-full px-4 py-2 border rounded-lg"
          >
            <option value="OPERATION_MANUAL">운영 매뉴얼</option>
            <option value="INCIDENT_REPORT">장애 보고서</option>
            <option value="WORK_RESULT">작업 결과서</option>
            <option value="EMERGENCY_CONTACT">비상 연락망</option>
            <option value="STARTUP_PROCEDURE">기동 절차서</option>
            <option value="SLA">SLA 문서</option>
            <option value="RESOURCE_STATUS">자원 현황표</option>
            <option value="CONFIGURATION">구성도</option>
            <option value="MONTHLY_REPORT">월 보고서</option>
            <option value="RFP">제안 요청서</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-1">태그</label>
          <input
            type="text"
            value={uploadState.tags}
            onChange={(e) => setUploadState(prev => ({ ...prev, tags: e.target.value }))}
            className="w-full px-4 py-2 border rounded-lg"
            placeholder="쉼표로 구분된 태그"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="isVersioned"
            checked={uploadState.isVersioned}
            onChange={(e) => setUploadState(prev => ({ ...prev, isVersioned: e.target.checked }))}
            className="rounded"
          />
          <label htmlFor="isVersioned" className="text-sm">버전 관리 활성화</label>
        </div>
        
        <button
          onClick={handleUpload}
          disabled={isUploading || !uploadState.file}
          className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {isUploading ? '업로드 중...' : '업로드'}
        </button>
      </div>
    </div>
  )

  const renderDocumentsTab = () => (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">문서 목록</h2>
        <button
          onClick={loadDocuments}
          className="px-4 py-2 text-blue-600 border border-blue-600 rounded-lg hover:bg-blue-50"
        >
          새로고침
        </button>
      </div>
      
      {isLoadingDocs ? (
        <p className="text-gray-500">로딩 중...</p>
      ) : documents.length === 0 ? (
        <p className="text-gray-500">문서가 없습니다.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">제목</th>
                <th className="px-4 py-2 text-left">유형</th>
                <th className="px-4 py-2 text-left">상태</th>
                <th className="px-4 py-2 text-left">버전</th>
                <th className="px-4 py-2 text-left">생성일</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-t">
                  <td className="px-4 py-2">{doc.title}</td>
                  <td className="px-4 py-2">{doc.document_type}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      doc.processing_status === 'completed' ? 'bg-green-100 text-green-700' :
                      doc.processing_status === 'failed' ? 'bg-red-100 text-red-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {doc.processing_status}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {doc.version || 1}
                    {doc.is_latest && <span className="ml-1 text-xs text-green-600">(최신)</span>}
                  </td>
                  <td className="px-4 py-2">{new Date(doc.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">문서 관리</h1>
      
      <div className="flex gap-4 mb-6 border-b">
        <button
          onClick={() => setActiveTab('search')}
          className={`px-4 py-2 font-medium ${
            activeTab === 'search' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'
          }`}
        >
          검색 & 채팅
        </button>
        <button
          onClick={() => setActiveTab('upload')}
          className={`px-4 py-2 font-medium ${
            activeTab === 'upload' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'
          }`}
        >
          문서 업로드
        </button>
        <button
          onClick={() => {
            setActiveTab('documents')
            loadDocuments()
          }}
          className={`px-4 py-2 font-medium ${
            activeTab === 'documents' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'
          }`}
        >
          문서 목록
        </button>
      </div>
      
      {activeTab === 'search' && renderSearchTab()}
      {activeTab === 'upload' && renderUploadTab()}
      {activeTab === 'documents' && renderDocumentsTab()}
    </div>
  )
}
