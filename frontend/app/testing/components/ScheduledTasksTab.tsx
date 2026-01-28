'use client'

import { useState, useEffect } from 'react'
import { useProject } from '../../contexts/ProjectContext'
import { Clock, Play, Pause, Trash2, Plus, Calendar, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

export default function ScheduledTasksTab() {
    const { currentProject } = useProject()
    const [jobs, setJobs] = useState<any[]>([])
    const [scenarios, setScenarios] = useState<any[]>([])
    const [environments, setEnvironments] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [selectedJobHistory, setSelectedJobHistory] = useState<any>(null)
    const [jobHistory, setJobHistory] = useState<any[]>([])

    // 新建任务表单
    const [newJob, setNewJob] = useState({
        name: '',
        description: '',
        scenario_id: 0,
        cron: '0 2 * * *',
        environment_id: null,
        notify_on_failure: false
    })

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

    const handleCreateJob = async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/scheduler/jobs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...newJob,
                    project_id: currentProject
                })
            })
            if (response.ok) {
                setShowCreateModal(false)
                setNewJob({
                    name: '',
                    description: '',
                    scenario_id: 0,
                    cron: '0 2 * * *',
                    environment_id: null,
                    notify_on_failure: false
                })
                fetchJobs()
            }
        } catch (error) {
            console.error('创建任务失败:', error)
        }
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
        { label: '每月1号凌晨3点', value: '0 3 1 * *' }
    ]

    return (
        <>
            {/* 创建任务按钮 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <p style={{ color: '#6B7280' }}>
                    项目: {currentProject} | 共 {jobs.length} 个任务
                </p>
                <button
                    onClick={() => setShowCreateModal(true)}
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
                        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem' }}>创建定时任务</h2>

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
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.5rem' }}>Cron表达式</label>
                                <select
                                    value={newJob.cron}
                                    onChange={(e) => setNewJob({ ...newJob, cron: e.target.value })}
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '0.375rem',
                                        marginBottom: '0.5rem'
                                    }}
                                >
                                    {cronPresets.map((preset) => (
                                        <option key={preset.value} value={preset.value}>{preset.label} ({preset.value})</option>
                                    ))}
                                </select>
                                <input
                                    type="text"
                                    value={newJob.cron}
                                    onChange={(e) => setNewJob({ ...newJob, cron: e.target.value })}
                                    placeholder="自定义 Cron 表达式"
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem',
                                        border: '1px solid #E5E7EB',
                                        borderRadius: '0.375rem',
                                        fontSize: '0.875rem'
                                    }}
                                />
                            </div>

                            <div>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                    <input
                                        type="checkbox"
                                        checked={newJob.notify_on_failure}
                                        onChange={(e) => setNewJob({ ...newJob, notify_on_failure: e.target.checked })}
                                    />
                                    <span style={{ fontSize: '0.875rem' }}>失败时发送通知</span>
                                </label>
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
                                    onClick={handleCreateJob}
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
                                    创建
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 执行历史弹窗 */}
            {selectedJobHistory && (
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
            )}
        </>
    )
}
