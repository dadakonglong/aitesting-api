'use client'

import { useState, useEffect } from 'react'
import {
    Loader2,
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    FileCode,
    Play,
    BarChart3,
    FileText,
    Trash2,
    List,
    CheckCircle,
    XCircle,
    AlertCircle,
    Wand2,
} from 'lucide-react'

const STEP_DETAIL_TABS = ['responseBody', 'responseHeaders', 'assertions', 'extraction', 'requestContent'] as const
type StepDetailTab = (typeof STEP_DETAIL_TABS)[number]
const STEP_TAB_LABELS: Record<StepDetailTab, string> = {
    responseBody: '响应体',
    responseHeaders: '响应头',
    assertions: '断言',
    extraction: '提取',
    requestContent: '请求内容',
}

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
import { useProject } from '../../contexts/ProjectContext'
import type { SingleApiCaseItem } from '../page'
import { getSingleApiDisplayName } from '../page'

interface EnvItem {
    id: number
    env_name: string
    base_url: string
    is_default?: number
}

type Props = {
    /** 已保存的单接口测试用例列表（不覆盖、按接口命名） */
    items: SingleApiCaseItem[]
    /** 当前选中的用例 id */
    selectedId: string | null
    /** 选中某条用例 */
    onSelect: (id: string | null) => void
    /** 再次执行并分析后更新某条用例的数据 */
    onResultChange: (id: string, data: any) => void
    /** 删除某条用例 */
    onDelete: (id: string) => void
}

/** 根据流水线结果生成 Agent 风格汇总文本 */
function formatAgentSummary(result: any): string {
    if (!result) return '暂无数据'
    const lines: string[] = ['开始处理任务...', '']

    // RAG Agent
    const s1 = result.phase1_structured
    const entities = s1?.entities || []
    const chunks = s1?.chunks || []
    const endpoints = result.phase2_plan?.endpoints || []
    const apiCount = endpoints.length || (chunks.length ? Math.min(chunks.length, 20) : 0)
    let moduleNames = [...new Set(entities.map((e: any) => e.entity_name || e.name || '').filter(Boolean))]
    if (moduleNames.length === 0 && endpoints.length > 0) {
        moduleNames = [...new Set(endpoints.map((ep: any) => {
            const s = (ep.summary || ep.name || ep.path || '').toString()
            const part = s.split(/[/\-_]/).filter(Boolean)[0] || s.slice(0, 8)
            return part || '接口'
        }).filter(Boolean))]
    }
    lines.push('检索 API 文档信息...')
    if (moduleNames.length > 0) {
        lines.push(`   ✓ 识别 ${moduleNames.length} 个相关实体：${moduleNames.slice(0, 5).join('、')}${moduleNames.length > 5 ? '...' : ''}`)
    } else if (entities.length > 0) {
        lines.push(`   ✓ 识别 ${entities.length} 个实体`)
    }
    lines.push(`   ✓ 提取 ${apiCount || (chunks.length || 1)} 个 API 端点`)
    const hasAuth = JSON.stringify(s1 || '').includes('认证') || JSON.stringify(chunks).toLowerCase().includes('auth')
    if (hasAuth) lines.push('   ✓ 识别认证机制')
    lines.push('')

    // Planner Agent
    const cases = endpoints.flatMap((ep: any) => ep.cases || [])
    const totalCases = cases.length
    const cat = (c: any) => (c.category || c.type || '').toLowerCase()
    const funcCases = cases.filter((c: any) => cat(c).includes('功能')).length
    const secCases = cases.filter((c: any) => cat(c).includes('安全')).length
    const intCases = cases.filter((c: any) => cat(c).includes('集成')).length
    const otherCases = totalCases - funcCases - secCases - intCases
    lines.push('生成测试计划...')
    if (funcCases > 0) lines.push(`   ✓ 功能测试：${funcCases} 个用例`)
    if (secCases > 0) lines.push(`   ✓ 安全测试：${secCases} 个用例`)
    if (intCases > 0) lines.push(`   ✓ 集成测试：${intCases} 个用例`)
    if (otherCases > 0) lines.push(`   ✓ 其他：${otherCases} 个用例`)
    if (totalCases > 0 && funcCases === 0 && secCases === 0 && intCases === 0 && otherCases === 0) {
        lines.push(`   ✓ 共 ${totalCases} 个用例`)
    }
    lines.push('')

    // Generator Agent
    const code = result.phase3_code || ''
    const specMatches = code.match(/test_[a-zA-Z0-9_]+\.spec\.ts/g) || code.match(/test_[a-zA-Z0-9_]+\.py/g) || []
    const uniqSpecs = [...new Set(specMatches)]
    const hasConftest = /conftest\.(py|ts|js)/.test(code)
    lines.push('生成测试代码...')
    uniqSpecs.forEach((f) => lines.push(`   ✓ 生成 ${f}`))
    if (uniqSpecs.length === 0 && code.trim()) lines.push('   ✓ 生成测试文件')
    if (hasConftest) lines.push('   ✓ 生成 conftest')
    if (!code.trim()) lines.push('   ✓ 待生成')
    lines.push('')

    // Executor Agent
    const r4 = result.phase4_result
    lines.push('执行测试...')
    lines.push('   ✓ 自动解析前置依赖（KG + AI）')
    if (r4) {
        const total = r4.total_cases ?? 0
        const passed = r4.passed_cases ?? 0
        const failed = r4.failed_cases ?? 0
        const dur = r4.duration_ms != null ? (r4.duration_ms / 1000).toFixed(1) : '-'
        lines.push(`   ✓ 执行 ${total} 个测试用例`)
        lines.push(`   ✓ 通过：${passed} 个`)
        lines.push(`   ✓ 失败：${failed} 个`)
        lines.push(`   ✓ 执行时间：${dur}s`)
    } else {
        lines.push('   ✓ 未执行（请配置接口基础地址后点击「再次执行并分析」）')
    }
    lines.push('')

    // Analyzer Agent
    const hasReport = result.phase5_report && String(result.phase5_report).trim()
    const hasChart = result.phase5_chart_data != null
    lines.push('生成报告...')
    if (hasReport) {
        lines.push('   ✓ 生成测试摘要')
        if (hasChart) lines.push('   ✓ 生成可视化图表')
        lines.push('   ✓ 分析失败原因')
        lines.push('   ✓ 提供优化建议')
    } else {
        lines.push('   ✓ 待生成（执行后可生成）')
    }
    lines.push('')
    lines.push('任务完成！')
    return lines.join('\n')
}

