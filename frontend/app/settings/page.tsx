'use client'

import { useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { FolderKanban, Globe } from 'lucide-react'
import ProjectManagementTab from './components/ProjectManagementTab'
import EnvironmentManagementTab from './components/EnvironmentManagementTab'

export default function SettingsPage() {
    const searchParams = useSearchParams()
    const initialTab = searchParams?.get('tab') || 'projects'
    const [activeTab, setActiveTab] = useState(initialTab)

    const tabs = [
        { id: 'projects', name: '项目管理', icon: FolderKanban },
        { id: 'environments', name: '环境配置', icon: Globe }
    ]

    return (
        <div style={{ padding: '1rem 0' }}>
            {/* 页面标题 */}
            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem', fontWeight: '700', color: '#111827', marginBottom: '0.5rem' }}>
                    ⚙️ 项目设置
                </h1>
                <p style={{ color: '#6B7280' }}>
                    管理项目和环境配置
                </p>
            </div>

            {/* Tab导航 */}
            <div style={{ marginBottom: '1.5rem', borderBottom: '2px solid #E5E7EB' }}>
                <div style={{ display: 'flex', gap: '2rem' }}>
                    {tabs.map((tab) => {
                        const Icon = tab.icon
                        const isActive = activeTab === tab.id
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                style={{
                                    padding: '0.75rem 0',
                                    border: 'none',
                                    background: 'transparent',
                                    cursor: 'pointer',
                                    fontSize: '0.875rem',
                                    fontWeight: '600',
                                    color: isActive ? '#667eea' : '#6B7280',
                                    borderBottom: isActive ? '2px solid #667eea' : '2px solid transparent',
                                    marginBottom: '-2px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    transition: 'all 0.2s'
                                }}
                            >
                                <Icon size={18} />
                                {tab.name}
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* Tab内容 */}
            {activeTab === 'projects' ? (
                <ProjectManagementTab />
            ) : (
                <EnvironmentManagementTab />
            )}
        </div>
    )
}
