'use client'

import { useState, useEffect } from 'react'
import { Plus, Edit2, Trash2, CheckCircle, Globe } from 'lucide-react'

interface Environment {
    id: number
    env_name: string
    base_url: string
    is_default: number
    created_at: string
}

export default function EnvironmentsPage() {
    const [environments, setEnvironments] = useState<Environment[]>([])
    const [projectId, setProjectId] = useState('default-project')
    const [showForm, setShowForm] = useState(false)
    const [editingEnv, setEditingEnv] = useState<Environment | null>(null)
    const [formData, setFormData] = useState({
        env_name: '',
        base_url: '',
        is_default: false
    })

    useEffect(() => {
        loadEnvironments()
    }, [projectId])

    const loadEnvironments = async () => {
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects/${projectId}/environments`)
            if (res.ok) {
                const data = await res.json()
                setEnvironments(data)
            }
        } catch (error) {
            console.error('加载环境失败:', error)
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            const res = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects/${projectId}/environments`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                }
            )
            if (res.ok) {
                loadEnvironments()
                setShowForm(false)
                setFormData({ env_name: '', base_url: '', is_default: false })
                setEditingEnv(null)
            }
        } catch (error) {
            console.error('保存环境失败:', error)
        }
    }

    const handleDelete = async (envName: string) => {
        if (!confirm(`确定删除环境 "${envName}" 吗?`)) return
        try {
            const res = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects/${projectId}/environments/${envName}`,
                { method: 'DELETE' }
            )
            if (res.ok) {
                loadEnvironments()
            }
        } catch (error) {
            console.error('删除环境失败:', error)
        }
    }

    const handleEdit = (env: Environment) => {
        setEditingEnv(env)
        setFormData({
            env_name: env.env_name,
            base_url: env.base_url,
            is_default: env.is_default === 1
        })
        setShowForm(true)
    }

    return (
        <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                    <Globe size={32} style={{ color: '#3B82F6' }} />
                    <h1 style={{ fontSize: '2rem', fontWeight: '700', color: '#1F2937' }}>环境管理</h1>
                </div>
                <p style={{ color: '#6B7280' }}>管理多套测试环境,支持快速切换和配置</p>
            </div>

            {/* Add Button */}
            <button
                onClick={() => {
                    setShowForm(true)
                    setEditingEnv(null)
                    setFormData({ env_name: '', base_url: '', is_default: false })
                }}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.75rem 1.5rem',
                    background: 'linear-gradient(to right, #3B82F6, #2563EB)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.5rem',
                    cursor: 'pointer',
                    fontWeight: '600',
                    marginBottom: '1.5rem'
                }}
            >
                <Plus size={20} />
                添加环境
            </button>

            {/* Form */}
            {showForm && (
                <div style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '0.75rem',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                    marginBottom: '1.5rem'
                }}>
                    <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem' }}>
                        {editingEnv ? '编辑环境' : '新建环境'}
                    </h3>
                    <form onSubmit={handleSubmit}>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                环境名称
                            </label>
                            <input
                                type="text"
                                value={formData.env_name}
                                onChange={(e) => setFormData({ ...formData, env_name: e.target.value })}
                                placeholder="如: dev, test, staging, prod"
                                required
                                disabled={!!editingEnv}
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '2px solid #E5E7EB',
                                    borderRadius: '0.5rem',
                                    outline: 'none'
                                }}
                            />
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                Base URL
                            </label>
                            <input
                                type="url"
                                value={formData.base_url}
                                onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                                placeholder="https://api.example.com"
                                required
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '2px solid #E5E7EB',
                                    borderRadius: '0.5rem',
                                    outline: 'none'
                                }}
                            />
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={formData.is_default}
                                    onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                                    style={{ width: '1.25rem', height: '1.25rem', cursor: 'pointer' }}
                                />
                                <span style={{ fontWeight: '500' }}>设为默认环境</span>
                            </label>
                        </div>
                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <button
                                type="submit"
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#3B82F6',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '0.5rem',
                                    cursor: 'pointer',
                                    fontWeight: '600'
                                }}
                            >
                                保存
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    setShowForm(false)
                                    setEditingEnv(null)
                                }}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    background: '#E5E7EB',
                                    color: '#374151',
                                    border: 'none',
                                    borderRadius: '0.5rem',
                                    cursor: 'pointer',
                                    fontWeight: '600'
                                }}
                            >
                                取消
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Environments List */}
            <div style={{ display: 'grid', gap: '1rem' }}>
                {environments.map((env) => (
                    <div
                        key={env.id}
                        style={{
                            background: 'white',
                            padding: '1.5rem',
                            borderRadius: '0.75rem',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                            border: env.is_default ? '2px solid #3B82F6' : '2px solid #E5E7EB',
                            position: 'relative'
                        }}
                    >
                        {env.is_default && (
                            <div style={{
                                position: 'absolute',
                                top: '1rem',
                                right: '1rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.25rem',
                                padding: '0.25rem 0.75rem',
                                background: '#DBEAFE',
                                color: '#1D4ED8',
                                borderRadius: '9999px',
                                fontSize: '0.75rem',
                                fontWeight: '600'
                            }}>
                                <CheckCircle size={14} />
                                默认
                            </div>
                        )}
                        <div style={{ marginBottom: '0.75rem' }}>
                            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#1F2937', marginBottom: '0.5rem' }}>
                                {env.env_name}
                            </h3>
                            <p style={{ color: '#6B7280', fontSize: '0.875rem' }}>{env.base_url}</p>
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                                onClick={() => handleEdit(env)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.25rem',
                                    padding: '0.5rem 1rem',
                                    background: '#F3F4F6',
                                    border: 'none',
                                    borderRadius: '0.375rem',
                                    cursor: 'pointer',
                                    fontSize: '0.875rem'
                                }}
                            >
                                <Edit2 size={16} />
                                编辑
                            </button>
                            <button
                                onClick={() => handleDelete(env.env_name)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.25rem',
                                    padding: '0.5rem 1rem',
                                    background: '#FEE2E2',
                                    color: '#DC2626',
                                    border: 'none',
                                    borderRadius: '0.375rem',
                                    cursor: 'pointer',
                                    fontSize: '0.875rem'
                                }}
                            >
                                <Trash2 size={16} />
                                删除
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {environments.length === 0 && !showForm && (
                <div style={{
                    textAlign: 'center',
                    padding: '3rem',
                    color: '#9CA3AF'
                }}>
                    <Globe size={48} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
                    <p>暂无环境配置,点击"添加环境"开始创建</p>
                </div>
            )}
        </div>
    )
}
