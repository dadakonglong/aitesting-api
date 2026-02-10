'use client'

import { useState, useEffect } from 'react'
import { Database, Search, Tag, ChevronDown, ChevronUp, Info, Trash2, Play, CheckCircle, XCircle, Globe, Plus, Code, Edit2 } from 'lucide-react'
import { useProject } from '../contexts/ProjectContext'

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

export default function APIListContent() {
    const { currentProject } = useProject()
    const [apis, setApis] = useState<API[]>([])

    const [loading, setLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState('')
    const [selectedMethod, setSelectedMethod] = useState<string>('all')
    const [expandedApiIds, setExpandedApiIds] = useState<Set<string>>(new Set())
    const [deletingId, setDeletingId] = useState<string | null>(null)
    const [executingId, setExecutingId] = useState<string | null>(null)
    const [executionResults, setExecutionResults] = useState<Record<string, any>>({})
    const [activeResultTab, setActiveResultTab] = useState<Record<string, string>>({}) // key: apiId, value: tab name
    const [environments, setEnvironments] = useState<any[]>([])
    const [selectedEnvId, setSelectedEnvId] = useState<number | null>(null)
    const [editableParams, setEditableParams] = useState<Record<string, string>>({}) // key: apiId, value: JSON string
    const [editableHeaders, setEditableHeaders] = useState<Record<string, string>>({}) // key: apiId, value: JSON string
    const [editableUrlParams, setEditableUrlParams] = useState<Record<string, string>>({}) // key: apiId, value: JSON string
    const [activeApiTab, setActiveApiTab] = useState<Record<string, string>>({}) // key: apiId, value: tab name
    const [confirmDelete, setConfirmDelete] = useState<{ show: boolean, id: string, name: string }>({ show: false, id: '', name: '' })
    const [showAddModal, setShowAddModal] = useState(false)
    const [isEditing, setIsEditing] = useState(false)
    const [editingApiId, setEditingApiId] = useState<string | null>(null)
    const [curlInput, setCurlInput] = useState('')
    const [parsingCurl, setParsingCurl] = useState(false)
    const [newApi, setNewApi] = useState<Partial<API>>({
        name: '',
        method: 'POST',
        path: '',
        description: '',
        project_id: currentProject,
        base_url: '',
        headers: {},
        request_body: {},
        parameters: []
    })
    const [saveLoading, setSaveLoading] = useState(false)

    // 压测相关状态
    const [showStressTestModal, setShowStressTestModal] = useState(false)
    const [stressTestApiId, setStressTestApiId] = useState<string | null>(null)
    const [stressTestConfig, setStressTestConfig] = useState({
        test_count: 10,
        expected_debounce_time: 500,
        request_interval: 100
    })
    const [stressTestRunning, setStressTestRunning] = useState(false)
    const [stressTestResult, setStressTestResult] = useState<any>(null)
    const [expandedRequests, setExpandedRequests] = useState<Set<number>>(new Set())

    useEffect(() => {
        fetchAPIs()
    }, [currentProject])

    useEffect(() => {
        fetchEnvironments(currentProject)
    }, [currentProject])

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
            // 清理编辑状态
            setEditableParams(prev => { const n = { ...prev }; delete n[id]; return n; })
            setEditableHeaders(prev => { const n = { ...prev }; delete n[id]; return n; })
            setEditableUrlParams(prev => { const n = { ...prev }; delete n[id]; return n; })
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
                    throw new Error('请求体格式错误,请检查JSON格式')
                }
            }

            // 获取Headers:优先使用用户编辑的Headers
            let runtimeHeaders = api.headers || {}
            if (editableHeaders[api.id]) {
                try {
                    runtimeHeaders = JSON.parse(editableHeaders[api.id])
                } catch (e) {
                    throw new Error('Headers格式错误,请检查JSON格式')
                }
            }

            // 获取URL参数:优先使用用户编辑的Params
            let runtimeUrlParams = api.parameters || []
            if (editableUrlParams[api.id]) {
                try {
                    runtimeUrlParams = JSON.parse(editableUrlParams[api.id])
                } catch (e) {
                    throw new Error('URL参数格式错误,请检查JSON格式')
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
                    path: api.path, // 兼容后端 path/api_path
                    api_path: api.path,
                    method: api.method, // 兼容后端 method/api_method
                    api_method: api.method,
                    params: params,
                    headers: runtimeHeaders,
                    url_params: runtimeUrlParams,
                    param_mappings: [],
                    assertions: []
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

    const parseCurl = async () => {
        if (!curlInput.trim()) return
        setParsingCurl(true)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/parse/curl`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ curl: curlInput }),
            })
            if (response.ok) {
                const result = await response.json()
                setNewApi(prev => ({
                    ...prev,
                    name: result.name || prev.name || '未命名接口',
                    method: result.method || 'GET',
                    path: result.path || '',
                    base_url: result.base_url || '',
                    headers: result.headers || {},
                    request_body: result.request_body || result.body || {},
                    parameters: result.parameters || []
                }))
            } else {
                const err = await response.json()
                alert(`解析 cURL 失败: ${err.detail || '格式不规范'}`)
            }
        } catch (err) {
            console.error(err)
            alert('解析 cURL 出错')
        } finally {
            setParsingCurl(false)
        }
    }

    const saveApi = async () => {
        if (!newApi.name || !newApi.path) {
            alert('请填写接口名称和路径')
            return
        }
        setSaveLoading(true)
        try {
            const url = isEditing
                ? `${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/apis/${editingApiId}`
                : `${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/apis`
            const method = isEditing ? 'PUT' : 'POST'

            // 确保 parameters 是数组，防止因输入框为空对象 {} 导致后端 List 校验失败
            let finalParams = newApi.parameters
            if (!Array.isArray(finalParams)) {
                // 如果是空对象或者其他非数组类型，且内容为空，则默认为 []
                // 后端虽然已放宽校验，但前端保持严谨更好
                finalParams = []
            }

            const payload = {
                ...newApi,
                parameters: finalParams,
                request_body: newApi.request_body // 保持原样，后端支持 string/dict
            }

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })

            if (response.ok) {
                setShowAddModal(false)
                setIsEditing(false)
                setEditingApiId(null)
                setNewApi({
                    name: '',
                    method: 'POST',
                    path: '',
                    description: '',
                    project_id: currentProject,
                    base_url: '',
                    headers: {},
                    request_body: {},
                    parameters: []
                })
                setCurlInput('')
                fetchAPIs()
            } else {
                const errData = await response.json().catch(() => ({ detail: '未知错误' }))
                // 递归将对象转为更易读的字符串，防止出现 [object Object]
                const errorMessage = typeof errData.detail === 'object'
                    ? JSON.stringify(errData.detail)
                    : errData.detail || '服务器内部错误'
                alert(`保存失败: ${errorMessage}`)
            }
        } catch (err) {
            console.error(err)
            alert('保存出错')
        } finally {
            setSaveLoading(false)
        }
    }

    const openEditModal = (api: API) => {
        setIsEditing(true)
        setEditingApiId(api.id)
        setNewApi({
            name: api.name,
            method: api.method,
            path: api.path,
            description: api.description,
            project_id: api.project_id,
            base_url: api.base_url || '',
            headers: api.headers || {},
            request_body: api.request_body || {},
            parameters: api.parameters || []
        })
        setShowAddModal(true)
    }

    const handleStressTest = async () => {
        if (!stressTestApiId) return

        setStressTestRunning(true)
        setStressTestResult(null)

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/test/stress-test`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    api_id: parseInt(stressTestApiId),
                    test_count: stressTestConfig.test_count,
                    expected_debounce_time: stressTestConfig.expected_debounce_time,
                    request_interval: stressTestConfig.request_interval
                })
            })

            if (response.ok) {
                const result = await response.json()
                setStressTestResult(result)
            } else {
                const error = await response.json()
                alert(`压测失败: ${error.detail || '未知错误'}`)
            }
        } catch (error: any) {
            alert(`压测出错: ${error.message}`)
        } finally {
            setStressTestRunning(false)
        }
    }

    const projects = Array.from(new Set(apis.map(api => api.project_id || 'default-project')))

    const filteredAPIs = apis.filter(api => {
        const name = api.name || ''
        const path = api.path || ''
        const description = api.description || ''

        const matchesSearch = name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            path.toLowerCase().includes(searchTerm.toLowerCase()) ||
            description.toLowerCase().includes(searchTerm.toLowerCase())
        const matchesMethod = selectedMethod === 'all' || api.method === selectedMethod
        const matchesProject = (api.project_id || 'default-project') === currentProject
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
        <>
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

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginLeft: 'auto' }}>
                        <button
                            onClick={() => {
                                setIsEditing(false);
                                setEditingApiId(null);
                                setNewApi({
                                    name: '',
                                    method: 'POST',
                                    path: '',
                                    description: '',
                                    project_id: currentProject,
                                    base_url: '',
                                    headers: {},
                                    request_body: {},
                                    parameters: []
                                });
                                setCurlInput('');
                                setShowAddModal(true);
                            }}
                            style={{
                                padding: '0.75rem 1rem',
                                border: 'none',
                                borderRadius: '0.75rem',
                                background: '#3B82F6',
                                color: 'white',
                                cursor: 'pointer',
                                fontSize: '0.875rem',
                                fontWeight: '500',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem'
                            }}
                        >
                            <Plus size={18} />
                            手动添加接口
                        </button>
                        <Globe size={18} style={{ color: '#6B7280' }} />
                        <select
                            value={selectedEnvId || ''}
                            onChange={(e) => setSelectedEnvId(Number(e.target.value))}
                            style={{
                                padding: '0.75rem 1rem',
                                border: '2px solid #E5E7EB',
                                borderRadius: '0.75rem',
                                outline: 'none',
                                background: 'white',
                                cursor: 'pointer',
                                minWidth: '200px'
                            }}
                        >
                            <option value="">使用默认域名</option>
                            {environments.map(e => (
                                <option key={e.id} value={e.id}>
                                    {e.env_name} ({e.base_url})
                                </option>
                            ))}
                        </select>
                    </div>
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
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setStressTestApiId(api.id);
                                            setStressTestResult(null);
                                            setShowStressTestModal(true);
                                        }}
                                        style={{
                                            padding: '0.5rem 0.75rem',
                                            background: '#FEF3C7',
                                            color: '#D97706',
                                            border: 'none',
                                            borderRadius: '0.5rem',
                                            cursor: 'pointer',
                                            fontSize: '0.75rem',
                                            fontWeight: '500'
                                        }}
                                        title="压力测试"
                                    >
                                        压测
                                    </button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); openEditModal(api); }}
                                        style={{
                                            padding: '0.5rem',
                                            background: '#F3F4F6',
                                            color: '#374151',
                                            border: 'none',
                                            borderRadius: '0.5rem',
                                            cursor: 'pointer'
                                        }}
                                        title="编辑接口定义"
                                    >
                                        <Edit2 size={16} />
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
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                                                <h4 style={{ fontSize: '0.875rem', fontWeight: '600' }}>请求头 (可编辑)</h4>
                                                <button
                                                    onClick={() => {
                                                        setEditableHeaders(prev => {
                                                            const next = { ...prev }
                                                            delete next[api.id]
                                                            return next
                                                        })
                                                    }}
                                                    style={{
                                                        padding: '0.25rem 0.75rem',
                                                        fontSize: '0.75rem',
                                                        background: '#F3F4F6',
                                                        border: '1px solid #E5E7EB',
                                                        borderRadius: '0.375rem',
                                                        cursor: 'pointer',
                                                        color: '#374151'
                                                    }}
                                                >
                                                    重置
                                                </button>
                                            </div>
                                            <textarea
                                                value={editableHeaders[api.id] !== undefined ? editableHeaders[api.id] : JSON.stringify(api.headers || {}, null, 2)}
                                                onChange={(e) => setEditableHeaders(prev => ({ ...prev, [api.id]: e.target.value }))}
                                                style={{
                                                    width: '100%',
                                                    minHeight: '200px',
                                                    background: '#F8FAFC',
                                                    padding: '1rem',
                                                    borderRadius: '0.5rem',
                                                    fontSize: '0.75rem',
                                                    border: '1px solid #E2E8F0',
                                                    fontFamily: 'monospace',
                                                    resize: 'vertical',
                                                    outline: 'none'
                                                }}
                                                placeholder="输入JSON格式的请求头"
                                            />
                                            <p style={{ fontSize: '0.7rem', color: '#6B7280', marginTop: '0.5rem' }}>
                                                💡 提示: 修改请求头后点击右上角"执行"按钮生效
                                            </p>
                                        </div>
                                    )}

                                    {/* Body 标签页 */}
                                    {(activeApiTab[api.id] || 'Headers') === 'Body' && (
                                        <div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                                                <h4 style={{ fontSize: '0.875rem', fontWeight: '600' }}>请求参数 (可编辑)</h4>
                                                <button
                                                    onClick={() => {
                                                        setEditableParams(prev => {
                                                            const next = { ...prev }
                                                            delete next[api.id]
                                                            return next
                                                        })
                                                    }}
                                                    style={{
                                                        padding: '0.25rem 0.75rem',
                                                        fontSize: '0.75rem',
                                                        background: '#F3F4F6',
                                                        border: '1px solid #E5E7EB',
                                                        borderRadius: '0.375rem',
                                                        cursor: 'pointer',
                                                        color: '#374151'
                                                    }}
                                                >
                                                    重置
                                                </button>
                                            </div>
                                            <textarea
                                                value={editableParams[api.id] !== undefined ? editableParams[api.id] : JSON.stringify(api.request_body || {}, null, 2)}
                                                onChange={(e) => setEditableParams(prev => ({ ...prev, [api.id]: e.target.value }))}
                                                style={{
                                                    width: '100%',
                                                    minHeight: '300px',
                                                    background: '#F8FAFC',
                                                    padding: '1rem',
                                                    borderRadius: '0.5rem',
                                                    fontSize: '0.75rem',
                                                    border: '1px solid #E2E8F0',
                                                    fontFamily: 'monospace',
                                                    resize: 'vertical',
                                                    outline: 'none'
                                                }}
                                                placeholder="输入JSON格式的请求参数"
                                            />
                                            <p style={{ fontSize: '0.7rem', color: '#6B7280', marginTop: '0.5rem' }}>
                                                💡 提示: 修改参数后点击右上角"执行"按钮,将使用修改后的参数进行请求
                                            </p>
                                        </div>
                                    )}

                                    {/* Params 标签页 */}
                                    {(activeApiTab[api.id] || 'Headers') === 'Params' && (
                                        <div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                                                <h4 style={{ fontSize: '0.875rem', fontWeight: '600' }}>URL参数 (可编辑)</h4>
                                                <button
                                                    onClick={() => {
                                                        setEditableUrlParams(prev => {
                                                            const next = { ...prev }
                                                            delete next[api.id]
                                                            return next
                                                        })
                                                    }}
                                                    style={{
                                                        padding: '0.25rem 0.75rem',
                                                        fontSize: '0.75rem',
                                                        background: '#F3F4F6',
                                                        border: '1px solid #E5E7EB',
                                                        borderRadius: '0.375rem',
                                                        cursor: 'pointer',
                                                        color: '#374151'
                                                    }}
                                                >
                                                    重置
                                                </button>
                                            </div>
                                            <textarea
                                                value={editableUrlParams[api.id] !== undefined ? editableUrlParams[api.id] : JSON.stringify(api.parameters || [], null, 2)}
                                                onChange={(e) => setEditableUrlParams(prev => ({ ...prev, [api.id]: e.target.value }))}
                                                style={{
                                                    width: '100%',
                                                    minHeight: '200px',
                                                    background: '#F8FAFC',
                                                    padding: '1rem',
                                                    borderRadius: '0.5rem',
                                                    fontSize: '0.75rem',
                                                    border: '1px solid #E2E8F0',
                                                    fontFamily: 'monospace',
                                                    resize: 'vertical',
                                                    outline: 'none'
                                                }}
                                                placeholder="输入JSON格式的URL参数 (即Swagger中的parameters)"
                                            />
                                            <p style={{ fontSize: '0.7rem', color: '#6B7280', marginTop: '0.5rem' }}>
                                                💡 提示: 数组格式,包含 name, in (query/path), required 等字段
                                            </p>
                                        </div>
                                    )}

                                    {/* 执行结果 */}
                                    {(activeApiTab[api.id] || 'Headers') === '执行结果' && executionResults[api.id] && (
                                        <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '2px solid #E5E7EB' }}>
                                            <div style={{
                                                padding: '0.75rem 1rem',
                                                borderRadius: '0.5rem',
                                                fontSize: '0.875rem',
                                                marginBottom: '1rem',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                background: executionResults[api.id].error || !executionResults[api.id].success ? '#FEF2F2' : '#F0FDF4',
                                                color: executionResults[api.id].error || !executionResults[api.id].success ? '#B91C1C' : '#166534',
                                                border: `1px solid ${executionResults[api.id].error || !executionResults[api.id].success ? '#FECACA' : '#BBF7D0'}`
                                            }}>
                                                {executionResults[api.id].error || !executionResults[api.id].success ? <XCircle size={18} /> : <CheckCircle size={18} />}
                                                <span style={{ fontWeight: '600' }}>
                                                    {executionResults[api.id].error || (executionResults[api.id].success ? `执行成功: ${executionResults[api.id].status_code}` : `执行失败: ${executionResults[api.id].status_code}`)}
                                                </span>
                                            </div>

                                            {/* 标签页 */}
                                            <div style={{ display: 'flex', borderBottom: '2px solid #E5E7EB', marginBottom: '1rem' }}>
                                                {['响应体', '响应头', '断言', '请求内容'].map(tab => (
                                                    <button
                                                        key={tab}
                                                        onClick={() => setActiveResultTab(prev => ({ ...prev, [api.id]: tab }))}
                                                        style={{
                                                            padding: '0.75rem 1.5rem',
                                                            background: (activeResultTab[api.id] || '响应体') === tab ? '#3B82F6' : 'transparent',
                                                            color: (activeResultTab[api.id] || '响应体') === tab ? 'white' : '#6B7280',
                                                            border: 'none',
                                                            cursor: 'pointer',
                                                            fontWeight: (activeResultTab[api.id] || '响应体') === tab ? '600' : '400',
                                                            fontSize: '0.875rem',
                                                            transition: 'all 0.2s',
                                                            borderRadius: '0.5rem 0.5rem 0 0'
                                                        }}
                                                    >
                                                        {tab}
                                                    </button>
                                                ))}
                                            </div>

                                            {/* 标签页内容 */}
                                            <div>
                                                {(activeResultTab[api.id] || '响应体') === '响应体' && (
                                                    <pre style={{ background: '#F8FAFC', padding: '1rem', borderRadius: '0.5rem', overflow: 'auto', maxHeight: '400px', fontSize: '0.75rem', margin: 0, border: '1px solid #E2E8F0' }}>
                                                        {typeof executionResults[api.id].response === 'string' ? executionResults[api.id].response : JSON.stringify(executionResults[api.id].response, null, 2)}
                                                    </pre>
                                                )}
                                                {(activeResultTab[api.id] || '响应体') === '响应头' && executionResults[api.id].response_headers && (
                                                    <div style={{ fontSize: '0.8125rem', border: '1px solid #E2E8F0', borderRadius: '0.5rem', overflow: 'hidden' }}>
                                                        {Object.entries(executionResults[api.id].response_headers).map(([key, value]: [string, any]) => (
                                                            <div key={key} style={{ padding: '0.75rem', borderBottom: '1px solid #F3F4F6', display: 'flex', gap: '1rem' }}>
                                                                <span style={{ fontWeight: '600', minWidth: '200px', color: '#374151' }}>{key}:</span>
                                                                <span style={{ color: '#6B7280' }}>{Array.isArray(value) ? value.join(', ') : String(value)}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                                {(activeResultTab[api.id] || '响应体') === '断言' && (
                                                    <div style={{ fontSize: '0.8125rem' }}>
                                                        {executionResults[api.id].assertions && executionResults[api.id].assertions.length > 0 ? (
                                                            executionResults[api.id].assertions.map((assertion: any, idx: number) => (
                                                                <div key={idx} style={{ padding: '1rem', marginBottom: '0.75rem', background: assertion.passed ? '#F0FDF4' : '#FEF2F2', border: `1px solid ${assertion.passed ? '#BBF7D0' : '#FECACA'}`, borderRadius: '0.625rem' }}>
                                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                                        <div style={{ color: assertion.passed ? '#10B981' : '#EF4444', display: 'flex', alignItems: 'center' }}>
                                                                            {assertion.passed ? <CheckCircle size={18} /> : <XCircle size={18} />}
                                                                        </div>
                                                                        <div style={{ flex: 1 }}>
                                                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                                                                                <span style={{ fontWeight: '700', color: assertion.passed ? '#065F46' : '#991B1B' }}>
                                                                                    {assertion.description || `${assertion.field || assertion.type} ${assertion.operator || '校验'}`}
                                                                                </span>
                                                                                <span style={{ fontSize: '0.7rem', color: assertion.passed ? '#059669' : '#DC2626', background: 'white', padding: '0.125rem 0.5rem', borderRadius: '1rem', border: '1px solid currentColor' }}>
                                                                                    {assertion.type}
                                                                                </span>
                                                                            </div>
                                                                            <div style={{ display: 'flex', gap: '2rem', fontSize: '0.875rem' }}>
                                                                                <div>
                                                                                    <span style={{ color: '#6B7280', fontSize: '0.75rem' }}>期望结果: </span>
                                                                                    <span style={{ fontFamily: 'monospace', fontWeight: '600' }}>{JSON.stringify(assertion.expected)}</span>
                                                                                </div>
                                                                                <div>
                                                                                    <span style={{ color: '#6B7280', fontSize: '0.75rem' }}>实际结果: </span>
                                                                                    <span style={{ fontFamily: 'monospace', fontWeight: '600', color: assertion.passed ? '#059669' : '#DC2626' }}>{JSON.stringify(assertion.actual)}</span>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            ))
                                                        ) : (
                                                            <p style={{ textAlign: 'center', color: '#9CA3AF', padding: '2rem' }}>暂无断言</p>
                                                        )}
                                                    </div>
                                                )}
                                                {(activeResultTab[api.id] || '响应体') === '请求内容' && (
                                                    <div style={{ background: '#F8FAFC', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #E2E8F0', maxHeight: '400px', overflow: 'auto' }}>
                                                        {executionResults[api.id].url_params && Object.keys(executionResults[api.id].url_params).length > 0 && (
                                                            <div style={{ marginBottom: '1rem' }}>
                                                                <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>URL 参数 (Query):</div>
                                                                <pre style={{ margin: 0, fontSize: '0.75rem' }}>
                                                                    {JSON.stringify(executionResults[api.id].url_params, null, 2)}
                                                                </pre>
                                                            </div>
                                                        )}
                                                        <div>
                                                            <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>请求体 (Body):</div>
                                                            <pre style={{ margin: 0, fontSize: '0.75rem' }}>
                                                                {JSON.stringify(executionResults[api.id].request_data || {}, null, 2)}
                                                            </pre>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {confirmDelete.show && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000
                }} onClick={() => setConfirmDelete({ show: false, id: '', name: '' })}>
                    <div style={{
                        background: 'white',
                        padding: '2rem',
                        borderRadius: '1rem',
                        maxWidth: '400px',
                        boxShadow: '0 20px 25px -5px rgba(0,0,0,0.3)'
                    }} onClick={(e) => e.stopPropagation()}>
                        <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>确认删除</h3>
                        <p style={{ color: '#6B7280', marginBottom: '1.5rem' }}>
                            确定要删除 <strong>{confirmDelete.name}</strong> 吗?此操作不可恢复。
                        </p>
                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => setConfirmDelete({ show: false, id: '', name: '' })}
                                style={{
                                    padding: '0.5rem 1rem',
                                    border: '1px solid #E5E7EB',
                                    borderRadius: '0.5rem',
                                    background: 'white',
                                    cursor: 'pointer'
                                }}
                            >
                                取消
                            </button>
                            <button
                                onClick={() => deleteApi(confirmDelete.id)}
                                style={{
                                    padding: '0.5rem 1rem',
                                    border: 'none',
                                    borderRadius: '0.5rem',
                                    background: '#EF4444',
                                    color: 'white',
                                    cursor: 'pointer'
                                }}
                            >
                                删除
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* 手动添加/编辑接口 Modal */}
            {showAddModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    zIndex: 1000, padding: '20px'
                }} onClick={() => setShowAddModal(false)}>
                    <div style={{
                        background: 'white', borderRadius: '1.25rem', width: '100%', maxWidth: '900px',
                        maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
                        display: 'flex', flexDirection: 'column'
                    }} onClick={(e) => e.stopPropagation()}>
                        {/* Header */}
                        <div style={{ padding: '1.5rem', borderBottom: '1px solid #E5E7EB', display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'sticky', top: 0, background: 'white', zIndex: 10 }}>
                            <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#111827', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <Database size={24} style={{ color: '#3B82F6' }} />
                                {isEditing ? '编辑接口定义' : '手动添加接口'}
                            </h2>
                            <button onClick={() => setShowAddModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6B7280' }}>
                                <XCircle size={28} />
                            </button>
                        </div>

                        <div style={{ padding: '2rem' }}>
                            {/* cURL 解析区 */}
                            {!isEditing && (
                                <div style={{ marginBottom: '2rem', padding: '1.5rem', background: '#F0F9FF', borderRadius: '1rem', border: '1px dashed #7DD3FC' }}>
                                    <h3 style={{ fontSize: '1rem', fontWeight: '600', color: '#0369A1', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <Code size={18} /> 通过 cURL 快速导入 (可选)
                                    </h3>
                                    <div style={{ display: 'flex', gap: '1rem' }}>
                                        <textarea
                                            value={curlInput}
                                            onChange={(e) => setCurlInput(e.target.value)}
                                            placeholder="粘贴 cURL 命令，如: curl -X POST http://api.com -H 'Content-Type: application/json' -d '{&quot;id&quot;:1}'"
                                            style={{
                                                flex: 1, height: '80px', padding: '0.75rem', borderRadius: '0.5rem',
                                                border: '1px solid #BAE6FD', fontSize: '0.8125rem', fontFamily: 'monospace', outline: 'none'
                                            }}
                                        />
                                        <button
                                            onClick={parseCurl}
                                            disabled={parsingCurl || !curlInput.trim()}
                                            style={{
                                                padding: '0 1.5rem', background: parsingCurl || !curlInput.trim() ? '#CBD5E1' : '#0EA5E9',
                                                color: 'white', borderRadius: '0.5rem', border: 'none', fontWeight: '600', cursor: 'pointer'
                                            }}
                                        >
                                            {parsingCurl ? '解析中...' : '解析'}
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* 基本信息 */}
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.5rem', marginBottom: '1.5rem' }}>
                                <div style={{ gridColumn: 'span 2' }}>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>接口名称 *</label>
                                    <input
                                        type="text"
                                        value={newApi.name}
                                        onChange={(e) => setNewApi({ ...newApi, name: e.target.value })}
                                        placeholder="如: 歌曲下单接口"
                                        style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB', outline: 'none' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>请求方法 *</label>
                                    <select
                                        value={newApi.method}
                                        onChange={(e) => setNewApi({ ...newApi, method: e.target.value })}
                                        style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB', outline: 'none', background: 'white' }}
                                    >
                                        <option value="GET">GET</option>
                                        <option value="POST">POST</option>
                                        <option value="PUT">PUT</option>
                                        <option value="DELETE">DELETE</option>
                                        <option value="PATCH">PATCH</option>
                                    </select>
                                </div>
                                <div>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>所属项目</label>
                                    <input
                                        type="text"
                                        value={newApi.project_id}
                                        onChange={(e) => setNewApi({ ...newApi, project_id: e.target.value })}
                                        placeholder="default-project"
                                        style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB', outline: 'none' }}
                                    />
                                </div>
                                <div style={{ gridColumn: 'span 2' }}>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>接口路径 (Path) *</label>
                                    <input
                                        type="text"
                                        value={newApi.path}
                                        onChange={(e) => setNewApi({ ...newApi, path: e.target.value })}
                                        placeholder="如: /api/v1/user/login"
                                        style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB', outline: 'none' }}
                                    />
                                </div>
                                <div style={{ gridColumn: 'span 2' }}>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>默认域名 (Base URL)</label>
                                    <input
                                        type="text"
                                        value={newApi.base_url}
                                        onChange={(e) => setNewApi({ ...newApi, base_url: e.target.value })}
                                        placeholder="如: http://api.example.com"
                                        style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB', outline: 'none' }}
                                    />
                                </div>
                            </div>

                            {/* 详细配置 */}
                            <div style={{ display: 'grid', gap: '1.5rem' }}>
                                <div>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>请求头 (Headers JSON)</label>
                                    <textarea
                                        value={typeof newApi.headers === 'string' ? newApi.headers : JSON.stringify(newApi.headers, null, 2)}
                                        onChange={(e) => {
                                            try {
                                                const parsed = JSON.parse(e.target.value)
                                                setNewApi({ ...newApi, headers: parsed })
                                            } catch (err) {
                                                setNewApi({ ...newApi, headers: e.target.value as any })
                                            }
                                        }}
                                        placeholder="{}"
                                        style={{ width: '100%', height: '120px', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB', outline: 'none', fontFamily: 'monospace', fontSize: '0.8125rem' }}
                                    />
                                </div>
                                <div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                        <label style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151' }}>请求体 (RequestBody JSON)</label>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                const val = (typeof newApi.request_body === 'string' ? newApi.request_body : '').trim()
                                                if (!val) {
                                                    alert('请先输入 Form Data 字符串')
                                                    return
                                                }
                                                // 尝试检测是否为 key=value 格式
                                                if (val.includes('=') && !val.trim().startsWith('{') && !val.trim().startsWith('[')) {
                                                    try {
                                                        const parts = val.split('&')
                                                        const obj: Record<string, string> = {}
                                                        let isForm = false
                                                        for (const part of parts) {
                                                            const [rawK, rawV] = part.split('=')
                                                            if (rawK) {
                                                                const k = decodeURIComponent(rawK.trim())
                                                                const v = rawV ? decodeURIComponent(rawV.trim()) : ''
                                                                obj[k] = v
                                                                isForm = true
                                                            }
                                                        }
                                                        if (isForm && Object.keys(obj).length > 0) {
                                                            setNewApi({ ...newApi, request_body: obj })
                                                        } else {
                                                            alert('未识别到有效的 key=value 格式')
                                                        }
                                                    } catch (err) {
                                                        alert('转换失败: ' + String(err))
                                                    }
                                                } else {
                                                    alert('当前内容似乎不是 Form Data 格式 (key=value&...)')
                                                }
                                            }}
                                            style={{
                                                fontSize: '0.75rem',
                                                padding: '0.25rem 0.5rem',
                                                background: '#E0F2FE',
                                                color: '#0284C7',
                                                border: '1px solid #7DD3FC',
                                                borderRadius: '0.25rem',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            格式化 Form Data
                                        </button>
                                    </div>
                                    <textarea
                                        value={typeof newApi.request_body === 'string' ? newApi.request_body : JSON.stringify(newApi.request_body, null, 2)}
                                        onChange={(e) => {
                                            try {
                                                const parsed = JSON.parse(e.target.value)
                                                setNewApi({ ...newApi, request_body: parsed })
                                            } catch (err) {
                                                setNewApi({ ...newApi, request_body: e.target.value as any })
                                            }
                                        }}
                                        onBlur={(e) => {
                                            const val = e.target.value.trim()
                                            if (!val) return
                                            // 尝试检测是否为 key=value 格式 (简单的启发式检测)
                                            if (val.includes('=') && !val.trim().startsWith('{') && !val.trim().startsWith('[')) {
                                                try {
                                                    const parts = val.split('&')
                                                    const obj: Record<string, string> = {}
                                                    let isForm = false
                                                    for (const part of parts) {
                                                        const [rawK, rawV] = part.split('=')
                                                        if (rawK) {
                                                            const k = decodeURIComponent(rawK.trim())
                                                            const v = rawV ? decodeURIComponent(rawV.trim()) : ''
                                                            obj[k] = v
                                                            isForm = true
                                                        }
                                                    }
                                                    if (isForm && Object.keys(obj).length > 0) {
                                                        setNewApi({ ...newApi, request_body: obj })
                                                    }
                                                } catch (err) {
                                                    console.warn('Auto convert form data failed', err)
                                                }
                                            }
                                        }}
                                        placeholder="{}"
                                        style={{ width: '100%', height: '200px', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB', outline: 'none', fontFamily: 'monospace', fontSize: '0.8125rem' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>URL参数定义 (Parameters JSON Array)</label>
                                    <textarea
                                        value={typeof newApi.parameters === 'string' ? newApi.parameters : JSON.stringify(newApi.parameters, null, 2)}
                                        onChange={(e) => {
                                            try {
                                                const parsed = JSON.parse(e.target.value)
                                                setNewApi({ ...newApi, parameters: parsed })
                                            } catch (err) {
                                                setNewApi({ ...newApi, parameters: e.target.value as any })
                                            }
                                        }}
                                        placeholder="[]"
                                        style={{ width: '100%', height: '120px', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB', outline: 'none', fontFamily: 'monospace', fontSize: '0.8125rem' }}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Footer */}
                        <div style={{ padding: '1.5rem', borderTop: '1px solid #E5E7EB', display: 'flex', gap: '1rem', justifyContent: 'flex-end', position: 'sticky', bottom: 0, background: 'white' }}>
                            <button
                                onClick={() => setShowAddModal(false)}
                                style={{ padding: '0.75rem 2rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB', background: 'white', cursor: 'pointer', fontWeight: '600' }}
                            >
                                取消
                            </button>
                            <button
                                onClick={saveApi}
                                disabled={saveLoading}
                                style={{
                                    padding: '0.75rem 3rem', borderRadius: '0.5rem', border: 'none', background: '#3B82F6',
                                    color: 'white', fontWeight: '700', cursor: saveLoading ? 'not-allowed' : 'pointer'
                                }}
                            >
                                {saveLoading ? '保存中...' : (isEditing ? '更新接口' : '立即保存')}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* 压测对话框 */}
            {showStressTestModal && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(0, 0, 0, 0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000
                }}>
                    <div style={{
                        background: 'white',
                        borderRadius: '1rem',
                        width: '90%',
                        maxWidth: '800px',
                        maxHeight: '90vh',
                        overflow: 'auto'
                    }}>
                        {/* Header */}
                        <div style={{ padding: '1.5rem', borderBottom: '1px solid #E5E7EB' }}>
                            <h2 style={{ fontSize: '1.5rem', fontWeight: '700' }}>⚡ API 压测</h2>
                            <p style={{ color: '#6B7280', fontSize: '0.875rem', marginTop: '0.5rem' }}>
                                对选中的API进行压力测试，分析是否存在防抖逻辑
                            </p>
                        </div>

                        {/* Body */}
                        <div style={{ padding: '1.5rem' }}>
                            {!stressTestResult ? (
                                <div>
                                    <div style={{ marginBottom: '1.5rem' }}>
                                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>测试次数</label>
                                        <input
                                            type="number"
                                            value={stressTestConfig.test_count}
                                            onChange={(e) => setStressTestConfig({ ...stressTestConfig, test_count: parseInt(e.target.value) })}
                                            style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB' }}
                                        />
                                    </div>
                                    <div style={{ marginBottom: '1.5rem' }}>
                                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>预期防抖时间 (ms)</label>
                                        <input
                                            type="number"
                                            value={stressTestConfig.expected_debounce_time}
                                            onChange={(e) => setStressTestConfig({ ...stressTestConfig, expected_debounce_time: parseInt(e.target.value) })}
                                            style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB' }}
                                        />
                                    </div>
                                    <div style={{ marginBottom: '1.5rem' }}>
                                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>请求间隔 (ms)</label>
                                        <input
                                            type="number"
                                            value={stressTestConfig.request_interval}
                                            onChange={(e) => setStressTestConfig({ ...stressTestConfig, request_interval: parseInt(e.target.value) })}
                                            style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB' }}
                                        />
                                    </div>
                                </div>
                            ) : (
                                <div>
                                    {/* 测试结果 */}
                                    <div style={{ marginBottom: '1.5rem', padding: '1rem', background: stressTestResult.analysis.has_debounce ? '#ECFDF5' : '#FEF2F2', borderRadius: '0.5rem' }}>
                                        <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                                            {stressTestResult.analysis.has_debounce ? '✅ 检测到防抖' : '❌ 未检测到防抖'}
                                        </h3>
                                        <p style={{ fontSize: '0.875rem', color: '#6B7280' }}>置信度: {stressTestResult.analysis.confidence}%</p>
                                    </div>

                                    {stressTestResult.analysis.reasons.length > 0 && (
                                        <div style={{ marginBottom: '1.5rem' }}>
                                            <h4 style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>判断依据:</h4>
                                            <ul style={{ paddingLeft: '1.5rem' }}>
                                                {stressTestResult.analysis.reasons.map((reason: string, i: number) => (
                                                    <li key={i} style={{ fontSize: '0.875rem', color: '#6B7280', marginBottom: '0.25rem' }}>{reason}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    <div style={{ marginBottom: '1.5rem' }}>
                                        <h4 style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>统计信息:</h4>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                                            <div style={{ padding: '0.75rem', background: '#F3F4F6', borderRadius: '0.5rem' }}>
                                                <div style={{ fontSize: '0.75rem', color: '#6B7280' }}>总请求数</div>
                                                <div style={{ fontSize: '1.5rem', fontWeight: '700' }}>{stressTestResult.stats.total_requests}</div>
                                            </div>
                                            <div style={{ padding: '0.75rem', background: '#F3F4F6', borderRadius: '0.5rem' }}>
                                                <div style={{ fontSize: '0.75rem', color: '#6B7280' }}>成功请求</div>
                                                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#10B981' }}>{stressTestResult.stats.successful_requests}</div>
                                            </div>
                                            <div style={{ padding: '0.75rem', background: '#F3F4F6', borderRadius: '0.5rem' }}>
                                                <div style={{ fontSize: '0.75rem', color: '#6B7280' }}>平均耗时</div>
                                                <div style={{ fontSize: '1.5rem', fontWeight: '700' }}>{stressTestResult.stats.avg_duration}s</div>
                                            </div>
                                            <div style={{ padding: '0.75rem', background: '#F3F4F6', borderRadius: '0.5rem' }}>
                                                <div style={{ fontSize: '0.75rem', color: '#6B7280' }}>总耗时</div>
                                                <div style={{ fontSize: '1.5rem', fontWeight: '700' }}>{stressTestResult.stats.total_time}s</div>
                                            </div>
                                        </div>
                                    </div>

                                    <div>
                                        <h4 style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>请求详情:</h4>
                                        <div style={{ maxHeight: '400px', overflow: 'auto' }}>
                                            {stressTestResult.test_results.map((result: any) => {
                                                const isExpanded = expandedRequests.has(result.request_id);
                                                return (
                                                    <div key={result.request_id} style={{ marginBottom: '0.75rem', border: '1px solid #E5E7EB', borderRadius: '0.5rem', overflow: 'hidden' }}>
                                                        <div
                                                            onClick={() => {
                                                                setExpandedRequests(prev => {
                                                                    const next = new Set(prev);
                                                                    if (next.has(result.request_id)) {
                                                                        next.delete(result.request_id);
                                                                    } else {
                                                                        next.add(result.request_id);
                                                                    }
                                                                    return next;
                                                                });
                                                            }}
                                                            style={{
                                                                padding: '0.75rem',
                                                                background: result.success ? '#F0FDF4' : '#FEF2F2',
                                                                cursor: 'pointer',
                                                                fontSize: '0.875rem',
                                                                fontWeight: '500',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                gap: '0.5rem'
                                                            }}
                                                        >
                                                            <span style={{ fontWeight: '600' }}>#{result.request_id}</span>
                                                            <span style={{
                                                                padding: '0.125rem 0.5rem',
                                                                borderRadius: '0.25rem',
                                                                fontSize: '0.75rem',
                                                                background: result.success ? '#10B981' : '#EF4444',
                                                                color: 'white'
                                                            }}>
                                                                {result.success ? '成功' : '失败'}
                                                            </span>
                                                            <span style={{ color: '#6B7280' }}>耗时: {result.duration}s</span>
                                                            {result.status_code && (
                                                                <span style={{
                                                                    padding: '0.125rem 0.5rem',
                                                                    borderRadius: '0.25rem',
                                                                    fontSize: '0.75rem',
                                                                    background: result.status_code === 200 ? '#DBEAFE' : result.status_code === 429 ? '#FEF3C7' : '#FEE2E2',
                                                                    color: result.status_code === 200 ? '#1E40AF' : result.status_code === 429 ? '#D97706' : '#DC2626'
                                                                }}>
                                                                    状态码: {result.status_code}
                                                                </span>
                                                            )}
                                                            <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: '#6B7280' }}>
                                                                {isExpanded ? '▼ 收起' : '▶ 展开'}
                                                            </span>
                                                        </div>
                                                        {isExpanded && (
                                                            <div style={{ padding: '1rem', background: '#F9FAFB', borderTop: '1px solid #E5E7EB' }}>
                                                                {result.success ? (
                                                                    <div>
                                                                        <h5 style={{ fontSize: '0.75rem', fontWeight: '600', marginBottom: '0.5rem', color: '#374151' }}>响应内容:</h5>
                                                                        <pre style={{
                                                                            background: '#1F2937',
                                                                            color: '#F3F4F6',
                                                                            padding: '0.75rem',
                                                                            borderRadius: '0.375rem',
                                                                            fontSize: '0.75rem',
                                                                            overflow: 'auto',
                                                                            maxHeight: '300px',
                                                                            margin: 0,
                                                                            whiteSpace: 'pre-wrap',
                                                                            wordBreak: 'break-word'
                                                                        }}>
                                                                            {JSON.stringify(result.response, null, 2)}
                                                                        </pre>
                                                                    </div>
                                                                ) : (
                                                                    <div>
                                                                        <h5 style={{ fontSize: '0.75rem', fontWeight: '600', marginBottom: '0.5rem', color: '#DC2626' }}>错误信息:</h5>
                                                                        <div style={{
                                                                            background: '#FEE2E2',
                                                                            color: '#991B1B',
                                                                            padding: '0.75rem',
                                                                            borderRadius: '0.375rem',
                                                                            fontSize: '0.75rem'
                                                                        }}>
                                                                            {result.error || '未知错误'}
                                                                        </div>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Footer */}
                        <div style={{ padding: '1.5rem', borderTop: '1px solid #E5E7EB', display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => {
                                    setShowStressTestModal(false)
                                    setStressTestResult(null)
                                }}
                                style={{ padding: '0.75rem 2rem', borderRadius: '0.5rem', border: '1px solid #D1D5DB', background: 'white', cursor: 'pointer', fontWeight: '600' }}
                            >
                                关闭
                            </button>
                            {!stressTestResult && (
                                <button
                                    onClick={handleStressTest}
                                    disabled={stressTestRunning}
                                    style={{
                                        padding: '0.75rem 3rem',
                                        borderRadius: '0.5rem',
                                        border: 'none',
                                        background: stressTestRunning ? '#D1D5DB' : '#D97706',
                                        color: 'white',
                                        fontWeight: '700',
                                        cursor: stressTestRunning ? 'not-allowed' : 'pointer'
                                    }}
                                >
                                    {stressTestRunning ? '测试中...' : '开始压测'}
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
