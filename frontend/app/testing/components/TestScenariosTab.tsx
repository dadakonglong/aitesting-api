'use client'

import { useState, useEffect } from 'react'
import { Play, Clock, CheckCircle, XCircle, FileText, ChevronDown, ChevronUp, Trash2, Filter, Database, Settings, Plus, X, Globe, ListChecks, AlertCircle } from 'lucide-react'
import { useProject } from '../../contexts/ProjectContext'

export default function TestScenariosTab() {
    const { currentProject } = useProject()
    const [scenarios, setScenarios] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [executingIds, setExecutingIds] = useState<Set<number>>(new Set())
    const [executionResults, setExecutionResults] = useState<Record<number, any>>({})
    const [expandedScenarios, setExpandedScenarios] = useState<Set<number>>(new Set())
    const [previewScenarios, setPreviewScenarios] = useState<Set<number>>(new Set())
    const [isDeleting, setIsDeleting] = useState<number | null>(null)
    const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set()) // scenarioId_stepOrder
    const [activeStepTab, setActiveStepTab] = useState<Record<string, string>>({}) // key: scenarioId_stepOrder, value: tab name
    const [executingSingleStep, setExecutingSingleStep] = useState<string | null>(null) // scenarioId_stepOrder
    const [singleStepResults, setSingleStepResults] = useState<Record<string, any>>({}) // key: scenarioId_stepOrder

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

    // 定时任务相关
    const [showSchedulerModal, setShowSchedulerModal] = useState(false)
    const [schedulerScenario, setSchedulerScenario] = useState<any>(null)
    const [schedulerForm, setSchedulerForm] = useState({
        name: '',
        cron: '0 2 * * *',
        timeMode: 'preset' as 'preset' | 'custom',
        customHour: '9',
        customMinute: '0',
        frequency: 'daily' as 'daily' | 'hourly' | 'weekly' | 'once',
        weekday: '1',
        environment_id: null as number | null,
        use_project_webhook: true,
        custom_webhook: '',
        is_active: true
    })
    const [projectFeishuWebhook, setProjectFeishuWebhook] = useState('')

    useEffect(() => {
        const init = async () => {
            const scenarioData = await fetchScenarios()
            if (scenarioData) {
                fetchHistory(currentProject, scenarioData)
            }
        }
        init()
    }, [currentProject])

    useEffect(() => {
        fetchEnvironments(currentProject)
    }, [currentProject])


    const fetchHistory = async (projectId: string, scenarioData: any[]) => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/executions?project_id=${projectId}&limit=50`)
            if (response.ok) {
                const history = await response.json()
                const resultsMap: Record<number, any> = {}
                history.forEach((exec: any) => {
                    const scenario = scenarioData.find(s => String(s.test_case_id) === String(exec.test_case_id))
                    if (scenario && !resultsMap[scenario.id]) {
                        resultsMap[scenario.id] = exec
                    }
                })
                setExecutionResults(prev => ({ ...prev, ...resultsMap }))
            }
        } catch (error) {
            console.error('获取执行历史失败:', error)
        }
    }



    const fetchScenarios = async () => {
        setLoading(true)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scenarios`)
            if (response.ok) {
                const data = await response.json()
                setScenarios(data)
                return data
            }
        } catch (error) {
            console.error('获取场景列表失败:', error)
        } finally {
            setLoading(false)
        }
        return null
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
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/projects/${currentProject}/environments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    env_name: newEnvName,
                    base_url: newEnvUrl,
                    is_default: environments.length === 0
                })
            })
            if (response.ok) {
                fetchEnvironments(currentProject)
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
                    const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/projects/${currentProject}/environments/${envName}`, {
                        method: 'DELETE'
                    })
                    if (response.ok) {
                        fetchEnvironments(currentProject)
                    }
                } catch (error) {
                    console.error('删除环境失败:', error)
                }
                setShowConfirm(prev => ({ ...prev, show: false }))
            }
        })
    }

    // 定时任务相关函数
    const handleOpenScheduler = (scenario: any) => {
        setSchedulerScenario(scenario)
        setSchedulerForm({
            name: `定时执行-${scenario.name}`,
            cron: '0 2 * * *',
            timeMode: 'preset',
            customHour: '9',
            customMinute: '0',
            frequency: 'daily',
            weekday: '1',
            environment_id: selectedEnvId,
            use_project_webhook: true,
            custom_webhook: '',
            is_active: true
        })
        setShowSchedulerModal(true)
    }

    const handleCreateScheduledJob = async () => {
        if (!schedulerScenario) return

        try {
            const notificationConfig = {
                type: 'feishu',
                webhook_url: schedulerForm.use_project_webhook ? projectFeishuWebhook : schedulerForm.custom_webhook,
                use_project_default: schedulerForm.use_project_webhook,
                enabled: true,
                notify_always: true
            }

            const finalCron = generateCron()

            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: schedulerForm.name,
                    description: `场景: ${schedulerScenario.name}`,
                    project_id: currentProject,
                    scenario_id: schedulerScenario.id,
                    cron: finalCron,
                    environment_id: schedulerForm.environment_id,
                    notification_config: JSON.stringify(notificationConfig),
                    is_active: schedulerForm.is_active
                })
            })

            if (response.ok) {
                alert('定时任务创建成功！')
                setShowSchedulerModal(false)
            } else {
                const error = await response.json()
                alert(`创建失败: ${error.detail || '未知错误'}`)
            }
        } catch (error) {
            console.error('创建定时任务失败:', error)
            alert('创建失败，请检查网络连接')
        }
    }

    const cronPresets = [
        { label: '立即执行（1分钟后）', value: 'now' },
        { label: '每天凌晨2点', value: '0 2 * * *' },
        { label: '每天上午9点', value: '0 9 * * *' },
        { label: '每小时', value: '0 * * * *' },
        { label: '每30分钟', value: '*/30 * * * *' },
        { label: '每周一上午9点', value: '0 9 * * 1' },
        { label: '自定义时间', value: 'custom' }
    ]

    // 生成Cron表达式
    const generateCron = () => {
        if (schedulerForm.timeMode === 'preset') {
            if (schedulerForm.cron === 'now') {
                const now = new Date()
                now.setMinutes(now.getMinutes() + 1)
                return `${now.getMinutes()} ${now.getHours()} * * *`
            }
            return schedulerForm.cron === 'custom' ? `${schedulerForm.customMinute} ${schedulerForm.customHour} * * *` : schedulerForm.cron
        } else {
            // 自定义模式
            const { customHour, customMinute, frequency, weekday } = schedulerForm
            if (frequency === 'daily') {
                return `${customMinute} ${customHour} * * *`
            } else if (frequency === 'hourly') {
                return `${customMinute} * * * *`
            } else if (frequency === 'weekly') {
                return `${customMinute} ${customHour} * * ${weekday}`
            } else {
                return `${customMinute} ${customHour} * * *`
            }
        }
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

    const handleDeleteStep = async (scenarioId: number, testCaseId: number, stepOrder: number) => {
        if (!confirm(`确定要删除第 ${stepOrder} 步吗？`)) return

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/test_cases/${testCaseId}/steps/${stepOrder}`, {
                method: 'DELETE'
            })
            if (response.ok) {
                const data = await response.json()
                // 更新本地状态：找到对应场景并更新其 test_case_steps
                setScenarios(prev => prev.map(s => {
                    if (s.id === scenarioId) {
                        return { ...s, test_case_steps: JSON.stringify(data.steps) }
                    }
                    return s
                }))
            } else {
                alert('删除步骤失败，请稍后重试')
            }
        } catch (error) {
            console.error('删除步骤出错:', error)
        }
    }

    const handleSingleStepExecute = async (scenarioId: number, step: any) => {
        const stepKey = `${scenarioId}_${step.step_order}`
        setExecutingSingleStep(stepKey)
        const env = environments.find(e => e.id === selectedEnvId)
        const baseUrl = env ? env.base_url : 'http://localhost:8000'

        // 检查是否有参数映射依赖
        if (step.param_mappings && step.param_mappings.length > 0) {
            const dependentSteps = step.param_mappings.map((m: any) => m.from_step).filter(Boolean)
            if (dependentSteps.length > 0) {
                const confirmed = confirm(
                    `⚠️ 此接口依赖步骤 ${dependentSteps.join(', ')} 的数据。\n\n` +
                    `单独执行时无法获取依赖数据,可能导致执行失败。\n\n` +
                    `建议执行完整场景,或确保已手动配置所需参数。\n\n` +
                    `是否继续执行?`
                )
                if (!confirmed) {
                    setExecutingSingleStep(null)
                    return
                }
            }
        }

        try {
            // 直接发送步骤数组,不需要test_case_id
            const requestBody = {
                environment: env?.env_name || 'test',
                base_url: baseUrl,
                steps: [step]
            }

            const response = await fetch(`${process.env.NEXT_PUBLIC_EXEC_API_URL}/api/v1/executions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            })

            if (response.ok) {
                const execution = await response.json()
                setSingleStepResults(prev => ({ ...prev, [stepKey]: execution.results[0] }))
                // 自动展开结果
                setExpandedSteps(prev => new Set(prev).add(stepKey))
                setActiveStepTab(prev => ({ ...prev, [stepKey]: '响应体' }))
            } else {
                const errData = await response.json().catch(() => ({}))
                throw new Error(errData.detail || '接口执行失败')
            }
        } catch (error: any) {
            setSingleStepResults(prev => ({
                ...prev,
                [stepKey]: {
                    success: false,
                    error: error.message || '执行失败',
                    status_code: 'Error'
                }
            }))
        } finally {
            setExecutingSingleStep(null)
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
            if (next.has(key)) {
                next.delete(key)
            } else {
                next.add(key)
                // 默认显示"提取"标签页(核心功能)
                setActiveStepTab(prev => ({ ...prev, [key]: '提取' }))
            }
            return next
        })
    }

    const filteredScenarios = scenarios.filter(s =>
        (s.project_id || 'default-project') === currentProject
    )

    return (
        <>
            {/* 环境配置按钮 */}
            <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
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
            </div>

            {/* 环境配置弹窗 */}
            {showEnvConfig && (
                <div style={{
                    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100
                }}>
                    <div style={{ background: 'white', width: '40rem', maxHeight: '80vh', borderRadius: '1rem', padding: '1.5rem', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)', display: 'flex', flexDirection: 'column' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <h3 style={{ fontSize: '1.25rem', fontWeight: '700' }}>
                                【{currentProject}】环境域名配置
                            </h3>
                            <button onClick={() => setShowEnvConfig(false)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#6B7280' }}><X size={24} /></button>
                        </div>

                        {/* 添加环境表单 */}
                        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
                            <input placeholder="环境名(如 test)" value={newEnvName} onChange={e => setNewEnvName(e.target.value)} style={{ flex: 1, padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem' }} />
                            <input placeholder="Base URL" value={newEnvUrl} onChange={e => setNewEnvUrl(e.target.value)} style={{ flex: 2, padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem' }} />
                            <button onClick={handleSaveEnv} style={{ background: '#3B82F6', color: 'white', padding: '0.5rem 1rem', border: 'none', borderRadius: '0.375rem', cursor: 'pointer' }}><Plus size={20} /></button>
                        </div>

                        <div style={{ flex: 1, overflowY: 'auto' }}>
                            {environments.length === 0 ? (
                                <p style={{ textAlign: 'center', color: '#9CA3AF', padding: '1rem' }}>暂无配置,请添加接口对应的域名</p>
                            ) : (
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <thead style={{ background: '#F9FAFB', position: 'sticky', top: 0 }}>
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
                        <Globe size={18} style={{ color: '#6B7280' }} />
                        <select
                            value={selectedEnvId || ''}
                            onChange={(e) => setSelectedEnvId(Number(e.target.value))}
                            style={{ padding: '0.5rem 1rem', border: '1px solid #E5E7EB', borderRadius: '0.5rem', outline: 'none', background: 'white' }}
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
                                            onClick={(e) => { e.stopPropagation(); handleOpenScheduler(scenario); }}
                                            disabled={!scenario.test_case_id}
                                            style={{
                                                padding: '0.5rem',
                                                color: scenario.test_case_id ? '#667eea' : '#9CA3AF',
                                                background: scenario.test_case_id ? '#EEF2FF' : '#F3F4F6',
                                                border: `1px solid ${scenario.test_case_id ? '#C7D2FE' : '#E5E7EB'}`,
                                                borderRadius: '0.5rem',
                                                cursor: scenario.test_case_id ? 'pointer' : 'not-allowed',
                                                transition: 'all 0.2s'
                                            }}
                                            title="设置定时任务"
                                        >
                                            <Clock size={18} />
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
                                                {JSON.parse(scenario.test_case_steps).map((step: any, idx: number) => {
                                                    const stepKey = `${scenario.id}_${step.step_order}`
                                                    const singleResult = singleStepResults[stepKey]
                                                    const isExecuting = executingSingleStep === stepKey

                                                    return (
                                                        <div key={idx} style={{ marginBottom: idx === JSON.parse(scenario.test_case_steps).length - 1 ? 0 : '1rem' }}>
                                                            {/* 步骤信息和执行按钮 */}
                                                            <div style={{ fontSize: '0.8125rem', display: 'flex', gap: '1rem', padding: '0.5rem 0', alignItems: 'center' }}>
                                                                <b style={{ color: '#94A3B8', minWidth: '1.5rem' }}>{step.step_order}.</b>
                                                                <span style={{ fontWeight: '800', color: step.api_method === 'POST' ? '#3B82F6' : '#10B981', minWidth: '40px' }}>{step.api_method}</span>
                                                                <code style={{ fontFamily: 'monospace', color: '#334155', flex: 1 }}>{step.api_path}</code>
                                                                <span style={{ color: '#64748B' }}>- {step.description}</span>
                                                                {/* 依赖提示 */}
                                                                {step.param_mappings && step.param_mappings.length > 0 && (
                                                                    <span
                                                                        style={{
                                                                            fontSize: '0.7rem',
                                                                            color: '#F59E0B',
                                                                            background: '#FEF3C7',
                                                                            padding: '0.125rem 0.5rem',
                                                                            borderRadius: '0.25rem',
                                                                            display: 'flex',
                                                                            alignItems: 'center',
                                                                            gap: '0.25rem'
                                                                        }}
                                                                        title={`依赖步骤: ${step.param_mappings.map((m: any) => m.from_step).filter(Boolean).join(', ')}`}
                                                                    >
                                                                        <AlertCircle size={12} />
                                                                        依赖
                                                                    </span>
                                                                )}
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation()
                                                                        handleSingleStepExecute(scenario.id, step)
                                                                    }}
                                                                    disabled={isExecuting}
                                                                    style={{
                                                                        padding: '0.25rem 0.75rem',
                                                                        fontSize: '0.75rem',
                                                                        color: isExecuting ? '#9CA3AF' : '#3B82F6',
                                                                        background: isExecuting ? '#F3F4F6' : '#EFF6FF',
                                                                        border: `1px solid ${isExecuting ? '#E5E7EB' : '#DBEAFE'}`,
                                                                        borderRadius: '0.375rem',
                                                                        cursor: isExecuting ? 'not-allowed' : 'pointer',
                                                                        display: 'flex',
                                                                        alignItems: 'center',
                                                                        gap: '0.25rem',
                                                                        transition: 'all 0.2s',
                                                                        whiteSpace: 'nowrap'
                                                                    }}
                                                                    title="单独执行此接口"
                                                                >
                                                                    <Play size={12} fill="currentColor" />
                                                                    {isExecuting ? '执行中...' : '执行'}
                                                                </button>
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation()
                                                                        handleDeleteStep(scenario.id, scenario.test_case_id, step.step_order)
                                                                    }}
                                                                    style={{
                                                                        padding: '0.25rem',
                                                                        color: '#EF4444',
                                                                        background: 'none',
                                                                        border: 'none',
                                                                        cursor: 'pointer',
                                                                        display: 'flex',
                                                                        alignItems: 'center',
                                                                        justifyContent: 'center',
                                                                        borderRadius: '0.25rem',
                                                                        transition: 'all 0.2s'
                                                                    }}
                                                                    title="删除此步骤"
                                                                >
                                                                    <Trash2 size={14} />
                                                                </button>
                                                            </div>

                                                            {/* 单步执行结果 */}
                                                            {singleResult && (
                                                                <div style={{ marginTop: '0.5rem', marginLeft: '2.5rem' }}>
                                                                    <div
                                                                        onClick={() => toggleStepExpand(scenario.id, step.step_order)}
                                                                        style={{
                                                                            padding: '0.5rem 0.75rem',
                                                                            borderRadius: '0.5rem',
                                                                            fontSize: '0.75rem',
                                                                            cursor: 'pointer',
                                                                            display: 'flex',
                                                                            justifyContent: 'space-between',
                                                                            alignItems: 'center',
                                                                            background: singleResult.error || !singleResult.success ? '#FEF2F2' : '#F0FDF4',
                                                                            color: singleResult.error || !singleResult.success ? '#B91C1C' : '#166534',
                                                                            border: `1px solid ${singleResult.error || !singleResult.success ? '#FECACA' : '#BBF7D0'}`
                                                                        }}
                                                                    >
                                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                            {singleResult.error || !singleResult.success ? <XCircle size={14} /> : <CheckCircle size={14} />}
                                                                            <span>{singleResult.error || (singleResult.success ? `成功: ${singleResult.status_code}` : `失败: ${singleResult.status_code}`)}</span>
                                                                        </div>
                                                                        {expandedSteps.has(stepKey) ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                                                    </div>

                                                                    {/* 简化的结果展示 */}
                                                                    {expandedSteps.has(stepKey) && (
                                                                        <div style={{ padding: '0.75rem', marginTop: '0.5rem', background: 'white', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                                                                            <div style={{ display: 'flex', borderBottom: '2px solid #E5E7EB', marginBottom: '0.75rem' }}>
                                                                                {['响应体', '响应头', '请求内容'].map(tab => (
                                                                                    <button
                                                                                        key={tab}
                                                                                        onClick={(e) => {
                                                                                            e.stopPropagation()
                                                                                            setActiveStepTab(prev => ({ ...prev, [stepKey]: tab }))
                                                                                        }}
                                                                                        style={{
                                                                                            padding: '0.5rem 1rem',
                                                                                            background: (activeStepTab[stepKey] || '响应体') === tab ? '#3B82F6' : 'transparent',
                                                                                            color: (activeStepTab[stepKey] || '响应体') === tab ? 'white' : '#6B7280',
                                                                                            border: 'none',
                                                                                            cursor: 'pointer',
                                                                                            fontWeight: (activeStepTab[stepKey] || '响应体') === tab ? '600' : '400',
                                                                                            fontSize: '0.75rem'
                                                                                        }}
                                                                                    >
                                                                                        {tab}
                                                                                    </button>
                                                                                ))}
                                                                            </div>
                                                                            <div style={{ fontSize: '0.75rem' }}>
                                                                                {(activeStepTab[stepKey] || '响应体') === '响应体' && (
                                                                                    <pre style={{ background: '#F8FAFC', padding: '0.75rem', borderRadius: '0.5rem', overflow: 'auto', maxHeight: '300px', fontSize: '0.7rem', margin: 0 }}>
                                                                                        {typeof singleResult.response === 'string' ? singleResult.response : JSON.stringify(singleResult.response, null, 2)}
                                                                                    </pre>
                                                                                )}
                                                                                {(activeStepTab[stepKey] || '响应体') === '响应头' && singleResult.response_headers && (
                                                                                    <div style={{ fontSize: '0.7rem' }}>
                                                                                        {Object.entries(singleResult.response_headers).map(([key, value]: [string, any]) => (
                                                                                            <div key={key} style={{ padding: '0.25rem 0', borderBottom: '1px solid #F3F4F6' }}>
                                                                                                <b>{key}:</b> {Array.isArray(value) ? value.join(', ') : String(value)}
                                                                                            </div>
                                                                                        ))}
                                                                                    </div>
                                                                                )}
                                                                                {(activeStepTab[stepKey] || '响应体') === '请求内容' && (
                                                                                    <pre style={{ background: '#F8FAFC', padding: '0.75rem', borderRadius: '0.5rem', overflow: 'auto', maxHeight: '300px', fontSize: '0.7rem', margin: 0 }}>
                                                                                        {JSON.stringify(singleResult.request_data, null, 2)}
                                                                                    </pre>
                                                                                )}
                                                                            </div>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            )}

                                                            {/* 分隔线 */}
                                                            {idx !== JSON.parse(scenario.test_case_steps).length - 1 && !singleResult && (
                                                                <div style={{ borderBottom: '1px dashed #E2E8F0', marginTop: '0.5rem' }} />
                                                            )}
                                                        </div>
                                                    )
                                                })}
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
                                                                <div style={{ padding: '0 1rem 1rem 3.75rem' }}>
                                                                    {/* 标签页导航 */}
                                                                    <div style={{ display: 'flex', borderBottom: '2px solid #E5E7EB', marginBottom: '1rem' }}>
                                                                        {['提取', '响应体', '响应头', '断言', '请求内容'].map(tab => (
                                                                            <button
                                                                                key={tab}
                                                                                onClick={() => setActiveStepTab(prev => ({ ...prev, [stepKey]: tab }))}
                                                                                style={{
                                                                                    padding: '0.75rem 1.5rem',
                                                                                    background: (activeStepTab[stepKey] || '提取') === tab ? '#3B82F6' : 'transparent',
                                                                                    color: (activeStepTab[stepKey] || '提取') === tab ? 'white' : '#6B7280',
                                                                                    border: 'none',
                                                                                    borderBottom: (activeStepTab[stepKey] || '提取') === tab ? '3px solid #3B82F6' : 'none',
                                                                                    cursor: 'pointer',
                                                                                    fontWeight: (activeStepTab[stepKey] || '提取') === tab ? '600' : '400',
                                                                                    transition: 'all 0.2s',
                                                                                    fontSize: '0.875rem'
                                                                                }}
                                                                            >
                                                                                {tab}
                                                                            </button>
                                                                        ))}
                                                                    </div>

                                                                    {/* 标签页内容 */}
                                                                    <div style={{ fontSize: '0.75rem' }}>
                                                                        {/* 提取标签页 (默认,核心功能) */}
                                                                        {(activeStepTab[stepKey] || '提取') === '提取' && (
                                                                            <div>
                                                                                {res.extractions && res.extractions.length > 0 ? (
                                                                                    <table style={{ width: '100%', background: 'white', borderRadius: '0.5rem', borderCollapse: 'collapse' }}>
                                                                                        <thead style={{ background: '#EFF6FF' }}>
                                                                                            <tr>
                                                                                                <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #DBEAFE' }}>来源步骤</th>
                                                                                                <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #DBEAFE' }}>来源字段</th>
                                                                                                <th style={{ padding: '0.75rem', textAlign: 'center', borderBottom: '2px solid #DBEAFE', width: '60px' }}>→</th>
                                                                                                <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #DBEAFE' }}>目标字段</th>
                                                                                                <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #DBEAFE' }}>提取的值</th>
                                                                                                <th style={{ padding: '0.75rem', textAlign: 'center', borderBottom: '2px solid #DBEAFE', width: '60px' }}>状态</th>
                                                                                            </tr>
                                                                                        </thead>
                                                                                        <tbody>
                                                                                            {res.extractions.map((ext: any, idx: number) => (
                                                                                                <tr key={idx} style={{ borderBottom: idx === res.extractions.length - 1 ? 'none' : '1px solid #F3F4F6' }}>
                                                                                                    <td style={{ padding: '0.75rem' }}>
                                                                                                        <span style={{
                                                                                                            background: '#DBEAFE',
                                                                                                            color: '#1E40AF',
                                                                                                            padding: '0.25rem 0.5rem',
                                                                                                            borderRadius: '0.25rem',
                                                                                                            fontWeight: '600',
                                                                                                            fontSize: '0.75rem'
                                                                                                        }}>
                                                                                                            步骤 {ext.from_step}
                                                                                                        </span>
                                                                                                    </td>
                                                                                                    <td style={{ padding: '0.75rem', fontFamily: 'monospace', fontSize: '0.75rem', color: '#475569' }}>
                                                                                                        {ext.from_field}
                                                                                                    </td>
                                                                                                    <td style={{ padding: '0.75rem', textAlign: 'center', color: '#3B82F6', fontSize: '1.25rem', fontWeight: 'bold' }}>
                                                                                                        →
                                                                                                    </td>
                                                                                                    <td style={{ padding: '0.75rem', fontFamily: 'monospace', fontSize: '0.75rem', color: '#475569' }}>
                                                                                                        {ext.to_field}
                                                                                                    </td>
                                                                                                    <td style={{ padding: '0.75rem' }}>
                                                                                                        <code style={{
                                                                                                            background: '#F3F4F6',
                                                                                                            padding: '0.25rem 0.5rem',
                                                                                                            borderRadius: '0.25rem',
                                                                                                            fontSize: '0.75rem',
                                                                                                            maxWidth: '200px',
                                                                                                            display: 'inline-block',
                                                                                                            overflow: 'hidden',
                                                                                                            textOverflow: 'ellipsis',
                                                                                                            whiteSpace: 'nowrap',
                                                                                                            color: '#1F2937'
                                                                                                        }}>
                                                                                                            {typeof ext.extracted_value === 'object'
                                                                                                                ? JSON.stringify(ext.extracted_value)
                                                                                                                : String(ext.extracted_value)}
                                                                                                        </code>
                                                                                                    </td>
                                                                                                    <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                                                                                                        {ext.success ? (
                                                                                                            <span style={{ color: '#10B981', fontSize: '1.25rem' }}>✅</span>
                                                                                                        ) : (
                                                                                                            <span style={{ color: '#EF4444', fontSize: '1.25rem' }} title={ext.error_msg}>❌</span>
                                                                                                        )}
                                                                                                    </td>
                                                                                                </tr>
                                                                                            ))}
                                                                                        </tbody>
                                                                                    </table>
                                                                                ) : (
                                                                                    <div style={{
                                                                                        background: 'white',
                                                                                        padding: '2rem',
                                                                                        textAlign: 'center',
                                                                                        borderRadius: '0.5rem',
                                                                                        color: '#9CA3AF'
                                                                                    }}>
                                                                                        <p style={{ margin: 0, fontSize: '0.875rem' }}>此步骤未从其他步骤提取数据</p>
                                                                                        <p style={{ margin: '0.5rem 0 0', fontSize: '0.75rem' }}>
                                                                                            (AI会自动识别接口间的依赖关系并生成提取配置)
                                                                                        </p>
                                                                                    </div>
                                                                                )}
                                                                            </div>
                                                                        )}

                                                                        {/* 响应体标签页 */}
                                                                        {(activeStepTab[stepKey] || '提取') === '响应体' && (
                                                                            <pre style={{
                                                                                background: 'white',
                                                                                padding: '1rem',
                                                                                borderRadius: '0.5rem',
                                                                                overflow: 'auto',
                                                                                maxHeight: '400px',
                                                                                fontSize: '0.75rem',
                                                                                margin: 0,
                                                                                border: '1px solid #E5E7EB'
                                                                            }}>
                                                                                {typeof res.response === 'string'
                                                                                    ? res.response
                                                                                    : JSON.stringify(res.response, null, 2)}
                                                                            </pre>
                                                                        )}

                                                                        {/* 响应头标签页 */}
                                                                        {(activeStepTab[stepKey] || '提取') === '响应头' && (
                                                                            <div>
                                                                                {res.response_headers && Object.keys(res.response_headers).length > 0 ? (
                                                                                    <table style={{ width: '100%', background: 'white', borderRadius: '0.5rem', borderCollapse: 'collapse' }}>
                                                                                        <thead style={{ background: '#F3F4F6' }}>
                                                                                            <tr>
                                                                                                <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #E5E7EB' }}>Header名称</th>
                                                                                                <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #E5E7EB' }}>值</th>
                                                                                            </tr>
                                                                                        </thead>
                                                                                        <tbody>
                                                                                            {Object.entries(res.response_headers).map(([key, value]: [string, any]) => (
                                                                                                <tr key={key} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                                                                                    <td style={{ padding: '0.75rem', fontWeight: '600', fontSize: '0.75rem' }}>{key}</td>
                                                                                                    <td style={{ padding: '0.75rem', fontFamily: 'monospace', fontSize: '0.75rem', color: '#475569' }}>
                                                                                                        {Array.isArray(value) ? value.join(', ') : String(value)}
                                                                                                    </td>
                                                                                                </tr>
                                                                                            ))}
                                                                                        </tbody>
                                                                                    </table>
                                                                                ) : (
                                                                                    <div style={{ background: 'white', padding: '2rem', textAlign: 'center', borderRadius: '0.5rem', color: '#9CA3AF' }}>
                                                                                        <p style={{ margin: 0 }}>无响应头信息</p>
                                                                                    </div>
                                                                                )}
                                                                            </div>
                                                                        )}

                                                                        {/* 断言标签页 */}
                                                                        {(activeStepTab[stepKey] || '提取') === '断言' && (
                                                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                                                                {res.assertions && res.assertions.length > 0 ? (
                                                                                    res.assertions.map((assertion: any, idx: number) => (
                                                                                        <div key={idx} style={{
                                                                                            background: 'white',
                                                                                            padding: '1rem',
                                                                                            borderRadius: '0.5rem',
                                                                                            borderLeft: `4px solid ${assertion.passed ? '#10B981' : '#EF4444'}`
                                                                                        }}>
                                                                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                                                                                <span style={{ fontSize: '1.25rem' }}>{assertion.passed ? '✅' : '❌'}</span>
                                                                                                <span style={{ fontWeight: '600', fontSize: '0.875rem' }}>
                                                                                                    {assertion.description || assertion.type || assertion.assertion?.description}
                                                                                                </span>
                                                                                            </div>
                                                                                            <div style={{ fontSize: '0.75rem', color: '#6B7280', marginLeft: '1.75rem' }}>
                                                                                                <div>期望值: <code style={{ background: '#F3F4F6', padding: '0.125rem 0.25rem', borderRadius: '0.25rem' }}>
                                                                                                    {JSON.stringify(assertion.expected || assertion.assertion?.expected_value)}
                                                                                                </code></div>
                                                                                                <div style={{ marginTop: '0.25rem' }}>实际值: <code style={{ background: '#F3F4F6', padding: '0.125rem 0.25rem', borderRadius: '0.25rem' }}>
                                                                                                    {JSON.stringify(assertion.actual || assertion.actual_value)}
                                                                                                </code></div>
                                                                                            </div>
                                                                                        </div>
                                                                                    ))
                                                                                ) : (
                                                                                    <div style={{ background: 'white', padding: '2rem', textAlign: 'center', borderRadius: '0.5rem', color: '#9CA3AF' }}>
                                                                                        <p style={{ margin: 0 }}>无断言信息</p>
                                                                                    </div>
                                                                                )}
                                                                            </div>
                                                                        )}

                                                                        {/* 请求内容标签页 */}
                                                                        {(activeStepTab[stepKey] || '提取') === '请求内容' && (
                                                                            <pre style={{
                                                                                background: 'white',
                                                                                padding: '1rem',
                                                                                borderRadius: '0.5rem',
                                                                                overflow: 'auto',
                                                                                maxHeight: '400px',
                                                                                fontSize: '0.75rem',
                                                                                margin: 0,
                                                                                border: '1px solid #E5E7EB'
                                                                            }}>
                                                                                {JSON.stringify(res.request_data, null, 2)}
                                                                            </pre>
                                                                        )}
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

            {/* 定时任务配置弹窗 */}
            {showSchedulerModal && (
                <div style={{
                    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
                }} onClick={() => setShowSchedulerModal(false)}>
                    <div style={{
                        background: 'white',
                        borderRadius: '1rem',
                        padding: '2rem',
                        width: '90%',
                        maxWidth: '600px',
                        maxHeight: '80vh',
                        overflowY: 'auto',
                        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)'
                    }} onClick={(e) => e.stopPropagation()}>
                        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Clock size={24} style={{ color: '#667eea' }} />
                            设置定时任务
                        </h2>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                            {/* 任务名称 */}
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem', color: '#374151' }}>
                                    任务名称 *
                                </label>
                                <input
                                    type="text"
                                    value={schedulerForm.name}
                                    onChange={(e) => setSchedulerForm({ ...schedulerForm, name: e.target.value })}
                                    placeholder="例如: 每日回归测试"
                                    style={{
                                        width: '100%',
                                        padding: '0.75rem',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '0.5rem',
                                        fontSize: '0.875rem',
                                        outline: 'none'
                                    }}
                                />
                            </div>

                            {/* 执行时间 */}
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem', color: '#374151' }}>
                                    执行时间 *
                                </label>
                                <select
                                    value={schedulerForm.cron}
                                    onChange={(e) => {
                                        setSchedulerForm({ ...schedulerForm, cron: e.target.value, timeMode: e.target.value === 'custom' ? 'custom' : 'preset' })
                                    }}
                                    style={{
                                        width: '100%',
                                        padding: '0.75rem',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '0.5rem',
                                        fontSize: '0.875rem',
                                        marginBottom: '0.75rem',
                                        outline: 'none'
                                    }}
                                >
                                    {cronPresets.map((preset) => (
                                        <option key={preset.value} value={preset.value}>
                                            {preset.label}
                                        </option>
                                    ))}
                                </select>

                                {/* 自定义时间选择器 */}
                                {schedulerForm.cron === 'custom' && (
                                    <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                                        <div style={{ marginBottom: '0.75rem' }}>
                                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>
                                                执行频率
                                            </label>
                                            <select
                                                value={schedulerForm.frequency}
                                                onChange={(e) => setSchedulerForm({ ...schedulerForm, frequency: e.target.value as any })}
                                                style={{
                                                    width: '100%',
                                                    padding: '0.5rem',
                                                    border: '1px solid #E5E7EB',
                                                    borderRadius: '0.375rem',
                                                    fontSize: '0.875rem',
                                                    outline: 'none'
                                                }}
                                            >
                                                <option value="daily">每天</option>
                                                <option value="hourly">每小时</option>
                                                <option value="weekly">每周</option>
                                            </select>
                                        </div>

                                        {schedulerForm.frequency !== 'hourly' && (
                                            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.75rem' }}>
                                                <div style={{ flex: 1 }}>
                                                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>
                                                        小时 (0-23)
                                                    </label>
                                                    <input
                                                        type="number"
                                                        min="0"
                                                        max="23"
                                                        value={schedulerForm.customHour}
                                                        onChange={(e) => setSchedulerForm({ ...schedulerForm, customHour: e.target.value })}
                                                        style={{
                                                            width: '100%',
                                                            padding: '0.5rem',
                                                            border: '1px solid #E5E7EB',
                                                            borderRadius: '0.375rem',
                                                            fontSize: '0.875rem',
                                                            outline: 'none'
                                                        }}
                                                    />
                                                </div>
                                                <div style={{ flex: 1 }}>
                                                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>
                                                        分钟 (0-59)
                                                    </label>
                                                    <input
                                                        type="number"
                                                        min="0"
                                                        max="59"
                                                        value={schedulerForm.customMinute}
                                                        onChange={(e) => setSchedulerForm({ ...schedulerForm, customMinute: e.target.value })}
                                                        style={{
                                                            width: '100%',
                                                            padding: '0.5rem',
                                                            border: '1px solid #E5E7EB',
                                                            borderRadius: '0.375rem',
                                                            fontSize: '0.875rem',
                                                            outline: 'none'
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        )}

                                        {schedulerForm.frequency === 'hourly' && (
                                            <div style={{ marginBottom: '0.75rem' }}>
                                                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>
                                                    分钟 (0-59)
                                                </label>
                                                <input
                                                    type="number"
                                                    min="0"
                                                    max="59"
                                                    value={schedulerForm.customMinute}
                                                    onChange={(e) => setSchedulerForm({ ...schedulerForm, customMinute: e.target.value })}
                                                    style={{
                                                        width: '100%',
                                                        padding: '0.5rem',
                                                        border: '1px solid #E5E7EB',
                                                        borderRadius: '0.375rem',
                                                        fontSize: '0.875rem',
                                                        outline: 'none'
                                                    }}
                                                />
                                            </div>
                                        )}

                                        {schedulerForm.frequency === 'weekly' && (
                                            <div>
                                                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>
                                                    星期几
                                                </label>
                                                <select
                                                    value={schedulerForm.weekday}
                                                    onChange={(e) => setSchedulerForm({ ...schedulerForm, weekday: e.target.value })}
                                                    style={{
                                                        width: '100%',
                                                        padding: '0.5rem',
                                                        border: '1px solid #E5E7EB',
                                                        borderRadius: '0.375rem',
                                                        fontSize: '0.875rem',
                                                        outline: 'none'
                                                    }}
                                                >
                                                    <option value="1">星期一</option>
                                                    <option value="2">星期二</option>
                                                    <option value="3">星期三</option>
                                                    <option value="4">星期四</option>
                                                    <option value="5">星期五</option>
                                                    <option value="6">星期六</option>
                                                    <option value="0">星期日</option>
                                                </select>
                                            </div>
                                        )}

                                        <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#6B7280', background: '#EFF6FF', padding: '0.5rem', borderRadius: '0.375rem' }}>
                                            💡 预览: {generateCron()}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* 环境选择 */}
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem', color: '#374151' }}>
                                    执行环境
                                </label>
                                <select
                                    value={schedulerForm.environment_id || ''}
                                    onChange={(e) => setSchedulerForm({ ...schedulerForm, environment_id: e.target.value ? Number(e.target.value) : null })}
                                    style={{
                                        width: '100%',
                                        padding: '0.75rem',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '0.5rem',
                                        fontSize: '0.875rem',
                                        outline: 'none'
                                    }}
                                >
                                    <option value="">使用默认环境</option>
                                    {environments.map(e => (
                                        <option key={e.id} value={e.id}>
                                            {e.env_name} ({e.base_url})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* 飞书通知配置 */}
                            <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.75rem', color: '#374151' }}>
                                    飞书通知配置
                                </label>
                                <div style={{ marginBottom: '0.75rem' }}>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginBottom: '0.5rem' }}>
                                        <input
                                            type="radio"
                                            checked={schedulerForm.use_project_webhook}
                                            onChange={() => setSchedulerForm({ ...schedulerForm, use_project_webhook: true })}
                                        />
                                        <span style={{ fontSize: '0.875rem' }}>使用项目默认Webhook</span>
                                    </label>
                                    {schedulerForm.use_project_webhook && (
                                        <div style={{ marginLeft: '1.5rem', fontSize: '0.75rem', color: '#6B7280' }}>
                                            {projectFeishuWebhook ? `当前: ${projectFeishuWebhook.substring(0, 50)}...` : '未配置项目Webhook'}
                                        </div>
                                    )}
                                </div>
                                <div>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginBottom: '0.5rem' }}>
                                        <input
                                            type="radio"
                                            checked={!schedulerForm.use_project_webhook}
                                            onChange={() => setSchedulerForm({ ...schedulerForm, use_project_webhook: false })}
                                        />
                                        <span style={{ fontSize: '0.875rem' }}>自定义Webhook URL</span>
                                    </label>
                                    {!schedulerForm.use_project_webhook && (
                                        <input
                                            type="text"
                                            value={schedulerForm.custom_webhook}
                                            onChange={(e) => setSchedulerForm({ ...schedulerForm, custom_webhook: e.target.value })}
                                            placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
                                            style={{
                                                width: '100%',
                                                padding: '0.5rem',
                                                border: '1px solid #E5E7EB',
                                                borderRadius: '0.375rem',
                                                fontSize: '0.75rem',
                                                marginLeft: '1.5rem',
                                                outline: 'none'
                                            }}
                                        />
                                    )}
                                </div>
                                <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#6B7280', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                    <AlertCircle size={14} />
                                    每次执行都会发送通知（成功和失败）
                                </div>
                            </div>

                            {/* 立即启用 */}
                            <div>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                    <input
                                        type="checkbox"
                                        checked={schedulerForm.is_active}
                                        onChange={(e) => setSchedulerForm({ ...schedulerForm, is_active: e.target.checked })}
                                        style={{ width: '1.125rem', height: '1.125rem' }}
                                    />
                                    <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>创建后立即启用</span>
                                </label>
                            </div>

                            {/* 操作按钮 */}
                            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
                                <button
                                    onClick={() => setShowSchedulerModal(false)}
                                    style={{
                                        flex: 1,
                                        padding: '0.75rem',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '0.5rem',
                                        background: 'white',
                                        cursor: 'pointer',
                                        fontSize: '0.875rem',
                                        fontWeight: '500'
                                    }}
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleCreateScheduledJob}
                                    disabled={!schedulerForm.name || !schedulerForm.cron}
                                    style={{
                                        flex: 1,
                                        padding: '0.75rem',
                                        border: 'none',
                                        borderRadius: '0.5rem',
                                        background: schedulerForm.name && schedulerForm.cron ? '#667eea' : '#9CA3AF',
                                        color: 'white',
                                        cursor: schedulerForm.name && schedulerForm.cron ? 'pointer' : 'not-allowed',
                                        fontWeight: '600',
                                        fontSize: '0.875rem'
                                    }}
                                >
                                    创建定时任务
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
