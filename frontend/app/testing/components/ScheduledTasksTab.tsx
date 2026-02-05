'use client'

import { useState, useEffect } from 'react'
import { useProject } from '../../contexts/ProjectContext'
import { Clock, Play, Pause, Trash2, Plus, Calendar, CheckCircle, XCircle, AlertCircle, Edit } from 'lucide-react'

export default function ScheduledTasksTab() {
    const { currentProject } = useProject()
    const [jobs, setJobs] = useState<any[]>([])
    const [scenarios, setScenarios] = useState<any[]>([])
    const [environments, setEnvironments] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [selectedJobHistory, setSelectedJobHistory] = useState<any>(null)
    const [jobHistory, setJobHistory] = useState<any[]>([])
    const [editingJobId, setEditingJobId] = useState<number | null>(null)

    // 新建任务表单
    const [newJob, setNewJob] = useState({
        name: '',
        description: '',
        scenario_id: 0,
        cron: '0 2 * * *',
        environment_id: null,
        notify_on_failure: false,
        notification_config: '{}',
        // UI辅助状态
        timeMode: 'preset', // 'preset' | 'custom'
        frequency: 'daily', // 'daily' | 'hourly' | 'weekly'
        customHour: '9',
        customMinute: '0',
        weekday: '1',
        use_project_webhook: false, // 暂时默认为false，因为后端暂未自动处理项目webhook
        custom_webhook: ''
    })

    const generateCron = (form: any) => {
        const { frequency, customHour, customMinute, weekday } = form
        const m = parseInt(customMinute) || 0
        const h = parseInt(customHour) || 0
        if (frequency === 'hourly') {
            return `${m} * * * *`
        } else if (frequency === 'daily') {
            return `${m} ${h} * * *`
        } else if (frequency === 'weekly') {
            return `${m} ${h} * * ${weekday}`
        }
        return '* * * * *'
    }

    // 当自定义时间参数变化时更新 Cron
    useEffect(() => {
        if (newJob.timeMode === 'custom') {
            const cron = generateCron(newJob)
            // 避免无限循环，只有当cron真正变化时才更新
            if (cron !== newJob.cron) {
                setNewJob(prev => ({ ...prev, cron }))
            }
        }
    }, [newJob.timeMode, newJob.frequency, newJob.customHour, newJob.customMinute, newJob.weekday])

    // 当 Webhook 设置变化时更新 notification_config
    useEffect(() => {
        if (newJob.custom_webhook) {
            const config = {
                type: 'feishu',
                webhook_url: newJob.custom_webhook
            }
            const configStr = JSON.stringify(config)
            if (configStr !== newJob.notification_config) {
                setNewJob(prev => ({ ...prev, notification_config: configStr }))
            }
        }
    }, [newJob.use_project_webhook, newJob.custom_webhook])

    useEffect(() => {
        fetchJobs()
        fetchScenarios()
        fetchEnvironments()
    }, [currentProject])

    const fetchJobs = async () => {
        setLoading(true)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs?project_id=${currentProject}`)
            if (response.ok) {
                const data = await response.json()
                setJobs(Array.isArray(data) ? data : [])
            } else {
                setJobs([])
            }
        } catch (error) {
            console.error('获取任务列表失败:', error)
            setJobs([])
        } finally {
            setLoading(false)
        }
    }

    const fetchScenarios = async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scenarios?project_id=${currentProject}`)
            const data = await response.json()
            setScenarios(data)
        } catch (error) {
            console.error('获取场景列表失败:', error)
        }
    }

    const fetchEnvironments = async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/projects/${currentProject}/environments`)
            const data = await response.json()
            setEnvironments(data)
        } catch (error) {
            console.error('获取环境列表失败:', error)
        }
    }

    const handleSaveJob = async () => {
        try {
            const url = editingJobId
                ? `${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${editingJobId}`
                : `${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs`

            const method = editingJobId ? 'PUT' : 'POST'

            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...newJob,
                    project_id: currentProject
                })
            })

            if (response.ok) {
                setShowCreateModal(false)
                resetForm()
                fetchJobs()
            }
        } catch (error) {
            console.error('保存任务失败:', error)
        }
    }

    const handleEditJob = (job: any) => {
        setEditingJobId(job.id)

        // 解析 Cron
        const isPreset = cronPresets.some(p => p.value === job.cron_expression && p.value !== 'custom')
        let timeState = {
            timeMode: isPreset ? 'preset' : 'custom',
            frequency: 'daily',
            customHour: '9',
            customMinute: '0',
            weekday: '1'
        }

        if (!isPreset && job.cron_expression) {
            const parts = job.cron_expression.split(' ')
            if (parts.length === 5) {
                const [m, h, d, mon, w] = parts
                if (h === '*' && d === '*' && mon === '*' && w === '*') {
                    timeState = { ...timeState, frequency: 'hourly', customMinute: m, customHour: '0' }
                } else if (d === '*' && mon === '*' && w === '*') {
                    timeState = { ...timeState, frequency: 'daily', customMinute: m, customHour: h }
                } else if (d === '*' && mon === '*') {
                    timeState = { ...timeState, frequency: 'weekly', customMinute: m, customHour: h, weekday: w }
                }
            }
        }

        // 解析 Webhook
        let webhookUrl = ''
        let hasValidConfig = false
        try {
            let config: any = {}
            try {
                config = JSON.parse(job.notification_config || '{}')
                if (typeof config === 'string') config = JSON.parse(config)
            } catch (e) { }
            webhookUrl = config.webhook_url || ''
            if (webhookUrl) hasValidConfig = true
        } catch (e) { }

        setNewJob({
            name: job.name,
            description: job.description || '',
            scenario_id: job.scenario_id,
            cron: job.cron_expression,
            environment_id: job.environment_id,
            notify_on_failure: Boolean(job.notify_on_failure) || hasValidConfig,
            notification_config: job.notification_config || '{}',
            // 辅助字段
            timeMode: timeState.timeMode,
            frequency: timeState.frequency,
            customHour: timeState.customHour,
            customMinute: timeState.customMinute,
            weekday: timeState.weekday,
            use_project_webhook: false,
            custom_webhook: webhookUrl
        })
        setShowCreateModal(true)
    }

    const resetForm = () => {
        setEditingJobId(null)
        setNewJob({
            name: '',
            description: '',
            scenario_id: 0,
            cron: '0 2 * * *',
            environment_id: null,
            notify_on_failure: false,
            notification_config: '{}',
            timeMode: 'preset',
            frequency: 'daily',
            customHour: '9',
            customMinute: '0',
            weekday: '1',
            use_project_webhook: false,
            custom_webhook: ''
        })
    }

    const handlePauseJob = async (jobId: number) => {
        try {
            await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${jobId}/pause`, {
                method: 'PUT'
            })
            fetchJobs()
        } catch (error) {
            console.error('暂停任务失败:', error)
        }
    }

    const handleResumeJob = async (jobId: number) => {
        try {
            await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${jobId}/resume`, {
                method: 'PUT'
            })
            fetchJobs()
        } catch (error) {
            console.error('恢复任务失败:', error)
        }
    }

    const handleDeleteJob = async (jobId: number) => {
        if (!confirm('确定要删除这个定时任务吗?')) return
        try {
            await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${jobId}`, {
                method: 'DELETE'
            })
            fetchJobs()
        } catch (error) {
            console.error('删除任务失败:', error)
        }
    }

    const handleTriggerNow = async (jobId: number) => {
        try {
            await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${jobId}/trigger`, {
                method: 'POST'
            })
            alert('任务已触发执行')
        } catch (error) {
            console.error('触发任务失败:', error)
        }
    }

    const handleViewHistory = async (job: any) => {
        setSelectedJobHistory(job)
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${job.id}/history`)
            const data = await response.json()
            setJobHistory(data)
        } catch (error) {
            console.error('获取执行历史失败:', error)
        }
    }

    const cronPresets = [
        { label: '每天凌晨2点', value: '0 2 * * *' },
        { label: '每小时', value: '0 * * * *' },
        { label: '每30分钟', value: '*/30 * * * *' },
        { label: '每周一上午9点', value: '0 9 * * 1' },
        { label: '每月1号凌晨3点', value: '0 3 1 * *' },
        { label: '自定义时间...', value: 'custom' }
    ]

    return (
        <>
            {/* 创建任务按钮 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <p style={{ color: '#6B7280' }}>
                    项目: {currentProject} | 共 {jobs.length} 个任务
                </p>
                <button
                    onClick={() => { resetForm(); setShowCreateModal(true); }}
                    style={{
                        padding: '0.75rem 1.5rem',
                        background: '#667eea',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.5rem',
                        fontSize: '0.875rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
                    }}
                >
                    <Plus size={18} />
                    创建任务
                </button>
            </div>

            {/* 任务列表 */}
            {loading ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: 'white' }}>加载中...</div>
            ) : jobs.length === 0 ? (
                <div style={{
                    background: 'rgba(255,255,255,0.95)',
                    borderRadius: '1rem',
                    padding: '3rem',
                    textAlign: 'center',
                    color: '#6B7280'
                }}>
                    <Clock size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
                    <p>还没有定时任务,点击"创建任务"开始</p>
                </div>
            ) : (
                <div style={{ display: 'grid', gap: '1rem' }}>
                    {jobs.map((job) => (
                        <div key={job.id} style={{
                            background: 'rgba(255,255,255,0.95)',
                            borderRadius: '1rem',
                            padding: '1.5rem',
                            boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                                        <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#111827' }}>{job.name}</h3>
                                        <span style={{
                                            padding: '0.25rem 0.75rem',
                                            borderRadius: '0.375rem',
                                            fontSize: '0.75rem',
                                            fontWeight: '600',
                                            background: job.is_active ? '#D1FAE5' : '#FEE2E2',
                                            color: job.is_active ? '#065F46' : '#991B1B'
                                        }}>
                                            {job.is_active ? '运行中' : '已暂停'}
                                        </span>
                                    </div>
                                    {job.description && (
                                        <p style={{ color: '#6B7280', fontSize: '0.875rem', marginBottom: '0.75rem' }}>{job.description}</p>
                                    )}
                                    <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.875rem', color: '#6B7280' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                            <Calendar size={16} />
                                            <span>{job.cron_expression}</span>
                                        </div>
                                        <div>场景: {job.scenario_name || `ID: ${job.scenario_id}`}</div>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button
                                        onClick={() => handleTriggerNow(job.id)}
                                        style={{
                                            padding: '0.5rem',
                                            border: '1px solid #E5E7EB',
                                            borderRadius: '0.375rem',
                                            background: 'white',
                                            cursor: 'pointer',
                                            color: '#3B82F6'
                                        }}
                                        title="立即执行"
                                    >
                                        <Play size={16} />
                                    </button>
                                    <button
                                        onClick={() => handleEditJob(job)}
                                        style={{
                                            padding: '0.5rem',
                                            border: '1px solid #E5E7EB',
                                            borderRadius: '0.375rem',
                                            background: 'white',
                                            cursor: 'pointer',
                                            color: '#6B7280'
                                        }}
                                        title="编辑"
                                    >
                                        <Edit size={16} />
                                    </button>
                                    {job.is_active ? (
                                        <button
                                            onClick={() => handlePauseJob(job.id)}
                                            style={{
                                                padding: '0.5rem',
                                                border: '1px solid #E5E7EB',
                                                borderRadius: '0.375rem',
                                                background: 'white',
                                                cursor: 'pointer',
                                                color: '#F59E0B'
                                            }}
                                            title="暂停"
                                        >
                                            <Pause size={16} />
                                        </button>
                                    ) : (
                                        <button
                                            onClick={() => handleResumeJob(job.id)}
                                            style={{
                                                padding: '0.5rem',
                                                border: '1px solid #E5E7EB',
                                                borderRadius: '0.375rem',
                                                background: 'white',
                                                cursor: 'pointer',
                                                color: '#10B981'
                                            }}
                                            title="恢复"
                                        >
                                            <Play size={16} />
                                        </button>
                                    )}
                                    <button
                                        onClick={() => handleViewHistory(job)}
                                        style={{
                                            padding: '0.5rem 1rem',
                                            border: '1px solid #E5E7EB',
                                            borderRadius: '0.375rem',
                                            background: 'white',
                                            cursor: 'pointer',
                                            fontSize: '0.875rem',
                                            color: '#6B7280'
                                        }}
                                    >
                                        历史
                                    </button>
                                    <button
                                        onClick={() => handleDeleteJob(job.id)}
                                        style={{
                                            padding: '0.5rem',
                                            border: '1px solid #E5E7EB',
                                            borderRadius: '0.375rem',
                                            background: 'white',
                                            cursor: 'pointer',
                                            color: '#EF4444'
                                        }}
                                        title="删除"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* 创建任务弹窗 */}
            {showCreateModal && (
                <div style={{
                    position: 'fixed',
                    inset: 0,
                    background: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000
                }} onClick={() => setShowCreateModal(false)}>
                    <div style={{
                        background: 'white',
                        borderRadius: '1rem',
                        padding: '2rem',
                        width: '90%',
                        maxWidth: '500px',
                        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)'
                    }} onClick={(e) => e.stopPropagation()}>
                        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem' }}>
                            {editingJobId ? '编辑定时任务' : '创建定时任务'}
                        </h2>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.5rem' }}>任务名称</label>
                                <input
                                    type="text"
                                    value={newJob.name}
                                    onChange={(e) => setNewJob({ ...newJob, name: e.target.value })}
                                    placeholder="例如: 每日回归测试"
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '0.375rem'
                                    }}
                                />
                            </div>

                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.5rem' }}>描述(可选)</label>
                                <input
                                    type="text"
                                    value={newJob.description}
                                    onChange={(e) => setNewJob({ ...newJob, description: e.target.value })}
                                    placeholder="任务描述"
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '0.375rem'
                                    }}
                                />
                            </div>

                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.5rem' }}>测试场景</label>
                                <select
                                    value={newJob.scenario_id}
                                    onChange={(e) => setNewJob({ ...newJob, scenario_id: parseInt(e.target.value) })}
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '0.375rem'
                                    }}
                                >
                                    <option value={0}>选择场景</option>
                                    {scenarios.map((s) => (
                                        <option key={s.id} value={s.id}>{s.name}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.5rem' }}>执行时间</label>
                                <select
                                    value={newJob.timeMode === 'custom' ? 'custom' : newJob.cron}
                                    onChange={(e) => {
                                        const isCustom = e.target.value === 'custom'
                                        setNewJob({
                                            ...newJob,
                                            timeMode: isCustom ? 'custom' : 'preset',
                                            cron: isCustom ? newJob.cron : e.target.value
                                        })
                                    }}
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '0.375rem',
                                        marginBottom: '0.5rem'
                                    }}
                                >
                                    {cronPresets.map((preset) => (
                                        <option key={preset.value} value={preset.value}>{preset.label} {preset.value !== 'custom' && `(${preset.value})`}</option>
                                    ))}
                                </select>

                                {newJob.timeMode === 'custom' && (
                                    <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #E5E7EB', marginTop: '0.5rem' }}>
                                        <div style={{ marginBottom: '0.75rem' }}>
                                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>执行频率</label>
                                            <select
                                                value={newJob.frequency}
                                                onChange={(e) => setNewJob({ ...newJob, frequency: e.target.value })}
                                                style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.875rem' }}
                                            >
                                                <option value="daily">每天</option>
                                                <option value="hourly">每小时</option>
                                                <option value="weekly">每周</option>
                                            </select>
                                        </div>

                                        {newJob.frequency !== 'hourly' && (
                                            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.75rem' }}>
                                                <div style={{ flex: 1 }}>
                                                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>小时 (0-23)</label>
                                                    <input
                                                        type="number" min="0" max="23"
                                                        value={newJob.customHour}
                                                        onChange={(e) => setNewJob({ ...newJob, customHour: e.target.value })}
                                                        style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.875rem' }}
                                                    />
                                                </div>
                                                <div style={{ flex: 1 }}>
                                                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>分钟 (0-59)</label>
                                                    <input
                                                        type="number" min="0" max="59"
                                                        value={newJob.customMinute}
                                                        onChange={(e) => setNewJob({ ...newJob, customMinute: e.target.value })}
                                                        style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.875rem' }}
                                                    />
                                                </div>
                                            </div>
                                        )}

                                        {newJob.frequency === 'hourly' && (
                                            <div style={{ marginBottom: '0.75rem' }}>
                                                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>分钟 (0-59)</label>
                                                <input
                                                    type="number" min="0" max="59"
                                                    value={newJob.customMinute}
                                                    onChange={(e) => setNewJob({ ...newJob, customMinute: e.target.value })}
                                                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.875rem' }}
                                                />
                                            </div>
                                        )}

                                        {newJob.frequency === 'weekly' && (
                                            <div>
                                                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>星期几</label>
                                                <select
                                                    value={newJob.weekday}
                                                    onChange={(e) => setNewJob({ ...newJob, weekday: e.target.value })}
                                                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.875rem' }}
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
                                            💡 预览Cron: {newJob.cron}
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.75rem', color: '#374151' }}>
                                    飞书通知配置
                                </label>
                                <div style={{ marginBottom: '0.5rem' }}>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={newJob.notify_on_failure}
                                            onChange={(e) => setNewJob({ ...newJob, notify_on_failure: e.target.checked })}
                                        />
                                        <span style={{ fontSize: '0.875rem' }}>需要发送通知 (成功/失败)</span>
                                    </label>
                                </div>

                                {!!newJob.notify_on_failure && (
                                    <div style={{ marginTop: '0.75rem' }}>
                                        <div style={{ marginBottom: '0.75rem' }}>
                                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginBottom: '0.5rem' }}>
                                                <input
                                                    type="radio"
                                                    checked={!newJob.use_project_webhook}
                                                    onChange={() => setNewJob({ ...newJob, use_project_webhook: false })}
                                                />
                                                <span style={{ fontSize: '0.875rem' }}>自定义Webhook URL</span>
                                            </label>
                                            {!newJob.use_project_webhook && (
                                                <input
                                                    type="text"
                                                    value={newJob.custom_webhook}
                                                    onChange={(e) => setNewJob({ ...newJob, custom_webhook: e.target.value })}
                                                    placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
                                                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.75rem', marginLeft: '1.5rem', outline: 'none' }}
                                                />
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                <button
                                    onClick={() => setShowCreateModal(false)}
                                    style={{
                                        flex: 1,
                                        padding: '0.75rem',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '0.5rem',
                                        background: 'white',
                                        cursor: 'pointer'
                                    }}
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleSaveJob}
                                    disabled={!newJob.name || !newJob.scenario_id}
                                    style={{
                                        flex: 1,
                                        padding: '0.75rem',
                                        border: 'none',
                                        borderRadius: '0.5rem',
                                        background: newJob.name && newJob.scenario_id ? '#667eea' : '#9CA3AF',
                                        color: 'white',
                                        cursor: newJob.name && newJob.scenario_id ? 'pointer' : 'not-allowed',
                                        fontWeight: '600'
                                    }}
                                >
                                    {editingJobId ? '保存修改' : '创建任务'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 执行历史弹窗 */}
            {
                selectedJobHistory && (
                    <div style={{
                        position: 'fixed',
                        inset: 0,
                        background: 'rgba(0,0,0,0.5)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 1000
                    }} onClick={() => setSelectedJobHistory(null)}>
                        <div style={{
                            background: 'white',
                            borderRadius: '1rem',
                            padding: '2rem',
                            width: '90%',
                            maxWidth: '800px',
                            maxHeight: '80vh',
                            overflowY: 'auto',
                            boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)'
                        }} onClick={(e) => e.stopPropagation()}>
                            <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem' }}>
                                执行历史 - {selectedJobHistory.name}
                            </h2>

                            {jobHistory.length === 0 ? (
                                <p style={{ textAlign: 'center', color: '#6B7280', padding: '2rem' }}>暂无执行记录</p>
                            ) : (
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <thead>
                                        <tr style={{ background: '#F9FAFB', borderBottom: '2px solid #E5E7EB' }}>
                                            <th style={{ padding: '0.75rem', textAlign: 'left', fontSize: '0.75rem', fontWeight: '600', color: '#6B7280' }}>状态</th>
                                            <th style={{ padding: '0.75rem', textAlign: 'left', fontSize: '0.75rem', fontWeight: '600', color: '#6B7280' }}>开始时间</th>
                                            <th style={{ padding: '0.75rem', textAlign: 'left', fontSize: '0.75rem', fontWeight: '600', color: '#6B7280' }}>完成时间</th>
                                            <th style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.75rem', fontWeight: '600', color: '#6B7280' }}>步骤</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {jobHistory.map((record) => (
                                            <tr key={record.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                                <td style={{ padding: '0.75rem' }}>
                                                    {record.status === 'success' ? (
                                                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#10B981' }}>
                                                            <CheckCircle size={16} /> 成功
                                                        </span>
                                                    ) : record.status === 'failed' ? (
                                                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#EF4444' }}>
                                                            <XCircle size={16} /> 失败
                                                        </span>
                                                    ) : (
                                                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#F59E0B' }}>
                                                            <AlertCircle size={16} /> 运行中
                                                        </span>
                                                    )}
                                                </td>
                                                <td style={{ padding: '0.75rem', fontSize: '0.875rem' }}>{new Date(record.started_at).toLocaleString()}</td>
                                                <td style={{ padding: '0.75rem', fontSize: '0.875rem' }}>{record.completed_at ? new Date(record.completed_at).toLocaleString() : '-'}</td>
                                                <td style={{ padding: '0.75rem', textAlign: 'center', fontSize: '0.875rem' }}>
                                                    {record.total_steps ? `${record.passed_steps}/${record.total_steps}` : '-'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </div>
                )
            }
        </>
    )
}
