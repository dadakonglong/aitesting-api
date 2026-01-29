'use client'

import { useState, useEffect } from 'react'
import { Globe, Plus, Trash2, X } from 'lucide-react'
import { useSearchParams } from 'next/navigation'
import { useProject } from '../../contexts/ProjectContext'

export default function EnvironmentManagementTab() {
    const { currentProject, setCurrentProject, projects } = useProject()
    const searchParams = useSearchParams()
    const [environments, setEnvironments] = useState<any[]>([])
    const [newEnvName, setNewEnvName] = useState('')
    const [newEnvUrl, setNewEnvUrl] = useState('')

    // 监听 URL 中的 project 参数并更新当前项目
    useEffect(() => {
        const projectId = searchParams?.get('project')
        if (projectId && projectId !== currentProject) {
            setCurrentProject(projectId)
        }
    }, [searchParams, currentProject, setCurrentProject])

    // 获取当前项目名称
    const projectName = projects.find(p => p.id === currentProject)?.name || currentProject

    useEffect(() => {
        if (currentProject) {
            fetchEnvironments(currentProject)
        }
    }, [currentProject])

    const fetchEnvironments = async (projectId: string) => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/projects/${projectId}/environments`)
            if (response.ok) {
                const data = await response.json()
                setEnvironments(Array.isArray(data) ? data : [])
            } else {
                setEnvironments([])
            }
        } catch (error) {
            console.error('获取环境配置失败:', error)
            setEnvironments([])
        }
    }

    const handleSaveEnv = async () => {
        if (!newEnvName || !newEnvUrl) {
            alert('请填写环境名称和Base URL')
            return
        }

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
            } else {
                alert('保存失败,请稍后重试')
            }
        } catch (error) {
            console.error('保存环境失败:', error)
            alert('保存失败,请稍后重试')
        }
    }

    const handleDeleteEnv = async (envName: string) => {
        if (!confirm(`确定要删除环境 "${envName}" 吗?`)) return

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_AI_API_URL}/api/v1/projects/${currentProject}/environments/${envName}`, {
                method: 'DELETE'
            })
            if (response.ok) {
                fetchEnvironments(currentProject)
            } else {
                alert('删除失败,请稍后重试')
            }
        } catch (error) {
            console.error('删除环境失败:', error)
            alert('删除失败,请稍后重试')
        }
    }

    return (
        <>
            {/* 说明 */}
            <div style={{
                background: '#EFF6FF',
                border: '1px solid #DBEAFE',
                borderRadius: '0.75rem',
                padding: '1rem',
                marginBottom: '1.5rem'
            }}>
                <p style={{ fontSize: '0.875rem', color: '#1E40AF', margin: 0 }}>
                    💡 为项目 <strong>{projectName}</strong> 配置不同环境的域名,在执行测试时可以选择对应环境
                </p>
            </div>

            {/* 添加环境表单 */}
            <div style={{
                background: 'white',
                borderRadius: '0.75rem',
                padding: '1.5rem',
                marginBottom: '1.5rem',
                boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                border: '1px solid #E5E7EB'
            }}>
                <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Plus size={20} style={{ color: '#3B82F6' }} />
                    添加新环境
                </h3>
                <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                    <input
                        placeholder="环境名称 (如: test, prod)"
                        value={newEnvName}
                        onChange={e => setNewEnvName(e.target.value)}
                        style={{
                            flex: '1',
                            minWidth: '150px',
                            padding: '0.75rem',
                            border: '2px solid #E5E7EB',
                            borderRadius: '0.5rem',
                            outline: 'none'
                        }}
                    />
                    <input
                        placeholder="Base URL (如: https://api.example.com)"
                        value={newEnvUrl}
                        onChange={e => setNewEnvUrl(e.target.value)}
                        style={{
                            flex: '2',
                            minWidth: '250px',
                            padding: '0.75rem',
                            border: '2px solid #E5E7EB',
                            borderRadius: '0.5rem',
                            outline: 'none'
                        }}
                    />
                    <button
                        onClick={handleSaveEnv}
                        style={{
                            padding: '0.75rem 1.5rem',
                            background: '#3B82F6',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.5rem',
                            cursor: 'pointer',
                            fontWeight: '600',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        <Plus size={18} />
                        添加
                    </button>
                </div>
                <p style={{ fontSize: '0.75rem', color: '#6B7280', margin: 0 }}>
                    第一个添加的环境将自动设为默认环境
                </p>
            </div>

            {/* 环境列表 */}
            {environments.length === 0 ? (
                <div style={{
                    textAlign: 'center',
                    padding: '3rem',
                    background: 'white',
                    borderRadius: '0.75rem',
                    border: '2px dashed #E5E7EB'
                }}>
                    <Globe size={48} style={{ margin: '0 auto 1rem', opacity: 0.3, color: '#9CA3AF' }} />
                    <p style={{ color: '#6B7280' }}>暂无环境配置,请添加第一个环境</p>
                </div>
            ) : (
                <div style={{
                    background: 'white',
                    borderRadius: '0.75rem',
                    overflow: 'hidden',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                    border: '1px solid #E5E7EB'
                }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead style={{ background: '#F9FAFB' }}>
                            <tr>
                                <th style={{ textAlign: 'left', padding: '1rem', fontSize: '0.875rem', fontWeight: '600', color: '#6B7280' }}>状态</th>
                                <th style={{ textAlign: 'left', padding: '1rem', fontSize: '0.875rem', fontWeight: '600', color: '#6B7280' }}>环境名称</th>
                                <th style={{ textAlign: 'left', padding: '1rem', fontSize: '0.875rem', fontWeight: '600', color: '#6B7280' }}>Base URL</th>
                                <th style={{ width: '80px', padding: '1rem' }}></th>
                            </tr>
                        </thead>
                        <tbody>
                            {environments.map((env, index) => (
                                <tr key={env.id} style={{ borderTop: index > 0 ? '1px solid #F3F4F6' : 'none' }}>
                                    <td style={{ padding: '1rem' }}>
                                        {env.is_default ? (
                                            <span style={{
                                                padding: '0.25rem 0.75rem',
                                                background: '#D1FAE5',
                                                color: '#065F46',
                                                borderRadius: '0.375rem',
                                                fontSize: '0.75rem',
                                                fontWeight: '600'
                                            }}>
                                                ✓ 默认
                                            </span>
                                        ) : (
                                            <span style={{ color: '#9CA3AF', fontSize: '0.875rem' }}>-</span>
                                        )}
                                    </td>
                                    <td style={{ padding: '1rem', fontWeight: '600', color: '#111827' }}>{env.env_name}</td>
                                    <td style={{ padding: '1rem', color: '#6B7280', fontSize: '0.875rem', fontFamily: 'monospace' }}>{env.base_url}</td>
                                    <td style={{ padding: '1rem', textAlign: 'right' }}>
                                        <button
                                            onClick={() => handleDeleteEnv(env.env_name)}
                                            style={{
                                                padding: '0.5rem',
                                                background: '#FEE2E2',
                                                color: '#DC2626',
                                                border: 'none',
                                                borderRadius: '0.375rem',
                                                cursor: 'pointer',
                                                display: 'inline-flex',
                                                alignItems: 'center'
                                            }}
                                            title="删除环境"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </>
    )
}