export default function SingleApiTestTab({
    items,
    selectedId,
    onSelect,
    onResultChange,
    onDelete,
}: Props) {
    const { currentProject } = useProject()
    const [execLoading, setExecLoading] = useState(false)
    const [stepsExpanded, setStepsExpanded] = useState(false) // 总折叠：默认不展开 5 步骤详情
    const [expanded, setExpanded] = useState<string | null>(null) // 当前展开的 phase
    const [phase4ExpandedSteps, setPhase4ExpandedSteps] = useState<Set<number>>(new Set())
    const [phase4StepDetailTab, setPhase4StepDetailTab] = useState<Record<number, StepDetailTab>>({})
    const [environments, setEnvironments] = useState<EnvItem[]>([])
    const [selectedEnvId, setSelectedEnvId] = useState<number | 'custom' | null>(null)
    /** 执行时使用的接口基础地址：从下拉选择或自定义输入 */
    const [execBaseUrl, setExecBaseUrl] = useState('')
    const [healAnalyzeLoading, setHealAnalyzeLoading] = useState(false)
    const [healAnalyzeResult, setHealAnalyzeResult] = useState<any>(null)
    const [healApplyLoading, setHealApplyLoading] = useState(false)
    const [healLog, setHealLog] = useState<string[]>([])

    useEffect(() => {
        const load = async () => {
            try {
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects/${encodeURIComponent(currentProject)}/environments`)
                if (!res.ok) return
                const data = await res.json()
                const list: EnvItem[] = Array.isArray(data) ? data : []
                setEnvironments(list)
                const defaultEnv = list.find((e) => e.is_default === 1)
                const first = list[0]
                if (defaultEnv) {
                    setSelectedEnvId(defaultEnv.id)
                    setExecBaseUrl(defaultEnv.base_url || '')
                } else if (first) {
                    setSelectedEnvId(first.id)
                    setExecBaseUrl(first.base_url || '')
                } else {
                    setSelectedEnvId(null)
                    setExecBaseUrl('')
                }
            } catch {
                setEnvironments([])
                setSelectedEnvId(null)
                setExecBaseUrl('')
            }
        }
        load()
    }, [currentProject])

    // 切换选中的用例时清空失败分析结果和修复日志，避免在别的用例上误显示
    useEffect(() => {
        setHealAnalyzeResult(null)
        setHealLog([])
    }, [selectedId])

    const selected = items.find((it) => it.id === selectedId)
    const result = selected?.data

    const handleExecuteAndAnalyze = async () => {
        if (!result?.phase2_plan?.endpoints?.length || !selectedId) {
            alert('当前无已生成的测试计划，请先在「AI生成」Tab 选择「接口测试」并生成')
            return
        }
        setExecLoading(true)
        setHealAnalyzeResult(null)
        try {
            const execRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/single-api/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: currentProject,
                    base_url: execBaseUrl.trim(),
                    environment: 'test',
                    plan: result.phase2_plan,
                    generated_code: result.phase3_code || undefined,
                }),
            })
            if (!execRes.ok) {
                const err = await execRes.json().catch(() => ({}))
                throw new Error(err.detail || err.message || '执行失败')
            }
            const suiteResult = await execRes.json()

            const analyzeRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/single-api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ suite_result: suiteResult }),
            })
            if (!analyzeRes.ok) {
                onResultChange(selectedId, {
                    ...result,
                    phase4_result: suiteResult,
                    phase5_report: null,
                    phase5_chart_data: null,
                })
                return
            }
            const analyzeData = await analyzeRes.json()
            const newData = {
                ...result,
                phase4_result: suiteResult,
                phase5_report: analyzeData.report ?? null,
                phase5_chart_data: analyzeData.chart_data ?? null,
            }
            onResultChange(selectedId, newData)

            const now = new Date()
            const year = now.getFullYear()
            const month = String(now.getMonth() + 1).padStart(2, '0')
            const day = String(now.getDate()).padStart(2, '0')
            const hour = String(now.getHours()).padStart(2, '0')
            const minute = String(now.getMinutes()).padStart(2, '0')
            const second = String(now.getSeconds()).padStart(2, '0')
            const timeStr = `${year}-${month}-${day} ${hour}:${minute}:${second}`
            const reportName = `${getSingleApiDisplayName(newData)}-${timeStr}`
            try {
                await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/test-reports`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: currentProject,
                        name: reportName,
                        report_type: '接口测试',
                        trigger_method: '手动触发',
                        status: suiteResult.failed_cases > 0 ? 'error' : 'success',
                        payload: { phase2_plan: newData.phase2_plan, phase4_result: suiteResult, phase5_report: analyzeData.report, phase5_chart_data: analyzeData.chart_data },
                    }),
                })
            } catch (_e) {
                /* 保存报告失败不影响主流程 */
            }
            setExpanded('phase4')
            setStepsExpanded(true)
        } catch (error: any) {
            alert(`错误: ${error.message}`)
        } finally {
            setExecLoading(false)
        }
    }

    const handleDelete = () => {
        if (!selectedId) return
        if (!confirm(`确定删除「${selected?.name ?? '该用例'}」吗？`)) return
        onDelete(selectedId)
    }

    const runHealAnalyze = async () => {
        const execId = result?.phase4_result?.execution_id
        if (!execId) {
            alert('请先执行用例后再进行失败分析（需有执行记录）')
            return
        }
        setHealAnalyzeLoading(true)
        setHealAnalyzeResult(null)
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/heal/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ execution_id: execId }),
            })
            const data = await res.json()
            setHealAnalyzeResult(data)
        } catch (e: any) {
            alert(e?.message || '分析失败')
        } finally {
            setHealAnalyzeLoading(false)
        }
    }

    const runHealApplySingleApi = async () => {
        const execId = result?.phase4_result?.execution_id
        const plan = result?.phase2_plan
        if (!execId || !plan) {
            alert('请先执行用例后再使用一键修复')
            return
        }
        setHealApplyLoading(true)
        setHealLog(['🔍 API Healer：分析失败原因...'])
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/heal/apply-single-api-plan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ execution_id: execId, plan }),
            })
            const data = await res.json()
            if (!res.ok) throw new Error(data.detail || '修复失败')

            const log: string[] = ['🔍 API Healer：分析失败原因...']
            const analyses: any[] = data.analysis?.analysis || []
            analyses.forEach((a: any, i: number) => {
                if (a.failure_type) log.push(`   ✓ 识别问题 ${analyses.length > 1 ? `#${i + 1}` : ''}：${a.failure_type}`)
                if (a.root_cause) log.push(`   ✓ 根本原因：${a.root_cause}`)
                if (a.patch_hint) log.push(`   ✓ 修复提示：${a.patch_hint}`)
            })
            if (!analyses.length && data.analysis?.message) {
                log.push(`   ${data.analysis.message}`)
            }
            log.push('')

            if (data.status === 'healed') {
                log.push('🛠️ API Healer：生成修复方案...')
                const actions: Record<string, string> = data.heal_actions || {}
                analyses.forEach((a: any, i: number) => {
                    const action = actions[String(i)]
                    if (action === 'fix_request') {
                        log.push(`   ✓ 修复策略：修正请求参数（健壮用例缺字段校验，删除多余字段）`)
                    } else if (a.suggested_fix) {
                        log.push(`   ✓ 修复策略：${a.suggested_fix}`)
                    }
                    if (a.can_heal) log.push(`   ✓ 置信度：高`)
                })
                log.push('')
                log.push('✅ API Healer：应用修复...')
                log.push('   ✓ 更新测试用例计划')
                log.push('   ✓ 修复完成，请重新执行验证')
                setHealLog(log)
                onResultChange(selectedId!, { ...result, phase2_plan: data.healed_plan })
            } else if (data.status === 'cannot_heal') {
                const isBug = (data.message || '').includes('接口自身的 Bug') || (data.message || '').includes('未做校验')
                log.push(isBug ? '🐛 API Healer：发现接口 Bug' : '⚠️ API Healer：无法自动修复')
                const msgLines = (data.message || '失败原因需要人工介入').split('\n')
                msgLines.forEach((l: string) => log.push(`   ${l}`))
                setHealLog(log)
            } else {
                log.push('⚠️ API Healer：无法自动修复')
                log.push(`   ${data.message || '失败原因需要人工介入'}`)
                setHealLog(log)
            }
        } catch (e: any) {
            setHealLog(['🔍 API Healer：分析失败原因...', '', `❌ 请求失败：${e?.message || '未知错误'}`])
        } finally {
            setHealApplyLoading(false)
        }
    }

    const toggle = (phase: string) => setExpanded((p) => (p === phase ? null : phase))
    const phase1Doc = result?.phase1_structured
        ? (() => {
            const s = result.phase1_structured
            const intent = s.intent || ''
            const entities = s.entities || []
            const chunks = s.chunks || []
            const lines: string[] = []
            if (intent) lines.push('意图\n' + intent)
            if (entities.length) {
                lines.push('\n实体')
                entities.forEach((e: any) => {
                    const name = e.entity_name || e.name || ''
                    const type = e.entity_type || e.type || ''
                    const desc = e.description || ''
                    lines.push(`• ${name}（${type}）${desc ? '：' + desc : ''}`)
                })
            }
            if (chunks.length) {
                lines.push('\n接口/文本信息')
                chunks.forEach((c: any, i: number) => {
                    const content = typeof c === 'string' ? c : (c.content || '')
                    if (content) lines.push(`${i + 1}. ${content}`)
                })
            }
            return lines.join('\n') || '暂无结构化内容'
        })()
        : '暂无'
    const hasCode =
        result?.phase3_code &&
        String(result.phase3_code).trim() &&
        !/^[\s\{\[\]]*$/.test(String(result.phase3_code))
    const phaseTitle = (id: string, label: string, icon: React.ReactNode) => (
        <button
            type="button"
            onClick={() => toggle(id)}
            style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                width: '100%',
                padding: '0.75rem 1rem',
                background: '#F3F4F6',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontWeight: '600',
                color: '#1F2937',
                textAlign: 'left',
            }}
        >
            {expanded === id ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            {icon}
            {label}
        </button>
    )

    if (items.length === 0) {
        return (
            <div
                style={{
                    padding: '3rem 2rem',
                    textAlign: 'center',
                    background: '#F9FAFB',
                    borderRadius: '0.75rem',
                    color: '#6B7280',
                    fontSize: '0.9375rem',
                }}
            >
                <p style={{ marginBottom: '0.5rem' }}>暂无接口用例</p>
                <p style={{ fontSize: '0.875rem' }}>
                    请先在「AI生成」Tab 选择「接口测试」并生成，新生成的用例会追加到此处，不会删除之前的记录
                </p>
            </div>
        )
    }

    return (
        <div style={{ display: 'flex', gap: '1rem', minHeight: '400px' }}>
            {/* 左侧：用例列表 */}
            <div
                style={{
                    width: '240px',
                    flexShrink: 0,
                    background: '#F9FAFB',
                    borderRadius: '0.5rem',
                    padding: '0.75rem',
                    border: '1px solid #E5E7EB',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', fontWeight: '600', color: '#374151' }}>
                    <List size={18} />
                    接口测试用例
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    {items.map((it) => (
                        <button
                            key={it.id}
                            type="button"
                            onClick={() => onSelect(it.id)}
                            style={{
                                padding: '0.5rem 0.75rem',
                                textAlign: 'left',
                                borderRadius: '0.375rem',
                                border: 'none',
                                background: selectedId === it.id ? '#E0E7FF' : 'transparent',
                                color: selectedId === it.id ? '#4338CA' : '#4B5563',
                                fontWeight: selectedId === it.id ? '600' : '400',
                                cursor: 'pointer',
                                fontSize: '0.875rem',
                            }}
                        >
                            {it.name}
                        </button>
                    ))}
                </div>
            </div>

            {/* 右侧：选中用例详情 */}
            <div style={{ flex: 1, minWidth: 0 }}>
                {!selected ? (
                    <div
                        style={{
                            padding: '2rem',
                            textAlign: 'center',
                            background: '#F9FAFB',
                            borderRadius: '0.75rem',
                            color: '#6B7280',
                            fontSize: '0.9375rem',
                        }}
                    >
                        请从左侧选择一条用例查看
                    </div>
                ) : (
                    <div
                        style={{
                            background: 'white',
                            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                            borderRadius: '0.5rem',
                            padding: '1.5rem',
                        }}
                    >
                        <div
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                marginBottom: '1rem',
                                flexWrap: 'wrap',
                                gap: '0.75rem',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                                <CheckCircle2 style={{ color: '#10B981', marginRight: '0.5rem' }} size={24} />
                                <h2 style={{ fontSize: '1.25rem', fontWeight: '700', color: '#111827' }}>
                                    {selected.name}
                                </h2>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                {result?.phase2_plan?.endpoints?.length > 0 && (
                                    <>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                            <label style={{ fontSize: '0.875rem', color: '#374151', whiteSpace: 'nowrap' }}>
                                                接口基础地址：
                                            </label>
                                            {environments.length > 0 ? (
                                                <>
                                                    <select
                                                        value={selectedEnvId === 'custom' ? 'custom' : (selectedEnvId ?? '')}
                                                        onChange={(e) => {
                                                            const v = e.target.value
                                                            if (v === 'custom') {
                                                                setSelectedEnvId('custom')
                                                                setExecBaseUrl('')
                                                            } else {
                                                                const id = Number(v)
                                                                const env = environments.find((ep) => ep.id === id)
                                                                if (env) {
                                                                    setSelectedEnvId(id)
                                                                    setExecBaseUrl(env.base_url || '')
                                                                }
                                                            }
                                                        }}
                                                        style={{
                                                            minWidth: '200px',
                                                            padding: '0.5rem 0.75rem',
                                                            border: '1px solid #D1D5DB',
                                                            borderRadius: '0.5rem',
                                                            fontSize: '0.875rem',
                                                            background: 'white',
                                                        }}
                                                    >
                                                        {environments.map((env) => (
                                                            <option key={env.id} value={env.id}>
                                                                {env.env_name} — {env.base_url}
                                                            </option>
                                                        ))}
                                                        <option value="custom">自定义输入...</option>
                                                    </select>
                                                    {selectedEnvId === 'custom' && (
                                                        <input
                                                            type="text"
                                                            value={execBaseUrl}
                                                            onChange={(e) => setExecBaseUrl(e.target.value)}
                                                            placeholder="如 https://api.example.com"
                                                            style={{
                                                                width: '280px',
                                                                padding: '0.5rem 0.75rem',
                                                                border: '1px solid #D1D5DB',
                                                                borderRadius: '0.5rem',
                                                                fontSize: '0.875rem',
                                                            }}
                                                        />
                                                    )}
                                                </>
                                            ) : (
                                                <input
                                                    type="text"
                                                    value={execBaseUrl}
                                                    onChange={(e) => setExecBaseUrl(e.target.value)}
                                                    placeholder="如 https://api.example.com，或在项目设置中配置环境"
                                                    style={{
                                                        width: '280px',
                                                        padding: '0.5rem 0.75rem',
                                                        border: '1px solid #D1D5DB',
                                                        borderRadius: '0.5rem',
                                                        fontSize: '0.875rem',
                                                    }}
                                                />
                                            )}
                                        </div>
                                        <button
                                            type="button"
                                            onClick={handleExecuteAndAnalyze}
                                            disabled={execLoading}
                                            style={{
                                                padding: '0.5rem 1rem',
                                                background: execLoading
                                                    ? '#9CA3AF'
                                                    : 'linear-gradient(to right, #10B981, #059669)',
                                                color: 'white',
                                                fontWeight: '600',
                                                borderRadius: '0.5rem',
                                                border: 'none',
                                                cursor: execLoading ? 'not-allowed' : 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                            }}
                                        >
                                            {execLoading ? (
                                                <Loader2 className="animate-spin" size={18} />
                                            ) : (
                                                <Play size={18} />
                                            )}
                                            {execLoading ? '执行中...' : '再次执行并分析'}
                                        </button>
                                    </>
                                )}
                                <button
                                    type="button"
                                    onClick={handleDelete}
                                    title="删除该用例"
                                    style={{
                                        padding: '0.5rem 0.75rem',
                                        background: '#FEE2E2',
                                        color: '#DC2626',
                                        fontWeight: '500',
                                        borderRadius: '0.5rem',
                                        border: 'none',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.25rem',
                                    }}
                                >
                                    <Trash2 size={18} />
                                    删除
                                </button>
                            </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            {/* Agent 风格汇总（默认展示） */}
                            <div
                                style={{
                                    padding: '1rem',
                                    background: '#F9FAFB',
                                    borderRadius: '0.5rem',
                                    fontSize: '0.875rem',
                                    color: '#374151',
                                    whiteSpace: 'pre-wrap',
                                    lineHeight: 1.8,
                                    fontFamily: 'ui-monospace, monospace',
                                }}
                            >
                                {formatAgentSummary(result)}
                            </div>
                            {/* 总折叠按钮：点击展开 5 步骤详情 */}
                            <button
                                type="button"
                                onClick={() => setStepsExpanded((v) => !v)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0.5rem 1rem',
                                    background: '#E5E7EB',
                                    border: 'none',
                                    borderRadius: '0.5rem',
                                    cursor: 'pointer',
                                    fontWeight: '600',
                                    color: '#4B5563',
                                    fontSize: '0.875rem',
                                }}
                            >
                                {stepsExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                {stepsExpanded ? '收起步骤详情' : '展开 5 个步骤详情'}
                            </button>
                            {/* 5 步骤详情（折叠时不展示） */}
                            {stepsExpanded && (
                                <>
                                    <div>
                                        {phaseTitle('phase1', '1️⃣ 接口分析', <FileText size={18} />)}
                                        {expanded === 'phase1' && (
                                            <div
                                                style={{
                                                    marginTop: '0.5rem',
                                                    padding: '1rem',
                                                    background: '#F9FAFB',
                                                    borderRadius: '0.375rem',
                                                    fontSize: '0.875rem',
                                                    color: '#374151',
                                                    whiteSpace: 'pre-wrap',
                                                    lineHeight: 1.6,
                                                }}
                                            >
                                                {phase1Doc}
                                            </div>
                                        )}
                                    </div>
                                    <div>
                                        {phaseTitle('phase2', '2️⃣ 测试计划', <FileCode size={18} />)}
                                        {expanded === 'phase2' && (
                                            <div
                                                style={{
                                                    marginTop: '0.5rem',
                                                    padding: '1rem',
                                                    background: '#F9FAFB',
                                                    borderRadius: '0.375rem',
                                                    fontSize: '0.875rem',
                                                    color: '#374151',
                                                    whiteSpace: 'pre-wrap',
                                                }}
                                            >
                                                {(result.phase2_plan_markdown || '').trim() || '(无)'}
                                            </div>
                                        )}
                                    </div>
                                    <div>
                                        {phaseTitle('phase3', '3️⃣ 代码生成', <FileCode size={18} />)}
                                        {expanded === 'phase3' && (
                                            <div
                                                style={{
                                                    marginTop: '0.5rem',
                                                    padding: '1rem',
                                                    background: '#1F2937',
                                                    color: '#E5E7EB',
                                                    borderRadius: '0.375rem',
                                                    fontSize: '0.8rem',
                                                    overflow: 'auto',
                                                    maxHeight: '400px',
                                                }}
                                            >
                                                {hasCode ? (
                                                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                                                        {result.phase3_code}
                                                    </pre>
                                                ) : (
                                                    <p style={{ color: '#9CA3AF', margin: 0 }}>
                                                        未生成测试代码。请重新在「AI生成」Tab 生成接口测试，或检查接口定义与测试计划是否完整。
                                                    </p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                    <div>
                                        {phaseTitle('phase4', '4️⃣ 测试执行', <Play size={18} />)}
                                        {expanded === 'phase4' && (
                                            <div
                                                style={{
                                                    marginTop: '0.5rem',
                                                    padding: '1rem',
                                                    background: '#F9FAFB',
                                                    borderRadius: '0.375rem',
                                                    fontSize: '0.875rem',
                                                    color: '#374151',
                                                }}
                                            >
                                                {result.phase4_executor_summary && (
                                                    <div style={{ marginBottom: '0.75rem' }}>
                                                        <p style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                                                            执行策略（大模型）：
                                                        </p>
                                                        <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem', margin: 0 }}>
                                                            {typeof result.phase4_executor_summary === 'object'
                                                                ? JSON.stringify(result.phase4_executor_summary, null, 2)
                                                                : result.phase4_executor_summary}
                                                        </pre>
                                                    </div>
                                                )}
                                                {result.phase4_result ? (
                                                    <div>
                                                        <p style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                                                            执行结果：通过 {result.phase4_result.passed_cases} /{' '}
                                                            {result.phase4_result.total_cases}，失败{' '}
                                                            {result.phase4_result.failed_cases}，耗时{' '}
                                                            {result.phase4_result.duration_ms} ms
                                                        </p>
                                                        {result.phase4_result.failed_cases > 0 && result.phase4_result.execution_id && (
                                                            <div style={{ marginBottom: '0.75rem' }}>
                                                                {healAnalyzeLoading && (
                                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0.75rem', background: '#FEF3C7', borderRadius: '0.375rem', marginBottom: '0.5rem', fontSize: '0.875rem', color: '#92400E' }}>
                                                                        <Loader2 size={18} className="animate-spin" style={{ flexShrink: 0 }} />
                                                                        <span>分析中，请稍候...</span>
                                                                    </div>
                                                                )}
                                                                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                                                    <button
                                                                        type="button"
                                                                        onClick={runHealAnalyze}
                                                                        disabled={healAnalyzeLoading || healApplyLoading}
                                                                        style={{ padding: '0.4rem 0.8rem', background: (healAnalyzeLoading || healApplyLoading) ? '#9CA3AF' : '#F59E0B', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.8rem', cursor: (healAnalyzeLoading || healApplyLoading) ? 'not-allowed' : 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                                                                    >
                                                                        {healAnalyzeLoading ? <Loader2 size={14} className="animate-spin" /> : <AlertCircle size={14} />}
                                                                        失败分析
                                                                    </button>
                                                                    <button
                                                                        type="button"
                                                                        onClick={runHealApplySingleApi}
                                                                        disabled={healAnalyzeLoading || healApplyLoading}
                                                                        style={{ padding: '0.4rem 0.8rem', background: (healAnalyzeLoading || healApplyLoading) ? '#9CA3AF' : '#EF4444', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.8rem', cursor: (healAnalyzeLoading || healApplyLoading) ? 'not-allowed' : 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                                                                    >
                                                                        {healApplyLoading ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
                                                                        一键修复
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        )}
                                                        {healAnalyzeResult && healAnalyzeResult.status === 'analyzed' && (
                                                            <div style={{ marginBottom: '0.75rem', padding: '0.75rem 1rem', background: '#FEF3C7', border: '1px solid #FDE68A', borderRadius: '0.5rem' }}>
                                                                <div style={{ fontWeight: '600', marginBottom: '0.5rem', fontSize: '0.875rem', color: '#92400E' }}>失败原因分析</div>
                                                                <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8125rem', color: '#78350F', lineHeight: 1.6 }}>
                                                                    {(healAnalyzeResult.analysis || []).map((a: any, i: number) => (
                                                                        <li key={i} style={{ marginBottom: '0.35rem' }}>
                                                                            <strong>{a.failure_type || '未知'}</strong>：{a.root_cause || ''}
                                                                            {a.suggested_fix && <div style={{ marginTop: '0.2rem', fontStyle: 'italic' }}>建议：{a.suggested_fix}</div>}
                                                                            {a.can_heal === false && <span style={{ color: '#B45309', marginLeft: '0.25rem' }}>(需人工介入)</span>}
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                                {healAnalyzeResult.healable && <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#65A30D' }}>✓ 可尝试一键修复</div>}
                                                            </div>
                                                        )}
                                                        {healAnalyzeResult && healAnalyzeResult.status === 'no_failure' && (
                                                            <p style={{ fontSize: '0.8125rem', color: '#6B7280', marginBottom: '0.5rem' }}>{healAnalyzeResult.message}</p>
                                                        )}
                                                        {healAnalyzeResult && healAnalyzeResult.status !== 'no_failure' && healAnalyzeResult.status !== 'analyzed' && !healAnalyzeResult.healable && (
                                                            <p style={{ fontSize: '0.8125rem', color: '#92400E', marginBottom: '0.5rem' }}>{healAnalyzeResult.message || '失败原因需要人工介入'}</p>
                                                        )}
                                                        {(healLog.length > 0 || healApplyLoading) && (
                                                            <div style={{ marginBottom: '0.75rem', background: '#0F172A', borderRadius: '0.5rem', padding: '0.75rem 1rem', fontFamily: 'monospace', fontSize: '0.8125rem', lineHeight: 1.7 }}>
                                                                <div style={{ color: '#94A3B8', marginBottom: '0.35rem', fontSize: '0.75rem', letterSpacing: '0.05em' }}>— AI 修复过程 —</div>
                                                                {healLog.map((line, i) => {
                                                                    const isEmpty = line === ''
                                                                    const isSuccess = line.startsWith('✅')
                                                                    const isWarn = line.startsWith('⚠️')
                                                                    const isError = line.startsWith('❌')
                                                                    const isSection = line.startsWith('🔍') || line.startsWith('🛠️')
                                                                    const isDetail = line.startsWith('   ✓')
                                                                    const color = isSuccess ? '#4ADE80' : isWarn ? '#FBBF24' : isError ? '#F87171' : isSection ? '#60A5FA' : isDetail ? '#A3E635' : '#E2E8F0'
                                                                    return isEmpty ? <div key={i} style={{ height: '0.35rem' }} /> : (
                                                                        <div key={i} style={{ color, display: 'flex', alignItems: 'flex-start', gap: '0.25rem' }}>
                                                                            <span style={{ whiteSpace: 'pre-wrap' }}>{line}</span>
                                                                        </div>
                                                                    )
                                                                })}
                                                                {healApplyLoading && (
                                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94A3B8', marginTop: '0.35rem' }}>
                                                                        <Loader2 size={13} className="animate-spin" />
                                                                        <span>处理中...</span>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        )}
                                                        <p style={{ fontSize: '0.8125rem', color: '#6B7280', marginBottom: '0.75rem' }}>
                                                            执行优先按「代码生成」中的用例；解析不到时按「测试计划」用例执行。
                                                        </p>
                                                        {(result.phase4_result.results || []).length > 0 ? (
                                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                                                {(result.phase4_result.results as any[]).map((r: any, i: number) => {
                                                                    const isFailed = !r.success
                                                                    const isExp = phase4ExpandedSteps.has(i)
                                                                    const planCases = (result.phase2_plan?.endpoints || []).flatMap((ep: any) => ep.cases || [])
                                                                    // 优先用执行结果中带回的用例名（正向/边界/健壮等），其次用计划中的名称，避免只显示「步骤1」
                                                                    const caseName = (r?.name || planCases[i]?.name || '').trim() || `步骤 ${i + 1}`
                                                                    const d = {
                                                                        // 优先用执行结果中的 request_data/request_headers（后端已从 plan 注入），保证有请求头与 body
                                                                        requestData: r?.request_data ?? r?.params ?? planCases[i]?.request_template?.params ?? {},
                                                                        urlParams: r?.url_params ?? planCases[i]?.request_template?.url_params ?? {},
                                                                        requestHeaders: r?.request_headers ?? r?.headers ?? planCases[i]?.request_template?.headers ?? {},
                                                                        response: r?.response,
                                                                        responseHeaders: r?.response_headers ?? {},
                                                                        extractions: r?.extractions ?? [],
                                                                        fullUrl: r?.full_url ?? r?.url ?? '',
                                                                        method: r?.api_method ?? r?.method ?? 'GET',
                                                                    }
                                                                    const getTab = () => phase4StepDetailTab[i] || 'responseBody'
                                                                    const setTab = (t: StepDetailTab) => setPhase4StepDetailTab((p) => ({ ...p, [i]: t }))
                                                                    return (
                                                                        <div
                                                                            key={i}
                                                                            style={{
                                                                                border: '1px solid #E5E7EB',
                                                                                borderRadius: '0.5rem',
                                                                                overflow: 'hidden',
                                                                                background: isFailed ? '#FEF2F2' : 'white',
                                                                            }}
                                                                        >
                                                                            <button
                                                                                type="button"
                                                                                onClick={() => setPhase4ExpandedSteps((prev) => {
                                                                                    const next = new Set(prev)
                                                                                    if (next.has(i)) next.delete(i)
                                                                                    else next.add(i)
                                                                                    return next
                                                                                })}
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
                                                                                    {isExp ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                                                                    <span style={{ fontWeight: '500' }}>① {isFailed ? '' : '√'} {caseName}</span>
                                                                                    {isFailed ? <XCircle size={18} color="#EF4444" /> : <CheckCircle size={18} color="#10B981" />}
                                                                                </span>
                                                                                <span style={{ color: isFailed ? '#EF4444' : '#10B981', fontWeight: '500' }}>{isFailed ? '失败' : '成功'}</span>
                                                                            </button>
                                                                            {isExp && (
                                                                                <div style={{ padding: '1rem', borderTop: '1px solid #E5E7EB', background: '#F9FAFB' }}>
                                                                                    <div style={{ marginBottom: '1rem', padding: '1rem', background: 'white', borderRadius: '0.5rem', border: '1px solid #E5E7EB' }}>
                                                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center', marginBottom: '0.5rem' }}>
                                                                                            <span style={{ fontWeight: '700', color: '#3B82F6', fontSize: '0.875rem' }}>{d.method}</span>
                                                                                            <span style={{ fontSize: '0.8125rem', color: '#374151', wordBreak: 'break-all', flex: 1 }}>{d.fullUrl || `${d.method} ${r.api_path || r.url || ''}`}</span>
                                                                                        </div>
                                                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', fontSize: '0.8125rem', color: '#6B7280' }}>
                                                                                            {r.duration != null && <span>响应时间 {(r.duration * 1000).toFixed(0)} ms</span>}
                                                                                            <span style={{ color: (r.status_code ?? 200) < 400 ? '#10B981' : '#EF4444', fontWeight: '600' }}>HTTP {r.status_code ?? '-'}</span>
                                                                                            <span>{(r.response_size ?? 0)} 字节</span>
                                                                                            <span style={{ padding: '0.2rem 0.5rem', borderRadius: '0.25rem', background: r.success ? '#D1FAE5' : '#FEE2E2', color: r.success ? '#065F46' : '#991B1B', fontWeight: '600' }}>{r.success ? '成功' : '失败'}</span>
                                                                                        </div>
                                                                                    </div>
                                                                                    <div style={{ marginBottom: '0.5rem', display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                                                                                        {STEP_DETAIL_TABS.map((tab) => (
                                                                                            <button key={tab} type="button" onClick={() => setTab(tab)} style={{ padding: '0.35rem 0.75rem', fontSize: '0.8125rem', border: 'none', borderRadius: '0.25rem', cursor: 'pointer', background: getTab() === tab ? '#667eea' : '#E5E7EB', color: getTab() === tab ? 'white' : '#374151', fontWeight: getTab() === tab ? '600' : '400' }}>
                                                                                                {STEP_TAB_LABELS[tab]}
                                                                                            </button>
                                                                                        ))}
                                                                                    </div>
                                                                                    <div style={{ minHeight: '120px' }}>
                                                                                        {getTab() === 'responseBody' && ((d.response != null && d.response !== '') ? <JsonWithLines data={d.response} maxHeight={280} /> : <div style={{ padding: '1rem', color: '#6B7280' }}>暂无响应体</div>)}
                                                                                        {getTab() === 'responseHeaders' && (d.responseHeaders && Object.keys(d.responseHeaders).length > 0 ? <JsonWithLines data={d.responseHeaders} maxHeight={180} /> : <div style={{ padding: '1rem', color: '#6B7280' }}>暂无响应头</div>)}
                                                                                        {getTab() === 'assertions' && (
                                                                                            <div style={{ padding: '1rem', color: '#374151', fontSize: '0.875rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                                                                                {(r.assertions && Array.isArray(r.assertions) && r.assertions.length > 0)
                                                                                                    ? r.assertions.map((a: any, ai: number) => {
                                                                                                        // 尝试解析 message 中的详细信息
                                                                                                        let detailedItems: any[] = [];
                                                                                                        let cleanMsg = a.message || '';

                                                                                                        try {
                                                                                                            if (a.message) {
                                                                                                                const startIdx = a.message.indexOf('[');
                                                                                                                const endIdx = a.message.lastIndexOf(']');

                                                                                                                if (startIdx >= 0 && endIdx > startIdx) {
                                                                                                                    const listStr = a.message.substring(startIdx, endIdx + 1);
                                                                                                                    const jsonStr = listStr
                                                                                                                        .replace(/'/g, '"')
                                                                                                                        .replace(/True/g, 'true')
                                                                                                                        .replace(/False/g, 'false')
                                                                                                                        .replace(/None/g, 'null');

                                                                                                                    const parsed = JSON.parse(jsonStr);
                                                                                                                    if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].field) {
                                                                                                                        detailedItems = parsed;
                                                                                                                        cleanMsg = a.message.substring(0, startIdx).trim();
                                                                                                                        if (cleanMsg.endsWith(':')) cleanMsg = cleanMsg.slice(0, -1).trim();
                                                                                                                    }
                                                                                                                }
                                                                                                            }
                                                                                                        } catch (e) { /* 解析失败保留原样 */ }

                                                                                                        // 也尝试使用 a.details
                                                                                                        if (detailedItems.length === 0 && a.details && a.details.length > 0) {
                                                                                                            detailedItems = a.details;
                                                                                                            cleanMsg = a.message || '';
                                                                                                        }

                                                                                                        return (
                                                                                                            <div key={ai} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                                                                                                                {/* 标题行 */}
                                                                                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                                    <span style={{ color: a.passed ? '#10B981' : '#EF4444', fontWeight: 600 }}>{a.passed ? '✓' : '✗'}</span>
                                                                                                                    <span style={{ fontWeight: 600, color: '#6B7280' }}>{a.type === 'http' ? '响应码断言' : '业务断言'}</span>
                                                                                                                    {/* 如果有干净的消息文本则显示 */}
                                                                                                                    {cleanMsg && detailedItems.length > 0 && <span style={{ color: '#4B5563' }}>{cleanMsg}</span>}
                                                                                                                    {/* 如果没有解析成功，显示原始消息 */}
                                                                                                                    {detailedItems.length === 0 && a.message && <span>{a.message}</span>}
                                                                                                                </div>
                                                                                                                {/* 详细字段列表 (一行一个) */}
                                                                                                                {detailedItems.length > 0 && (
                                                                                                                    <div style={{ marginLeft: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.15rem', fontSize: '0.8125rem' }}>
                                                                                                                        {detailedItems.map((item: any, di: number) => (
                                                                                                                            <div key={di} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'monospace' }}>
                                                                                                                                <span style={{ fontWeight: 600, color: '#374151' }}>{item.field}:</span>
                                                                                                                                <span style={{ color: '#6B7280' }}>期望</span>
                                                                                                                                <span style={{ color: '#059669' }}>{JSON.stringify(item.expected)}</span>
                                                                                                                                <span style={{ color: '#6B7280' }}>，实际</span>
                                                                                                                                <span style={{ color: item.passed ? '#059669' : '#DC2626' }}>{JSON.stringify(item.actual)}</span>
                                                                                                                                <span style={{ fontWeight: 'bold' }}>{item.passed ? <span style={{ color: '#10B981' }}>✓</span> : <span style={{ color: '#EF4444' }}>✗</span>}</span>
                                                                                                                            </div>
                                                                                                                        ))}
                                                                                                                    </div>
                                                                                                                )}
                                                                                                            </div>
                                                                                                        );
                                                                                                    })
                                                                                                    : (r.success ? `✓ 状态码 ${r.status_code} 与期望 ${r.expected_status ?? 200} 一致` : `✗ 状态码 ${r.status_code} 未通过（期望 ${r.expected_status ?? '2xx'})`)}
                                                                                            </div>
                                                                                        )}
                                                                                        {getTab() === 'extraction' && (d.extractions?.length > 0 ? <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}><thead><tr style={{ background: '#F3F4F6' }}><th style={{ padding: '0.5rem', textAlign: 'left' }}>目标字段</th><th style={{ padding: '0.5rem', textAlign: 'left' }}>来源步骤</th><th style={{ padding: '0.5rem', textAlign: 'left' }}>提取结果</th></tr></thead><tbody>{d.extractions.map((ex: any, ei: number) => <tr key={ei} style={{ borderTop: '1px solid #E5E7EB' }}><td style={{ padding: '0.5rem' }}>{ex.to_field}</td><td style={{ padding: '0.5rem' }}>步骤 {ex.from_step}</td><td style={{ padding: '0.5rem' }}>{ex.success ? String(ex.extracted_value ?? '-') : (ex.error_msg || '失败')}</td></tr>)}</tbody></table></div> : <div style={{ padding: '1rem', color: '#6B7280' }}>此步骤未提取数据</div>)}
                                                                                        {getTab() === 'requestContent' && (
                                                                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                                                                                <div><div style={{ fontWeight: '600', marginBottom: '0.35rem', fontSize: '0.8125rem' }}>请求地址</div><div style={{ fontSize: '0.8125rem', wordBreak: 'break-all' }}>{d.fullUrl || `${d.method} ${r.api_path || r.url || '-'}`}</div></div>
                                                                                                {d.requestHeaders && Object.keys(d.requestHeaders).length > 0 && <div><div style={{ fontWeight: '600', marginBottom: '0.35rem', fontSize: '0.8125rem' }}>请求头</div><JsonWithLines data={d.requestHeaders} maxHeight={150} /></div>}
                                                                                                <div><div style={{ fontWeight: '600', marginBottom: '0.35rem', fontSize: '0.8125rem' }}>Body / 参数</div>{(d.requestData && Object.keys(d.requestData).length > 0) ? <JsonWithLines data={d.requestData} maxHeight={180} /> : (d.urlParams && Object.keys(d.urlParams).length > 0) ? <JsonWithLines data={d.urlParams} maxHeight={120} /> : <div style={{ padding: '0.75rem', color: '#9CA3AF', fontSize: '0.8125rem' }}>无请求体</div>}</div>
                                                                                            </div>
                                                                                        )}
                                                                                    </div>
                                                                                    {r.error && <div style={{ marginTop: '0.75rem', color: '#EF4444', fontSize: '0.875rem' }}>{r.error}</div>}
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    )
                                                                })}
                                                            </div>
                                                        ) : (
                                                            <pre style={{ marginTop: '0.5rem', whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>{JSON.stringify(result.phase4_result.case_results || [], null, 2)}</pre>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <p style={{ color: '#6B7280' }}>
                                                        未执行。请在上方填写「接口基础地址」（如 https://api.example.com）后点击「再次执行并分析」，或先在项目环境中配置 base_url。
                                                    </p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                    <div>
                                        {phaseTitle('phase5', '5️⃣ 结果分析', <BarChart3 size={18} />)}
                                        {expanded === 'phase5' && (
                                            <div
                                                style={{
                                                    marginTop: '0.5rem',
                                                    padding: '1rem',
                                                    background: '#F9FAFB',
                                                    borderRadius: '0.375rem',
                                                    fontSize: '0.875rem',
                                                    color: '#374151',
                                                    whiteSpace: 'pre-wrap',
                                                }}
                                            >
                                                {result.phase5_report ? (
                                                    <pre
                                                        style={{
                                                            margin: 0,
                                                            whiteSpace: 'pre-wrap',
                                                            fontFamily: 'inherit',
                                                        }}
                                                    >
                                                        {result.phase5_report}
                                                    </pre>
                                                ) : (
                                                    <p style={{ color: '#6B7280' }}>
                                                        无分析报告（请先点击「再次执行并分析」）
                                                    </p>
                                                )}
                                                {result.phase5_chart_data?.summary && (
                                                    <p style={{ marginTop: '0.5rem' }}>
                                                        汇总: 通过 {result.phase5_chart_data.summary.passed}，失败{' '}
                                                        {result.phase5_chart_data.summary.failed}，总耗时{' '}
                                                        {result.phase5_chart_data.summary.duration_ms} ms
                                                    </p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
