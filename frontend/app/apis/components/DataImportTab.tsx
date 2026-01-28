'use client'

import { useState } from 'react'
import { Upload, Link as LinkIcon, FileJson, FileCode, CheckCircle } from 'lucide-react'
import { useProject } from '../../contexts/ProjectContext'

export default function DataImportTab() {
    const { currentProject } = useProject()
    const [importType, setImportType] = useState<'swagger' | 'postman' | 'har'>('swagger')
    const [swaggerMode, setSwaggerMode] = useState<'url' | 'file'>('url')
    const [swaggerUrl, setSwaggerUrl] = useState('')
    const [file, setFile] = useState<File | null>(null)
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<any>(null)

    const handleSwaggerImport = async () => {
        if (swaggerMode === 'url' && !swaggerUrl.trim()) {
            alert('请输入Swagger URL')
            return
        }
        if (swaggerMode === 'file' && !file) {
            alert('请选择Swagger JSON文件')
            return
        }

        setLoading(true)
        setResult(null)

        try {
            const formData = new FormData()
            formData.append('project_id', currentProject)

            if (swaggerMode === 'url') {
                formData.append('source', swaggerUrl)
            } else {
                formData.append('file', file!)
            }

            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/import/swagger`, {
                method: 'POST',
                body: formData,
            })

            if (!response.ok) throw new Error('导入失败')
            const data = await response.json()
            setResult(data)
        } catch (error: any) {
            alert(`错误: ${error.message}`)
        } finally {
            setLoading(false)
        }
    }

    const handleFileImport = async () => {
        if (!file) {
            alert('请选择文件')
            return
        }

        setLoading(true)
        setResult(null)

        try {
            const formData = new FormData()
            formData.append('file', file)
            formData.append('project_id', currentProject)

            const endpoint = importType === 'postman' ? 'postman' : 'har'
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/import/${endpoint}`, {
                method: 'POST',
                body: formData,
            })

            if (!response.ok) throw new Error('导入失败')
            const data = await response.json()
            setResult(data)
        } catch (error: any) {
            alert(`错误: ${error.message}`)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div>
            {/* 导入类型选择 */}
            <div style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
                    {[
                        { type: 'swagger', icon: FileJson, label: 'Swagger/OpenAPI' },
                        { type: 'postman', icon: FileCode, label: 'Postman Collection' },
                        { type: 'har', icon: Upload, label: 'HAR文件' }
                    ].map(({ type, icon: Icon, label }) => (
                        <button
                            key={type}
                            onClick={() => setImportType(type as any)}
                            style={{
                                flex: 1,
                                padding: '1rem',
                                border: importType === type ? '2px solid #667eea' : '2px solid #E5E7EB',
                                borderRadius: '0.75rem',
                                background: importType === type ? 'rgba(102, 126, 234, 0.1)' : 'white',
                                cursor: 'pointer',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                gap: '0.5rem',
                                transition: 'all 0.2s'
                            }}
                        >
                            <Icon size={24} style={{ color: importType === type ? '#667eea' : '#6B7280' }} />
                            <span style={{ fontSize: '0.875rem', fontWeight: '600', color: importType === type ? '#667eea' : '#374151' }}>
                                {label}
                            </span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Swagger导入 */}
            {importType === 'swagger' && (
                <div style={{ background: 'white', borderRadius: '0.75rem', padding: '1.5rem', border: '1px solid #E5E7EB' }}>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem' }}>导入Swagger/OpenAPI</h3>

                    <div style={{ marginBottom: '1rem' }}>
                        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                            <button
                                onClick={() => setSwaggerMode('url')}
                                style={{
                                    padding: '0.5rem 1rem',
                                    border: swaggerMode === 'url' ? '2px solid #667eea' : '1px solid #E5E7EB',
                                    borderRadius: '0.5rem',
                                    background: swaggerMode === 'url' ? 'rgba(102, 126, 234, 0.1)' : 'white',
                                    cursor: 'pointer',
                                    fontSize: '0.875rem',
                                    fontWeight: '500'
                                }}
                            >
                                URL导入
                            </button>
                            <button
                                onClick={() => setSwaggerMode('file')}
                                style={{
                                    padding: '0.5rem 1rem',
                                    border: swaggerMode === 'file' ? '2px solid #667eea' : '1px solid #E5E7EB',
                                    borderRadius: '0.5rem',
                                    background: swaggerMode === 'file' ? 'rgba(102, 126, 234, 0.1)' : 'white',
                                    cursor: 'pointer',
                                    fontSize: '0.875rem',
                                    fontWeight: '500'
                                }}
                            >
                                文件上传
                            </button>
                        </div>

                        {swaggerMode === 'url' ? (
                            <input
                                type="text"
                                value={swaggerUrl}
                                onChange={(e) => setSwaggerUrl(e.target.value)}
                                placeholder="https://example.com/swagger.json"
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid #E5E7EB',
                                    borderRadius: '0.5rem',
                                    fontSize: '0.875rem'
                                }}
                            />
                        ) : (
                            <input
                                type="file"
                                accept=".json,.yaml,.yml"
                                onChange={(e) => setFile(e.target.files?.[0] || null)}
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '1px solid #E5E7EB',
                                    borderRadius: '0.5rem',
                                    fontSize: '0.875rem'
                                }}
                            />
                        )}
                    </div>

                    <button
                        onClick={handleSwaggerImport}
                        disabled={loading}
                        style={{
                            padding: '0.75rem 1.5rem',
                            background: loading ? '#9CA3AF' : '#667eea',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.5rem',
                            fontSize: '0.875rem',
                            fontWeight: '600',
                            cursor: loading ? 'not-allowed' : 'pointer'
                        }}
                    >
                        {loading ? '导入中...' : '开始导入'}
                    </button>
                </div>
            )}

            {/* Postman/HAR导入 */}
            {(importType === 'postman' || importType === 'har') && (
                <div style={{ background: 'white', borderRadius: '0.75rem', padding: '1.5rem', border: '1px solid #E5E7EB' }}>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem' }}>
                        导入{importType === 'postman' ? 'Postman Collection' : 'HAR文件'}
                    </h3>

                    <input
                        type="file"
                        accept={importType === 'postman' ? '.json' : '.har'}
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                        style={{
                            width: '100%',
                            padding: '0.75rem',
                            border: '1px solid #E5E7EB',
                            borderRadius: '0.5rem',
                            fontSize: '0.875rem',
                            marginBottom: '1rem'
                        }}
                    />

                    <button
                        onClick={handleFileImport}
                        disabled={loading}
                        style={{
                            padding: '0.75rem 1.5rem',
                            background: loading ? '#9CA3AF' : '#667eea',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.5rem',
                            fontSize: '0.875rem',
                            fontWeight: '600',
                            cursor: loading ? 'not-allowed' : 'pointer'
                        }}
                    >
                        {loading ? '导入中...' : '开始导入'}
                    </button>
                </div>
            )}

            {/* 导入结果 */}
            {result && (
                <div style={{
                    marginTop: '2rem',
                    padding: '1.5rem',
                    background: '#F0FDF4',
                    border: '1px solid #86EFAC',
                    borderRadius: '0.75rem'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                        <CheckCircle size={20} style={{ color: '#16A34A' }} />
                        <h4 style={{ fontSize: '1rem', fontWeight: '600', color: '#16A34A' }}>导入成功!</h4>
                    </div>
                    <p style={{ fontSize: '0.875rem', color: '#166534' }}>
                        成功导入 {result.imported_count || result.count || 0} 个API
                    </p>
                    {result.message && (
                        <p style={{ fontSize: '0.875rem', color: '#166534', marginTop: '0.5rem' }}>
                            {result.message}
                        </p>
                    )}
                </div>
            )}
        </div>
    )
}
