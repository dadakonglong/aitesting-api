'use client'

import { useState, useEffect } from 'react'
import { Play, Clock, CheckCircle, XCircle, FileText, ChevronDown, ChevronUp, Trash2, Filter, Database, Settings, Plus, X, Globe, ListChecks } from 'lucide-react'

export default function TestsPage() {
    const [scenarios, setScenarios] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [executingIds, setExecutingIds] = useState<Set<number>>(new Set())
    const [executionResults, setExecutionResults] = useState<Record<number, any>>({})
    const [expandedScenarios, setExpandedScenarios] = useState<Set<number>>(new Set())
    const [previewScenarios, setPreviewScenarios] = useState<Set<number>>(new Set())
    const [selectedProject, setSelectedProject] = useState<string>('all')
    const [allProjects, setAllProjects] = useState<string[]>([])
    const [isDeleting, setIsDeleting] = useState<number | null>(null)
    const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set()) // scenarioId_stepOrder

    // 批量执行相关
    const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
    const [isBatchExecuting, setIsBatchExecuting] = useState(false)

    // 确认框相关
    const [showConfirm, setShowConfirm] = useState<{
        show: boolean,
        title: string,
        message: string,
        onConfirm: () => void,
        type: 'danger' | 'warning'
    }>({
        show: false,
        title: '',
        message: '',
        onConfirm: () => { },
        type: 'danger'
    })

    // 环境配置相关
    const [showEnvConfig, setShowEnvConfig] = useState(false)
    const [environments, setEnvironments] = useState<any[]>([])
    const [selectedEnvId, setSelectedEnvId] = useState<number | null>(null)
    const [newEnvName, setNewEnvName] = useState('')
    const [newEnvUrl, setNewEnvUrl] = useState('')

    useEffect(() => {
        fetchScenarios()
        fetchProjects()
    }, [])

    useEffect(() => {
        if (selectedProject !== 'all') {
            fetchEnvironments(selectedProject)
        } else {
            setEnvironments([])
            setSelectedEnvId(null)
        }
    }, [selectedProject])

    const fetchProjects = async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/projects`)
            if (response.ok) {
                const data = await response.json()
                setAllProjects(data.projects || [])
            }
        } catch (error) {
            console.error('获取项目列表失败:', error)
        }
    }

    const fetchScenarios = async () => {
        setLoading(true)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scenarios`)
            if (response.ok) {
                const data = await response.json()
                setScenarios(data)
            }
        } catch (error) {
            console.error('获取场景列表失败:', error)
        } finally {
            setLoading(false)
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

    const handleSaveEnv = async () => {
        if (!newEnvName || !newEnvUrl) return
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/projects/${selectedProject}/environments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    env_name: newEnvName,
                    base_url: newEnvUrl,
                    is_default: environments.length === 0
                })
            })
            if (response.ok) {
                fetchEnvironments(selectedProject)
                setNewEnvName('')
                setNewEnvUrl('')
            }
        } catch (error) {
            console.error('保存环境失败:', error)
        }
    }

    const handleDeleteEnv = async (envName: string) => {
        setShowConfirm({
            show: true,
            title: '删除项目环境',
            message: `确定要删除环境 "${envName}" 吗？此操作不可恢复。`,
            type: 'danger',
            onConfirm: async () => {
                try {
                    const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/projects/${selectedProject}/environments/${envName}`, {
                        method: 'DELETE'
                    })
                    if (response.ok) fetchEnvironments(selectedProject)
                } catch (error) {
                    console.error('删除环境失败:', error)
                }
                setShowConfirm(prev => ({ ...prev, show: false }))
            }
        })
    }

    const handleDelete = (e: React.MouseEvent, scenarioId: number) => {
        e.stopPropagation()
        setShowConfirm({
            show: true,
            title: '删除测试场景',
            message: '提示：确定要删除这个测试场景吗？此操作将同步删除关联的测试用例，且不可撤销。',
            type: 'danger',
            onConfirm: () => performDelete(scenarioId)
        })
    }

    const performDelete = async (scenarioId: number) => {
        setIsDeleting(scenarioId)
        setShowConfirm(prev => ({ ...prev, show: false }))
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scenarios/${scenarioId}`, {
                method: 'DELETE'
            })
            if (response.ok) {
                setScenarios(prev => prev.filter(s => s.id !== scenarioId))
                setSelectedIds(prev => {
                    const next = new Set(prev)
                    next.delete(scenarioId)
                    return next
                })
            }
        } catch (error) {
            console.error('删除失败:', error)
            alert('服务器响应异常，请检查后端服务是否正常。')
        } finally {
            setIsDeleting(null)
        }
    }

    const handleExecute = async (scenarioId: number, testCaseId: string) => {
        setExecutingIds(prev => new Set(prev).add(scenarioId))
        const env = environments.find(e => e.id === selectedEnvId)
        const baseUrl = env ? env.base_url : 'http://localhost:8000'

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_EXEC_API_URL}/api/v1/executions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    test_case_id: testCaseId,
                    environment: env?.env_name || 'test',
                    base_url: baseUrl
                }),
            })

            if (response.ok) {
                const execution = await response.json()
                setExecutionResults(prev => ({ ...prev, [scenarioId]: execution }))
                setExpandedScenarios(prev => new Set(prev).add(scenarioId))
            } else {
                const errData = await response.json().catch(() => ({}))
                throw new Error(errData.detail || '接口执行失败，请检查 Base URL 是否有效')
            }
        } catch (error: any) {
            setExecutionResults(prev => ({ ...prev, [scenarioId]: { error: error.message } }))
        } finally {
            setExecutingIds(prev => {
                const next = new Set(prev)
                next.delete(scenarioId)
                return next
            })
        }
    }

    const handleBatchExecute = async () => {
        if (selectedIds.size === 0) return
        if (!confirm(`确定要执行选中的 ${selectedIds.size} 个场景吗？`)) return

        setIsBatchExecuting(true)
        const toRun = filteredScenarios.filter(s => selectedIds.has(s.id) && s.test_case_id)

        for (const scenario of toRun) {
            await handleExecute(scenario.id, scenario.test_case_id)
        }
        setIsBatchExecuting(false)
    }

    const toggleSelectAll = () => {
        if (selectedIds.size === filteredScenarios.length) {
            setSelectedIds(new Set())
        } else {
            setSelectedIds(new Set(filteredScenarios.map(s => s.id)))
        }
    }

    const toggleSelect = (e: React.MouseEvent, id: number) => {
        e.stopPropagation()
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            return next
        })
    }

    const toggleExpand = (scenarioId: number) => {
        setExpandedScenarios(prev => {
            const next = new Set(prev)
            if (next.has(scenarioId)) next.delete(scenarioId)
            else next.add(scenarioId)
            return next
        })
    }

    const togglePreview = (scenarioId: number) => {
        setPreviewScenarios(prev => {
            const next = new Set(prev)
            if (next.has(scenarioId)) next.delete(scenarioId)
            else next.add(scenarioId)
            return next
        })
    }

    const toggleStepExpand = (scenarioId: number, stepOrder: number) => {
        const key = `${scenarioId}_${stepOrder}`
        setExpandedSteps(prev => {
            const next = new Set(prev)
            if (next.has(key)) next.delete(key)
            else next.add(key)
            return next
        })
    }

    const projects = Array.from(new Set([...allProjects, ...scenarios.map(s => s.project_id || 'default-project')]))
    const filteredScenarios = scenarios.filter(s =>
        selectedProject === 'all' || (s.project_id || 'default-project') === selectedProject
    )

    return (
        <div style={{ padding: '1rem 0' }}>
            {/* 顶栏 */}
            <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <div>
                    <h1 style={{ fontSize: '2rem', fontWeight: '700', color: '#111827', marginBottom: '0.5rem' }}>
                        📋 测试管理
                    </h1>
                    <p style={{ color: '#6B7280' }}>
                        管理测试环境与执行场景用例
                    </p>
                </div>
                {selectedProject !== 'all' && (
                    <button
                        onClick={() => setShowEnvConfig(true)}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '0.5rem',
                            padding: '0.5rem 1rem', background: 'white', border: '1px solid #E5E7EB',
                            borderRadius: '0.5rem', color: '#374151', fontSize: '0.875rem', fontWeight: '500',
                            cursor: 'pointer', transition: 'all 0.2s'
                        }}
                    >
                        <Settings size={18} /> 项目环境配置
                    </button>
                )}
            </div>

            {/* 环境配置弹窗 */}
            {showEnvConfig && (
                <div style={{
                    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100
                }}>
                    <div style={{ background: 'white', width: '32rem', borderRadius: '1rem', padding: '1.5rem', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <h3 style={{ fontSize: '1.25rem', fontWeight: '700' }}>【{selectedProject}】环境域名配置</h3>
                            <button onClick={() => setShowEnvConfig(false)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#6B7280' }}><X size={24} /></button>
                        </div>

                        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
                            <input placeholder="环境名(如 test)" value={newEnvName} onChange={e => setNewEnvName(e.target.value)} style={{ flex: 1, padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem' }} />
                            <input placeholder="Base URL" value={newEnvUrl} onChange={e => setNewEnvUrl(e.target.value)} style={{ flex: 2, padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem' }} />
                            <button onClick={handleSaveEnv} style={{ background: '#3B82F6', color: 'white', padding: '0.5rem 1rem', border: 'none', borderRadius: '0.375rem', cursor: 'pointer' }}><Plus size={20} /></button>
                        </div>

                        <div style={{ maxHeight: '20rem', overflowY: 'auto' }}>
                            {environments.length === 0 ? (
                                <p style={{ textAlign: 'center', color: '#9CA3AF', padding: '1rem' }}>暂无配置，请添加接口对应的域名</p>
                            ) : (
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <thead style={{ background: '#F9FAFB' }}>
                                        <tr>
                                            <th style={{ textAlign: 'left', padding: '0.75rem', fontSize: '0.75rem', color: '#6B7280' }}>状态</th>
                                            <th style={{ textAlign: 'left', padding: '0.75rem', fontSize: '0.75rem', color: '#6B7280' }}>环境名</th>
                                            <th style={{ textAlign: 'left', padding: '0.75rem', fontSize: '0.75rem', color: '#6B7280' }}>域名</th>
                                            <th style={{ width: '4rem' }}></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {environments.map(env => (
                                            <tr key={env.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                                <td style={{ padding: '0.75rem' }}>{env.is_default ? '✅' : '-'}</td>
                                                <td style={{ padding: '0.75rem', fontWeight: '500' }}>{env.env_name}</td>
                                                <td style={{ padding: '0.75rem', color: '#6B7280', fontSize: '0.8125rem' }}>{env.base_url}</td>
                                                <td>
                                                    <button onClick={() => handleDeleteEnv(env.env_name)} style={{ border: 'none', background: 'none', color: '#EF4444', cursor: 'pointer' }}><Trash2 size={16} /></button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* 批量操作与统计 */}
            <div style={{
                background: 'rgba(255, 255, 255, 0.8)', backdropFilter: 'blur(10px)',
                borderRadius: '1rem', padding: '1.5rem', marginBottom: '2rem',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)', border: '1px solid rgba(255, 255, 255, 0.2)',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Filter size={18} style={{ color: '#6B7280' }} />
                        <select
                            value={selectedProject}
                            onChange={(e) => setSelectedProject(e.target.value)}
                            style={{ padding: '0.5rem 1rem', border: '1px solid #E5E7EB', borderRadius: '0.5rem', outline: 'none', background: 'white' }}
                        >
                            <option value="all">所有项目</option>
                            {projects.map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                    </div>

                    {selectedProject !== 'all' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <Globe size={18} style={{ color: '#6B7280' }} />
                            <select
                                value={selectedEnvId || ''}
                                onChange={(e) => setSelectedEnvId(Number(e.target.value))}
                                style={{ padding: '0.5rem 1rem', border: '1px solid #E5E7EB', borderRadius: '0.5rem', outline: 'none', background: 'white' }}
                            >
                                <option value="">使用默认域名</option>
                                {environments.map(e => <option key={e.id} value={e.id}>{e.env_name} ({e.base_url})</option>)}
                            </select>
                        </div>
                    )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <button
                        onClick={handleBatchExecute}
                        disabled={selectedIds.size === 0 || isBatchExecuting}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '0.5rem',
                            padding: '0.6rem 1.25rem', background: selectedIds.size > 0 ? 'linear-gradient(to right, #4F46E5, #7C3AED)' : '#E5E7EB',
                            color: 'white', borderRadius: '0.75rem', border: 'none',
                            fontWeight: '600', cursor: selectedIds.size > 0 ? 'pointer' : 'not-allowed',
                            boxShadow: selectedIds.size > 0 ? '0 10px 15px -3px rgba(79, 70, 229, 0.4)' : 'none',
                            transition: 'all 0.2s'
                        }}
                    >
                        <ListChecks size={20} />
                        {isBatchExecuting ? '正在批量执行...' : `批量执行 (${selectedIds.size})`}
                    </button>
                    <div style={{ width: '1px', height: '2rem', background: '#E5E7EB' }}></div>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <div style={{ textAlign: 'center' }}><p style={{ fontSize: '0.75rem', color: '#6B7280', margin: 0 }}>总场景</p><p style={{ fontWeight: '700', margin: 0 }}>{filteredScenarios.length}</p></div>
                        <div style={{ textAlign: 'center' }}><p style={{ fontSize: '0.75rem', color: '#6B7280', margin: 0 }}>已选</p><p style={{ fontWeight: '700', margin: 0, color: '#4F46E5' }}>{selectedIds.size}</p></div>
                    </div>
                </div>
            </div>

            {/* 场景列表 */}
            {loading ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: '#6B7280' }}>加载中...</div>
            ) : filteredScenarios.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '5rem', background: 'white', borderRadius: '1rem' }}>
                    <Database size={64} style={{ color: '#E5E7EB', marginBottom: '1.5rem' }} />
                    <p style={{ color: '#6B7280', fontSize: '1.125rem' }}>暂无测试场景，请先去首页生成意图</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', padding: '0 1rem', marginBottom: '-0.5rem' }}>
                        <input
                            type="checkbox"
                            checked={selectedIds.size === filteredScenarios.length && filteredScenarios.length > 0}
                            onChange={toggleSelectAll}
                            style={{ width: '1.25rem', height: '1.25rem', cursor: 'pointer' }}
                        />
                        <span style={{ marginLeft: '1rem', fontSize: '0.875rem', color: '#6B7280', fontWeight: '500' }}>全选所有场景</span>
                    </div>

                    {filteredScenarios.map((scenario) => (
                        <div key={scenario.id} style={{
                            background: 'white', borderRadius: '1rem', padding: '1.5rem',
                            border: '1px solid #E5E7EB', position: 'relative', overflow: 'hidden',
                            display: 'flex', gap: '1.5rem'
                        }}>
                            <div style={{ display: 'flex', flexDirection: 'column', paddingTop: '0.2rem' }}>
                                <input
                                    type="checkbox"
                                    checked={selectedIds.has(scenario.id)}
                                    onChange={(e) => { }}
                                    onClick={(e) => toggleSelect(e, scenario.id)}
                                    style={{ width: '1.25rem', height: '1.25rem', cursor: 'pointer' }}
                                />
                            </div>

                            <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                                            <h3 style={{ fontSize: '1.125rem', fontWeight: '700', color: '#111827', margin: 0 }}>
                                                {scenario.name || '未命名场景'}
                                            </h3>
                                            <span style={{ fontSize: '0.7rem', background: '#F3F4F6', color: '#6B7280', padding: '0.15rem 0.5rem', borderRadius: '1rem' }}>
                                                ID: {scenario.id}
                                            </span>
                                        </div>
                                        <p style={{ fontSize: '0.875rem', color: '#6B7280', lineHeight: '1.5' }}>
                                            {scenario.description || scenario.natural_language_input}
                                        </p>
                                    </div>

                                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                                        <button
                                            onClick={() => scenario.test_case_id && handleExecute(scenario.id, scenario.test_case_id)}
                                            disabled={!scenario.test_case_id || executingIds.has(scenario.id)}
                                            style={{
                                                display: 'flex', alignItems: 'center', gap: '0.5rem', paddingLeft: '1rem', paddingRight: '1rem', paddingTop: '0.5rem', paddingBottom: '0.5rem',
                                                background: executingIds.has(scenario.id) ? '#9CA3AF' :
                                                    scenario.test_case_id ? 'linear-gradient(to right, #10B981, #059669)' : '#DBEAFE',
                                                color: scenario.test_case_id ? 'white' : '#3B82F6',
                                                border: 'none', borderRadius: '0.5rem', fontWeight: '600', fontSize: '0.875rem',
                                                cursor: (scenario.test_case_id && !executingIds.has(scenario.id)) ? 'pointer' : 'not-allowed',
                                                transition: 'all 0.2s', boxShadow: scenario.test_case_id && !executingIds.has(scenario.id) ? '0 4px 6px -1px rgba(16, 185, 129, 0.3)' : 'none'
                                            }}
                                        >
                                            <Play size={16} fill="currentColor" />
                                            执行测试
                                        </button>
                                        <button
                                            onClick={(e) => handleDelete(e, scenario.id)}
                                            disabled={isDeleting === scenario.id}
                                            style={{
                                                padding: '0.5rem',
                                                color: '#EF4444', background: '#FEF2F2', border: '1px solid #FECACA',
                                                borderRadius: '0.5rem', cursor: 'pointer', transition: 'all 0.2s'
                                            }}
                                            title="物理删除场景及用例"
                                        >
                                            <Trash2 size={18} />
                                        </button>
                                    </div>
                                </div>

                                {/* 编排预览 */}
                                {scenario.test_case_steps && (
                                    <div style={{ marginBottom: '1rem' }}>
                                        <div onClick={() => togglePreview(scenario.id)} style={{
                                            fontSize: '0.75rem', color: '#2563EB', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
                                            padding: '0.4rem 0.75rem', background: '#EFF6FF', borderRadius: '0.5rem', border: '1px solid #DBEAFE'
                                        }}>
                                            <FileText size={14} />
                                            编排详情: {JSON.parse(scenario.test_case_steps).length} 个步骤
                                            {previewScenarios.has(scenario.id) ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                        </div>
                                        {previewScenarios.has(scenario.id) && (
                                            <div style={{ marginTop: '0.75rem', padding: '1rem', background: '#F8FAFC', borderRadius: '0.75rem', border: '1px solid #E2E8F0' }}>
                                                {JSON.parse(scenario.test_case_steps).map((step: any, idx: number) => (
                                                    <div key={idx} style={{ fontSize: '0.8125rem', display: 'flex', gap: '1rem', padding: '0.5rem 0', borderBottom: idx === JSON.parse(scenario.test_case_steps).length - 1 ? 'none' : '1px dashed #E2E8F0' }}>
                                                        <b style={{ color: '#94A3B8', minWidth: '1.5rem' }}>{step.step_order}.</b>
                                                        <span style={{ fontWeight: '800', color: step.api_method === 'POST' ? '#3B82F6' : '#10B981', minWidth: '40px' }}>{step.api_method}</span>
                                                        <code style={{ fontFamily: 'monospace', color: '#334155' }}>{step.api_path}</code>
                                                        <span style={{ color: '#64748B' }}>- {step.description}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* 执行结果 */}
                                {executionResults[scenario.id] && (
                                    <div style={{ marginTop: '1.5rem' }}>
                                        <div onClick={() => toggleExpand(scenario.id)} style={{
                                            padding: '1rem', borderRadius: '0.75rem', fontSize: '0.9375rem', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                            background: executionResults[scenario.id].error ? '#FEF2F2' : '#F0FDF4',
                                            color: executionResults[scenario.id].error ? '#B91C1C' : '#166534',
                                            border: `1px solid ${executionResults[scenario.id].error ? '#FECACA' : '#BBF7D0'}`
                                        }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                {executionResults[scenario.id].error ? <XCircle size={20} /> : <CheckCircle size={20} />}
                                                <b>{executionResults[scenario.id].error ? `执行失败: ${executionResults[scenario.id].error}` : `执行完成: ${executionResults[scenario.id].status === 'success' ? '全部通过' : '存在异常'}`}</b>
                                            </div>
                                            {expandedScenarios.has(scenario.id) ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                                        </div>

                                        {expandedScenarios.has(scenario.id) && executionResults[scenario.id].results && (
                                            <div style={{ border: '1px solid #E5E7EB', borderRadius: '0.75rem', marginTop: '0.5rem', overflow: 'hidden' }}>
                                                {executionResults[scenario.id].results.map((res: any, idx: number) => {
                                                    const stepKey = `${scenario.id}_${res.step_order}`
                                                    return (
                                                        <div key={idx} style={{ borderBottom: idx === executionResults[scenario.id].results.length - 1 ? 'none' : '1px solid #F3F4F6' }}>
                                                            <div
                                                                onClick={() => toggleStepExpand(scenario.id, res.step_order)}
                                                                style={{
                                                                    padding: '1rem', display: 'flex', alignItems: 'center', gap: '1rem',
                                                                    background: res.success ? 'white' : '#FFF1F2',
                                                                    cursor: 'pointer'
                                                                }}
                                                            >
                                                                <span style={{
                                                                    width: '1.75rem', height: '1.75rem', borderRadius: '50%', background: res.success ? '#10B981' : '#EF4444',
                                                                    color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '0.75rem'
                                                                }}>{res.step_order}</span>
                                                                <div style={{ flex: 1 }}>
                                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                                        <span style={{ fontSize: '0.7rem', fontWeight: '700', borderRadius: '4px', background: '#E2E8F0', padding: '1px 4px' }}>{res.method}</span>
                                                                        <code style={{ fontSize: '0.8125rem', color: '#64748B', wordBreak: 'break-all' }}>{res.url}</code>
                                                                        <span style={{ fontSize: '0.875rem', fontWeight: '700', color: res.success ? '#059669' : '#DC2626' }}>{res.status_code}</span>
                                                                    </div>
                                                                    {res.error && <p style={{ margin: '0.5rem 0 0', fontSize: '0.75rem', color: '#EF4444' }}>{res.error}</p>}
                                                                </div>
                                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                    <span style={{ fontSize: '0.75rem', color: '#94A3B8' }}>{res.duration ? `${(res.duration * 1000).toFixed(0)}ms` : '-'}</span>
                                                                    {expandedSteps.has(stepKey) ? <ChevronUp size={16} color="#94A3B8" /> : <ChevronDown size={16} color="#94A3B8" />}
                                                                </div>
                                                            </div>

                                                            {expandedSteps.has(stepKey) && (
                                                                <div style={{ padding: '0 1rem 1rem 3.75rem', fontSize: '0.75rem' }}>
                                                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                                                        <div>
                                                                            <p style={{ fontWeight: '600', color: '#475569', marginBottom: '0.25rem' }}>请求内容 (Request):</p>
                                                                            <pre style={{ background: '#F8FAFC', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #E2E8F0', overflowX: 'auto' }}>
                                                                                {JSON.stringify(res.request_data, null, 2)}
                                                                            </pre>
                                                                        </div>
                                                                        <div>
                                                                            <p style={{ fontWeight: '600', color: '#475569', marginBottom: '0.25rem' }}>响应结果 (Response):</p>
                                                                            <pre style={{ background: '#F8FAFC', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #E2E8F0', overflowX: 'auto', maxHeight: '20rem' }}>
                                                                                {typeof res.response === 'string' ? res.response : JSON.stringify(res.response, null, 2)}
                                                                            </pre>
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
            {/* 通用确认模态框 */}
            {showConfirm.show && (
                <div style={{
                    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
                    backdropFilter: 'blur(4px)'
                }}>
                    <div style={{
                        background: 'white', width: '28rem', borderRadius: '1rem', padding: '2rem',
                        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)',
                        animation: 'confirm-in 0.2s ease-out'
                    }}>
                        <h3 style={{ fontSize: '1.25rem', fontWeight: '800', marginBottom: '1rem', color: '#1E293B' }}>
                            {showConfirm.type === 'danger' && <span style={{ marginRight: '0.5rem' }}>⚠️</span>}
                            {showConfirm.title}
                        </h3>
                        <p style={{ color: '#64748B', lineHeight: '1.6', marginBottom: '2rem' }}>
                            {showConfirm.message}
                        </p>
                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => setShowConfirm(prev => ({ ...prev, show: false }))}
                                style={{
                                    padding: '0.6rem 1.5rem', background: '#F1F5F9', color: '#475569',
                                    border: 'none', borderRadius: '0.6rem', fontWeight: '600', cursor: 'pointer'
                                }}
                            >
                                取消
                            </button>
                            <button
                                onClick={showConfirm.onConfirm}
                                style={{
                                    padding: '0.6rem 1.5rem',
                                    background: showConfirm.type === 'danger' ? '#EF4444' : '#3B82F6',
                                    color: 'white', border: 'none', borderRadius: '0.6rem',
                                    fontWeight: '600', cursor: 'pointer',
                                    boxShadow: showConfirm.type === 'danger' ? '0 10px 15px -3px rgba(239, 68, 68, 0.4)' : 'none'
                                }}
                            >
                                确定
                            </button>
                        </div>
                    </div>
                    <style>{`
                        @keyframes confirm-in {
                            from { transform: scale(0.95); opacity: 0; }
                            to { transform: scale(1); opacity: 1; }
                        }
                    `}</style>
                </div>
            )}
        </div>
    )
}
