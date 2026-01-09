'use client'

import { useState, useEffect } from 'react'
import { Database, Search, Tag, ChevronDown, ChevronUp, Info } from 'lucide-react'

interface API {
    id: string
    name: string
    method: string
    path: string
    description: string
    base_url?: string
    parameters?: any[]
    request_body?: any
    tags: string[]
    project_id: string
}

export default function APIsPage() {
    const [apis, setApis] = useState<API[]>([])
    const [loading, setLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState('')
    const [selectedMethod, setSelectedMethod] = useState<string>('all')
    const [selectedProject, setSelectedProject] = useState<string>('all')
    const [expandedApiIds, setExpandedApiIds] = useState<Set<string>>(new Set())

    useEffect(() => {
        fetchAPIs()
    }, [])

    const fetchAPIs = async () => {
        setLoading(true)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/apis`)
            if (response.ok) {
                const data = await response.json()
                setApis(data.apis || [])
            }
        } catch (error) {
            console.error('获取API列表失败:', error)
        } finally {
            setLoading(false)
        }
    }

    const toggleExpand = (apiId: string) => {
        setExpandedApiIds(prev => {
            const next = new Set(prev)
            if (next.has(apiId)) next.delete(apiId)
            else next.add(apiId)
            return next
        })
    }

    const projects = Array.from(new Set(apis.map(api => api.project_id || 'default-project')))

    const filteredAPIs = apis.filter(api => {
        const matchesSearch = api.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            api.path.toLowerCase().includes(searchTerm.toLowerCase()) ||
            api.description.toLowerCase().includes(searchTerm.toLowerCase())
        const matchesMethod = selectedMethod === 'all' || api.method === selectedMethod
        const matchesProject = selectedProject === 'all' || (api.project_id || 'default-project') === selectedProject
        return matchesSearch && matchesMethod && matchesProject
    })

    const methodColors: Record<string, string> = {
        'GET': '#10B981',
        'POST': '#3B82F6',
        'PUT': '#F59E0B',
        'DELETE': '#EF4444',
        'PATCH': '#8B5CF6'
    }

    return (
        <div style={{ padding: '1rem 0' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem', fontWeight: '700', color: '#111827', marginBottom: '0.5rem' }}>
                    📚 API 列表
                </h1>
                <p style={{ color: '#6B7280' }}>
                    查看所有已导入的 API 接口
                </p>
            </div>

            <div style={{
                background: 'rgba(255, 255, 255, 0.8)',
                backdropFilter: 'blur(10px)',
                borderRadius: '1rem',
                padding: '1.5rem',
                marginBottom: '2rem',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
                border: '1px solid rgba(255, 255, 255, 0.2)'
            }}>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <div style={{ flex: '1', minWidth: '300px', position: 'relative' }}>
                        <Search size={20} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: '#9CA3AF' }} />
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            placeholder="搜索 API 名称、路径或描述..."
                            style={{
                                width: '100%',
                                padding: '0.75rem 1rem 0.75rem 3rem',
                                border: '2px solid #E5E7EB',
                                borderRadius: '0.75rem',
                                outline: 'none'
                            }}
                        />
                    </div>

                    <select
                        value={selectedMethod}
                        onChange={(e) => setSelectedMethod(e.target.value)}
                        style={{
                            padding: '0.75rem 1rem',
                            border: '2px solid #E5E7EB',
                            borderRadius: '0.75rem',
                            outline: 'none',
                            cursor: 'pointer'
                        }}
                    >
                        <option value="all">所有方法</option>
                        <option value="GET">GET</option>
                        <option value="POST">POST</option>
                        <option value="PUT">PUT</option>
                        <option value="DELETE">DELETE</option>
                        <option value="PATCH">PATCH</option>
                    </select>

                    <select
                        value={selectedProject}
                        onChange={(e) => setSelectedProject(e.target.value)}
                        style={{
                            padding: '0.75rem 1rem',
                            border: '2px solid #E5E7EB',
                            borderRadius: '0.75rem',
                            outline: 'none',
                            cursor: 'pointer',
                            minWidth: '150px'
                        }}
                    >
                        <option value="all">所有项目</option>
                        {projects.map(p => (
                            <option key={p} value={p}>{p}</option>
                        ))}
                    </select>
                </div>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: '#6B7280' }}>加载中...</div>
            ) : filteredAPIs.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem', background: 'white', borderRadius: '1rem' }}>
                    <Database size={48} style={{ margin: '0 auto 1rem', color: '#9CA3AF' }} />
                    <p style={{ color: '#6B7280' }}>暂无 API 数据</p>
                </div>
            ) : (
                <div style={{ display: 'grid', gap: '1rem' }}>
                    {filteredAPIs.map((api) => (
                        <div
                            key={api.id}
                            onClick={() => toggleExpand(api.id)}
                            style={{
                                background: 'white',
                                borderRadius: '1rem',
                                padding: '1.5rem',
                                border: expandedApiIds.has(api.id) ? '1px solid #3B82F6' : '1px solid #E5E7EB',
                                cursor: 'pointer',
                                transition: 'all 0.2s'
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                                <span style={{
                                    padding: '0.25rem 0.75rem',
                                    background: methodColors[api.method] || '#6B7280',
                                    color: 'white',
                                    borderRadius: '0.375rem',
                                    fontSize: '0.75rem',
                                    fontWeight: '600'
                                }}>
                                    {api.method}
                                </span>
                                <code style={{ fontSize: '0.875rem', color: '#374151' }}>
                                    {api.base_url && <span style={{ color: '#9CA3AF', marginRight: '0.25rem' }}>{api.base_url}</span>}
                                    {api.path}
                                </code>
                            </div>

                            <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem' }}>{api.name}</h3>
                            <p style={{ fontSize: '0.875rem', color: '#6B7280', marginBottom: '1rem' }}>{api.description}</p>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                                {api.parameters && api.parameters.length > 0 && (
                                    <span style={{ fontSize: '0.75rem', color: '#059669', background: '#ECFDF5', padding: '0.25rem 0.5rem', borderRadius: '0.375rem' }}>
                                        ✓ {api.parameters.length} 个参数
                                    </span>
                                )}
                                {api.request_body && Object.keys(api.request_body).length > 0 && (
                                    <span style={{ fontSize: '0.75rem', color: '#2563EB', background: '#EFF6FF', padding: '0.25rem 0.5rem', borderRadius: '0.375rem' }}>
                                        ✓ 已定义 RequestBody
                                    </span>
                                )}
                                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <span style={{ fontSize: '0.75rem', color: '#6B7280', background: '#F3F4F6', padding: '0.2rem 0.6rem', borderRadius: '1rem' }}>
                                        {api.project_id || 'default-project'}
                                    </span>
                                    {expandedApiIds.has(api.id) ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                </div>
                            </div>

                            {expandedApiIds.has(api.id) && (
                                <div onClick={(e) => e.stopPropagation()} style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid #F3F4F6' }}>
                                    {api.parameters && api.parameters.length > 0 && (
                                        <div style={{ marginBottom: '1.5rem' }}>
                                            <h4 style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.75rem' }}>请求参数</h4>
                                            <div style={{ border: '1px solid #E5E7EB', borderRadius: '0.5rem', overflow: 'hidden' }}>
                                                <table style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse' }}>
                                                    <thead style={{ background: '#F9FAFB' }}>
                                                        <tr>
                                                            <th style={{ textAlign: 'left', padding: '0.5rem 0.75rem' }}>参数名</th>
                                                            <th style={{ textAlign: 'left', padding: '0.5rem 0.75rem' }}>位置</th>
                                                            <th style={{ textAlign: 'left', padding: '0.5rem 0.75rem' }}>类型</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {api.parameters.map((p, i) => (
                                                            <tr key={i} style={{ borderTop: '1px solid #F3F4F6' }}>
                                                                <td style={{ padding: '0.5rem 0.75rem', fontWeight: '500' }}>{p.name}</td>
                                                                <td style={{ padding: '0.5rem 0.75rem' }}>{p.in}</td>
                                                                <td style={{ padding: '0.5rem 0.75rem' }}>{p.schema?.type || 'string'}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    )}
                                    {api.request_body && Object.keys(api.request_body).length > 0 && (
                                        <div>
                                            <h4 style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.75rem' }}>请求体 (RequestBody)</h4>
                                            <pre style={{ background: '#F8FAFC', padding: '1rem', borderRadius: '0.5rem', fontSize: '0.75rem', border: '1px solid #E2E8F0' }}>
                                                {JSON.stringify(api.request_body, null, 2)}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
