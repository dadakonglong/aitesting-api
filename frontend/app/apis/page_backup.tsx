'use client'

import { useState, useEffect } from 'react'
import { Database, Search, Tag, ChevronDown, ChevronUp, Info, Trash2, Play, CheckCircle, XCircle } from 'lucide-react'

interface API {
    id: string
    name: string
    method: string
    path: string
    description: string
    base_url?: string
    parameters?: any[]
    request_body?: any
    headers?: Record<string, string>  // 新增:headers字段
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
    const [deletingId, setDeletingId] = useState<string | null>(null)
    const [executingId, setExecutingId] = useState<string | null>(null)
    const [executionResults, setExecutionResults] = useState<Record<string, any>>({})
    const [activeResultTab, setActiveResultTab] = useState<Record<string, string>>({}) // key: apiId, value: tab name
    const [environments, setEnvironments] = useState<any[]>([])
    const [selectedEnvId, setSelectedEnvId] = useState<number | null>(null)
    const [editableParams, setEditableParams] = useState<Record<string, string>>({}) // key: apiId, value: JSON string
    const [editableHeaders, setEditableHeaders] = useState<Record<string, Record<string, string>>>({}) // key: apiId, value: headers object
    const [activeApiTab, setActiveApiTab] = useState<Record<string, string>>({}) // key: apiId, value: tab name
    const [confirmDelete, setConfirmDelete] = useState<{ show: boolean, id: string, name: string }>({ show: false, id: '', name: '' })

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

    const deleteApi = async (id: string) => {
        setDeletingId(id)
        setConfirmDelete({ show: false, id: '', name: '' })
        try {
            await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/apis/${id}`, { method: 'DELETE' })
            fetchAPIs()
        } catch (err) {
            console.error(err)
        } finally {
            setDeletingId(null)
        }
    }

    const fetchEnvironments = async (projectId: string) => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/projects/${projectId}/environments`)
            if (response.ok) {
                const data = await response.json()
                setEnvironments(data)
                const defaultEnv = data.find((e: any) => e.is_default) || data[0]
                if (defaultEnv) setSelectedEnvId(defaultEnv.id)
            }
        } catch (error) {
            console.error('获取环境配置失败:', error)
        }
    }

    const handleExecuteApi = async (api: API) => {
        setExecutingId(api.id)
        const env = environments.find(e => e.id === selectedEnvId)
        const baseUrl = env ? env.base_url : (api.base_url || 'http://localhost:8000')

        try {
            // 获取参数:优先使用用户编辑的参数,否则使用API默认参数
            let params = api.request_body || {}
            if (editableParams[api.id]) {
                try {
                    params = JSON.parse(editableParams[api.id])
                } catch (e) {
                    throw new Error('参数格式错误,请检查JSON格式')
                }
            }

            // 构造请求体
            const requestBody = {
                environment: env?.env_name || 'test',
                base_url: baseUrl,
                steps: [{
                    step_order: 1,
                    api_id: api.id,
                    api_name: api.name,
                    api_path: api.path,
                    api_method: api.method,
                    description: api.description,
                    params: params,
                    headers: {},
                    param_mappings: [],
                    assertions: [],
                    expected_status: 200,
                    timeout: 30
                }]
            }

            const response = await fetch(`${process.env.NEXT_PUBLIC_EXEC_API_URL}/api/v1/executions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            })

            if (response.ok) {
                const execution = await response.json()
                setExecutionResults(prev => ({ ...prev, [api.id]: execution.results[0] }))
                setActiveResultTab(prev => ({ ...prev, [api.id]: '响应体' }))
                // 自动展开该API
                setExpandedApiIds(prev => new Set(prev).add(api.id))
            } else {
                const errData = await response.json().catch(() => ({}))
                throw new Error(errData.detail || '接口执行失败')
            }
        } catch (error: any) {
            setExecutionResults(prev => ({
                ...prev,
                [api.id]: {
                    success: false,
                    error: error.message || '执行失败',
                    status_code: 'Error'
                }
            }))
        } finally {
            setExecutingId(null)
        }
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
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handleExecuteApi(api); }}
                                        disabled={executingId === api.id}
                                        style={{
                                            padding: '0.5rem 0.75rem',
                                            background: executingId === api.id ? '#D1D5DB' : '#DBEAFE',
                                            color: executingId === api.id ? '#6B7280' : '#3B82F6',
                                            border: 'none',
                                            borderRadius: '0.5rem',
                                            cursor: executingId === api.id ? 'not-allowed' : 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.25rem',
                                            fontSize: '0.75rem',
                                            fontWeight: '500'
                                        }}
                                    >
                                        <Play size={14} fill="currentColor" />
                                        {executingId === api.id ? '执行中...' : '执行'}
                                    </button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); setConfirmDelete({ show: true, id: api.id, name: api.name }); }}
                                        disabled={deletingId === api.id}
                                        style={{
                                            padding: '0.5rem',
                                            background: deletingId === api.id ? '#D1D5DB' : '#FEE2E2',
                                            color: '#DC2626',
                                            border: 'none',
                                            borderRadius: '0.5rem',
                                            cursor: deletingId === api.id ? 'not-allowed' : 'pointer'
                                        }}
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                    {expandedApiIds.has(api.id) ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                </div>
                            </div>

                            {expandedApiIds.has(api.id) && (
                                <div onClick={(e) => e.stopPropagation()} style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid #F3F4F6' }}>
                                    {/* 标签页导航 */}
                                    <div style={{ display: 'flex', borderBottom: '2px solid #E5E7EB', marginBottom: '1.5rem' }}>
                                        {['Headers', 'Body', 'Params', '执行结果'].map(tab => (
                                            <button
                                                key={tab}
                                                onClick={() => setActiveApiTab(prev => ({ ...prev, [api.id]: tab }))}
                                                style={{
                                                    padding: '0.75rem 1.5rem',
                                                    background: (activeApiTab[api.id] || 'Headers') === tab ? 'white' : 'transparent',
                                                    color: (activeApiTab[api.id] || 'Headers') === tab ? '#3B82F6' : '#6B7280',
                                                    border: 'none',
                                                    borderBottom: (activeApiTab[api.id] || 'Headers') === tab ? '2px solid #3B82F6' : 'none',
                                                    cursor: 'pointer',
                                                    fontWeight: (activeApiTab[api.id] || 'Headers') === tab ? '600' : '400',
                                                    fontSize: '0.875rem',
                                                    transition: 'all 0.2s',
                                                    marginBottom: '-2px'
                                                }}
                                            >
                                                {tab}
                                                {tab === 'Params' && api.parameters && api.parameters.length > 0 && (
                                                    <span style={{ marginLeft: '0.5rem', background: '#E5E7EB', padding: '0.125rem 0.5rem', borderRadius: '1rem', fontSize: '0.7rem' }}>
                                                        {api.parameters.length}
                                                    </span>
                                                )}
                                            </button>
                                        ))}
                                    </div>

                                    {/* Headers 标签页 */}
                                    {(activeApiTab[api.id] || 'Headers') === 'Headers' && (
                                        <div>
