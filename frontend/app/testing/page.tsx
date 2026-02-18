'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { useSearchParams } from 'next/navigation'
import { Sparkles, TestTube, Target, Clock, ClipboardList } from 'lucide-react'
import AIGenerationTab from './components/AIGenerationTab'
import TestScenariosTab from './components/TestScenariosTab'
import SingleApiTestTab from './components/SingleApiTestTab'
import ScheduledTasksTab from './components/ScheduledTasksTab'
import ApiTestPlanTab from '../apis/components/ApiTestPlanTab'
import { useProject } from '../contexts/ProjectContext'

const STORAGE_KEY_PREFIX = 'single-api-results-'

export type SingleApiCaseItem = { id: string; name: string; data: any; createdAt: number }

function loadSingleApiResultsFromStorage(projectId: string): SingleApiCaseItem[] {
    if (typeof window === 'undefined') return []
    try {
        const raw = localStorage.getItem(STORAGE_KEY_PREFIX + projectId)
        if (!raw) return []
        const parsed = JSON.parse(raw)
        return Array.isArray(parsed) ? parsed : []
    } catch {
        return []
    }
}

function saveSingleApiResultsToStorage(projectId: string, items: SingleApiCaseItem[]) {
    if (typeof window === 'undefined') return
    try {
        localStorage.setItem(STORAGE_KEY_PREFIX + projectId, JSON.stringify(items))
    } catch (e) {
        console.warn('接口用例保存到本地失败（可能超出容量）:', e)
    }
}

/** 从流水线结果中提取展示名，单接口如「登录接口测试用例」，多接口如「登录、注册、忘记密码 接口测试用例」 */
export function getSingleApiDisplayName(data: any): string {
    if (!data?.phase2_plan?.endpoints?.length) return '未命名接口测试用例'
    const endpoints = data.phase2_plan.endpoints
    const parts = endpoints.slice(0, 5).map((ep: any) => {
        const summary = (ep?.summary || ep?.name || '').toString().trim()
        const path = (ep?.path || '').toString()
        const pathPart = path ? (path.replace(/^\//, '').split('/').filter(Boolean).pop() || '') : ''
        const raw = summary || pathPart || '接口'
        return raw.replace(/接口$/, '') || raw
    })
    const name = [...new Set(parts)].filter(Boolean).join('、') || '接口'
    return name + (name.endsWith('接口') ? '测试用例' : '接口测试用例')
}

export default function TestingCenterPage() {
    const searchParams = useSearchParams()
    const { currentProject } = useProject()
    const initialTab = searchParams?.get('tab') || 'ai'
    const [activeTab, setActiveTab] = useState(initialTab)
    // 接口用例列表：按项目持久化到 localStorage，不覆盖、可删除
    const [singleApiResults, setSingleApiResults] = useState<SingleApiCaseItem[]>([])
    const [selectedSingleApiId, setSelectedSingleApiId] = useState<string | null>(null)

    // 记录当前是否已加载完当前项目的数据，防止初始空状态覆盖 localStorage
    const [isLoaded, setIsLoaded] = useState(false)
    const [lastProject, setLastProject] = useState<string | null>(null)

    // 按项目从 localStorage 恢复
    useEffect(() => {
        setIsLoaded(false)
        const saved = loadSingleApiResultsFromStorage(currentProject)
        setSingleApiResults(saved)
        setSelectedSingleApiId(saved.length > 0 ? saved[0].id : null)
        setLastProject(currentProject)
        setIsLoaded(true)
    }, [currentProject])

    // 列表变化后写回 localStorage
    useEffect(() => {
        // 只有当数据已加载，且确实属于当前项目时，才允许写入
        if (isLoaded && lastProject === currentProject) {
            saveSingleApiResultsToStorage(currentProject, singleApiResults)
        }
    }, [currentProject, singleApiResults, isLoaded, lastProject])

    // 生成新的单接口测试时仅追加到列表，不覆盖、不删除之前的记录（会通过 useEffect 持久化）
    const addSingleApiResult = useCallback((data: any) => {
        const now = Date.now()
        const name = getSingleApiDisplayName(data)
        const id = `single-${now}-${Math.random().toString(36).slice(2, 9)}`
        const item: SingleApiCaseItem = { id, name, data, createdAt: now }
        // 新生成的排在最上面
        setSingleApiResults((prev) => [item, ...prev])
        setSelectedSingleApiId(id)
        setActiveTab('single-api')
    }, [])

    const updateSingleApiResult = useCallback((id: string, data: any) => {
        setSingleApiResults((prev) =>
            prev.map((it) => (it.id === id ? { ...it, data, name: getSingleApiDisplayName(data) } : it))
        )
    }, [])

    const removeSingleApiResult = useCallback((id: string) => {
        setSingleApiResults((prev) => prev.filter((it) => it.id !== id))
        setSelectedSingleApiId((cur) => (cur === id ? null : cur))
    }, [])

    // 有列表且当前未选或选中项已被删时，自动选中第一项
    useEffect(() => {
        if (singleApiResults.length === 0) return
        const hasSelected = selectedSingleApiId && singleApiResults.some((it) => it.id === selectedSingleApiId)
        if (!hasSelected) setSelectedSingleApiId(singleApiResults[0].id)
    }, [singleApiResults, selectedSingleApiId])

    const tabs = [
        { id: 'ai', name: 'AI生成', icon: Sparkles },
        { id: 'scenarios', name: '测试场景', icon: TestTube },
        { id: 'single-api', name: '接口用例', icon: Target },
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
                    {activeTab === 'ai' && (
                        <AIGenerationTab onSingleApiGenerated={addSingleApiResult} />
                    )}
                    {activeTab === 'scenarios' && <TestScenariosTab />}
                    {activeTab === 'single-api' && (
                        <SingleApiTestTab
                            items={singleApiResults}
                            selectedId={selectedSingleApiId}
                            onSelect={setSelectedSingleApiId}
                            onResultChange={updateSingleApiResult}
                            onDelete={removeSingleApiResult}
                        />
                    )}
                    {activeTab === 'plan' && <ApiTestPlanTab />}
                    {activeTab === 'scheduler' && <ScheduledTasksTab />}
                </div>
            </div>
        </div>
    )
}
