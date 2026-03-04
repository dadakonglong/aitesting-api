'use client'

import { useState, useEffect } from 'react'
import { useProject } from '../../contexts/ProjectContext'
import { Clock, Play, Pause, Trash2, Plus, Calendar, CheckCircle, XCircle, AlertCircle, Edit, TrendingUp, Activity, Wrench, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'

// ============ 趋势图辅助：纯CSS柱形图 ============

function MiniBarChart({ data, valueKey, colorFn }: {
    data: any[],
    valueKey: string,
    colorFn?: (v: number) => string
}) {
    if (!data || data.length === 0) return <span style={{ color: '#9CA3AF', fontSize: '0.75rem' }}>暂无数据</span>
    const max = Math.max(...data.map(d => d[valueKey] || 0), 1)
    return (
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '48px' }}>
            {data.map((d, i) => {
                const v = d[valueKey] || 0
                const h = Math.max(4, Math.round((v / max) * 44))
                const color = colorFn ? colorFn(v) : '#6366F1'
                return (
                    <div key={i} title={`${d.date}: ${v}`} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end' }}>
                        <div style={{ width: '100%', height: `${h}px`, background: color, borderRadius: '2px 2px 0 0', transition: 'height 0.3s ease' }} />
                    </div>
                )
            })}
        </div>
    )
}

// ============ 自愈状态徽章 ============

