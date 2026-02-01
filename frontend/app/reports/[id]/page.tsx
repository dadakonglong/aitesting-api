'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { CheckCircle, XCircle, FileText, BarChart2, AlertTriangle, Lightbulb, ChevronRight, ChevronDown } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_AI_API_URL || 'http://localhost:8000'

const STEP_DETAIL_TABS = ['responseBody', 'responseHeaders', 'assertions', 'extraction', 'requestContent'] as const
type StepDetailTab = (typeof STEP_DETAIL_TABS)[number]
const STEP_TAB_LABELS: Record<StepDetailTab, string> = {
    responseBody: '响应体',
    responseHeaders: '响应头',
    assertions: '断言',
    extraction: '提取',
    requestContent: '请求内容',
}

/** 格式化 JSON 显示，带行号 */
function JsonWithLines({ data, maxHeight = 300 }: { data: any; maxHeight?: number }) {
    let str = ''
    try {
        str = typeof data === 'object' ? JSON.stringify(data, null, 2) : String(data ?? '')
    } catch {
        str = String(data)
    }
    const lines = str.split('\n')
    return (
        <div style={{ display: 'flex', fontFamily: 'ui-monospace, monospace', fontSize: '0.8125rem', background: '#1E293B', color: '#E2E8F0', borderRadius: '0.375rem', overflow: 'auto', maxHeight: `${maxHeight}px` }}>
            <div style={{ padding: '0.5rem 0.75rem', background: '#334155', color: '#94A3B8', minWidth: '2.5rem', userSelect: 'none', textAlign: 'right' }}>
                {lines.map((_, i) => (
                    <div key={i} style={{ lineHeight: 1.5 }}>{i + 1}</div>
                ))}
            </div>
            <pre style={{ margin: 0, padding: '0.5rem 0.75rem', flex: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-all', lineHeight: 1.5 }}>{str}</pre>
        </div>
    )
}

export default function ReportDetailPage() {
    const params = useParams()
    const id = params?.id as string
    const [report, setReport] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [activeTab, setActiveTab] = useState<'all' | 'failed' | 'summary'>('all')
    const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())
    const [stepDetailTab, setStepDetailTab] = useState<Record<number, StepDetailTab>>({})

    useEffect(() => {
        if (!id) return
        const load = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/v1/test-reports/${id}`)
                if (res.ok) setReport(await res.json())
                else setReport(null)
            } catch {
                setReport(null)
            } finally {
                setLoading(false)
            }
        }
        load()
    }, [id])

    if (loading) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#6B7280' }}>加载中...</div>
        )
    }
    if (!report) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <p style={{ color: '#EF4444', marginBottom: '1rem' }}>报告不存在</p>
                <Link href="/reports" style={{ color: '#667eea', textDecoration: 'underline' }}>返回报告列表</Link>
            </div>
        )
    }

    const payload = report.payload || {}
    const phase4 = payload.phase4_result || {}
    const phase5 = payload.phase5_report || ''
    const chartData = payload.phase5_chart_data || {}
    const summary = chartData.summary || phase4
    const total = summary.total ?? phase4.total_cases ?? 0
    const passed = summary.passed ?? phase4.passed_cases ?? 0
    const failed = summary.failed ?? phase4.failed_cases ?? 0
    const durationMs = summary.duration_ms ?? phase4.duration_ms ?? 0
    const results = phase4.results || phase4.case_results || []
    const failedResults = results.filter((r: any) => !r.success)
    const failurePct = total > 0 ? Math.round((failed / total) * 100) : 0

    const phase2 = payload.phase2_plan || {}
    const allCases = (phase2.endpoints || []).flatMap((ep: any) => (ep.cases || []).map((c: any) => c.name || ''))
    const getStepCaseName = (idx: number) => allCases[idx] || `步骤 ${(results[idx]?.step_order ?? idx) + 1}`

    const getStepTab = (idx: number) => stepDetailTab[idx] || 'responseBody'
    const setStepTab = (idx: number, tab: StepDetailTab) => setStepDetailTab((p) => ({ ...p, [idx]: tab }))

    const planCases = (phase2.endpoints || []).flatMap((ep: any) => ep.cases || [])
    const getStepData = (r: any, idx: number) => {
        const planCase = planCases[idx] || null
        const rt = planCase?.request_template || {}
        return {
            requestData: r?.request_data ?? r?.params ?? rt?.params ?? {},
            urlParams: r?.url_params ?? r?.query ?? rt?.url_params ?? {},
            requestHeaders: r?.request_headers ?? r?.headers ?? rt?.headers ?? {},
            response: r?.response,
            responseHeaders: r?.response_headers ?? r?.responseHeaders ?? {},
            extractions: r?.extractions ?? [],
            fullUrl: r?.full_url ?? r?.url ?? '',
            method: r?.api_method ?? r?.method ?? 'GET',
        }
    }

    const toggleStep = (idx: number) => {
        setExpandedSteps((prev) => {
            const next = new Set(prev)
            if (next.has(idx)) next.delete(idx)
            else next.add(idx)
            return next
        })
    }

    return (
        <div style={{ padding: '2rem', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', minHeight: '100vh' }}>
            <div style={{ background: 'rgba(255,255,255,0.98)', borderRadius: '1rem', padding: '2rem', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}>
                {/* 标题与时间 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '2rem' }}>
                    <div>
                        <h1 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#111827', marginBottom: '0.5rem' }}>{report.name}</h1>
                        <div style={{ fontSize: '0.875rem', color: '#6B7280' }}>
                            开始时间: {report.created_at || '-'} · 结束时间: {report.end_time || report.created_at || '-'}
                        </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <Link
                            href="/reports"
                            style={{
                                padding: '0.5rem 1rem',
                                background: '#F3F4F6',
                                color: '#374151',
                                borderRadius: '0.5rem',
                                textDecoration: 'none',
                                fontWeight: '500',
                                fontSize: '0.875rem',
                            }}
                        >
                            取消
                        </Link>
                        <button
                            type="button"
                            onClick={() => alert('分享功能开发中')}
                            style={{
                                padding: '0.5rem 1rem',
                                background: '#FEE2E2',
                                color: '#DC2626',
                                borderRadius: '0.5rem',
                                border: 'none',
                                fontWeight: '500',
                                fontSize: '0.875rem',
                                cursor: 'pointer',
                            }}
                        >
                            分享报告
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                const blob = new Blob([phase5 || '暂无报告内容'], { type: 'text/markdown' })
                                const url = URL.createObjectURL(blob)
                                const a = document.createElement('a')
                                a.href = url
                                a.download = `${report.name}.md`
                                a.click()
                                URL.revokeObjectURL(url)
                            }}
                            style={{
                                padding: '0.5rem 1rem',
                                background: 'linear-gradient(135deg, #667eea, #764ba2)',
                                color: 'white',
                                borderRadius: '0.5rem',
                                border: 'none',
                                fontWeight: '500',
                                fontSize: '0.875rem',
                                cursor: 'pointer',
                            }}
                        >
                            导出报告
                        </button>
                    </div>
                </div>

                {/* 核心指标与图表 */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', marginBottom: '2rem', alignItems: 'flex-start' }}>
                    <div style={{ minWidth: '100px' }}>
                        <div style={{ fontSize: '2rem', fontWeight: '700', color: '#111827' }}>{durationMs}ms</div>
                        <div style={{ fontSize: '0.75rem', color: '#6B7280' }}>响应时间</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{ position: 'relative', width: '100px', height: '100px' }}>
                            <svg viewBox="0 0 36 36" style={{ width: '100px', height: '100px', transform: 'rotate(-90deg)' }}>
                                <path
                                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                    fill="none"
                                    stroke="#E5E7EB"
                                    strokeWidth="3"
                                />
                                {total > 0 && (
                                    <>
                                        <path
                                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                            fill="none"
                                            stroke="#10B981"
                                            strokeWidth="3"
                                            strokeDasharray={`${(passed / total) * 100} ${100 - (passed / total) * 100}`}
                                            strokeDashoffset="0"
                                        />
                                        <path
                                            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                            fill="none"
                                            stroke="#EF4444"
                                            strokeWidth="3"
                                            strokeDasharray={`${(failed / total) * 100} ${100 - (failed / total) * 100}`}
                                            strokeDashoffset={-(passed / total) * 100}
                                        />
                                    </>
                                )}
                            </svg>
                            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center', fontSize: '0.75rem', fontWeight: '600' }}>
                                {total} 请求
                            </div>
                        </div>
                        <div style={{ fontSize: '0.875rem' }}>
                            <span style={{ color: '#10B981' }}>● {passed} 成功</span>
                            <span style={{ color: '#EF4444', marginLeft: '0.5rem' }}>● {failed} 失败</span>
                        </div>
                    </div>
                    <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontSize: '0.875rem', color: '#6B7280' }}>步骤:</span>
                            <span style={{ fontWeight: '600' }}>{total}</span>
                            <span style={{ color: '#10B981', fontSize: '0.8rem' }}>{passed} 成功</span>
                            <span style={{ color: '#EF4444', fontSize: '0.8rem' }}>{failed} 失败</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <AlertTriangle size={16} color="#F59E0B" />
                            <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>{failurePct}% 失败</span>
                        </div>
                    </div>
                </div>

                {/* 标签页 */}
                <div style={{ borderBottom: '2px solid #E5E7EB', marginBottom: '1rem' }}>
                    <div style={{ display: 'flex', gap: '1.5rem' }}>
                        {(['all', 'failed', 'summary'] as const).map((tab) => (
                            <button
                                key={tab}
                                type="button"
                                onClick={() => setActiveTab(tab)}
                                style={{
                                    padding: '0.5rem 0',
                                    border: 'none',
                                    background: 'none',
                                    cursor: 'pointer',
                                    fontWeight: '600',
                                    fontSize: '0.875rem',
                                    color: activeTab === tab ? '#667eea' : '#6B7280',
                                    borderBottom: activeTab === tab ? '2px solid #667eea' : '2px solid transparent',
                                    marginBottom: '-2px',
                                }}
                            >
                                {tab === 'all' ? '全部' : tab === 'failed' ? '失败' : '测试摘要'}
                            </button>
                        ))}
                    </div>
                </div>

                {/* 步骤列表 */}
                {activeTab === 'all' && (
                    <div style={{ marginBottom: '2rem' }}>
                        {results.length === 0 ? (
                            <p style={{ color: '#6B7280' }}>暂无步骤数据</p>
                        ) : (
                            results.map((r: any, i: number) => {
                                const isFailed = !r.success
                                const isExpanded = expandedSteps.has(i)
                                return (
                                    <div
                                        key={i}
                                        style={{
                                            border: '1px solid #E5E7EB',
                                            borderRadius: '0.5rem',
                                            marginBottom: '0.5rem',
                                            overflow: 'hidden',
                                            background: isFailed ? '#FEF2F2' : 'white',
                                        }}
                                    >
                                        <button
                                            type="button"
                                            onClick={() => toggleStep(i)}
                                            style={{
                                                width: '100%',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'space-between',
                                                padding: '0.75rem 1rem',
                                                border: 'none',
                                                background: 'none',
                                                cursor: 'pointer',
                                                textAlign: 'left',
                                                fontSize: '0.875rem',
                                            }}
                                        >
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                                <span style={{ fontWeight: '500' }}>① {isFailed ? '' : '√'}{getStepCaseName(i)}</span>
                                                {isFailed ? <XCircle size={18} color="#EF4444" /> : <CheckCircle size={18} color="#10B981" />}
                                            </span>
                                            <span style={{ color: isFailed ? '#EF4444' : '#10B981', fontWeight: '500' }}>
                                                {isFailed ? '失败' : '成功'}
                                            </span>
                                        </button>
                                        {isExpanded && (
                                            <div style={{ padding: '1rem', borderTop: '1px solid #E5E7EB', background: '#F9FAFB' }}>
                                                <div style={{ marginBottom: '1rem', padding: '1rem', background: 'white', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                                                    {(() => {
                                                    const d = getStepData(r, i)
                                                    const hasRequestContent = (d.urlParams && Object.keys(d.urlParams).length > 0) || (d.requestData && Object.keys(d.requestData).length > 0) || (d.requestHeaders && Object.keys(d.requestHeaders).length > 0)
                                                    return (
                                                        <>
                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                                                        <span style={{ fontWeight: '700', color: '#3B82F6', fontSize: '0.875rem' }}>{d.method}</span>
                                                        <span style={{ fontSize: '0.8125rem', color: '#374151', wordBreak: 'break-all', flex: 1 }}>{d.fullUrl || `${d.method} ${r.api_path || r.url || ''}`}</span>
                                                    </div>
                                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', fontSize: '0.8125rem', color: '#6B7280', marginBottom: '0.5rem' }}>
                                                        <span>开始时间: {report.created_at || '-'}</span>
                                                        <span>结束时间: {report.end_time || report.created_at || '-'}</span>
                                                        <span style={{ color: (r.status_code ?? 200) < 400 ? '#10B981' : '#EF4444', fontWeight: '600' }}>HTTP {r.status_code ?? '-'}</span>
                                                        <span>{(r.response_size ?? (typeof r.response === 'string' ? r.response.length : r.response != null ? JSON.stringify(r.response).length : 0))} 字节</span>
                                                        <span style={{ padding: '0.2rem 0.5rem', borderRadius: '0.25rem', background: r.success ? '#D1FAE5' : '#FEE2E2', color: r.success ? '#065F46' : '#991B1B', fontWeight: '600' }}>{r.success ? '成功' : '失败'}</span>
                                                    </div>
                                                <div style={{ marginBottom: '0.5rem', display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                                                    {STEP_DETAIL_TABS.map((tab) => (
                                                        <button
                                                            key={tab}
                                                            type="button"
                                                            onClick={() => setStepTab(i, tab)}
                                                            style={{
                                                                padding: '0.35rem 0.75rem',
                                                                fontSize: '0.8125rem',
                                                                border: 'none',
                                                                borderRadius: '0.25rem',
                                                                cursor: 'pointer',
                                                                background: getStepTab(i) === tab ? '#667eea' : '#E5E7EB',
                                                                color: getStepTab(i) === tab ? 'white' : '#374151',
                                                                fontWeight: getStepTab(i) === tab ? '600' : '400',
                                                            }}
                                                        >
                                                            {STEP_TAB_LABELS[tab]}
                                                        </button>
                                                    ))}
                                                </div>
                                                <div style={{ minHeight: '120px' }}>
                                                    {getStepTab(i) === 'responseBody' && (
                                                        (d.response != null && d.response !== '') ? <JsonWithLines data={d.response} maxHeight={320} /> : <div style={{ padding: '1rem', color: '#6B7280' }}>暂无响应体（可能为旧版报告或数据未保存）</div>
                                                    )}
                                                    {getStepTab(i) === 'responseHeaders' && (
                                                        d.responseHeaders && Object.keys(d.responseHeaders).length > 0
                                                            ? <JsonWithLines data={d.responseHeaders} maxHeight={200} />
                                                            : <div style={{ padding: '1rem', color: '#6B7280' }}>暂无响应头</div>
                                                    )}
                                                    {getStepTab(i) === 'assertions' && (
                                                        <div style={{ padding: '1rem', color: '#6B7280', fontSize: '0.875rem' }}>
                                                            {r.success ? '✓ 状态码检查通过' : `✗ 状态码 ${r.status_code} 未通过（期望 2xx）`}
                                                        </div>
                                                    )}
                                                    {getStepTab(i) === 'extraction' && (
                                                        d.extractions && d.extractions.length > 0
                                                            ? <div style={{ overflowX: 'auto' }}>
                                                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                                                                    <thead><tr style={{ background: '#F3F4F6' }}><th style={{ padding: '0.5rem', textAlign: 'left' }}>目标字段</th><th style={{ padding: '0.5rem', textAlign: 'left' }}>来源步骤</th><th style={{ padding: '0.5rem', textAlign: 'left' }}>提取结果</th></tr></thead>
                                                                    <tbody>
                                                                        {d.extractions.map((ex: any, ei: number) => (
                                                                            <tr key={ei} style={{ borderTop: '1px solid #E5E7EB' }}>
                                                                                <td style={{ padding: '0.5rem' }}>{ex.to_field}</td>
                                                                                <td style={{ padding: '0.5rem' }}>步骤 {ex.from_step}</td>
                                                                                <td style={{ padding: '0.5rem' }}>{ex.success ? String(ex.extracted_value ?? '-') : (ex.error_msg || '失败')}</td>
                                                                            </tr>
                                                                        ))}
                                                                    </tbody>
                                                                </table>
                                                            </div>
                                                            : <div style={{ padding: '1rem', color: '#6B7280' }}>此步骤未从其他步骤提取数据</div>
                                                    )}
                                                    {getStepTab(i) === 'requestContent' && (
                                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                                            <div>
                                                                <div style={{ fontWeight: '600', marginBottom: '0.35rem', fontSize: '0.8125rem', color: '#374151' }}>请求地址</div>
                                                                <div style={{ fontSize: '0.8125rem', wordBreak: 'break-all', color: '#4B5563' }}>{d.fullUrl || `${d.method} ${r.api_path || r.url || '-'}`}</div>
                                                            </div>
                                                            {d.requestHeaders && Object.keys(d.requestHeaders).length > 0 && (
                                                                <div>
                                                                    <div style={{ fontWeight: '600', marginBottom: '0.35rem', fontSize: '0.8125rem', color: '#374151' }}>请求头</div>
                                                                    <JsonWithLines data={d.requestHeaders} maxHeight={150} />
                                                                </div>
                                                            )}
                                                            <div>
                                                                <div style={{ fontWeight: '600', marginBottom: '0.35rem', fontSize: '0.8125rem', color: '#374151' }}>Body / 参数</div>
                                                                {(d.requestData && Object.keys(d.requestData).length > 0) ? (
                                                                    <JsonWithLines data={d.requestData} maxHeight={200} />
                                                                ) : (d.urlParams && Object.keys(d.urlParams).length > 0) ? (
                                                                    <JsonWithLines data={d.urlParams} maxHeight={120} />
                                                                ) : (
                                                                    <div style={{ padding: '0.75rem', color: '#9CA3AF', fontSize: '0.8125rem' }}>{d.method === 'GET' ? 'GET 请求通常无 Body，参数在 URL 中' : '无请求体'}</div>
                                                                )}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                                        </>
                                                    )
                                                })()}
                                                </div>
                                                {r.error && <div style={{ marginTop: '0.75rem', color: '#EF4444', fontSize: '0.875rem' }}>{r.error}</div>}
                                            </div>
                                        )}
                                    </div>
                                )
                            })
                        )}
                    </div>
                )}

                {activeTab === 'failed' && (
                    <div style={{ marginBottom: '2rem' }}>
                        {failedResults.length === 0 ? (
                            <p style={{ color: '#10B981' }}>✓ 无失败用例</p>
                        ) : (
                            results.map((r: any, i: number) => {
                                if (r.success) return null
                                const isExpanded = expandedSteps.has(i)
                                return (
                                    <div key={i} style={{ border: '1px solid #FECACA', borderRadius: '0.5rem', marginBottom: '0.5rem', overflow: 'hidden', background: '#FEF2F2' }}>
                                        <button type="button" onClick={() => toggleStep(i)} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1rem', border: 'none', background: 'none', cursor: 'pointer', textAlign: 'left', fontSize: '0.875rem' }}>
                                            {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                            ① {getStepCaseName(i)} <XCircle size={18} color="#EF4444" />
                                        </button>
                                        {isExpanded && (() => {
                                            const d = getStepData(r, i)
                                            const hasReq = (d.urlParams && Object.keys(d.urlParams).length > 0) || (d.requestData && Object.keys(d.requestData).length > 0) || (d.requestHeaders && Object.keys(d.requestHeaders).length > 0)
                                            return (
                                            <div style={{ padding: '1rem', borderTop: '1px solid #FECACA' }}>
                                                <div style={{ marginBottom: '1rem', padding: '1rem', background: 'white', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                                                        <span style={{ fontWeight: '700', color: '#3B82F6', fontSize: '0.875rem' }}>{d.method}</span>
                                                        <span style={{ fontSize: '0.8125rem', color: '#374151', wordBreak: 'break-all', flex: 1 }}>{d.fullUrl || `${d.method} ${r.api_path || r.url || ''}`}</span>
                                                    </div>
                                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', fontSize: '0.8125rem', color: '#6B7280' }}>
                                                        <span style={{ color: '#EF4444', fontWeight: '600' }}>HTTP {r.status_code ?? '-'}</span>
                                                        <span style={{ padding: '0.2rem 0.5rem', borderRadius: '0.25rem', background: '#FEE2E2', color: '#991B1B', fontWeight: '600' }}>失败</span>
                                                    </div>
                                                </div>
                                                <div style={{ marginBottom: '0.5rem', display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                                                    {STEP_DETAIL_TABS.map((tab) => (
                                                        <button key={tab} type="button" onClick={() => setStepTab(i, tab)} style={{ padding: '0.35rem 0.75rem', fontSize: '0.8125rem', border: 'none', borderRadius: '0.25rem', cursor: 'pointer', background: getStepTab(i) === tab ? '#667eea' : '#E5E7EB', color: getStepTab(i) === tab ? 'white' : '#374151', fontWeight: getStepTab(i) === tab ? '600' : '400' }}>
                                                            {STEP_TAB_LABELS[tab]}
                                                        </button>
                                                    ))}
                                                </div>
                                                <div style={{ minHeight: '120px' }}>
                                                    {getStepTab(i) === 'responseBody' && (d.response != null && d.response !== '' ? <JsonWithLines data={d.response} maxHeight={320} /> : <div style={{ padding: '1rem', color: '#6B7280' }}>暂无响应体</div>)}
                                                    {getStepTab(i) === 'responseHeaders' && (d.responseHeaders && Object.keys(d.responseHeaders).length > 0 ? <JsonWithLines data={d.responseHeaders} maxHeight={200} /> : <div style={{ padding: '1rem', color: '#6B7280' }}>暂无响应头</div>)}
                                                    {getStepTab(i) === 'assertions' && <div style={{ padding: '1rem', color: '#6B7280' }}>状态码 {r.status_code} 未通过</div>}
                                                    {getStepTab(i) === 'extraction' && (d.extractions?.length > 0 ? <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}><thead><tr style={{ background: '#F3F4F6' }}><th style={{ padding: '0.5rem', textAlign: 'left' }}>目标字段</th><th style={{ padding: '0.5rem', textAlign: 'left' }}>来源步骤</th><th style={{ padding: '0.5rem', textAlign: 'left' }}>提取结果</th></tr></thead><tbody>{d.extractions.map((ex: any, ei: number) => <tr key={ei} style={{ borderTop: '1px solid #E5E7EB' }}><td style={{ padding: '0.5rem' }}>{ex.to_field}</td><td style={{ padding: '0.5rem' }}>步骤 {ex.from_step}</td><td style={{ padding: '0.5rem' }}>{ex.success ? String(ex.extracted_value ?? '-') : (ex.error_msg || '失败')}</td></tr>)}</tbody></table></div> : <div style={{ padding: '1rem', color: '#6B7280' }}>此步骤未从其他步骤提取数据</div>)}
                                                    {getStepTab(i) === 'requestContent' && (
                                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                                            <div>
                                                                <div style={{ fontWeight: '600', marginBottom: '0.35rem', fontSize: '0.8125rem' }}>请求地址</div>
                                                                <div style={{ fontSize: '0.8125rem', wordBreak: 'break-all' }}>{d.fullUrl || `${d.method} ${r.api_path || r.url || '-'}`}</div>
                                                            </div>
                                                            {d.requestHeaders && Object.keys(d.requestHeaders).length > 0 && (
                                                                <div><div style={{ fontWeight: '600', marginBottom: '0.35rem', fontSize: '0.8125rem' }}>请求头</div><JsonWithLines data={d.requestHeaders} maxHeight={150} /></div>
                                                            )}
                                                            <div>
                                                                <div style={{ fontWeight: '600', marginBottom: '0.35rem', fontSize: '0.8125rem' }}>Body / 参数</div>
                                                                {(d.requestData && Object.keys(d.requestData).length > 0) ? <JsonWithLines data={d.requestData} maxHeight={200} /> : (d.urlParams && Object.keys(d.urlParams).length > 0) ? <JsonWithLines data={d.urlParams} maxHeight={120} /> : <div style={{ padding: '0.75rem', color: '#9CA3AF', fontSize: '0.8125rem' }}>无请求体</div>}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                                {r.error && <div style={{ marginTop: '0.75rem', color: '#EF4444', fontSize: '0.875rem' }}>{r.error}</div>}
                                            </div>
                                            )
                                        })()}
                                    </div>
                                )
                            })
                        )}
                    </div>
                )}

                {activeTab === 'summary' && (
                    <div style={{ marginBottom: '2rem' }}>
                        <div style={{ display: 'grid', gap: '1.5rem' }}>
                            <div style={{ padding: '1rem', background: '#F9FAFB', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                                <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <FileText size={18} /> 测试摘要
                                </h3>
                                <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.875rem', lineHeight: 1.6 }}>{phase5 || '暂无摘要'}</div>
                            </div>
                            <div style={{ padding: '1rem', background: '#FFFBEB', borderRadius: '0.5rem', border: '1px solid #FDE68A' }}>
                                <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <AlertTriangle size={18} /> 失败分析
                                </h3>
                                <div style={{ fontSize: '0.875rem' }}>
                                    {failed > 0 ? `共 ${failed} 个用例失败，详见「失败」Tab 及上方报告摘要中的分析。` : '无失败用例。'}
                                </div>
                            </div>
                            <div style={{ padding: '1rem', background: '#ECFDF5', borderRadius: '0.5rem', border: '1px solid #A7F3D0' }}>
                                <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <Lightbulb size={18} /> 优化建议
                                </h3>
                                <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}>{phase5?.includes('建议') ? phase5 : '详见上方测试摘要中的建议部分。'}</div>
                            </div>
                        </div>
                    </div>
                )}

                {/* 底部报告全文（折叠或简化） */}
                {phase5 && activeTab !== 'summary' && (
                    <details style={{ marginTop: '2rem' }}>
                        <summary style={{ cursor: 'pointer', fontWeight: '600', color: '#6B7280', marginBottom: '0.5rem' }}>完整分析报告</summary>
                        <div style={{ padding: '1rem', background: '#F9FAFB', borderRadius: '0.5rem', whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}>{phase5}</div>
                    </details>
                )}
            </div>
        </div>
    )
}
