'use client'

import React, { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useProject } from '../../contexts/ProjectContext'
import { ClipboardList, Play, CheckCircle, XCircle, AlertCircle, Loader2, FileText, Wand2, Trash2, RefreshCw, X } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_AI_API_URL || 'http://localhost:8000'

// --- Helpers ---
const TabButton = ({ active, label, onClick }: { active: boolean, label: string, onClick: () => void }) => (
    <button onClick={onClick} style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', border: 'none', background: 'transparent', borderBottom: active ? '2px solid #667eea' : '2px solid transparent', color: active ? '#4c51bf' : '#718096', fontWeight: active ? '600' : '400', cursor: 'pointer' }}>{label}</button>
)

const KeyValueTable = ({ data, emptyText = "暂无数据" }: { data: any, emptyText?: string }) => {
    if (!data || (typeof data === 'object' && Object.keys(data).length === 0)) return <div style={{ fontSize: '0.8rem', color: '#9CA3AF', padding: '0.5rem' }}>{emptyText}</div>
    if (typeof data !== 'object') return <div style={{ fontSize: '0.8rem', padding: '0.5rem', fontFamily: 'monospace' }}>{String(data)}</div>
    return (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
            <tbody>
                {Object.entries(data).map(([k, v]: [string, any]) => (
                    <tr key={k} style={{ borderBottom: '1px solid #F3F4F6' }}>
                        <td style={{ padding: '0.35rem 0.5rem', background: '#F9FAFB', width: '30%', color: '#4B5563', fontWeight: '500' }}>{k}</td>
                        <td style={{ padding: '0.35rem 0.5rem', color: '#1F2937', fontFamily: 'monospace' }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    )
}

// --- Interfaces ---
interface EnvItem {
    id: number
    env_name: string
    base_url: string
    is_default?: number
}

interface ApiTestCase {
    id: number
    project_id: string
    api_id?: number
    case_name?: string
    name?: string
    case_type: string
    method: string
    path: string
    source?: string
    request_template: any
    expected_template: any
    created_at?: string
}

interface PlanEndpoint {
    id: number
    path: string
    method: string
    module?: string
    base_url?: string
    cases: any[]
}

interface TestPlan {
    endpoint_count?: number
    endpoints: PlanEndpoint[]
}

export default function ApiTestPlanTab() {
    const { currentProject } = useProject()
    const [environments, setEnvironments] = useState<EnvItem[]>([])
    const [selectedEnvId, setSelectedEnvId] = useState<number | null>(null)
    const [planLoading, setPlanLoading] = useState(false)
    const [plan, setPlan] = useState<TestPlan | null>(null)
    const [executeLoading, setExecuteLoading] = useState(false)
    const [executeResult, setExecuteResult] = useState<any>(null)
    const [healAnalyzeLoading, setHealAnalyzeLoading] = useState(false)
    const [healAnalyzeResult, setHealAnalyzeResult] = useState<any>(null)
    const [caseTypes, setCaseTypes] = useState('positive,boundary,robustness,security')
    const [selectedApiIds, setSelectedApiIds] = useState<Set<number>>(new Set())
    const [aiGenerateProgress, setAiGenerateProgress] = useState<{ current: number; total: number } | null>(null)
    const [selectedCaseDetail, setSelectedCaseDetail] = useState<{ ep: any; c: any } | null>(null)
    const [caseDetailMainTab, setCaseDetailMainTab] = useState<'request' | 'response' | 'expected'>('request')
    const [caseDetailSubTab, setCaseDetailSubTab] = useState<'params' | 'body' | 'headers' | 'cookies'>('body')
    const [singleRunLoading, setSingleRunLoading] = useState<string | null>(null)
    const [singleRunResult, setSingleRunResult] = useState<Record<string, { status: string; status_code?: number; error?: string; response?: unknown }>>({})
    const [selectedResultDetail, setSelectedResultDetail] = useState<any>(null)
    const [resultDetailTab, setResultDetailTab] = useState<'request' | 'response'>('request')
    const [resultDetailSubTab, setResultDetailSubTab] = useState<'params' | 'body' | 'headers'>('body')
    const testCaseListRef = useRef<HTMLDivElement>(null)
    const [aiGenerateDoneHint, setAiGenerateDoneHint] = useState<string | null>(null)
    const [savedCases, setSavedCases] = useState<ApiTestCase[]>([])
    const [savedCasesLoading, setSavedCasesLoading] = useState(false)
    const [savedCasesError, setSavedCasesError] = useState<string | null>(null)
    const [savedCaseRunLoading, setSavedCaseRunLoading] = useState<number | null>(null)
    const [savedCaseRunResult, setSavedCaseRunResult] = useState<Record<number, { status: string; status_code?: number; error?: string; response?: unknown; execution_id?: number }>>({})
    const [healApplyLoading, setHealApplyLoading] = useState<Record<number, boolean>>({})

    useEffect(() => {
        const load = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/v1/projects/${encodeURIComponent(currentProject)}/environments`)
                if (!res.ok) return
                const data = await res.json()
                const list = Array.isArray(data) ? data : []
                setEnvironments(list)
                const defaultEnv = list.find((e: EnvItem) => e.is_default === 1)
                const first = list[0]
                setSelectedEnvId(defaultEnv?.id ?? first?.id ?? null)
            } catch {
                setEnvironments([])
                setSelectedEnvId(null)
            }
        }
        load()
    }, [currentProject])

    const selectedEnv = environments.find(e => e.id === selectedEnvId)
    const baseUrl = selectedEnv?.base_url ?? ''

    const loadSavedCases = async () => {
        setSavedCasesLoading(true)
        setSavedCasesError(null)
        try {
            const res = await fetch(`${API_BASE}/api/v1/api-test-cases?project_id=${encodeURIComponent(currentProject)}`)
            if (!res.ok) {
                const data = await res.json().catch(() => ({}))
                throw new Error(data.detail || data.message || `HTTP ${res.status}`)
            }
            const data = await res.json()
            setSavedCases(Array.isArray(data) ? data : [])
        } catch (e: any) {
            setSavedCasesError(e.message || '加载已保存用例失败')
        } finally {
            setSavedCasesLoading(false)
        }
    }

    useEffect(() => {
        loadSavedCases()
    }, [currentProject])

    const fetchPlan = async () => {
        setPlanLoading(true)
        setPlan(null)
        setExecuteResult(null)
        setAiGenerateProgress(null)
        setAiGenerateDoneHint(null)
        try {
            const types = caseTypes ? `&case_types=${encodeURIComponent(caseTypes)}` : ''
            const res = await fetch(`${API_BASE}/api/v1/api-test-plan?project_id=${encodeURIComponent(currentProject)}${types}`)
            if (!res.ok) throw new Error('获取计划失败')
            const data = await res.json()
            setPlan(data)
            const ids = new Set<number>((data?.endpoints ?? []).map((ep: any) => ep.id).filter(Boolean))
            setSelectedApiIds(ids)
        } catch (e: any) {
            alert(e.message || '获取计划失败')
        } finally {
            setPlanLoading(false)
        }
    }

    const runAiGenerateForSelected = async () => {
        if (!plan?.endpoints?.length) return
        const ids = Array.from(selectedApiIds).filter(id => plan.endpoints.some((ep: any) => ep.id === id))
        if (ids.length === 0) {
            alert('请至少勾选一个接口')
            return
        }
        setAiGenerateProgress({ current: 0, total: ids.length })
        const types = caseTypes ? caseTypes.split(',').map((t: string) => t.trim()).filter(Boolean) : ['positive', 'boundary', 'robustness', 'security']
        const updatedEndpoints = [...(plan.endpoints || [])]
        for (let i = 0; i < ids.length; i++) {
            setAiGenerateProgress({ current: i + 1, total: ids.length })
            try {
                const res = await fetch(`${API_BASE}/api/v1/api-test-plan/generate-ai-case`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: currentProject,
                        api_id: ids[i],
                        case_types: types.join(','),
                    }),
                })
                const data = await res.json()
                if (data.detail) throw new Error(data.detail)
                const apiId = data.api_id != null ? Number(data.api_id) : null
                const epIdx = apiId != null ? updatedEndpoints.findIndex((ep: any) => Number(ep.id) === apiId) : -1
                if (epIdx >= 0 && Array.isArray(data.cases) && data.cases.length > 0) {
                    updatedEndpoints[epIdx] = { ...updatedEndpoints[epIdx], cases: data.cases }
                }
            } catch (e: any) {
                console.warn(`AI 生成失败 api_id=${ids[i]}:`, e.message)
            }
        }
        setPlan({ ...plan, endpoints: updatedEndpoints })
        setAiGenerateProgress(null)
        const totalCases = updatedEndpoints.reduce((n: number, ep: any) => n + (ep.cases?.length || 0), 0)
        setAiGenerateDoneHint(`已生成 AI 用例，共 ${totalCases} 条，请查看下方「测试用例列表」`)
        setTimeout(() => setAiGenerateDoneHint(null), 5000)
        setTimeout(() => testCaseListRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200)
    }

    const runExecute = async () => {
        if (!baseUrl.trim()) {
            alert('请先选择当前项目已配置的环境（在项目设置中可添加环境）')
            return
        }
        if (plan?.endpoints) {
            const types = caseTypes ? caseTypes.split(',').map((t: string) => t.trim().toLowerCase()).filter(Boolean) : null
            let totalCases = 0
            plan.endpoints.forEach((ep: any) => {
                const cases = ep.cases || []
                if (types && types.length > 0) {
                    const matchedCases = cases.filter((c: any) => types.includes((c.case_type || 'positive').toLowerCase()))
                    totalCases += matchedCases.length
                } else {
                    totalCases += cases.length
                }
            })
            if (totalCases === 0) {
                if (types && types.length > 0) {
                    alert(`当前测试计划中没有匹配用例类型 [${types.join(', ')}] 的用例`)
                } else {
                    alert('请先点击「AI生成用例」按钮生成测试用例')
                }
                return
            }
        }
        setExecuteLoading(true)
        setExecuteResult(null)
        setHealAnalyzeResult(null)
        try {
            const types = caseTypes ? caseTypes.split(',').map((t: string) => t.trim()).filter(Boolean) : null
            const res = await fetch(`${API_BASE}/api/v1/api-test-plan/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: currentProject,
                    base_url: baseUrl.trim(),
                    case_types: types ? types.join(',') : undefined,
                    environment: 'test',
                    plan: plan ?? undefined,
                }),
            })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail || data.message || `HTTP ${res.status}`)
            setExecuteResult(data)
        } catch (e: any) {
            alert(e.message || '执行失败')
        } finally {
            setExecuteLoading(false)
        }
    }

    const runHealAnalyze = async (executionId: number) => {
        setHealAnalyzeLoading(true)
        setHealAnalyzeResult(null)
        try {
            const res = await fetch(`${API_BASE}/api/v1/heal/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ execution_id: executionId }),
            })
            const data = await res.json()
            setHealAnalyzeResult(data)
        } catch (e: any) {
            alert(e.message || '分析失败')
        } finally {
            setHealAnalyzeLoading(false)
        }
    }

    const runHealApiCase = async (apiTestCaseId: number, executionId: number) => {
        setHealApplyLoading(prev => ({ ...prev, [apiTestCaseId]: true }))
        try {
            const res = await fetch(`${API_BASE}/api/v1/heal/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_test_case_id: apiTestCaseId, execution_id: executionId }),
            })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail || '修复失败')
            if (data.status === 'healed') {
                alert(`✅ 修复成功！\n\n接口用例已更新，请重新执行验证。`)
                loadSavedCases()
            } else {
                alert(`⚠️ 无法自动修复\n\n原因: ${data.message}`)
            }
        } catch (e: any) {
            alert(`请求失败: ${e.message}`)
        } finally {
            setHealApplyLoading(prev => ({ ...prev, [apiTestCaseId]: false }))
        }
    }

    const summary = executeResult?.summary
    const hasFailed = summary && summary.failed > 0

    return (
        <div style={{ background: 'white', borderRadius: '0.75rem', padding: '1.5rem', border: '1px solid #E5E7EB' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ClipboardList size={20} style={{ color: '#667eea' }} />
                接口测试计划
            </h3>
            <p style={{ fontSize: '0.875rem', color: '#6B7280', marginBottom: '1.5rem' }}>
                基于当前项目已导入的 API，自动生成测试计划并执行；执行后可对失败用例做「失败分析」。
            </p>

            {/* 当前项目 */}
            <div style={{ marginBottom: '1rem' }}>
                <span style={{ fontSize: '0.875rem', color: '#6B7280' }}>当前项目：</span>
                <strong style={{ marginLeft: '0.5rem' }}>{currentProject}</strong>
            </div>

            {/* 用例类型 */}
            <div style={{ marginBottom: '1rem' }}>
                <label style={{ fontSize: '0.875rem', fontWeight: '500', display: 'block', marginBottom: '0.25rem' }}>用例类型（逗号分隔）</label>
                <input
                    type="text"
                    value={caseTypes}
                    onChange={(e) => setCaseTypes(e.target.value)}
                    placeholder="positive,boundary,robustness,security"
                    style={{ width: '100%', maxWidth: '400px', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.5rem', fontSize: '0.875rem' }}
                />
            </div>

            {/* 生成计划 */}
            <div style={{ marginBottom: '1.5rem' }}>
                <button
                    onClick={fetchPlan}
                    disabled={planLoading}
                    style={{
                        padding: '0.5rem 1rem',
                        background: planLoading ? '#9CA3AF' : '#667eea',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.5rem',
                        fontSize: '0.875rem',
                        fontWeight: '600',
                        cursor: planLoading ? 'not-allowed' : 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                    }}
                >
                    {planLoading ? <Loader2 size={16} /> : <ClipboardList size={16} />}
                    生成测试计划
                </button>
                {plan && (
                    <span style={{ marginLeft: '1rem', fontSize: '0.875rem', color: '#6B7280' }}>
                        共 {plan.endpoint_count ?? 0} 个接口，{plan.endpoints?.reduce((n: number, ep: any) => n + (ep.cases?.length || 0), 0) ?? 0} 条用例
                    </span>
                )}
            </div>

            {/* 选择接口 + 为选中接口生成 AI 用例（有进度） */}
            {(plan?.endpoints?.length ?? 0) > 0 && (
                <div style={{ marginBottom: '1.5rem', padding: '1rem', background: '#F9FAFB', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>选择要生成 AI 用例的接口</div>
                    <p style={{ fontSize: '0.8rem', color: '#6B7280', marginBottom: '0.75rem' }}>勾选接口后点击下方按钮，大模型会为选中接口生成真实测试用例。</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
                        <button
                            type="button"
                            onClick={() => setSelectedApiIds(new Set((plan?.endpoints ?? []).map((ep: any) => ep.id).filter(Boolean)))}
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', border: '1px solid #E5E7EB', borderRadius: '0.25rem', background: 'white', cursor: 'pointer' }}
                        >
                            全选
                        </button>
                        <button
                            type="button"
                            onClick={() => setSelectedApiIds(new Set())}
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', border: '1px solid #E5E7EB', borderRadius: '0.25rem', background: 'white', cursor: 'pointer' }}
                        >
                            取消全选
                        </button>
                        <span style={{ fontSize: '0.8rem', color: '#6B7280' }}>已选 {selectedApiIds.size} 个接口</span>
                    </div>
                    <div style={{ maxHeight: '180px', overflowY: 'auto', border: '1px solid #E5E7EB', borderRadius: '0.375rem', padding: '0.5rem', background: 'white', marginBottom: '0.75rem' }}>
                        {(plan?.endpoints ?? []).map((ep: any) => (
                            <label key={ep.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.25rem 0', cursor: 'pointer', fontSize: '0.8rem' }}>
                                <input
                                    type="checkbox"
                                    checked={selectedApiIds.has(ep.id)}
                                    onChange={(e) => {
                                        if (e.target.checked) setSelectedApiIds(prev => new Set([...prev, ep.id]))
                                        else setSelectedApiIds(prev => { const n = new Set(prev); n.delete(ep.id); return n })
                                    }}
                                />
                                <span style={{ fontWeight: '500' }}>{ep.method}</span>
                                <span style={{ color: '#6B7280', fontFamily: 'monospace' }}>{ep.path}</span>
                            </label>
                        ))}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                        <button
                            type="button"
                            onClick={runAiGenerateForSelected}
                            disabled={!!aiGenerateProgress || selectedApiIds.size === 0}
                            style={{
                                padding: '0.5rem 1rem',
                                background: aiGenerateProgress || selectedApiIds.size === 0 ? '#9CA3AF' : '#667eea',
                                color: 'white',
                                border: 'none',
                                borderRadius: '0.5rem',
                                fontSize: '0.875rem',
                                fontWeight: '600',
                                cursor: aiGenerateProgress || selectedApiIds.size === 0 ? 'not-allowed' : 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                            }}
                        >
                            {aiGenerateProgress ? <Loader2 size={16} /> : null}
                            {aiGenerateProgress ? `正在生成 ${aiGenerateProgress.current}/${aiGenerateProgress.total}…` : '为选中接口生成 AI 用例'}
                        </button>
                    </div>
                </div>
            )}

            {/* 执行环境 */}
            <div style={{ marginBottom: '1rem' }}>
                <label style={{ fontSize: '0.875rem', fontWeight: '500', display: 'block', marginBottom: '0.25rem' }}>执行环境</label>
                <select
                    value={selectedEnvId ?? ''}
                    onChange={(e) => setSelectedEnvId(e.target.value ? Number(e.target.value) : null)}
                    style={{ width: '100%', maxWidth: '480px', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.5rem', fontSize: '0.875rem' }}
                >
                    <option value="">请选择环境</option>
                    {environments.map((e) => (
                        <option key={e.id} value={e.id}>{e.env_name} — {e.base_url}</option>
                    ))}
                </select>
            </div>
            <div style={{ marginBottom: '1.5rem' }}>
                <button
                    onClick={runExecute}
                    disabled={executeLoading || !baseUrl.trim()}
                    style={{
                        padding: '0.5rem 1rem',
                        background: executeLoading || !baseUrl.trim() ? '#9CA3AF' : '#10B981',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.5rem',
                        fontSize: '0.875rem',
                        fontWeight: '600',
                        cursor: executeLoading || !baseUrl.trim() ? 'not-allowed' : 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                    }}
                >
                    {executeLoading ? <Loader2 size={16} /> : <Play size={16} />}
                    执行计划
                </button>
            </div>

            {/* 执行结果 */}
            {executeResult && (
                <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#F9FAFB', borderRadius: '0.75rem', border: '1px solid #E5E7EB' }}>
                    <h4 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {executeResult.status === 'success' ? <CheckCircle size={18} style={{ color: '#10B981' }} /> : <XCircle size={18} style={{ color: '#EF4444' }} />}
                        执行结果 #{executeResult.id}
                    </h4>
                    {summary && (
                        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginBottom: '0.75rem', fontSize: '0.875rem' }}>
                            <span>总数: <strong>{summary.total}</strong></span>
                            <span style={{ color: '#10B981' }}>通过: <strong>{summary.passed}</strong></span>
                            <span style={{ color: '#EF4444' }}>失败: <strong>{summary.failed}</strong></span>
                        </div>
                    )}
                    <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                        <Link href={`/reports?execution_id=${executeResult.id}`} style={{ padding: '0.4rem 0.8rem', background: '#667eea', color: 'white', borderRadius: '0.375rem', fontSize: '0.8rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                            <FileText size={14} /> 查看测试报告
                        </Link>
                        {hasFailed && (
                            <button onClick={() => runHealAnalyze(executeResult.id)} disabled={healAnalyzeLoading} style={{ padding: '0.4rem 0.8rem', background: '#F59E0B', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.8rem', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                                {healAnalyzeLoading ? <Loader2 size={14} /> : <AlertCircle size={14} />} 失败分析
                            </button>
                        )}
                    </div>
                    {executeResult.results?.length > 0 && (
                        <div style={{ marginTop: '1rem' }}>
                            <h5 style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '0.5rem' }}>执行明细</h5>
                            <div style={{ overflowX: 'auto', maxHeight: '320px', overflowY: 'auto', border: '1px solid #E5E7EB', borderRadius: '0.5rem' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                    <thead style={{ background: '#F3F4F6', position: 'sticky', top: 0 }}>
                                        <tr>
                                            <th style={{ padding: '0.5rem', textAlign: 'left' }}>步骤</th>
                                            <th style={{ padding: '0.5rem', textAlign: 'left' }}>接口</th>
                                            <th style={{ padding: '0.5rem', textAlign: 'center' }}>结果</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {executeResult.results.map((r: any, i: number) => (
                                            <tr key={i} style={{ borderTop: '1px solid #E5E7EB', background: r.success ? 'transparent' : '#FEF2F2', cursor: 'pointer' }} onClick={() => setSelectedResultDetail(r)}>
                                                <td style={{ padding: '0.5rem' }}>{r.step_order ?? i + 1}</td>
                                                <td style={{ padding: '0.5rem' }}><span style={{ fontWeight: '500' }}>{r.method}</span> {r.url}</td>
                                                <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                                                    {r.success ? <span style={{ color: '#10B981' }}>通过</span> : <span style={{ color: '#EF4444' }}>失败</span>}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            {selectedResultDetail && (() => {
                                const rd = selectedResultDetail
                                const reqData = (rd.request_data || {}) as Record<string, unknown>
                                const urlParams = (rd.url_params || {}) as Record<string, unknown>
                                const reqHeaders = (rd.request_headers || {}) as Record<string, unknown>
                                const kvTable = (obj: Record<string, unknown>) => (
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                        <tbody>
                                            {Object.entries(obj).map(([k, v]) => (
                                                <tr key={k} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                                    <td style={{ padding: '0.4rem 0.6rem', color: '#6B7280', width: '30%' }}>{k}</td>
                                                    <td style={{ padding: '0.4rem 0.6rem', wordBreak: 'break-all' }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )
                                return (
                                    <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'white', border: '1px solid #E5E7EB', borderRadius: '0.5rem' }} onClick={(e) => e.stopPropagation()}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                            <strong>执行步骤详情</strong>
                                            <button onClick={() => setSelectedResultDetail(null)} style={{ fontSize: '0.75rem', cursor: 'pointer' }}>关闭</button>
                                        </div>
                                        <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #E5E7EB', marginBottom: '0.5rem' }}>
                                            <button onClick={() => setResultDetailTab('request')} style={{ padding: '0.35rem', border: 'none', borderBottom: resultDetailTab === 'request' ? '2px solid #667eea' : 'none', background: 'transparent', cursor: 'pointer' }}>请求</button>
                                            <button onClick={() => setResultDetailTab('response')} style={{ padding: '0.35rem', border: 'none', borderBottom: resultDetailTab === 'response' ? '2px solid #667eea' : 'none', background: 'transparent', cursor: 'pointer' }}>响应</button>
                                        </div>
                                        {resultDetailTab === 'request' && (
                                            <div style={{ maxHeight: '200px', overflow: 'auto' }}>
                                                {Object.keys(reqData).length > 0 && <pre style={{ fontSize: '0.75rem' }}>{JSON.stringify(reqData, null, 2)}</pre>}
                                                {kvTable(reqHeaders)}
                                            </div>
                                        )}
                                        {resultDetailTab === 'response' && (
                                            <div>
                                                <div style={{ marginBottom: '0.5rem' }}>状态码: <strong>{rd.status_code}</strong></div>
                                                {rd.response && <pre style={{ fontSize: '0.75rem', background: '#F9FAFB', padding: '0.5rem' }}>{typeof rd.response === 'string' ? rd.response : JSON.stringify(rd.response, null, 2)}</pre>}

                                                {/* Categorized Assertions (from bjb HEAD) */}
                                                <div style={{ marginTop: '0.75rem' }}>
                                                    <span style={{ color: '#6B7280', fontSize: '0.75rem' }}>断言结果</span>
                                                    <div style={{ marginTop: '0.25rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                                                        {rd.assertions.map((a: any, idx: number) => {
                                                            // 尝试解析 message 中的详细信息
                                                            let detailedAssertions: any[] = [];
                                                            let cleanMessage = a.message || '';

                                                            try {
                                                                if (a.message) {
                                                                    const startIdx = a.message.indexOf('[');
                                                                    const endIdx = a.message.lastIndexOf(']');

                                                                    if (startIdx >= 0 && endIdx > startIdx) {
                                                                        const listStr = a.message.substring(startIdx, endIdx + 1);

                                                                        // 简单的 Python repr 转 JSON
                                                                        const jsonStr = listStr
                                                                            .replace(/'/g, '"')
                                                                            .replace(/True/g, 'true')
                                                                            .replace(/False/g, 'false')
                                                                            .replace(/None/g, 'null');

                                                                        const parsed = JSON.parse(jsonStr);
                                                                        if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].field) {
                                                                            detailedAssertions = parsed;
                                                                            // 如果解析成功，从原始消息中移除列表部分，得到干净的提示语
                                                                            cleanMessage = (a.message.substring(0, startIdx) + a.message.substring(endIdx + 1)).trim();
                                                                            // 去除可能残留的冒号
                                                                            if (cleanMessage.endsWith(':')) {
                                                                                cleanMessage = cleanMessage.substring(0, cleanMessage.length - 1).trim();
                                                                            }
                                                                        }
                                                                    }
                                                                }
                                                            } catch (e) {
                                                                // 解析失败则保留原样，不做处理
                                                            }

                                                            // 如果有解析出的详细断言，则优先展示
                                                            if (detailedAssertions.length > 0) {
                                                                return (
                                                                    <div key={idx} style={{ padding: '0.5rem', borderRadius: '0.375rem', background: a.passed ? '#ECFDF3' : '#FEF2F2', border: `1px solid ${a.passed ? '#BBF7D0' : '#FECACA'}`, fontSize: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>

                                                                        {/* 标题行: 类型 + 状态 */}
                                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                                            <span style={{ fontWeight: 600 }}>
                                                                                {a.type === 'http' ? '响应码断言' : '业务断言'}
                                                                            </span>
                                                                            <span style={{ color: a.passed ? '#16A34A' : '#DC2626', fontWeight: 600 }}>{a.passed ? '通过' : '未通过'}</span>
                                                                        </div>

                                                                        {/* 消息文本 (移除列表后的) */}
                                                                        {cleanMessage && (
                                                                            <div style={{ color: '#4B5563', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                                                                                {cleanMessage}
                                                                            </div>
                                                                        )}

                                                                        {/* 详细字段列表 (一行一个) */}
                                                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', paddingTop: '0.25rem', borderTop: '1px solid rgba(0,0,0,0.05)' }}>
                                                                            {detailedAssertions.map((item: any, i: number) => (
                                                                                <div key={i} style={{ display: 'flex', alignItems: 'center', flexWrap: 'nowrap', gap: '0.5rem', padding: '0.25rem 0', fontFamily: 'monospace' }}>
                                                                                    <span style={{ minWidth: '1.2rem' }}>
                                                                                        {item.passed ? <span style={{ color: '#16A34A', fontWeight: 'bold' }}>✓</span> : <span style={{ color: '#DC2626', fontWeight: 'bold' }}>✕</span>}
                                                                                    </span>
                                                                                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                                                                                        <span style={{ fontWeight: 600, color: '#374151' }}>{item.field}:</span>
                                                                                        <span style={{ color: '#6B7280' }}>期望</span>
                                                                                        <span style={{ color: '#059669', background: 'rgba(255,255,255,0.6)', padding: '0 0.2rem', borderRadius: '0.2rem' }}>
                                                                                            {typeof item.expected === 'string' ? `"${item.expected}"` : JSON.stringify(item.expected)}
                                                                                        </span>
                                                                                        <span style={{ color: '#6B7280' }}>, 实际</span>
                                                                                        <span style={{ color: '#DC2626', background: 'rgba(255,255,255,0.6)', padding: '0 0.2rem', borderRadius: '0.2rem' }}>
                                                                                            {typeof item.actual === 'string' ? `"${item.actual}"` : JSON.stringify(item.actual)}
                                                                                        </span>
                                                                                    </div>
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    </div>
                                                                );
                                                            }

                                                            // 默认展示 (解析失败或无详细信息)
                                                            return (
                                                                <div key={idx} style={{ padding: '0.4rem', borderRadius: '0.375rem', background: a.passed ? '#ECFDF3' : '#FEF2F2', border: `1px solid ${a.passed ? '#BBF7D0' : '#FECACA'}`, fontSize: '0.75rem', display: 'flex', flexDirection: 'column' }}>
                                                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                                                        <span style={{ fontWeight: 500 }}>{a.type === 'http' ? '响应码断言' : '业务断言'}</span>
                                                                        <span style={{ color: a.passed ? '#16A34A' : '#DC2626' }}>{a.passed ? '通过' : '未通过'}</span>
                                                                    </div>
                                                                    {a.message && <div style={{ color: '#4B5563', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{a.message}</div>}
                                                                    {a.details && a.details.length > 0 && (
                                                                        <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1rem' }}>
                                                                            {a.details.map((d: any, di: number) => (
                                                                                <li key={di}>{d.field}: 期望 {String(d.expected)}, 实际 {String(d.actual)}</li>
                                                                            ))}
                                                                        </ul>
                                                                    )}
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )
                            })()}
                        </div>
                    )}
                </div>
            )}

            {/* Heal Analyze Results Display */}
            {healAnalyzeResult && (
                <div style={{ marginTop: '1rem', padding: '1rem', background: '#FEF3C7', border: '1px solid #FDE68A', borderRadius: '0.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                        <h5 style={{ margin: 0, fontSize: '0.9rem', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <AlertCircle size={16} /> 失败原因分析 & 修复建议
                        </h5>
                        <button onClick={() => setHealAnalyzeResult(null)} style={{ background: 'none', border: 'none', color: '#92400E', cursor: 'pointer' }}>
                            <X size={14} />
                        </button>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#92400E' }}>
                        {healAnalyzeResult.findings && healAnalyzeResult.findings.length > 0 ? (
                            <ul style={{ margin: '0.5rem 0', paddingLeft: '1.2rem' }}>
                                {healAnalyzeResult.findings.map((f: any, fi: number) => (
                                    <li key={fi} style={{ marginBottom: '0.5rem' }}>
                                        <strong>{f.type === 'schema_change' ? '接口变更' : '逻辑错误'}:</strong> {f.description}
                                        {f.suggestion && <div style={{ marginTop: '0.2rem', color: '#B45309', fontStyle: 'italic' }}>建议: {f.suggestion}</div>}
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p>未发现明显的结构性问题，可能是网络波动或临时环境问题。</p>
                        )}
                    </div>
                </div>
            )}

            {/* 已保存用例（用例库） */}
            <div style={{ marginTop: '1.5rem', border: '1px solid #E5E7EB', borderRadius: '0.75rem', overflow: 'hidden' }}>
                <div style={{ padding: '0.75rem 1rem', background: '#F9FAFB', borderBottom: '1px solid #E5E7EB', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: '600', margin: 0 }}>已保存用例（用例库）</h4>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.8rem', color: '#6B7280' }}>共 {savedCases.length} 条</span>
                        <button
                            type="button"
                            onClick={loadSavedCases}
                            disabled={savedCasesLoading}
                            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', borderRadius: '0.25rem', border: '1px solid #D1D5DB', background: savedCasesLoading ? '#E5E7EB' : '#FFFFFF', cursor: savedCasesLoading ? 'not-allowed' : 'pointer', color: '#374151', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                        >
                            <RefreshCw size={12} className={savedCasesLoading ? 'spin' : ''} />
                            {savedCasesLoading ? '刷新中' : '刷新'}
                        </button>
                    </div>
                </div>
                {savedCasesError && (
                    <div style={{ padding: '0.5rem 1rem', color: '#B91C1C', fontSize: '0.8rem', borderBottom: '1px solid #FECACA', background: '#FEF2F2' }}>
                        加载已保存用例失败：{savedCasesError}
                    </div>
                )}
                <div style={{ maxHeight: '260px', overflowY: 'auto' }}>
                    {savedCases.length === 0 && !savedCasesLoading ? (
                        <div style={{ padding: '0.75rem 1rem', fontSize: '0.85rem', color: '#9CA3AF' }}>当前项目还没有已保存的接口用例，可以在上方测试用例列表中为某条用例点击「保存」。</div>
                    ) : (
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                            <thead style={{ background: '#F3F4F6' }}>
                                <tr>
                                    <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>接口</th>
                                    <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>来源</th>
                                    <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>用例类型</th>
                                    <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>用例名称</th>
                                    <th style={{ padding: '0.5rem 0.75rem', textAlign: 'center', width: '140px' }}>操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                {savedCases.map((sc: any) => (
                                    <tr key={sc.id} style={{ borderTop: '1px solid #E5E7EB' }}>
                                        <td style={{ padding: '0.5rem 0.75rem' }}>
                                            <span style={{ fontWeight: '500' }}>{sc.method}</span> <span style={{ fontFamily: 'monospace' }}>{sc.path}</span>
                                        </td>
                                        <td style={{ padding: '0.5rem 0.75rem' }}>
                                            {sc.source === 'ai' ? (
                                                <span style={{ padding: '0.15rem 0.4rem', borderRadius: '0.25rem', background: '#DBEAFE', color: '#1D4ED8', fontSize: '0.7rem', fontWeight: '600' }}>AI</span>
                                            ) : (
                                                <span style={{ padding: '0.15rem 0.4rem', borderRadius: '0.25rem', background: '#F3F4F6', color: '#6B7280', fontSize: '0.7rem' }}>规则</span>
                                            )}
                                        </td>
                                        <td style={{ padding: '0.5rem 0.75rem' }}>{sc.case_type ?? '-'}</td>
                                        <td style={{ padding: '0.5rem 0.75rem', color: '#6B7280' }}>{sc.name ?? '-'}</td>
                                        <td style={{ padding: '0.5rem 0.75rem', textAlign: 'center' }}>
                                            <button
                                                type="button"
                                                disabled={savedCaseRunLoading === sc.id || !baseUrl.trim()}
                                                onClick={async () => {
                                                    if (!baseUrl.trim()) { alert('请先选择执行环境 Base URL'); return }
                                                    setSavedCaseRunLoading(sc.id)
                                                    setSavedCaseRunResult((prev: any) => { const n = { ...prev }; delete n[sc.id]; return n })
                                                    try {
                                                        const res = await fetch(`${API_BASE}/api/v1/api-test-plan/execute-case`, {
                                                            method: 'POST',
                                                            headers: { 'Content-Type': 'application/json' },
                                                            body: JSON.stringify({
                                                                project_id: currentProject,
                                                                base_url: baseUrl.trim(),
                                                                environment: 'test',
                                                                endpoint: { method: sc.method, path: sc.path, base_url: '' },
                                                                case: { ...sc },
                                                            }),
                                                        })
                                                        const data = await res.json()
                                                        setSavedCaseRunResult((prev: any) => ({ ...prev, [sc.id]: { status: data.result?.success ? 'passed' : 'failed', status_code: data.result?.status_code, error: data.result?.error, response: data.result?.response, execution_id: data.execution_id } }))
                                                    } catch (e: any) {
                                                        setSavedCaseRunResult((prev: any) => ({ ...prev, [sc.id]: { status: 'error', error: e.message } }))
                                                    } finally {
                                                        setSavedCaseRunLoading(null)
                                                    }
                                                }}
                                                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', border: '1px solid #667eea', borderRadius: '0.25rem', background: savedCaseRunLoading === sc.id ? '#E5E7EB' : '#667eea', color: 'white' }}
                                            >
                                                {savedCaseRunLoading === sc.id ? '执行中' : '执行'}
                                            </button>
                                            {savedCaseRunResult[sc.id] && (
                                                <>
                                                    <span style={{ marginLeft: '0.35rem', fontSize: '0.75rem', color: savedCaseRunResult[sc.id].status === 'passed' ? '#10B981' : '#EF4444' }}>
                                                        {savedCaseRunResult[sc.id].status === 'passed' ? `✓` : `✗`}
                                                    </span>
                                                    {savedCaseRunResult[sc.id].status !== 'passed' && savedCaseRunResult[sc.id].execution_id && (
                                                        <button
                                                            onClick={(e: any) => {
                                                                e.stopPropagation()
                                                                if (savedCaseRunResult[sc.id].execution_id) {
                                                                    runHealApiCase(sc.id, savedCaseRunResult[sc.id].execution_id!)
                                                                }
                                                            }}
                                                            disabled={healApplyLoading[sc.id]}
                                                            title="一键修复"
                                                            style={{ marginLeft: '0.5rem', padding: '0.2rem 0.4rem', background: healApplyLoading[sc.id] ? '#FCA5A5' : '#EF4444', color: 'white', border: 'none', borderRadius: '0.25rem', fontSize: '0.7rem', cursor: healApplyLoading[sc.id] ? 'not-allowed' : 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                                                        >
                                                            <Wand2 size={12} className={healApplyLoading[sc.id] ? 'spin' : ''} />
                                                            修复
                                                        </button>
                                                    )}
                                                </>
                                            )}
                                            <button
                                                type="button"
                                                onClick={async (e: any) => {
                                                    e.stopPropagation()
                                                    if (!confirm('确定删除该已保存用例？')) return
                                                    try {
                                                        const res = await fetch(`${API_BASE}/api/v1/api-test-cases/${sc.id}`, { method: 'DELETE' })
                                                        if (!res.ok) throw new Error('删除失败')
                                                        loadSavedCases()
                                                    } catch (err: any) {
                                                        alert(err.message)
                                                    }
                                                }}
                                                style={{ marginLeft: '0.5rem', border: 'none', background: 'transparent', color: '#EF4444', cursor: 'pointer' }}
                                                title="删除"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {/* 测试用例列表 */}
            {(plan?.endpoints?.length ?? 0) > 0 && (
                <div ref={testCaseListRef} style={{ marginTop: '1.5rem', border: '1px solid #E5E7EB', borderRadius: '0.75rem', overflow: 'hidden' }}>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: '600', padding: '0.75rem 1rem', background: '#F9FAFB', margin: 0, borderBottom: '1px solid #E5E7EB' }}>
                        测试用例列表（共 {plan?.endpoint_count ?? 0} 个接口，{plan?.endpoints?.reduce((n: number, ep: any) => n + (ep.cases?.length || 0), 0) ?? 0} 条用例）
                    </h4>
                    <div style={{ maxHeight: '360px', overflowY: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                            <thead style={{ background: '#F3F4F6' }}>
                                <tr>
                                    <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>接口</th>
                                    <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>来源</th>
                                    <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>用例类型</th>
                                    <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>用例名称</th>
                                    <th style={{ padding: '0.5rem 0.75rem', textAlign: 'center', width: '90px' }}>操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                {plan?.endpoints?.map((ep: any, ei: number) =>
                                    (ep.cases ?? []).map((c: any, ci: number) => {
                                        const caseKey = `${ei}-${ci}`
                                        const runState = singleRunResult[caseKey]
                                        const running = singleRunLoading === caseKey
                                        return (
                                            <tr key={caseKey} style={{ borderTop: '1px solid #E5E7EB', cursor: 'pointer' }} onClick={() => setSelectedCaseDetail({ ep, c })}>
                                                <td style={{ padding: '0.5rem 0.75rem' }}><span style={{ fontWeight: '500' }}>{ep.method}</span> {ep.path}</td>
                                                <td style={{ padding: '0.5rem 0.75rem' }}>{c.source === 'ai' ? 'AI' : '规则'}</td>
                                                <td style={{ padding: '0.5rem 0.75rem' }}>{c.case_type ?? '-'}</td>
                                                <td style={{ padding: '0.5rem 0.75rem' }}>{c.name ?? c.description ?? '-'}</td>
                                                <td style={{ padding: '0.5rem 0.75rem', textAlign: 'center' }} onClick={e => e.stopPropagation()}>
                                                    <button
                                                        onClick={async () => {
                                                            setSingleRunLoading(caseKey)
                                                            try {
                                                                const res = await fetch(`${API_BASE}/api/v1/api-test-plan/execute-case`, {
                                                                    method: 'POST',
                                                                    headers: { 'Content-Type': 'application/json' },
                                                                    body: JSON.stringify({
                                                                        project_id: currentProject,
                                                                        base_url: baseUrl,
                                                                        environment: 'test',
                                                                        endpoint: { method: ep.method, path: ep.path },
                                                                        case: { ...c },
                                                                    }),
                                                                })
                                                                const data = await res.json()
                                                                setSingleRunResult((prev: any) => ({ ...prev, [caseKey]: { status: data.result?.success ? 'passed' : 'failed', status_code: data.result?.status_code, error: data.result?.error, response: data.result?.response } }))
                                                            } catch (e: any) {
                                                                setSingleRunResult((prev: any) => ({ ...prev, [caseKey]: { status: 'error', error: e.message } }))
                                                            } finally {
                                                                setSingleRunLoading(null)
                                                            }
                                                        }}
                                                        disabled={running}
                                                        style={{ padding: '0.2rem 0.4rem', background: '#667eea', color: 'white', borderRadius: '0.25rem' }}
                                                    >
                                                        {running ? '...' : '执行'}
                                                    </button>
                                                </td>
                                            </tr>
                                        )
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* 用例详情弹窗 */}
            {selectedCaseDetail && (
                <div
                    style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}
                    onClick={() => setSelectedCaseDetail(null)}
                >
                    <div
                        style={{ background: 'white', width: '100%', maxWidth: '800px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', borderRadius: '1rem', overflow: 'hidden', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div style={{ padding: '1rem 1.5rem', borderBottom: '1px solid #E5E7EB', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#F9FAFB' }}>
                            <div>
                                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600', color: '#1F2937' }}>用例详情报告</h3>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
                                    <span style={{ fontSize: '0.75rem', padding: '0.1rem 0.4rem', borderRadius: '0.25rem', background: '#EEF2FF', color: '#4F46E5', fontWeight: '600' }}>{selectedCaseDetail.ep.method}</span>
                                    <span style={{ fontSize: '0.85rem', color: '#6B7280', fontFamily: 'monospace' }}>{selectedCaseDetail.ep.path}</span>
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedCaseDetail(null)}
                                style={{ background: 'none', border: 'none', color: '#9CA3AF', cursor: 'pointer', padding: '0.5rem' }}
                            >
                                <X size={20} />
                            </button>
                        </div>

                        {/* Tabs */}
                        <div style={{ display: 'flex', background: '#FFFFFF', borderBottom: '1px solid #E5E7EB', padding: '0 1rem' }}>
                            <TabButton active={caseDetailMainTab === 'request'} label="请求配置" onClick={() => setCaseDetailMainTab('request')} />
                            <TabButton active={caseDetailMainTab === 'expected'} label="期望结果" onClick={() => setCaseDetailMainTab('expected')} />
                            {singleRunResult[`${plan?.endpoints?.indexOf(selectedCaseDetail.ep)}-${selectedCaseDetail.ep.cases?.indexOf(selectedCaseDetail.c)}`] && (
                                <TabButton active={caseDetailMainTab === 'response'} label="执行响应" onClick={() => setCaseDetailMainTab('response')} />
                            )}
                        </div>

                        {/* Content */}
                        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
                            {caseDetailMainTab === 'request' && (
                                <div>
                                    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', borderBottom: '1px solid #F3F4F6' }}>
                                        <button onClick={() => setCaseDetailSubTab('params')} style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem', border: 'none', background: caseDetailSubTab === 'params' ? '#F3F4F6' : 'transparent', color: caseDetailSubTab === 'params' ? '#1F2937' : '#6B7280', borderRadius: '0.375rem 0.375rem 0 0', cursor: 'pointer' }}>Params</button>
                                        <button onClick={() => setCaseDetailSubTab('headers')} style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem', border: 'none', background: caseDetailSubTab === 'headers' ? '#F3F4F6' : 'transparent', color: caseDetailSubTab === 'headers' ? '#1F2937' : '#6B7280', borderRadius: '0.375rem 0.375rem 0 0', cursor: 'pointer' }}>Headers</button>
                                        <button onClick={() => setCaseDetailSubTab('body')} style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem', border: 'none', background: caseDetailSubTab === 'body' ? '#F3F4F6' : 'transparent', color: caseDetailSubTab === 'body' ? '#1F2937' : '#6B7280', borderRadius: '0.375rem 0.375rem 0 0', cursor: 'pointer' }}>Body</button>
                                    </div>
                                    <div style={{ border: '1px solid #F3F4F6', borderRadius: '0.5rem', overflow: 'hidden' }}>
                                        {caseDetailSubTab === 'params' && <KeyValueTable data={selectedCaseDetail.c.request_template?.params} />}
                                        {caseDetailSubTab === 'headers' && <KeyValueTable data={selectedCaseDetail.c.request_template?.headers} />}
                                        {caseDetailSubTab === 'body' && (
                                            <div style={{ padding: '0.5rem', maxHeight: '300px', overflowY: 'auto' }}>
                                                {selectedCaseDetail.c.request_template?.body ? (
                                                    <pre style={{ margin: 0, fontSize: '0.75rem', fontFamily: 'monospace', color: '#374151' }}>
                                                        {typeof selectedCaseDetail.c.request_template.body === 'string' ? selectedCaseDetail.c.request_template.body : JSON.stringify(selectedCaseDetail.c.request_template.body, null, 2)}
                                                    </pre>
                                                ) : <div style={{ color: '#9CA3AF', fontSize: '0.8rem' }}>无 Body 数据</div>}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {caseDetailMainTab === 'expected' && (
                                <div>
                                    <h4 style={{ fontSize: '0.85rem', color: '#4B5563', marginBottom: '0.75rem' }}>预期校验规则</h4>
                                    <div style={{ border: '1px solid #F3F4F6', borderRadius: '0.5rem', overflow: 'hidden' }}>
                                        <KeyValueTable data={selectedCaseDetail.c.expected_template} />
                                    </div>
                                </div>
                            )}

                            {caseDetailMainTab === 'response' && (
                                <div>
                                    {(() => {
                                        const res = singleRunResult[`${plan?.endpoints?.indexOf(selectedCaseDetail.ep)}-${selectedCaseDetail.ep.cases?.indexOf(selectedCaseDetail.c)}`]
                                        if (!res) return null
                                        return (
                                            <>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.25rem 0.75rem', borderRadius: '1rem', background: res.status === 'passed' ? '#D1FAE5' : '#FEE2E2', color: res.status === 'passed' ? '#065F46' : '#991B1B', fontSize: '0.75rem', fontWeight: '600' }}>
                                                        {res.status === 'passed' ? <CheckCircle size={14} /> : <XCircle size={14} />}
                                                        {res.status === 'passed' ? '测试通过' : '测试失败'}
                                                    </div>
                                                    <div style={{ fontSize: '0.85rem', color: '#6B7280' }}>
                                                        Status: <span style={{ color: '#1F2937', fontWeight: '600', fontFamily: 'monospace' }}>{res.status_code || 'Error'}</span>
                                                    </div>
                                                </div>
                                                <div style={{ border: '1px solid #F3F4F6', borderRadius: '0.5rem', overflow: 'hidden', padding: '1rem', background: '#F9FAFB', maxHeight: '300px', overflowY: 'auto' }}>
                                                    <pre style={{ margin: 0, fontSize: '0.75rem', fontFamily: 'monospace' }}>
                                                        {JSON.stringify(res.response, null, 2)}
                                                    </pre>
                                                </div>
                                            </>
                                        )
                                    })()}
                                </div>
                            )}
                        </div>

                        {/* Footer Actions */}
                        <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid #E5E7EB', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', background: '#F9FAFB' }}>
                            <button
                                onClick={async () => {
                                    try {
                                        const res = await fetch(`${API_BASE}/api/v1/api-test-cases`, {
                                            method: 'POST',
                                            headers: { 'Content-Type': 'application/json' },
                                            body: JSON.stringify({
                                                ...selectedCaseDetail.c,
                                                project_id: currentProject,
                                                method: selectedCaseDetail.ep.method,
                                                path: selectedCaseDetail.ep.path,
                                                api_id: selectedCaseDetail.ep.id
                                            })
                                        })
                                        if (res.ok) {
                                            alert('用例已保存至用例库')
                                            loadSavedCases()
                                        } else {
                                            const data = await res.json()
                                            alert(`保存失败: ${data.detail || '未知错误'}`)
                                        }
                                    } catch (err: any) {
                                        alert(`保存异常: ${err.message}`)
                                    }
                                }}
                                style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', background: '#667eea', color: 'white', border: 'none', borderRadius: '0.5rem', fontWeight: '500', cursor: 'pointer' }}
                            >
                                执行并保存到用例库
                            </button>
                            <button
                                onClick={() => setSelectedCaseDetail(null)}
                                style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', background: '#FFFFFF', color: '#374151', border: '1px solid #D1D5DB', borderRadius: '0.5rem', fontWeight: '500', cursor: 'pointer' }}
                            >
                                关闭
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
