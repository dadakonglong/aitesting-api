'use client'

import { useState, useEffect } from 'react'
import { Plus, Edit2, Trash2, FolderOpen, Settings, Download, Upload } from 'lucide-react'

interface Project {
    id: string
    name: string
    description: string
    created_at: string
}

export default function ProjectManagementTab() {
    const [projects, setProjects] = useState<Project[]>([])
    const [showForm, setShowForm] = useState(false)
    const [editingProject, setEditingProject] = useState<Project | null>(null)
    const [formData, setFormData] = useState({
        name: '',
        description: ''
    })
    const [importLoading, setImportLoading] = useState(false)

    const handleExport = async (project: Project) => {
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects/${project.id}/export`)
            if (res.ok) {
                const data = await res.json()
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
                const url = window.URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `${project.name}_backup.json`
                document.body.appendChild(a)
                a.click()
                window.URL.revokeObjectURL(url)
                document.body.removeChild(a)
            } else {
                alert('导出失败')
            }
        } catch (error) {
            console.error('导出失败:', error)
            alert('导出失败')
        }
    }

    const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        setImportLoading(true)
        try {
            const reader = new FileReader()
            reader.onload = async (event) => {
                try {
                    const content = JSON.parse(event.target?.result as string)
                    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects/import`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(content)
                    })
                    if (res.ok) {
                        const result = await res.json()
                        alert(result.message || '导入成功')
                        loadProjects()
                    } else {
                        const err = await res.json()
                        alert(`导入失败: ${err.detail || '未知错误'}`)
                    }
                } catch (err) {
                    alert('文件格式错误，请确保上传的是有效的导出 JSON')
                } finally {
                    setImportLoading(false)
                    // Reset input
                    e.target.value = ''
                }
            }
            reader.readAsText(file)
        } catch (error) {
            console.error('读取文件失败:', error)
            setImportLoading(false)
        }
    }

    useEffect(() => {
        loadProjects()
    }, [])

    const loadProjects = async () => {
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects`)
            if (res.ok) {
                const data = await res.json()
                // 确保data是数组
                if (Array.isArray(data)) {
                    setProjects(data)
                } else {
                    console.error('API返回的不是数组:', data)
                    setProjects([])
                }
            } else {
                console.error('加载项目失败,状态码:', res.status)
                setProjects([])
            }
        } catch (error) {
            console.error('加载项目失败:', error)
            setProjects([])
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            const res = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                }
            )
            if (res.ok) {
                loadProjects()
                setShowForm(false)
                setFormData({ name: '', description: '' })
                setEditingProject(null)
            }
        } catch (error) {
            console.error('保存项目失败:', error)
        }
    }

    const handleDelete = async (projectId: string) => {
        if (!confirm(`确定删除项目 "${projectId}" 吗? 这将删除该项目下的所有数据!`)) return
        try {
            const res = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects/${projectId}`,
                { method: 'DELETE' }
            )
            if (res.ok) {
                loadProjects()
            }
        } catch (error) {
            console.error('删除项目失败:', error)
        }
    }

    return (
        <>

            {/* Add Button */}
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
                <button
                    onClick={() => {
                        setShowForm(true)
                        setEditingProject(null)
                        setFormData({ name: '', description: '' })
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
                    }}
                >
                    <Plus size={20} />
                    新建项目
                </button>

                <div style={{ position: 'relative' }}>
                    <input
                        type="file"
                        accept=".json"
                        onChange={handleImport}
                        style={{
                            position: 'absolute',
                            inset: 0,
                            opacity: 0,
                            cursor: 'pointer',
                            zIndex: 10
                        }}
                        disabled={importLoading}
                    />
                    <button
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.75rem 1.5rem',
                            background: 'white',
                            color: '#374151',
                            border: '2px solid #E5E7EB',
                            borderRadius: '0.5rem',
                            cursor: 'pointer',
                            fontWeight: '600',
                            opacity: importLoading ? 0.5 : 1
                        }}
                    >
                        <Upload size={20} />
                        {importLoading ? '导入中...' : '导入项目'}
                    </button>
                </div>
            </div>

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
                        {editingProject ? '编辑项目' : '新建项目'}
                    </h3>
                    <form onSubmit={handleSubmit}>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                项目名称
                            </label>
                            <input
                                type="text"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                placeholder="如: 我的应用, 用户服务"
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
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                                项目描述
                            </label>
                            <textarea
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                placeholder="简要描述该项目的用途"
                                rows={3}
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    border: '2px solid #E5E7EB',
                                    borderRadius: '0.5rem',
                                    outline: 'none',
                                    resize: 'vertical'
                                }}
                            />
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
                                    setEditingProject(null)
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

            {/* Projects Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
                {projects.map((project) => (
                    <div
                        key={project.id}
                        style={{
                            background: 'white',
                            padding: '1.5rem',
                            borderRadius: '0.75rem',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                            border: '2px solid #E5E7EB',
                            transition: 'all 0.2s',
                            cursor: 'pointer'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = '#3B82F6'
                            e.currentTarget.style.boxShadow = '0 4px 12px rgba(59, 130, 246, 0.2)'
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = '#E5E7EB'
                            e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.05)'
                        }}
                    >
                        <div style={{ marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                <FolderOpen size={20} style={{ color: '#3B82F6' }} />
                                <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#1F2937', margin: 0 }}>
                                    {project.name}
                                </h3>
                            </div>
                            <p style={{ fontSize: '0.75rem', color: '#9CA3AF', margin: 0 }}>
                                ID: {project.id}
                            </p>
                        </div>
                        <p style={{ color: '#6B7280', fontSize: '0.875rem', marginBottom: '1rem', minHeight: '2.5rem' }}>
                            {project.description || '暂无描述'}
                        </p>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                                onClick={() => window.location.href = `/environments?project=${project.id}`}
                                style={{
                                    flex: 1,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '0.25rem',
                                    padding: '0.5rem',
                                    background: '#EFF6FF',
                                    color: '#2563EB',
                                    border: 'none',
                                    borderRadius: '0.375rem',
                                    cursor: 'pointer',
                                    fontSize: '0.875rem',
                                    fontWeight: '500'
                                }}
                            >
                                <Settings size={16} />
                                管理
                            </button>
                            <button
                                onClick={() => handleExport(project)}
                                title="导出项目"
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    padding: '0.5rem',
                                    background: '#F3F4F6',
                                    color: '#4B5563',
                                    border: 'none',
                                    borderRadius: '0.375rem',
                                    cursor: 'pointer',
                                    fontSize: '0.875rem'
                                }}
                            >
                                <Download size={16} />
                            </button>
                            <button
                                onClick={() => handleDelete(project.id)}
                                title="删除项目"
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    padding: '0.5rem',
                                    background: '#FEE2E2',
                                    color: '#DC2626',
                                    border: 'none',
                                    borderRadius: '0.375rem',
                                    cursor: 'pointer',
                                    fontSize: '0.875rem'
                                }}
                            >
                                <Trash2 size={16} />
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {projects.length === 0 && !showForm && (
                <div style={{
                    textAlign: 'center',
                    padding: '4rem 2rem',
                    background: 'white',
                    borderRadius: '0.75rem',
                    border: '2px dashed #E5E7EB'
                }}>
                    <FolderOpen size={64} style={{ margin: '0 auto 1rem', opacity: 0.3, color: '#9CA3AF' }} />
                    <h3 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#1F2937', marginBottom: '0.5rem' }}>
                        还没有项目
                    </h3>
                    <p style={{ color: '#6B7280', marginBottom: '1.5rem' }}>
                        创建您的第一个项目,开始管理API测试
                    </p>
                    <button
                        onClick={() => setShowForm(true)}
                        style={{
                            padding: '0.75rem 1.5rem',
                            background: 'linear-gradient(to right, #3B82F6, #2563EB)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.5rem',
                            cursor: 'pointer',
                            fontWeight: '600'
                        }}
                    >
                        立即创建
                    </button>
                </div>
            )}
        </>
    )
}
