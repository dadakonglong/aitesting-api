'use client'

import { useState } from 'react'
import { Upload, Link as LinkIcon, FileJson, FileCode, CheckCircle } from 'lucide-react'

export default function ImportPage() {
    const [importType, setImportType] = useState<'swagger' | 'postman' | 'har'>('swagger')
    const [swaggerMode, setSwaggerMode] = useState<'url' | 'file'>('url')
    const [swaggerUrl, setSwaggerUrl] = useState('')
    const [file, setFile] = useState<File | null>(null)
    const [projectId, setProjectId] = useState('default-project')
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
            formData.append('project_id', projectId)

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
            formData.append('project_id', projectId)

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
        <div style={{ padding: '1rem 0' }}>
            {/* 页面标题 */}
            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem', fontWeight: '700', color: '#111827', marginBottom: '0.5rem' }}>
                    📥 数据导入
                </h1>
                <p style={{ color: '#6B7280' }}>
                    从Swagger、Postman或HAR文件导入API定义
                </p>
            </div>

            <div style={{ maxWidth: '56rem', margin: '0 auto' }}>
                {/* 导入类型选择 */}
                <div style={{
                    background: 'rgba(255, 255, 255, 0.8)',
                    backdropFilter: 'blur(10px)',
                    borderRadius: '1rem',
                    padding: '2rem',
                    marginBottom: '2rem',
                    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.2)'
                }}>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#111827', marginBottom: '1.5rem' }}>
                        选择导入方式
                    </h2>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
                        {[
                            { type: 'swagger' as const, icon: <LinkIcon size={24} />, label: 'Swagger URL', desc: '在线Swagger文档' },
                            { type: 'postman' as const, icon: <FileJson size={24} />, label: 'Postman', desc: 'Collection文件' },
                            { type: 'har' as const, icon: <FileCode size={24} />, label: 'HAR文件', desc: '浏览器导出' }
                        ].map((item) => (
                            <button
                                key={item.type}
                                onClick={() => setImportType(item.type)}
                                style={{
                                    padding: '1.5rem',
                                    background: importType === item.type ? 'linear-gradient(to right, #2563EB, #4F46E5)' : 'white',
                                    color: importType === item.type ? 'white' : '#374151',
                                    border: importType === item.type ? 'none' : '2px solid #E5E7EB',
                                    borderRadius: '0.75rem',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    textAlign: 'center'
                                }}
                            >
                                <div style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'center' }}>
                                    {item.icon}
                                </div>
                                <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>{item.label}</div>
                                <div style={{ fontSize: '0.75rem', opacity: 0.8 }}>{item.desc}</div>
                            </button>
                        ))}
                    </div>

                    {/* 项目ID */}
                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.75rem' }}>
                            📁 项目ID
                        </label>
                        <input
                            type="text"
                            value={projectId}
                            onChange={(e) => setProjectId(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '0.75rem 1rem',
                                background: 'rgba(255, 255, 255, 0.9)',
                                border: '2px solid #E5E7EB',
                                borderRadius: '0.75rem',
                                outline: 'none'
                            }}
                            placeholder="default-project"
                        />
                    </div>

                    {/* Swagger 导入 */}
                    {importType === 'swagger' && (
                        <div style={{ marginBottom: '1.5rem' }}>
                            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
                                <button
                                    onClick={() => setSwaggerMode('url')}
                                    style={{
                                        padding: '0.5rem 1rem',
                                        background: swaggerMode === 'url' ? '#EEF2FF' : 'transparent',
                                        color: swaggerMode === 'url' ? '#4F46E5' : '#6B7280',
                                        border: swaggerMode === 'url' ? '1px solid #4F46E5' : '1px solid #E5E7EB',
                                        borderRadius: '0.5rem',
                                        cursor: 'pointer',
                                        fontWeight: '500'
                                    }}
                                >
                                    URL 导入
                                </button>
                                <button
                                    onClick={() => setSwaggerMode('file')}
                                    style={{
                                        padding: '0.5rem 1rem',
                                        background: swaggerMode === 'file' ? '#EEF2FF' : 'transparent',
                                        color: swaggerMode === 'file' ? '#4F46E5' : '#6B7280',
                                        border: swaggerMode === 'file' ? '1px solid #4F46E5' : '1px solid #E5E7EB',
                                        borderRadius: '0.5rem',
                                        cursor: 'pointer',
                                        fontWeight: '500'
                                    }}
                                >
                                    文件上传
                                </button>
                            </div>

                            {swaggerMode === 'url' ? (
                                <>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.75rem' }}>
                                        🔗 Swagger URL
                                    </label>
                                    <input
                                        type="url"
                                        value={swaggerUrl}
                                        onChange={(e) => setSwaggerUrl(e.target.value)}
                                        style={{
                                            width: '100%',
                                            padding: '0.75rem 1rem',
                                            background: 'white',
                                            border: '2px solid #E5E7EB',
                                            borderRadius: '0.75rem',
                                            outline: 'none'
                                        }}
                                        placeholder="https://petstore.swagger.io/v2/swagger.json"
                                    />
                                </>
                            ) : (
                                <>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.75rem' }}>
                                        📄 上传 Swagger JSON 文件
                                    </label>
                                    <div style={{
                                        border: '2px dashed #D1D5DB',
                                        borderRadius: '0.75rem',
                                        padding: '1.5rem',
                                        textAlign: 'center',
                                        background: 'rgba(249, 250, 251, 0.5)'
                                    }}>
                                        <Upload size={32} style={{ margin: '0 auto 0.5rem', color: '#9CA3AF' }} />
                                        <input
                                            type="file"
                                            accept=".json"
                                            onChange={(e) => setFile(e.target.files?.[0] || null)}
                                            style={{ display: 'none' }}
                                            id="swagger-file-upload"
                                        />
                                        <label
                                            htmlFor="swagger-file-upload"
                                            style={{
                                                display: 'inline-block',
                                                padding: '0.5rem 1rem',
                                                background: 'white',
                                                border: '1px solid #D1D5DB',
                                                borderRadius: '0.5rem',
                                                cursor: 'pointer',
                                                fontWeight: '500',
                                                color: '#374151'
                                            }}
                                        >
                                            选择 JSON 文件
                                        </label>
                                        {file && (
                                            <p style={{ marginTop: '0.5rem', color: '#6B7280', fontSize: '0.875rem' }}>
                                                已选择: {file.name}
                                            </p>
                                        )}
                                    </div>
                                </>
                            )}

                            <button
                                onClick={handleSwaggerImport}
                                disabled={loading}
                                style={{
                                    width: '100%',
                                    marginTop: '1rem',
                                    padding: '0.75rem 1.5rem',
                                    background: loading ? '#9CA3AF' : 'linear-gradient(to right, #2563EB, #4F46E5)',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '0.75rem',
                                    fontWeight: '600',
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    transition: 'all 0.2s'
                                }}
                            >
                                {loading ? '导入中...' : '开始导入'}
                            </button>
                        </div>
                    )}

                    {/* 文件上传 */}
                    {(importType === 'postman' || importType === 'har') && (
                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.75rem' }}>
                                📄 选择文件
                            </label>
                            <div style={{
                                border: '2px dashed #D1D5DB',
                                borderRadius: '0.75rem',
                                padding: '2rem',
                                textAlign: 'center',
                                background: 'rgba(249, 250, 251, 0.5)'
                            }}>
                                <Upload size={48} style={{ margin: '0 auto 1rem', color: '#9CA3AF' }} />
                                <input
                                    type="file"
                                    accept={importType === 'postman' ? '.json' : '.har'}
                                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                                    style={{ display: 'none' }}
                                    id="file-upload"
                                />
                                <label
                                    htmlFor="file-upload"
                                    style={{
                                        display: 'inline-block',
                                        padding: '0.5rem 1rem',
                                        background: 'white',
                                        border: '1px solid #D1D5DB',
                                        borderRadius: '0.5rem',
                                        cursor: 'pointer',
                                        fontWeight: '500',
                                        color: '#374151'
                                    }}
                                >
                                    选择文件
                                </label>
                                {file && (
                                    <p style={{ marginTop: '1rem', color: '#6B7280', fontSize: '0.875rem' }}>
                                        已选择: {file.name}
                                    </p>
                                )}
                            </div>
                            <button
                                onClick={handleFileImport}
                                disabled={loading || !file}
                                style={{
                                    width: '100%',
                                    marginTop: '1rem',
                                    padding: '0.75rem 1.5rem',
                                    background: (loading || !file) ? '#9CA3AF' : 'linear-gradient(to right, #2563EB, #4F46E5)',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '0.75rem',
                                    fontWeight: '600',
                                    cursor: (loading || !file) ? 'not-allowed' : 'pointer',
                                    transition: 'all 0.2s'
                                }}
                            >
                                {loading ? '导入中...' : '开始导入'}
                            </button>
                        </div>
                    )}
                </div>

                {/* 导入结果 */}
                {result && (
                    <div style={{
                        background: 'rgba(255, 255, 255, 0.8)',
                        backdropFilter: 'blur(10px)',
                        borderRadius: '1rem',
                        padding: '2rem',
                        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
                        border: '1px solid rgba(255, 255, 255, 0.2)'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem' }}>
                            <CheckCircle size={24} style={{ color: '#10B981', marginRight: '0.5rem' }} />
                            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#111827' }}>
                                导入成功！
                            </h3>
                        </div>
                        <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.5rem' }}>
                            <p style={{ fontSize: '0.875rem', color: '#6B7280', marginBottom: '0.5rem' }}>
                                <span style={{ fontWeight: '500' }}>项目ID：</span>{result.project_id}
                            </p>
                            <p style={{ fontSize: '0.875rem', color: '#6B7280', marginBottom: '0.5rem' }}>
                                <span style={{ fontWeight: '500' }}>导入接口数：</span>{result.indexed || result.total || 0} 个
                            </p>
                            <p style={{ fontSize: '0.875rem', color: '#6B7280' }}>
                                <span style={{ fontWeight: '500' }}>状态：</span>
                                <span style={{ color: '#10B981' }}>✓ 已索引到向量数据库</span>
                            </p>
                        </div>
                        <div style={{ marginTop: '1rem', textAlign: 'center' }}>
                            <a
                                href="/"
                                style={{
                                    display: 'inline-block',
                                    padding: '0.5rem 1rem',
                                    background: 'linear-gradient(to right, #2563EB, #4F46E5)',
                                    color: 'white',
                                    borderRadius: '0.5rem',
                                    textDecoration: 'none',
                                    fontWeight: '500'
                                }}
                            >
                                → 开始创建测试场景
                            </a>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