function HealBadge({ status }: { status?: string }) {
    if (!status) return null
    const map: Record<string, { label: string, color: string, bg: string }> = {
        auto_healed: { label: '🤖 已自动修复', color: '#065F46', bg: '#D1FAE5' },
        manual_needed: { label: '👤 需人工介入', color: '#92400E', bg: '#FEF3C7' },
        analyzing: { label: '🔍 分析中', color: '#1E40AF', bg: '#DBEAFE' },
        failed: { label: '❌ 自愈失败', color: '#991B1B', bg: '#FEE2E2' },
    }
    const s = map[status]
    if (!s) return null
    return (
        <span style={{ padding: '0.15rem 0.5rem', borderRadius: '0.25rem', fontSize: '0.7rem', fontWeight: '600', background: s.bg, color: s.color }}>
            {s.label}
        </span>
    )
}

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
    const [expandedHistoryId, setExpandedHistoryId] = useState<number | null>(null)

    // 趋势监控面板
    const [trendJob, setTrendJob] = useState<any>(null)
    const [trendData, setTrendData] = useState<any[]>([])
    const [perfAlert, setPerfAlert] = useState<any>(null)
    const [trendLoading, setTrendLoading] = useState(false)

    // 自愈历史面板
    const [healingJob, setHealingJob] = useState<any>(null)
    const [healingHistory, setHealingHistory] = useState<any[]>([])
    const [healingLoading, setHealingLoading] = useState(false)
    const [healingTriggeringId, setHealingTriggeringId] = useState<number | null>(null)

    // 新建任务表单
    const [newJob, setNewJob] = useState({
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

    const generateCron = (form: any) => {
        const { frequency, customHour, customMinute, weekday } = form
        const m = parseInt(customMinute) || 0
        const h = parseInt(customHour) || 0
        if (frequency === 'hourly') return `${m} * * * *`
        if (frequency === 'daily') return `${m} ${h} * * *`
        if (frequency === 'weekly') return `${m} ${h} * * ${weekday}`
        return '* * * * *'
    }

    useEffect(() => {
        if (newJob.timeMode === 'custom') {
            const cron = generateCron(newJob)
            if (cron !== newJob.cron) setNewJob(prev => ({ ...prev, cron }))
        }
    }, [newJob.timeMode, newJob.frequency, newJob.customHour, newJob.customMinute, newJob.weekday])

    useEffect(() => {
        if (newJob.custom_webhook) {
            const config = { type: 'feishu', webhook_url: newJob.custom_webhook }
            const configStr = JSON.stringify(config)
            if (configStr !== newJob.notification_config) setNewJob(prev => ({ ...prev, notification_config: configStr }))
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
            } else { setJobs([]) }
        } catch { setJobs([]) } finally { setLoading(false) }
    }

    const fetchScenarios = async () => {
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scenarios?project_id=${currentProject}`)
            setScenarios(await res.json())
        } catch { }
    }

    const fetchEnvironments = async () => {
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/projects/${currentProject}/environments`)
            setEnvironments(await res.json())
        } catch { }
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
                body: JSON.stringify({ ...newJob, project_id: currentProject })
            })
            if (response.ok) { setShowCreateModal(false); resetForm(); fetchJobs() }
        } catch (e) { console.error('保存任务失败:', e) }
    }

    const handleEditJob = (job: any) => {
        setEditingJobId(job.id)
        const isPreset = cronPresets.some(p => p.value === job.cron_expression && p.value !== 'custom')
        let timeState = { timeMode: isPreset ? 'preset' : 'custom', frequency: 'daily', customHour: '9', customMinute: '0', weekday: '1' }
        if (!isPreset && job.cron_expression) {
            const [m, h, d, , w] = job.cron_expression.split(' ')
            if (h === '*') timeState = { ...timeState, frequency: 'hourly', customMinute: m, customHour: '0' }
            else if (d === '*' && w === '*') timeState = { ...timeState, frequency: 'daily', customMinute: m, customHour: h }
            else timeState = { ...timeState, frequency: 'weekly', customMinute: m, customHour: h, weekday: w }
        }
        let webhookUrl = ''
        try {
            let config: any = JSON.parse(job.notification_config || '{}')
            if (typeof config === 'string') config = JSON.parse(config)
            webhookUrl = config.webhook_url || ''
        } catch { }
        setNewJob({
            name: job.name, description: job.description || '', scenario_id: job.scenario_id,
            cron: job.cron_expression, environment_id: job.environment_id,
            notify_on_failure: Boolean(job.notify_on_failure) || !!webhookUrl,
            notification_config: job.notification_config || '{}',
            ...timeState, use_project_webhook: false, custom_webhook: webhookUrl
        })
        setShowCreateModal(true)
    }

    const resetForm = () => {
        setEditingJobId(null)
        setNewJob({ name: '', description: '', scenario_id: 0, cron: '0 2 * * *', environment_id: null, notify_on_failure: false, notification_config: '{}', timeMode: 'preset', frequency: 'daily', customHour: '9', customMinute: '0', weekday: '1', use_project_webhook: false, custom_webhook: '' })
    }

    const handlePauseJob = async (jobId: number) => {
        await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${jobId}/pause`, { method: 'PUT' })
        fetchJobs()
    }
    const handleResumeJob = async (jobId: number) => {
        await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${jobId}/resume`, { method: 'PUT' })
        fetchJobs()
    }
    const handleDeleteJob = async (jobId: number) => {
        if (!confirm('确定要删除这个定时任务吗?')) return
        await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${jobId}`, { method: 'DELETE' })
        fetchJobs()
    }
    const handleTriggerNow = async (jobId: number) => {
        await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${jobId}/trigger`, { method: 'POST' })
        alert('任务已触发执行，请稍后查看执行历史')
    }

    const handleViewHistory = async (job: any) => {
        setSelectedJobHistory(job)
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${job.id}/history`)
            setJobHistory(await res.json())
        } catch { }
    }

    // ============ 趋势监控 ============

    const handleViewTrend = async (job: any) => {
        setTrendJob(job)
        setTrendLoading(true)
        try {
            const [trendRes, alertRes] = await Promise.all([
                fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${job.id}/trend?days=7`),
                fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${job.id}/performance-alert`)
            ])
            const trendJson = await trendRes.json()
            setTrendData(trendJson.data || [])
            setPerfAlert(await alertRes.json())
        } catch { } finally { setTrendLoading(false) }
    }

    // ============ 自愈历史 ============

    const handleViewHealingHistory = async (job: any) => {
        setHealingJob(job)
        setHealingLoading(true)
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${job.id}/healing-history`)
            setHealingHistory(await res.json())
        } catch { } finally { setHealingLoading(false) }
    }

    const handleManualHeal = async (jobId: number) => {
        setHealingTriggeringId(jobId)
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs/${jobId}/heal`, { method: 'POST' })
            const data = await res.json()
            alert(data.message || '自愈流程已启动')
            if (healingJob?.id === jobId) {
                setTimeout(() => handleViewHealingHistory(healingJob), 2000)
            }
        } catch { } finally { setHealingTriggeringId(null) }
    }

    const cronPresets = [
        { label: '每天凌晨2点', value: '0 2 * * *' },
        { label: '每小时', value: '0 * * * *' },
        { label: '每30分钟', value: '*/30 * * * *' },
        { label: '每周一上午9点', value: '0 9 * * 1' },
        { label: '每月1号凌晨3点', value: '0 3 1 * *' },
        { label: '自定义时间...', value: 'custom' }
    ]

    const btnBase = { padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', background: 'white', cursor: 'pointer' }

    return (
        <>
            {/* 顶部工具栏 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <p style={{ color: '#6B7280' }}>项目: {currentProject} | 共 {jobs.length} 个任务</p>
                <button onClick={() => { resetForm(); setShowCreateModal(true) }} style={{ padding: '0.75rem 1.5rem', background: '#667eea', color: 'white', border: 'none', borderRadius: '0.5rem', fontSize: '0.875rem', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
                    <Plus size={18} />创建任务
                </button>
            </div>

            {/* 任务列表 */}
            {loading ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: 'white' }}>加载中...</div>
            ) : jobs.length === 0 ? (
                <div style={{ background: 'rgba(255,255,255,0.95)', borderRadius: '1rem', padding: '3rem', textAlign: 'center', color: '#6B7280' }}>
                    <Clock size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
                    <p>还没有定时任务，点击"创建任务"开始</p>
                </div>
            ) : (
                <div style={{ display: 'grid', gap: '1rem' }}>
                    {jobs.map(job => (
                        <div key={job.id} style={{ background: 'rgba(255,255,255,0.95)', borderRadius: '1rem', padding: '1.5rem', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                                        <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#111827' }}>{job.name}</h3>
                                        <span style={{ padding: '0.25rem 0.75rem', borderRadius: '0.375rem', fontSize: '0.75rem', fontWeight: '600', background: job.is_active ? '#D1FAE5' : '#FEE2E2', color: job.is_active ? '#065F46' : '#991B1B' }}>
                                            {job.is_active ? '运行中' : '已暂停'}
                                        </span>
                                    </div>
                                    {job.description && <p style={{ color: '#6B7280', fontSize: '0.875rem', marginBottom: '0.75rem' }}>{job.description}</p>}
                                    <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.875rem', color: '#6B7280' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                            <Calendar size={16} /><span>{job.cron_expression}</span>
                                        </div>
                                        <div>场景: {job.scenario_name || `ID: ${job.scenario_id}`}</div>
                                    </div>
                                </div>

                                {/* 操作按钮区 */}
                                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                                    {/* 立即执行 */}
                                    <button onClick={() => handleTriggerNow(job.id)} style={{ ...btnBase, color: '#3B82F6' }} title="立即执行"><Play size={16} /></button>
                                    {/* 编辑 */}
                                    <button onClick={() => handleEditJob(job)} style={{ ...btnBase, color: '#6B7280' }} title="编辑"><Edit size={16} /></button>
                                    {/* 暂停/恢复 */}
                                    {job.is_active
                                        ? <button onClick={() => handlePauseJob(job.id)} style={{ ...btnBase, color: '#F59E0B' }} title="暂停"><Pause size={16} /></button>
                                        : <button onClick={() => handleResumeJob(job.id)} style={{ ...btnBase, color: '#10B981' }} title="恢复"><Play size={16} /></button>
                                    }
                                    {/* 趋势 */}
                                    <button onClick={() => handleViewTrend(job)} style={{ ...btnBase, color: '#8B5CF6', display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.8rem', padding: '0.5rem 0.75rem' }} title="趋势监控">
                                        <TrendingUp size={15} />趋势
                                    </button>
                                    {/* 历史 */}
                                    <button onClick={() => handleViewHistory(job)} style={{ ...btnBase, color: '#6B7280', display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.875rem', padding: '0.5rem 0.75rem' }}>
                                        <Activity size={15} />历史
                                    </button>
                                    {/* 自愈历史 */}
                                    <button onClick={() => handleViewHealingHistory(job)} style={{ ...btnBase, color: '#10B981', display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.8rem', padding: '0.5rem 0.75rem' }} title="自愈历史">
                                        <Wrench size={15} />自愈
                                    </button>
                                    {/* 删除 */}
                                    <button onClick={() => handleDeleteJob(job.id)} style={{ ...btnBase, color: '#EF4444' }} title="删除"><Trash2 size={16} /></button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* ============ 创建/编辑任务弹窗 ============ */}
            {showCreateModal && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={() => setShowCreateModal(false)}>
                    <div style={{ background: 'white', borderRadius: '1rem', padding: '2rem', width: '90%', maxWidth: '500px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)', maxHeight: '90vh', overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
                        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem' }}>{editingJobId ? '编辑定时任务' : '创建定时任务'}</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.5rem' }}>任务名称</label>
                                <input type="text" value={newJob.name} onChange={e => setNewJob({ ...newJob, name: e.target.value })} placeholder="例如: 每日回归测试" style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem' }} />
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.5rem' }}>描述(可选)</label>
                                <input type="text" value={newJob.description} onChange={e => setNewJob({ ...newJob, description: e.target.value })} placeholder="任务描述" style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem' }} />
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.5rem' }}>测试场景</label>
                                <select value={newJob.scenario_id} onChange={e => setNewJob({ ...newJob, scenario_id: parseInt(e.target.value) })} style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem' }}>
                                    <option value={0}>选择场景</option>
                                    {scenarios.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                                </select>
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.5rem' }}>执行时间</label>
                                <select value={newJob.timeMode === 'custom' ? 'custom' : newJob.cron} onChange={e => { const isCustom = e.target.value === 'custom'; setNewJob({ ...newJob, timeMode: isCustom ? 'custom' : 'preset', cron: isCustom ? newJob.cron : e.target.value }) }} style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', marginBottom: '0.5rem' }}>
                                    {cronPresets.map(p => <option key={p.value} value={p.value}>{p.label} {p.value !== 'custom' && `(${p.value})`}</option>)}
                                </select>
                                {newJob.timeMode === 'custom' && (
                                    <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                                        <div style={{ marginBottom: '0.75rem' }}>
                                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>执行频率</label>
                                            <select value={newJob.frequency} onChange={e => setNewJob({ ...newJob, frequency: e.target.value })} style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.875rem' }}>
                                                <option value="daily">每天</option>
                                                <option value="hourly">每小时</option>
                                                <option value="weekly">每周</option>
                                            </select>
                                        </div>
                                        {newJob.frequency !== 'hourly' && (
                                            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.75rem' }}>
                                                <div style={{ flex: 1 }}>
                                                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>小时 (0-23)</label>
                                                    <input type="number" min="0" max="23" value={newJob.customHour} onChange={e => setNewJob({ ...newJob, customHour: e.target.value })} style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.875rem' }} />
                                                </div>
                                                <div style={{ flex: 1 }}>
                                                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>分钟 (0-59)</label>
                                                    <input type="number" min="0" max="59" value={newJob.customMinute} onChange={e => setNewJob({ ...newJob, customMinute: e.target.value })} style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.875rem' }} />
                                                </div>
                                            </div>
                                        )}
                                        {newJob.frequency === 'hourly' && (
                                            <div style={{ marginBottom: '0.75rem' }}>
                                                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>分钟 (0-59)</label>
                                                <input type="number" min="0" max="59" value={newJob.customMinute} onChange={e => setNewJob({ ...newJob, customMinute: e.target.value })} style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.875rem' }} />
                                            </div>
                                        )}
                                        {newJob.frequency === 'weekly' && (
                                            <div>
                                                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '500', marginBottom: '0.5rem', color: '#6B7280' }}>星期几</label>
                                                <select value={newJob.weekday} onChange={e => setNewJob({ ...newJob, weekday: e.target.value })} style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.875rem' }}>
                                                    <option value="1">星期一</option><option value="2">星期二</option><option value="3">星期三</option>
                                                    <option value="4">星期四</option><option value="5">星期五</option><option value="6">星期六</option><option value="0">星期日</option>
                                                </select>
                                            </div>
                                        )}
                                        <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#6B7280', background: '#EFF6FF', padding: '0.5rem', borderRadius: '0.375rem' }}>💡 预览Cron: {newJob.cron}</div>
                                    </div>
                                )}
                            </div>

                            {/* 飞书通知 */}
                            <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.75rem', color: '#374151' }}>飞书通知配置</label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                    <input type="checkbox" checked={newJob.notify_on_failure} onChange={e => setNewJob({ ...newJob, notify_on_failure: e.target.checked })} />
                                    <span style={{ fontSize: '0.875rem' }}>需要发送通知 (成功/失败/自愈)</span>
                                </label>
                                {!!newJob.notify_on_failure && (
                                    <div style={{ marginTop: '0.75rem' }}>
                                        <input type="text" value={newJob.custom_webhook} onChange={e => setNewJob({ ...newJob, custom_webhook: e.target.value })} placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." style={{ width: '100%', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', fontSize: '0.75rem', outline: 'none' }} />
                                    </div>
                                )}
                            </div>

                            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                <button onClick={() => setShowCreateModal(false)} style={{ flex: 1, padding: '0.75rem', border: '1px solid #E5E7EB', borderRadius: '0.5rem', background: 'white', cursor: 'pointer' }}>取消</button>
                                <button onClick={handleSaveJob} disabled={!newJob.name || !newJob.scenario_id} style={{ flex: 1, padding: '0.75rem', border: 'none', borderRadius: '0.5rem', background: newJob.name && newJob.scenario_id ? '#667eea' : '#9CA3AF', color: 'white', cursor: newJob.name && newJob.scenario_id ? 'pointer' : 'not-allowed', fontWeight: '600' }}>
                                    {editingJobId ? '保存修改' : '创建任务'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* ============ 执行历史弹窗（含自愈状态展开） ============ */}
            {selectedJobHistory && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={() => setSelectedJobHistory(null)}>
                    <div style={{ background: 'white', borderRadius: '1rem', padding: '2rem', width: '90%', maxWidth: '860px', maxHeight: '80vh', overflowY: 'auto', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)' }} onClick={e => e.stopPropagation()}>
                        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem' }}>执行历史 - {selectedJobHistory.name}</h2>
                        {jobHistory.length === 0
                            ? <p style={{ textAlign: 'center', color: '#6B7280', padding: '2rem' }}>暂无执行记录</p>
                            : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                    {jobHistory.map(record => (
                                        <div key={record.id} style={{ border: '1px solid #E5E7EB', borderRadius: '0.75rem', overflow: 'hidden' }}>
                                            {/* 记录主行 */}
                                            <div style={{ display: 'flex', alignItems: 'center', padding: '0.75rem 1rem', gap: '1rem', background: '#FAFAFA' }}>
                                                {/* 状态图标 */}
                                                <div style={{ flex: '0 0 80px' }}>
                                                    {record.status === 'success' ? <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: '#10B981', fontSize: '0.875rem' }}><CheckCircle size={15} />成功</span>
                                                        : record.status === 'failed' ? <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: '#EF4444', fontSize: '0.875rem' }}><XCircle size={15} />失败</span>
                                                            : <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: '#F59E0B', fontSize: '0.875rem' }}><AlertCircle size={15} />运行中</span>}
                                                </div>
                                                {/* 时间 */}
                                                <div style={{ flex: 1, fontSize: '0.8rem', color: '#6B7280' }}>
                                                    <div>{new Date(record.started_at).toLocaleString()}</div>
                                                    {record.duration_ms > 0 && <div style={{ color: '#9CA3AF' }}>耗时: {record.duration_ms}ms</div>}
                                                </div>
                                                {/* 步骤统计 */}
                                                <div style={{ fontSize: '0.8rem', color: '#6B7280', textAlign: 'center' }}>
                                                    {record.total_steps ? `${record.passed_steps}/${record.total_steps} 步骤` : '-'}
                                                </div>
                                                {/* 自愈状态 */}
                                                {record.heal_status && <HealBadge status={record.heal_status} />}
                                                {/* 展开按钮（失败记录有根因时） */}
                                                {record.status === 'failed' && (
                                                    <button onClick={() => setExpandedHistoryId(expandedHistoryId === record.id ? null : record.id)} style={{ ...btnBase, color: '#6B7280', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}>
                                                        {expandedHistoryId === record.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                                        {record.root_cause ? '根因' : '详情'}
                                                    </button>
                                                )}
                                            </div>

                                            {/* 展开区：根因分析 + 修复建议 */}
                                            {expandedHistoryId === record.id && (() => {
                                                // 规范化根因数据
                                                const rc = record.root_cause
                                                const analysisItems: any[] = Array.isArray(rc?.analysis) ? rc.analysis : []
                                                const hasItems = analysisItems.length > 0
                                                // 自愈结论（来自 join 的 heal_result 字段）
                                                const healResult = record.heal_result
                                                // 存根因但 analysis 为空的情况（如 no_failure/手动触发但无步骤数据）
                                                const rcMessage = rc?.message || ''
                                                const showTriggerBtn = !hasItems  // 无有效分析条目时，始终显示「触发自愈」

                                                return (
                                                    <div style={{ padding: '1rem', background: '#F8FAFF', borderTop: '1px solid #E5E7EB' }}>
                                                        <p style={{ fontSize: '0.8rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>🔍 根因分析</p>

                                                        {/* 有效分析条目 */}
                                                        {hasItems ? (
                                                            <>
                                                                {analysisItems.map((a: any, i: number) => (
                                                                    <div key={i} style={{ marginBottom: '0.5rem', padding: '0.5rem', background: 'white', borderRadius: '0.375rem', border: '1px solid #E5E7EB', fontSize: '0.8rem' }}>
                                                                        <div style={{ fontWeight: '600', color: '#374151' }}>{a.failure_type || '执行失败'}</div>
                                                                        <div style={{ color: '#6B7280', marginTop: '0.2rem' }}>{a.root_cause || a.message || ''}</div>
                                                                        {a.suggested_fix && <div style={{ color: '#4F46E5', marginTop: '0.25rem' }}>💡 {a.suggested_fix}</div>}
                                                                        {!a.can_heal && <div style={{ color: '#DC2626', marginTop: '0.25rem', fontSize: '0.75rem' }}>⚠️ 此问题需人工介入</div>}
                                                                    </div>
                                                                ))}
                                                                {/* 自愈结论 */}
                                                                {healResult?.message && (
                                                                    <p style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: healResult.status === 'healed' ? '#059669' : '#DC2626' }}>
                                                                        {healResult.status === 'healed' ? '✅' : '⚠️'} {healResult.message}
                                                                    </p>
                                                                )}
                                                            </>
                                                        ) : (
                                                            /* 无有效分析条目：显示原因说明 + 触发自愈按钮 */
                                                            <div style={{ background: '#FFF7ED', border: '1px solid #FDBA74', borderRadius: '0.5rem', padding: '0.75rem', display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                                                                <div style={{ flex: 1 }}>
                                                                    <p style={{ fontSize: '0.8rem', color: '#92400E', marginBottom: '0.3rem' }}>
                                                                        {rcMessage
                                                                            ? (rcMessage === '测试全部通过'
                                                                                ? '⚠️ 自愈分析时未能获取到真实失败步骤数据，无法生成根因报告'
                                                                                : `ℹ️ ${rcMessage}`)
                                                                            : `ℹ️ ${record.error_message || '执行失败，暂无详细根因数据'}`}
                                                                    </p>
                                                                    <p style={{ fontSize: '0.75rem', color: '#B45309' }}>
                                                                        点击「触发自愈」重新分析最近一次失败原因
                                                                    </p>
                                                                </div>
                                                                <button
                                                                    onClick={() => handleManualHeal(selectedJobHistory.id)}
                                                                    disabled={healingTriggeringId === selectedJobHistory.id}
                                                                    style={{ padding: '0.35rem 0.75rem', background: '#059669', color: 'white', border: 'none', borderRadius: '0.375rem', cursor: 'pointer', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.3rem', whiteSpace: 'nowrap', opacity: healingTriggeringId === selectedJobHistory.id ? 0.7 : 1 }}
                                                                >
                                                                    <Wrench size={12} />
                                                                    {healingTriggeringId === selectedJobHistory.id ? '启动中...' : '触发自愈'}
                                                                </button>
                                                            </div>
                                                        )}
                                                    </div>
                                                )
                                            })()}

                                        </div>
                                    ))}
                                </div>
                            )
                        }
                    </div>
                </div>
            )}

            {/* ============ 趋势监控弹窗 ============ */}
            {trendJob && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={() => setTrendJob(null)}>
                    <div style={{ background: 'white', borderRadius: '1rem', padding: '2rem', width: '90%', maxWidth: '700px', maxHeight: '80vh', overflowY: 'auto', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)' }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                            <TrendingUp size={22} color="#8B5CF6" />
                            <h2 style={{ fontSize: '1.5rem', fontWeight: '700' }}>趋势监控 - {trendJob.name}</h2>
                        </div>

                        {trendLoading ? (
                            <div style={{ textAlign: 'center', padding: '2rem', color: '#6B7280' }}>加载趋势数据中...</div>
                        ) : (
                            <>
                                {/* 性能劣化告警 */}
                                {perfAlert && perfAlert.degraded && (
                                    <div style={{ background: '#FEF3C7', border: '1px solid #F59E0B', borderRadius: '0.75rem', padding: '1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                        <AlertCircle size={20} color="#B45309" />
                                        <div>
                                            <p style={{ fontWeight: '600', color: '#92400E', fontSize: '0.9rem' }}>⚠️ 检测到性能劣化</p>
                                            <p style={{ color: '#92400E', fontSize: '0.8rem' }}>{perfAlert.message}</p>
                                            <p style={{ color: '#78350F', fontSize: '0.75rem', marginTop: '0.25rem' }}>基线均值: {perfAlert.baseline_avg_ms}ms → 近期均值: {perfAlert.recent_avg_ms}ms</p>
                                        </div>
                                    </div>
                                )}
                                {perfAlert && !perfAlert.degraded && perfAlert.change_pct !== undefined && (
                                    <div style={{ background: '#D1FAE5', border: '1px solid #10B981', borderRadius: '0.75rem', padding: '0.75rem 1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <CheckCircle size={18} color="#065F46" />
                                        <p style={{ color: '#065F46', fontSize: '0.85rem' }}>{perfAlert.message}</p>
                                    </div>
                                )}

                                {trendData.length === 0 ? (
                                    <div style={{ textAlign: 'center', padding: '2rem', color: '#9CA3AF' }}>
                                        <TrendingUp size={40} style={{ margin: '0 auto 0.5rem', opacity: 0.3 }} />
                                        <p>暂无趋势数据</p>
                                        <p style={{ fontSize: '0.8rem' }}>任务执行后会自动采集趋势数据</p>
                                    </div>
                                ) : (
                                    <>
                                        {/* 成功率图表 */}
                                        <div style={{ background: '#F9FAFB', borderRadius: '0.75rem', padding: '1rem', marginBottom: '1rem' }}>
                                            <p style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.75rem' }}>📊 近7天成功率</p>
                                            <MiniBarChart data={trendData} valueKey="success_rate" colorFn={v => v >= 80 ? '#10B981' : v >= 50 ? '#F59E0B' : '#EF4444'} />
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
                                                {trendData.map(d => <span key={d.date} style={{ fontSize: '0.6rem', color: '#9CA3AF', flex: 1, textAlign: 'center' }}>{d.date.slice(5)}</span>)}
                                            </div>
                                        </div>

                                        {/* 耗时图表 */}
                                        <div style={{ background: '#F9FAFB', borderRadius: '0.75rem', padding: '1rem', marginBottom: '1rem' }}>
                                            <p style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.75rem' }}>⏱️ 近7天执行耗时 (ms)</p>
                                            <MiniBarChart data={trendData} valueKey="avg_duration_ms" colorFn={_ => '#6366F1'} />
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
                                                {trendData.map(d => <span key={d.date} style={{ fontSize: '0.6rem', color: '#9CA3AF', flex: 1, textAlign: 'center' }}>{d.date.slice(5)}</span>)}
                                            </div>
                                        </div>

                                        {/* 明细表 */}
                                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                            <thead>
                                                <tr style={{ background: '#F3F4F6' }}>
                                                    {['日期', '执行次数', '成功率', '平均耗时', '最大耗时'].map(h => <th key={h} style={{ padding: '0.5rem 0.75rem', textAlign: 'left', color: '#6B7280', fontWeight: '600' }}>{h}</th>)}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {trendData.map(d => (
                                                    <tr key={d.date} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                                        <td style={{ padding: '0.5rem 0.75rem' }}>{d.date}</td>
                                                        <td style={{ padding: '0.5rem 0.75rem' }}>{d.total_runs}</td>
                                                        <td style={{ padding: '0.5rem 0.75rem' }}>
                                                            <span style={{ color: d.success_rate >= 80 ? '#10B981' : d.success_rate >= 50 ? '#F59E0B' : '#EF4444', fontWeight: '600' }}>{d.success_rate}%</span>
                                                        </td>
                                                        <td style={{ padding: '0.5rem 0.75rem' }}>{d.avg_duration_ms} ms</td>
                                                        <td style={{ padding: '0.5rem 0.75rem' }}>{d.max_duration_ms} ms</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </>
                                )}
                            </>
                        )}
                    </div>
                </div>
            )}

            {/* ============ 自愈历史弹窗 ============ */}
            {healingJob && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={() => setHealingJob(null)}>
                    <div style={{ background: 'white', borderRadius: '1rem', padding: '2rem', width: '90%', maxWidth: '760px', maxHeight: '80vh', overflowY: 'auto', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)' }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <Wrench size={22} color="#10B981" />
                                <h2 style={{ fontSize: '1.5rem', fontWeight: '700' }}>自愈历史 - {healingJob.name}</h2>
                            </div>
                            <button onClick={() => handleManualHeal(healingJob.id)} disabled={healingTriggeringId === healingJob.id} style={{ padding: '0.5rem 1rem', background: '#059669', color: 'white', border: 'none', borderRadius: '0.5rem', cursor: 'pointer', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: healingTriggeringId === healingJob.id ? 0.6 : 1 }}>
                                <RefreshCw size={15} />{healingTriggeringId === healingJob.id ? '自愈启动中...' : '手动触发自愈'}
                            </button>
                        </div>

                        {healingLoading ? (
                            <div style={{ textAlign: 'center', padding: '2rem', color: '#6B7280' }}>加载自愈历史...</div>
                        ) : healingHistory.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '3rem', color: '#9CA3AF' }}>
                                <Wrench size={40} style={{ margin: '0 auto 0.5rem', opacity: 0.3 }} />
                                <p>暂无自愈记录</p>
                                <p style={{ fontSize: '0.8rem' }}>任务执行失败时会自动触发自愈分析</p>
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {healingHistory.map(h => (
                                    <div key={h.id} style={{ border: '1px solid #E5E7EB', borderRadius: '0.75rem', overflow: 'hidden' }}>
                                        {/* 头部 */}
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', background: '#FAFAFA' }}>
                                            <HealBadge status={h.status} />
                                            <div style={{ flex: 1, fontSize: '0.8rem', color: '#6B7280' }}>
                                                <span>触发时间: {new Date(h.triggered_at).toLocaleString()}</span>
                                                {h.completed_at && <span style={{ marginLeft: '1rem' }}>完成: {new Date(h.completed_at).toLocaleString()}</span>}
                                            </div>
                                        </div>

                                        {/* 根因+修复内容 */}
                                        {h.root_cause && (
                                            <div style={{ padding: '0.75rem 1rem', fontSize: '0.8rem' }}>
                                                <p style={{ fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>根因分析</p>
                                                {(h.root_cause?.analysis || []).slice(0, 2).map((a: any, i: number) => (
                                                    <div key={i} style={{ marginBottom: '0.4rem', padding: '0.4rem 0.6rem', background: '#F9FAFB', borderRadius: '0.375rem', borderLeft: '3px solid #6366F1' }}>
                                                        <span style={{ fontWeight: '600', color: '#374151' }}>{a.failure_type}</span>
                                                        <span style={{ color: '#6B7280' }}> → {a.suggested_fix}</span>
                                                    </div>
                                                ))}
                                                {h.heal_result?.message && (
                                                    <p style={{ color: '#059669', marginTop: '0.4rem' }}>✅ {h.heal_result.message}</p>
                                                )}
                                                {h.heal_result?.status === 'cannot_heal' && (
                                                    <p style={{ color: '#DC2626', marginTop: '0.4rem' }}>⚠️ {h.heal_result.message}</p>
                                                )}
                                            </div>
                                        )}
                                        {h.error_message && (
                                            <div style={{ padding: '0.75rem 1rem', fontSize: '0.8rem', color: '#EF4444' }}>自愈异常: {h.error_message}</div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </>
    )
}
