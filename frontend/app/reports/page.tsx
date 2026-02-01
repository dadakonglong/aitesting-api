'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useProject } from '../contexts/ProjectContext'
import { BarChart2, Trash2, Pencil } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_AI_API_URL || 'http://localhost:8000'

interface TestReport {
    id: number
    name: string
    report_type: string
    creator: string
    created_at: string
    end_time: string
    trigger_method: string
    status: string
}

export default function ReportsPage() {
    const router = useRouter()
    const { currentProject } = useProject()
    const [reports, setReports] = useState<TestReport[]>([])
    const [loading, setLoading] = useState(true)
    const [editingId, setEditingId] = useState<number | null>(null)
    const [editingName, setEditingName] = useState('')

    useEffect(() => {
        const load = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/v1/test-reports?project_id=${encodeURIComponent(currentProject)}`)
                if (res.ok) {
                    const data = await res.json()
                    setReports(Array.isArray(data) ? data : [])
                }
            } catch {
                setReports([])
            } finally {
                setLoading(false)
            }
        }
        load()
    }, [currentProject])

    const handleDelete = async (id: number) => {
        if (!confirm('确定删除该报告吗？')) return
        try {
            const res = await fetch(`${API_BASE}/api/v1/test-reports/${id}`, { method: 'DELETE' })
            if (res.ok) setReports((prev) => prev.filter((r) => r.id !== id))
        } catch {
            alert('删除失败')
        }
    }

    const handleSaveName = async (id: number) => {
        if (!editingName.trim()) return
        try {
            const res = await fetch(`${API_BASE}/api/v1/test-reports/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: editingName.trim() }),
            })
            if (res.ok) {
                setReports((prev) => prev.map((r) => (r.id === id ? { ...r, name: editingName.trim() } : r)))
                setEditingId(null)
            }
        } catch {
            alert('保存失败')
        }
    }

    return (
        <div style={{ padding: '2rem', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', minHeight: '100vh' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem', fontWeight: '700', color: 'white', marginBottom: '0.5rem' }}>📊 测试报告</h1>
                <p style={{ color: 'rgba(255,255,255,0.8)' }}>项目: {currentProject}</p>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.98)', borderRadius: '1rem', padding: '1.5rem', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}>
                {loading ? (
                    <div style={{ padding: '3rem', textAlign: 'center', color: '#6B7280' }}>加载中...</div>
                ) : reports.length === 0 ? (
                    <div style={{ padding: '3rem', textAlign: 'center', color: '#6B7280' }}>暂无测试报告，执行接口测试后会自动保存</div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                            <thead>
                                <tr style={{ borderBottom: '2px solid #E5E7EB' }}>
                                    <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600', color: '#6B7280' }}>名称</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600', color: '#6B7280' }}>报告类型</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600', color: '#6B7280' }}>创建人</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600', color: '#6B7280' }}>创建时间</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600', color: '#6B7280' }}>结束时间</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600', color: '#6B7280' }}>触发方式</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600', color: '#6B7280' }}>状态</th>
                                    <th style={{ padding: '0.75rem', textAlign: 'center', fontWeight: '600', color: '#6B7280' }}>操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reports.map((r) => (
                                    <tr key={r.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                        <td style={{ padding: '0.75rem' }}>
                                            {editingId === r.id ? (
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <input
                                                        value={editingName}
                                                        onChange={(e) => setEditingName(e.target.value)}
                                                        onBlur={() => handleSaveName(r.id)}
                                                        onKeyDown={(e) => e.key === 'Enter' && handleSaveName(r.id)}
                                                        autoFocus
                                                        style={{ padding: '0.25rem 0.5rem', border: '1px solid #D1D5DB', borderRadius: '0.375rem', fontSize: '0.875rem' }}
                                                    />
                                                </div>
                                            ) : (
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    <span style={{ fontWeight: '500', color: '#111827' }}>{r.name}</span>
                                                    <button
                                                        type="button"
                                                        onClick={() => { setEditingId(r.id); setEditingName(r.name) }}
                                                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.25rem' }}
                                                        title="编辑名称"
                                                    >
                                                        <Pencil size={14} color="#9CA3AF" />
                                                    </button>
                                                </div>
                                            )}
                                        </td>
                                        <td style={{ padding: '0.75rem' }}>
                                            <span style={{ padding: '0.2rem 0.5rem', borderRadius: '0.25rem', border: '1px solid #C4B5FD', background: '#F5F3FF', fontSize: '0.75rem', marginRight: '0.25rem' }}>接口测试</span>
                                        </td>
                                        <td style={{ padding: '0.75rem', color: '#6B7280' }}>{r.creator || '-'}</td>
                                        <td style={{ padding: '0.75rem', color: '#6B7280' }}>{r.created_at || '-'}</td>
                                        <td style={{ padding: '0.75rem', color: '#6B7280' }}>{r.end_time || r.created_at || '-'}</td>
                                        <td style={{ padding: '0.75rem', color: '#6B7280' }}>{r.trigger_method || '手动触发'}</td>
                                        <td style={{ padding: '0.75rem' }}>
                                            <span
                                                style={{
                                                    padding: '0.2rem 0.6rem',
                                                    borderRadius: '9999px',
                                                    fontSize: '0.75rem',
                                                    fontWeight: '500',
                                                    background: r.status === 'success' ? '#D1FAE5' : '#FEE2E2',
                                                    color: r.status === 'success' ? '#065F46' : '#991B1B',
                                                }}
                                            >
                                                {r.status === 'success' ? '通过' : 'Error'}
                                            </span>
                                        </td>
                                        <td style={{ padding: '0.75rem' }}>
                                            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                                                <button
                                                    type="button"
                                                    onClick={() => router.push(`/reports/${r.id}`)}
                                                    style={{
                                                        width: '36px',
                                                        height: '36px',
                                                        borderRadius: '50%',
                                                        border: 'none',
                                                        background: 'linear-gradient(135deg, #667eea, #764ba2)',
                                                        color: 'white',
                                                        cursor: 'pointer',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                    }}
                                                    title="查看报告详情"
                                                >
                                                    <BarChart2 size={18} />
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => handleDelete(r.id)}
                                                    style={{
                                                        width: '36px',
                                                        height: '36px',
                                                        borderRadius: '50%',
                                                        border: 'none',
                                                        background: '#FEE2E2',
                                                        color: '#DC2626',
                                                        cursor: 'pointer',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                    }}
                                                    title="删除"
                                                >
                                                    <Trash2 size={18} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}
