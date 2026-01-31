'use client'

import { useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { Sparkles, TestTube, Clock, ClipboardList } from 'lucide-react'
import AIGenerationTab from './components/AIGenerationTab'
import TestScenariosTab from './components/TestScenariosTab'
import ScheduledTasksTab from './components/ScheduledTasksTab'
import ApiTestPlanTab from '../apis/components/ApiTestPlanTab'

export default function TestingCenterPage() {
    const searchParams = useSearchParams()
    const initialTab = searchParams?.get('tab') || 'ai'
    const [activeTab, setActiveTab] = useState(initialTab)

    const tabs = [
        { id: 'ai', name: 'AI生成', icon: Sparkles },
        { id: 'scenarios', name: '测试场景', icon: TestTube },
        { id: 'plan', name: '接口测试计划', icon: ClipboardList },
        { id: 'scheduler', name: '定时任务', icon: Clock }
    ]

    return (
        <div style={{ padding: '2rem', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', minHeight: '100vh' }}>
            {/* 页面标题 */}
            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem', fontWeight: '700', color: 'white', marginBottom: '0.5rem' }}>
                    🧪 测试中心
                </h1>
                <p style={{ color: 'rgba(255,255,255,0.8)' }}>
                    AI智能生成、测试场景管理和定时任务调度
                </p>
            </div>

            {/* Tab导航 */}
            <div style={{
                background: 'rgba(255,255,255,0.95)',
                borderRadius: '1rem 1rem 0 0',
                padding: '0',
                boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)'
            }}>
                <div style={{ display: 'flex', borderBottom: '2px solid #E5E7EB' }}>
                    {tabs.map((tab) => {
                        const Icon = tab.icon
                        const isActive = activeTab === tab.id
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                style={{
                                    padding: '1rem 2rem',
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

                {/* Tab内容 */}
                <div style={{ padding: '2rem', background: 'white', borderRadius: '0 0 1rem 1rem', minHeight: '60vh' }}>
                    {activeTab === 'ai' && <AIGenerationTab />}
                    {activeTab === 'scenarios' && <TestScenariosTab />}
                    {activeTab === 'plan' && <ApiTestPlanTab />}
                    {activeTab === 'scheduler' && <ScheduledTasksTab />}
                </div>
            </div>
        </div>
    )
}
