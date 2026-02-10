'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useProject } from '../../contexts/ProjectContext'
import { ClipboardList, Play, CheckCircle, XCircle, AlertCircle, Loader2, FileText, Wand2 } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_AI_API_URL || 'http://localhost:8000'

interface EnvItem {
    id: number
    env_name: string
    base_url: string
    is_default?: number
}

export default function ApiTestPlanTab() {
    const { currentProject } = useProject()
    const [environments, setEnvironments] = useState<EnvItem[]>([])
    const [selectedEnvId, setSelectedEnvId] = useState<number | null>(null)
    const [planLoading, setPlanLoading] = useState(false)
    const [plan, setPlan] = useState<any>(null)
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
    const [savedCases, setSavedCases] = useState<any[]>([])
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
                setEnvironments(Array.isArray(data) ? data : [])
                const list = Array.isArray(data) ? data : []
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
        // eslint-disable-next-line react-hooks/exhaustive-deps
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
            if (data.detail) throw new Error(data.detail)
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
                body: JSON.stringify({
                    api_test_case_id: apiTestCaseId,
                    execution_id: executionId
                }),
            })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail || '修复失败')

            if (data.status === 'healed') {
                alert(`✅ 修复成功！\n\n接口用例已更新，请重新执行验证。`)
                // 刷新已保存用例列表
                loadSavedCases()
            } else {
                alert(`⚠️ 无法自动修复\n\n原因: ${data.message}\n分析: ${data.analysis?.root_cause || '无详细分析'}`)
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
            {plan?.endpoints?.length > 0 && (
                <div style={{ marginBottom: '1.5rem', padding: '1rem', background: '#F9FAFB', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>选择要生成 AI 用例的接口</div>
                    <p style={{ fontSize: '0.8rem', color: '#6B7280', marginBottom: '0.75rem' }}>勾选接口后点击下方按钮，大模型会为选中接口生成真实测试用例（正向/边界/健壮/安全），可看到进度。</p>
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
                        {aiGenerateProgress && (
                            <span style={{ fontSize: '0.8rem', color: '#6B7280' }}>
                                进度 {aiGenerateProgress.current}/{aiGenerateProgress.total}
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* 选择项目环境（Base URL） */}
            <div style={{ marginBottom: '1rem' }}>
                <label style={{ fontSize: '0.875rem', fontWeight: '500', display: 'block', marginBottom: '0.25rem' }}>执行环境（选择当前项目已配置的 Base URL）</label>
                {environments.length === 0 ? (
                    <p style={{ fontSize: '0.875rem', color: '#9CA3AF' }}>
                        当前项目暂无环境配置，请先在「项目设置 → 环境配置」中为该项目添加环境（Base URL）。
                    </p>
                ) : (
                    <select
                        value={selectedEnvId ?? ''}
                        onChange={(e) => setSelectedEnvId(e.target.value ? Number(e.target.value) : null)}
                        style={{ width: '100%', maxWidth: '480px', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: '0.5rem', fontSize: '0.875rem' }}
                    >
                        <option value="">请选择环境</option>
                        {environments.map((e) => (
                            <option key={e.id} value={e.id}>
                                {e.env_name} — {e.base_url}
                            </option>
                        ))}
                    </select>
                )}
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

            {/* 执行结果摘要 */}
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
                            {summary.by_case_type && Object.entries(summary.by_case_type).map(([k, v]: [string, any]) => (
                                <span key={k}>[{k}] 通过 {v.passed}/{v.total}</span>
                            ))}
                        </div>
                    )}
                    <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                        <Link
                            href={`/reports?execution_id=${executeResult.id}`}
                            style={{
                                padding: '0.4rem 0.8rem',
                                background: '#667eea',
                                color: 'white',
                                border: 'none',
                                borderRadius: '0.375rem',
                                fontSize: '0.8rem',
                                fontWeight: '500',
                                textDecoration: 'none',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.25rem',
                            }}
                        >
                            <FileText size={14} />
                            查看测试报告
                        </Link>
                        {hasFailed && (
                            <button
                                onClick={() => runHealAnalyze(executeResult.id)}
                                disabled={healAnalyzeLoading}
                                style={{
                                    padding: '0.4rem 0.8rem',
                                    background: healAnalyzeLoading ? '#9CA3AF' : '#F59E0B',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '0.375rem',
                                    fontSize: '0.8rem',
                                    fontWeight: '500',
                                    cursor: healAnalyzeLoading ? 'not-allowed' : 'pointer',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.25rem',
                                }}
                            >
                                {healAnalyzeLoading ? <Loader2 size={14} /> : <AlertCircle size={14} />}
                                失败分析（AI 建议）
                            </button>
                        )}
                    </div>
                    {/* 执行明细：成功/失败每条可见 */}
                    {executeResult.results?.length > 0 && (
                        <div style={{ marginTop: '1rem' }}>
                            <h5 style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '0.5rem' }}>执行明细</h5>
                            <div style={{ overflowX: 'auto', maxHeight: '320px', overflowY: 'auto', border: '1px solid #E5E7EB', borderRadius: '0.5rem' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                    <thead style={{ background: '#F3F4F6', position: 'sticky', top: 0 }}>
                                        <tr>
                                            <th style={{ padding: '0.5rem', textAlign: 'left' }}>步骤</th>
                                            <th style={{ padding: '0.5rem', textAlign: 'left' }}>接口</th>
                                            <th style={{ padding: '0.5rem', textAlign: 'left' }}>用例类型</th>
                                            <th style={{ padding: '0.5rem', textAlign: 'center' }}>状态码</th>
                                            <th style={{ padding: '0.5rem', textAlign: 'center' }}>结果</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {executeResult.results.map((r: any, i: number) => (
                                            <tr
                                                key={i}
                                                style={{ borderTop: '1px solid #E5E7EB', background: r.success ? 'transparent' : '#FEF2F2', cursor: 'pointer' }}
                                                onClick={() => setSelectedResultDetail(r)}
                                            >
                                                <td style={{ padding: '0.5rem' }}>{r.step_order ?? i + 1}</td>
                                                <td style={{ padding: '0.5rem' }}><span style={{ fontWeight: '500' }}>{r.method}</span> {r.url}</td>
                                                <td style={{ padding: '0.5rem' }}>{r.case_type ?? '-'}</td>
                                                <td style={{ padding: '0.5rem', textAlign: 'center' }}>{r.status_code ?? '-'}</td>
                                                <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                                                    {r.success ? <span style={{ color: '#10B981', fontWeight: '500' }}>通过</span> : <span style={{ color: '#EF4444', fontWeight: '500' }}>失败</span>}
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
                                        <thead>
                                            <tr style={{ background: '#F9FAFB', borderBottom: '1px solid #E5E7EB' }}>
                                                <th style={{ padding: '0.4rem 0.6rem', textAlign: 'left', fontWeight: '600', color: '#6B7280', width: '38%' }}>参数名</th>
                                                <th style={{ padding: '0.4rem 0.6rem', textAlign: 'left', fontWeight: '600', color: '#6B7280' }}>参数值</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {Object.entries(obj).map(([k, v]) => (
                                                <tr key={k} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                                    <td style={{ padding: '0.4rem 0.6rem', fontFamily: 'monospace', color: '#374151' }}>{k}</td>
                                                    <td style={{ padding: '0.4rem 0.6rem', fontFamily: 'monospace', wordBreak: 'break-all' }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )
                                return (
                                    <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'white', border: '1px solid #E5E7EB', borderRadius: '0.5rem', fontSize: '0.8rem' }} onClick={(e) => e.stopPropagation()}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                            <strong>执行步骤详情</strong>
                                            <button type="button" onClick={() => setSelectedResultDetail(null)} style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', border: '1px solid #E5E7EB', borderRadius: '0.25rem', background: '#F9FAFB', cursor: 'pointer' }}>关闭</button>
                                        </div>
                                        <div style={{ marginBottom: '0.5rem' }}><span style={{ fontWeight: '500' }}>{rd.method}</span> <span style={{ fontFamily: 'monospace' }}>{rd.url}</span></div>
                                        <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #E5E7EB', marginBottom: '0.5rem' }}>
                                            <button type="button" onClick={() => { setResultDetailTab('request'); setResultDetailSubTab('body') }} style={{ padding: '0.35rem 0.75rem', border: 'none', borderBottom: resultDetailTab === 'request' ? '2px solid #667eea' : '2px solid transparent', background: 'transparent', cursor: 'pointer', fontSize: '0.8rem', color: resultDetailTab === 'request' ? '#667eea' : '#6B7280', fontWeight: resultDetailTab === 'request' ? '600' : '400' }}>请求</button>
                                            <button type="button" onClick={() => setResultDetailTab('response')} style={{ padding: '0.35rem 0.75rem', border: 'none', borderBottom: resultDetailTab === 'response' ? '2px solid #667eea' : '2px solid transparent', background: 'transparent', cursor: 'pointer', fontSize: '0.8rem', color: resultDetailTab === 'response' ? '#667eea' : '#6B7280', fontWeight: resultDetailTab === 'response' ? '600' : '400' }}>响应</button>
                                        </div>
                                        {resultDetailTab === 'request' && (
                                            <>
                                                <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '0.5rem', fontSize: '0.75rem' }}>
                                                    <button type="button" onClick={() => setResultDetailSubTab('params')} style={{ padding: '0.25rem 0.5rem', border: 'none', borderBottom: resultDetailSubTab === 'params' ? '2px solid #667eea' : '2px solid transparent', background: 'transparent', cursor: 'pointer', color: resultDetailSubTab === 'params' ? '#667eea' : '#6B7280' }}>Params</button>
                                                    <button type="button" onClick={() => setResultDetailSubTab('body')} style={{ padding: '0.25rem 0.5rem', border: 'none', borderBottom: resultDetailSubTab === 'body' ? '2px solid #667eea' : '2px solid transparent', background: 'transparent', cursor: 'pointer', color: resultDetailSubTab === 'body' ? '#667eea' : '#6B7280' }}>Body</button>
                                                    <button type="button" onClick={() => setResultDetailSubTab('headers')} style={{ padding: '0.25rem 0.5rem', border: 'none', borderBottom: resultDetailSubTab === 'headers' ? '2px solid #667eea' : '2px solid transparent', background: 'transparent', cursor: 'pointer', color: resultDetailSubTab === 'headers' ? '#667eea' : '#6B7280' }}>Headers</button>
                                                </div>
                                                <div style={{ maxHeight: '200px', overflow: 'auto', border: '1px solid #E5E7EB', borderRadius: '0.375rem' }}>
                                                    {resultDetailSubTab === 'params' && (Object.keys(urlParams).length > 0 ? kvTable(urlParams) : <div style={{ padding: '0.5rem', color: '#9CA3AF' }}>无 URL 参数</div>)}
                                                    {resultDetailSubTab === 'body' && (Object.keys(reqData).length > 0 ? <pre style={{ margin: 0, padding: '0.5rem', background: '#F9FAFB', fontSize: '0.75rem', overflow: 'auto' }}>{JSON.stringify(reqData, null, 2)}</pre> : <div style={{ padding: '0.5rem', color: '#9CA3AF' }}>无 Body</div>)}
                                                    {resultDetailSubTab === 'headers' && (Object.keys(reqHeaders).length > 0 ? kvTable(reqHeaders) : <div style={{ padding: '0.5rem', color: '#9CA3AF' }}>无请求头</div>)}
                                                </div>
                                            </>
                                        )}
                                        {resultDetailTab === 'response' && (
                                            <div>
                                                <div style={{ marginBottom: '0.5rem' }}><span style={{ color: '#6B7280' }}>状态码：</span><strong>{rd.status_code ?? '-'}</strong> {rd.expected_status != null && <span style={{ color: '#6B7280', fontSize: '0.8rem' }}>（期望 {rd.expected_status}）</span>}</div>
                                                {rd.error && <div style={{ color: '#EF4444', marginBottom: '0.5rem' }}>错误：{rd.error}</div>}
                                                {rd.response != null && (
                                                    <div><span style={{ color: '#6B7280', fontSize: '0.75rem' }}>响应体</span>
                                                        <pre style={{ margin: '0.25rem 0 0', padding: '0.5rem', background: '#F9FAFB', borderRadius: '0.25rem', overflow: 'auto', fontSize: '0.75rem', maxHeight: '180px' }}>{typeof rd.response === 'string' ? rd.response : JSON.stringify(rd.response, null, 2)}</pre>
                                                    </div>
                                                )}
                                                {rd.response == null && !rd.error && <div style={{ color: '#9CA3AF' }}>无响应体</div>}
                                            </div>
                                        )}
                                    </div>
                                )
                            })()}
                        </div>
                    )}
                </div>
            )}

            {/* 失败分析结果（带失败接口标识） */}
            {healAnalyzeResult && (
                <div style={{ marginTop: '1rem', padding: '1rem', background: '#FFFBEB', borderRadius: '0.75rem', border: '1px solid #FCD34D' }}>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: '600', marginBottom: '0.5rem' }}>失败分析结果</h4>
                    {healAnalyzeResult.status === 'no_failure' && <p style={{ fontSize: '0.875rem' }}>{healAnalyzeResult.message}</p>}
                    {healAnalyzeResult.analysis?.length > 0 && (() => {
                        const failedResults = (executeResult?.results ?? []).filter((r: any) => !r.success)
                        return (
                            <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.875rem' }}>
                                {healAnalyzeResult.analysis.map((a: any, i: number) => {
                                    const step = failedResults[i]
                                    const interfaceLabel = step ? `${step.method} ${step.url}` : `步骤 ${i + 1}`
                                    return (
                                        <li key={i} style={{ marginBottom: '0.75rem' }}>
                                            <span style={{ fontWeight: '600', color: '#B45309' }}>接口: {interfaceLabel}</span>
                                            <br />
                                            <strong>{a.failure_type}</strong> — {a.root_cause}
                                            <br />
                                            <span style={{ color: '#92400E' }}>{a.suggested_fix}</span>
                                            {a.patch_hint && <br />}
                                            {a.patch_hint && <span style={{ color: '#6B7280', fontSize: '0.8rem' }}>提示: {a.patch_hint}</span>}
                                        </li>
                                    )
                                })}
                            </ul>
                        )
                    })()}
                    {healAnalyzeResult.healable === true && (
                        <p style={{ fontSize: '0.8rem', color: '#92400E', marginTop: '0.5rem' }}>
                            此为场景用例执行时，可在「测试场景」中对该用例点击「应用修复」自动改步骤。
                        </p>
                    )}
                </div>
            )}

            {/* 生成完成提示 */}
            {aiGenerateDoneHint && (
                <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: '#ECFDF5', border: '1px solid #10B981', borderRadius: '0.5rem', fontSize: '0.875rem', color: '#065F46', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <CheckCircle size={18} style={{ flexShrink: 0 }} />
                    {aiGenerateDoneHint}
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
                            style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', borderRadius: '0.25rem', border: '1px solid #D1D5DB', background: savedCasesLoading ? '#E5E7EB' : '#FFFFFF', cursor: savedCasesLoading ? 'not-allowed' : 'pointer', color: '#374151' }}
                        >
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
                                                    setSavedCaseRunResult(prev => { const n = { ...prev }; delete n[sc.id]; return n })
                                                    try {
                                                        const res = await fetch(`${API_BASE}/api/v1/api-test-plan/execute-case`, {
                                                            method: 'POST',
                                                            headers: { 'Content-Type': 'application/json' },
                                                            body: JSON.stringify({
                                                                project_id: currentProject,
                                                                base_url: baseUrl.trim(),
                                                                environment: 'test',
                                                                endpoint: { method: sc.method, path: sc.path, base_url: '' },
                                                                case: {
                                                                    path: sc.path,
                                                                    method: sc.method,
                                                                    case_type: sc.case_type,
                                                                    name: sc.name,
                                                                    request_template: sc.request_template || {},
                                                                    expected_template: sc.expected_template || {},
                                                                },
                                                            }),
                                                        })
                                                        const data = await res.json().catch(() => ({}))
                                                        if (!res.ok) {
                                                            setSavedCaseRunResult(prev => ({ ...prev, [sc.id]: { status: 'error', error: data.detail || data.message || `HTTP ${res.status}` } }))
                                                            return
                                                        }
                                                        if (data.detail) {
                                                            setSavedCaseRunResult(prev => ({ ...prev, [sc.id]: { status: 'error', error: data.detail } }))
                                                            return
                                                        }
                                                        setSavedCaseRunResult(prev => ({
                                                            ...prev,
                                                            [sc.id]: {
                                                                status: data.result?.success ? 'passed' : 'failed',
                                                                status_code: data.result?.status_code,
                                                                error: data.result?.error,
                                                                response: data.result?.response,
                                                                execution_id: data.execution_id,
                                                            },
                                                        }))
                                                    } catch (e: any) {
                                                        setSavedCaseRunResult(prev => ({ ...prev, [sc.id]: { status: 'error', error: e.message || '执行失败' } }))
                                                    } finally {
                                                        setSavedCaseRunLoading(null)
                                                    }
                                                }}
                                                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', border: '1px solid #667eea', borderRadius: '0.25rem', background: savedCaseRunLoading === sc.id ? '#E5E7EB' : '#667eea', color: 'white', cursor: savedCaseRunLoading === sc.id ? 'not-allowed' : 'pointer' }}
                                            >
                                                {savedCaseRunLoading === sc.id ? '执行中' : '执行'}
                                            </button>
                                            {savedCaseRunResult[sc.id] && savedCaseRunLoading !== sc.id && (
                                                <>
                                                    <span style={{ marginLeft: '0.35rem', fontSize: '0.75rem', color: savedCaseRunResult[sc.id].status === 'passed' ? '#10B981' : '#EF4444' }}>
                                                        {savedCaseRunResult[sc.id].status === 'passed' ? `✓ ${savedCaseRunResult[sc.id].status_code}` : savedCaseRunResult[sc.id].status_code ? `✗ ${savedCaseRunResult[sc.id].status_code}` : savedCaseRunResult[sc.id].error || '失败'}
                                                    </span>
                                                    {savedCaseRunResult[sc.id].status !== 'passed' && savedCaseRunResult[sc.id].execution_id && (
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation()
                                                                runHealApiCase(sc.id, savedCaseRunResult[sc.id].execution_id!)
                                                            }}
                                                            disabled={healApplyLoading[sc.id]}
                                                            title="一键修复"
                                                            style={{
                                                                marginLeft: '0.5rem',
                                                                padding: '0.2rem 0.4rem',
                                                                background: healApplyLoading[sc.id] ? '#FCA5A5' : '#EF4444',
                                                                color: 'white',
                                                                border: 'none',
                                                                borderRadius: '0.25rem',
                                                                fontSize: '0.7rem',
                                                                cursor: healApplyLoading[sc.id] ? 'not-allowed' : 'pointer',
                                                                display: 'inline-flex',
                                                                alignItems: 'center',
                                                                gap: '0.25rem'
                                                            }}
                                                        >
                                                            <Wand2 size={12} className={healApplyLoading[sc.id] ? 'spin' : ''} />
                                                            {healApplyLoading[sc.id] ? '修复中...' : '修复'}
                                                        </button>
                                                    )}
                                                </>
                                            )}
                                            <button
                                                type="button"
                                                onClick={async () => {
                                                    if (!confirm('确定删除该已保存用例？')) return
                                                    try {
                                                        const res = await fetch(`${API_BASE}/api/v1/api-test-cases/${sc.id}`, { method: 'DELETE' })
                                                        if (!res.ok) {
                                                            const data = await res.json().catch(() => ({}))
                                                            alert(data.detail || data.message || `删除失败: HTTP ${res.status}`)
                                                            return
                                                        }
                                                        setSavedCases(prev => prev.filter((x) => x.id !== sc.id))
                                                        setSavedCaseRunResult(prev => { const n = { ...prev }; delete n[sc.id]; return n })
                                                    } catch (e: any) {
                                                        alert(e.message || '删除失败')
                                                    }
                                                }}
                                                style={{ marginLeft: '0.35rem', padding: '0.25rem 0.5rem', fontSize: '0.75rem', borderRadius: '0.25rem', border: '1px solid #F97373', background: '#FEF2F2', color: '#B91C1C', cursor: 'pointer' }}
                                            >
                                                删除
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {/* 测试用例列表（生成计划后可见） */}
            {plan?.endpoints?.length > 0 && (
                <div ref={testCaseListRef} style={{ marginTop: '1.5rem', border: '1px solid #E5E7EB', borderRadius: '0.75rem', overflow: 'hidden' }}>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: '600', padding: '0.75rem 1rem', background: '#F9FAFB', margin: 0, borderBottom: '1px solid #E5E7EB' }}>
                        测试用例列表（共 {plan.endpoint_count ?? 0} 个接口，{plan.endpoints?.reduce((n: number, ep: any) => n + (ep.cases?.length || 0), 0) ?? 0} 条用例）
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
                                {plan.endpoints.map((ep: any, ei: number) =>
                                    (ep.cases ?? []).map((c: any, ci: number) => {
                                        const caseKey = `${ei}-${ci}`
                                        const runState = singleRunResult[caseKey]
                                        const running = singleRunLoading === caseKey
                                        return (
                                            <tr
                                                key={caseKey}
                                                style={{ borderTop: '1px solid #E5E7EB', cursor: 'pointer' }}
                                                onClick={() => {
                                                    const rt = c.request_template || {}
                                                    setSelectedCaseDetail({ ep, c })
                                                    if (Object.keys(rt.params || {}).length > 0) setCaseDetailSubTab('body')
                                                    else if (Object.keys(rt.url_params || {}).length > 0) setCaseDetailSubTab('params')
                                                    else if (Object.keys(rt.headers || {}).length > 0) setCaseDetailSubTab('headers')
                                                    else if (Object.keys(rt.cookies || {}).length > 0) setCaseDetailSubTab('cookies')
                                                    else setCaseDetailSubTab('headers')
                                                    setCaseDetailMainTab('request')
                                                }}
                                            >
                                                <td style={{ padding: '0.5rem 0.75rem' }}><span style={{ fontWeight: '500' }}>{ep.method}</span> {ep.path}</td>
                                                <td style={{ padding: '0.5rem 0.75rem' }}>
                                                    {c.source === 'ai' ? (
                                                        <span style={{ padding: '0.15rem 0.4rem', borderRadius: '0.25rem', background: '#DBEAFE', color: '#1D4ED8', fontSize: '0.7rem', fontWeight: '600' }}>AI</span>
                                                    ) : (
                                                        <span style={{ padding: '0.15rem 0.4rem', borderRadius: '0.25rem', background: '#F3F4F6', color: '#6B7280', fontSize: '0.7rem' }}>规则</span>
                                                    )}
                                                </td>
                                                <td style={{ padding: '0.5rem 0.75rem' }}>{c.case_type ?? '-'}</td>
                                                <td style={{ padding: '0.5rem 0.75rem', color: '#6B7280' }}>{c.name ?? c.description ?? '-'}</td>
                                                <td style={{ padding: '0.5rem 0.75rem', textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                                                    <button
                                                        type="button"
                                                        disabled={running || !baseUrl.trim()}
                                                        onClick={async () => {
                                                            if (!baseUrl.trim()) { alert('请先选择执行环境 Base URL'); return }
                                                            setSingleRunLoading(caseKey)
                                                            setSingleRunResult(prev => { const n = { ...prev }; delete n[caseKey]; return n })
                                                            try {
                                                                const res = await fetch(`${API_BASE}/api/v1/api-test-plan/execute-case`, {
                                                                    method: 'POST',
                                                                    headers: { 'Content-Type': 'application/json' },
                                                                    body: JSON.stringify({
                                                                        project_id: currentProject,
                                                                        base_url: baseUrl.trim(),
                                                                        environment: 'test',
                                                                        endpoint: { method: ep.method, path: ep.path, base_url: ep.base_url },
                                                                        case: { ...c, path: ep.path, method: ep.method },
                                                                    }),
                                                                })
                                                                const data = await res.json().catch(() => ({}))
                                                                if (!res.ok) {
                                                                    const msg = data.detail || data.message || `HTTP ${res.status}`
                                                                    setSingleRunResult(prev => ({ ...prev, [caseKey]: { status: 'error', error: msg } }))
                                                                    return
                                                                }
                                                                if (data.detail) {
                                                                    setSingleRunResult(prev => ({ ...prev, [caseKey]: { status: 'error', error: data.detail } }))
                                                                    return
                                                                }
                                                                setSingleRunResult(prev => ({ ...prev, [caseKey]: { status: data.result?.success ? 'passed' : 'failed', status_code: data.result?.status_code, error: data.result?.error, response: data.result?.response } }))
                                                            } catch (e: any) {
                                                                setSingleRunResult(prev => ({ ...prev, [caseKey]: { status: 'error', error: e.message || '执行失败' } }))
                                                            } finally {
                                                                setSingleRunLoading(null)
                                                            }
                                                        }}
                                                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', border: '1px solid #667eea', borderRadius: '0.25rem', background: running ? '#E5E7EB' : '#667eea', color: 'white', cursor: running ? 'not-allowed' : 'pointer' }}
                                                    >
                                                        {running ? '执行中' : '执行'}
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={async () => {
                                                            try {
                                                                const res = await fetch(`${API_BASE}/api/v1/api-test-cases`, {
                                                                    method: 'POST',
                                                                    headers: { 'Content-Type': 'application/json' },
                                                                    body: JSON.stringify({
                                                                        project_id: currentProject,
                                                                        api_id: ep.id,
                                                                        method: ep.method,
                                                                        path: ep.path,
                                                                        source: c.source || 'rule',
                                                                        case_type: c.case_type,
                                                                        name: c.name || c.description || `${ep.method} ${ep.path}`,
                                                                        description: c.description || '',
                                                                        request_template: c.request_template || {},
                                                                        expected_template: c.expected_template || {},
                                                                    }),
                                                                })
                                                                const data = await res.json().catch(() => ({}))
                                                                if (!res.ok) {
                                                                    alert(data.detail || data.message || `保存失败: HTTP ${res.status}`)
                                                                    return
                                                                }
                                                                // 追加到已保存用例列表
                                                                setSavedCases(prev => [data, ...prev])
                                                            } catch (e: any) {
                                                                alert(e.message || '保存用例失败')
                                                            }
                                                        }}
                                                        style={{ marginLeft: '0.35rem', padding: '0.25rem 0.5rem', fontSize: '0.75rem', border: '1px solid #D1D5DB', borderRadius: '0.25rem', background: '#F9FAFB', color: '#4B5563', cursor: 'pointer' }}
                                                    >
                                                        保存
                                                    </button>
                                                    {runState && !running && (
                                                        <span style={{ marginLeft: '0.35rem', fontSize: '0.75rem', color: runState.status === 'passed' ? '#10B981' : '#EF4444' }}>
                                                            {runState.status === 'passed' ? `✓ ${runState.status_code}` : runState.status_code ? `✗ ${runState.status_code}` : runState.error || '失败'}
                                                        </span>
                                                    )}
                                                </td>
                                            </tr>
                                        )
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                    {/* 点击用例后展示的详情（Postman 风格：请求/期望 Tab，Params / Body / Headers） */}
                    {selectedCaseDetail && (() => {
                        const { ep, c } = selectedCaseDetail
                        const rt = c.request_template || {}
                        const et = c.expected_template || {}
                        const base = ep.base_url || ''
                        const fullUrl = base ? `${base.replace(/\/$/, '')}${ep.path}` : ep.path
                        const hasParams = Object.keys(rt.url_params || {}).length > 0
                        const hasBody = Object.keys(rt.params || {}).length > 0
                        const hasHeaders = Object.keys(rt.headers || {}).length > 0
                        const hasCookies = Object.keys(rt.cookies || {}).length > 0
                        const bodyJson = hasBody ? JSON.stringify(rt.params, null, 2) : ''
                        const paramsJson = hasParams ? JSON.stringify(rt.url_params, null, 2) : '{}'
                        const headersJson = hasHeaders ? JSON.stringify(rt.headers, null, 2) : '{}'
                        const cookiesJson = hasCookies ? JSON.stringify(rt.cookies, null, 2) : '{}'
                        const tab = (label: string, key: 'request' | 'response' | 'expected') => (
                            <button
                                type="button"
                                key={key}
                                onClick={(e) => { e.stopPropagation(); setCaseDetailMainTab(key) }}
                                style={{
                                    padding: '0.5rem 1rem',
                                    border: 'none',
                                    borderBottom: caseDetailMainTab === key ? '2px solid #667eea' : '2px solid transparent',
                                    background: 'transparent',
                                    cursor: 'pointer',
                                    fontSize: '0.875rem',
                                    fontWeight: '500',
                                    color: caseDetailMainTab === key ? '#667eea' : '#6B7280',
                                }}
                            >
                                {label}
                            </button>
                        )
                        const keyValueTable = (obj: Record<string, unknown>) => (
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                <thead>
                                    <tr style={{ background: '#F9FAFB', borderBottom: '1px solid #E5E7EB' }}>
                                        <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: '600', color: '#6B7280', width: '40%' }}>参数名</th>
                                        <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: '600', color: '#6B7280' }}>参数值</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {Object.entries(obj || {}).map(([k, v]) => (
                                        <tr key={k} style={{ borderBottom: '1px solid #F3F4F6' }}>
                                            <td style={{ padding: '0.5rem 0.75rem', fontFamily: 'monospace', color: '#374151' }}>{k}</td>
                                            <td style={{ padding: '0.5rem 0.75rem', fontFamily: 'monospace', wordBreak: 'break-all' }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )
                        const subTab = (label: string, key: 'params' | 'body' | 'headers' | 'cookies', count?: number) => (
                            <button
                                type="button"
                                key={key}
                                onClick={(e) => { e.stopPropagation(); setCaseDetailSubTab(key) }}
                                style={{
                                    padding: '0.4rem 0.75rem',
                                    border: 'none',
                                    borderBottom: caseDetailSubTab === key ? '2px solid #667eea' : '2px solid transparent',
                                    background: 'transparent',
                                    cursor: 'pointer',
                                    fontSize: '0.8rem',
                                    color: caseDetailSubTab === key ? '#667eea' : '#6B7280',
                                }}
                            >
                                {label}{count != null && count > 0 ? ` ${count}` : ''}
                            </button>
                        )
                        return (
                            <div style={{ borderTop: '1px solid #E5E7EB', background: '#fff' }} onClick={(e) => e.stopPropagation()}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', borderBottom: '1px solid #E5E7EB', background: '#F9FAFB' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                        <span style={{ padding: '0.25rem 0.5rem', borderRadius: '0.25rem', background: '#667eea', color: 'white', fontWeight: '600', fontSize: '0.75rem' }}>{ep.method}</span>
                                        <span style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>{fullUrl}</span>
                                        {c.source === 'ai' ? (
                                            <span style={{ padding: '0.2rem 0.45rem', borderRadius: '0.25rem', background: '#DBEAFE', color: '#1D4ED8', fontSize: '0.7rem', fontWeight: '600' }}>大模型生成</span>
                                        ) : (
                                            <span style={{ padding: '0.2rem 0.45rem', borderRadius: '0.25rem', background: '#F3F4F6', color: '#6B7280', fontSize: '0.7rem' }}>规则生成</span>
                                        )}
                                    </div>
                                    <button type="button" onClick={() => setSelectedCaseDetail(null)} style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem', border: '1px solid #E5E7EB', borderRadius: '0.375rem', background: 'white', cursor: 'pointer' }}>关闭</button>
                                </div>
                                <div style={{ padding: '0 1rem', borderBottom: '1px solid #E5E7EB' }}>
                                    <div style={{ display: 'flex', gap: '0.5rem' }}>{tab('请求', 'request')}{tab('响应', 'response')}{tab('期望', 'expected')}</div>
                                </div>
                                {caseDetailMainTab === 'request' && (
                                    <>
                                        <div style={{ display: 'flex', gap: '0.25rem', padding: '0.5rem 1rem 0', borderBottom: '1px solid #E5E7EB', fontSize: '0.8rem' }}>
                                            {subTab('Params', 'params', Object.keys(rt.url_params || {}).length)}
                                            {subTab('Body', 'body', Object.keys(rt.params || {}).length)}
                                            {subTab('Headers', 'headers', Object.keys(rt.headers || {}).length)}
                                            {subTab('Cookies', 'cookies', Object.keys(rt.cookies || {}).length)}
                                        </div>
                                        <div style={{ padding: '1rem', minHeight: '120px', background: '#fff' }}>
                                            {caseDetailSubTab === 'params' && (
                                                Object.keys(rt.url_params || {}).length > 0
                                                    ? keyValueTable(rt.url_params as Record<string, unknown>)
                                                    : <div style={{ color: '#9CA3AF', fontSize: '0.875rem' }}>无 URL 参数</div>
                                            )}
                                            {caseDetailSubTab === 'body' && (
                                                <div>
                                                    <div style={{ marginBottom: '0.5rem', fontSize: '0.75rem', color: '#6B7280' }}>raw · JSON</div>
                                                    <pre style={{ margin: 0, padding: '0.75rem', background: '#1e1e1e', color: '#d4d4d4', borderRadius: '0.5rem', overflow: 'auto', fontSize: '0.8rem', fontFamily: 'ui-monospace, monospace', minHeight: '100px' }}>
                                                        {bodyJson || '{}'}
                                                    </pre>
                                                </div>
                                            )}
                                            {caseDetailSubTab === 'headers' && (
                                                Object.keys(rt.headers || {}).length > 0
                                                    ? keyValueTable(rt.headers as Record<string, unknown>)
                                                    : <div style={{ color: '#9CA3AF', fontSize: '0.875rem' }}>无请求头</div>
                                            )}
                                            {caseDetailSubTab === 'cookies' && (
                                                Object.keys(rt.cookies || {}).length > 0
                                                    ? keyValueTable(rt.cookies as Record<string, unknown>)
                                                    : <div style={{ color: '#9CA3AF', fontSize: '0.875rem' }}>无 Cookies</div>
                                            )}
                                        </div>
                                    </>
                                )}
                                {caseDetailMainTab === 'response' && (() => {
                                    const ei = plan?.endpoints?.findIndex((e: any) => e === ep) ?? -1
                                    const ci = ep?.cases?.findIndex((c2: any) => c2 === c) ?? -1
                                    const caseKey = ei >= 0 && ci >= 0 ? `${ei}-${ci}` : ''
                                    const runData = caseKey ? singleRunResult[caseKey] : null
                                    if (runData && (runData.response !== undefined || runData.error || runData.status_code != null)) {
                                        return (
                                            <div style={{ padding: '1rem' }}>
                                                <div style={{ marginBottom: '0.5rem' }}><span style={{ color: '#6B7280', fontSize: '0.875rem' }}>状态码</span><span style={{ marginLeft: '0.5rem', fontWeight: '600' }}>{runData.status_code ?? '-'}</span> {runData.status === 'passed' ? <span style={{ color: '#10B981' }}>通过</span> : runData.status === 'failed' ? <span style={{ color: '#EF4444' }}>失败</span> : null}</div>
                                                {runData.error && <div style={{ color: '#EF4444', marginBottom: '0.5rem', fontSize: '0.875rem' }}>错误：{runData.error}</div>}
                                                {runData.response !== undefined && runData.response !== null && (
                                                    <div><span style={{ color: '#6B7280', fontSize: '0.75rem' }}>响应体</span>
                                                        <pre style={{ margin: '0.25rem 0 0', padding: '0.75rem', background: '#1e1e1e', color: '#d4d4d4', borderRadius: '0.5rem', overflow: 'auto', fontSize: '0.8rem', fontFamily: 'ui-monospace, monospace', maxHeight: '280px' }}>{typeof runData.response === 'string' ? runData.response : JSON.stringify(runData.response, null, 2)}</pre>
                                                    </div>
                                                )}
                                                {runData.response == null && !runData.error && <div style={{ color: '#9CA3AF', fontSize: '0.875rem' }}>无响应体</div>}
                                            </div>
                                        )
                                    }
                                    return (
                                        <div style={{ padding: '1rem', color: '#6B7280', fontSize: '0.875rem' }}>
                                            请点击该用例行的「执行」按钮后，在此处可查看响应；或执行完整计划后在「执行明细」中点击某一步查看请求与响应。
                                        </div>
                                    )
                                })()}
                                {caseDetailMainTab === 'expected' && (
                                    <div style={{ padding: '1rem' }}>
                                        <div style={{ marginBottom: '0.5rem' }}><span style={{ color: '#6B7280', fontSize: '0.875rem' }}>状态码</span><span style={{ marginLeft: '0.5rem', fontWeight: '600' }}>{et.status_code ?? '-'}</span></div>
                                        {et.description && <div style={{ fontSize: '0.875rem', color: '#374151' }}>{et.description}</div>}
                                        <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: '#6B7280' }}>用例类型：{c.case_type ?? '-'} · 名称：{c.name ?? '-'}</div>
                                    </div>
                                )}
                            </div>
                        )
                    })()}
                </div>
            )}
        </div>
    )
}
