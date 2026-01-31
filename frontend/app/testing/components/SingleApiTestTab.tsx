'use client'

import { useState } from 'react'
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
} from 'lucide-react'
import { useProject } from '../../contexts/ProjectContext'
import type { SingleApiCaseItem } from '../page'

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

export default function SingleApiTestTab({
    items,
    selectedId,
    onSelect,
    onResultChange,
    onDelete,
}: Props) {
    const { currentProject } = useProject()
    const [execLoading, setExecLoading] = useState(false)
    const [expanded, setExpanded] = useState<string | null>('phase1')
    /** 执行时使用的接口基础地址（可选，不填则使用项目环境配置） */
    const [execBaseUrl, setExecBaseUrl] = useState('')

    const selected = items.find((it) => it.id === selectedId)
    const result = selected?.data

    const handleExecuteAndAnalyze = async () => {
        if (!result?.phase2_plan?.endpoints?.length || !selectedId) {
            alert('当前无已生成的测试计划，请先在「AI生成」Tab 选择「单接口测试」并生成')
            return
        }
        setExecLoading(true)
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
            onResultChange(selectedId, {
                ...result,
                phase4_result: suiteResult,
                phase5_report: analyzeData.report ?? null,
                phase5_chart_data: analyzeData.chart_data ?? null,
            })
            setExpanded('phase4')
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
                    请先在「AI生成」Tab 选择「单接口测试」并生成，新生成的用例会追加到此处，不会删除之前的记录
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
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                            <label style={{ fontSize: '0.875rem', color: '#374151', whiteSpace: 'nowrap' }}>
                                                接口基础地址：
                                            </label>
                                            <input
                                                type="text"
                                                value={execBaseUrl}
                                                onChange={(e) => setExecBaseUrl(e.target.value)}
                                                placeholder="如 https://api.example.com，不填则用项目环境"
                                                style={{
                                                    width: '280px',
                                                    padding: '0.5rem 0.75rem',
                                                    border: '1px solid #D1D5DB',
                                                    borderRadius: '0.5rem',
                                                    fontSize: '0.875rem',
                                                }}
                                            />
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
                                                未生成测试代码。请重新在「AI生成」Tab 生成单接口测试，或检查接口定义与测试计划是否完整。
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
                                                <p style={{ fontWeight: '600' }}>
                                                    执行结果：通过 {result.phase4_result.passed_cases} /{' '}
                                                    {result.phase4_result.total_cases}，失败{' '}
                                                    {result.phase4_result.failed_cases}，耗时{' '}
                                                    {result.phase4_result.duration_ms} ms
                                                </p>
                                                <p style={{ fontSize: '0.8125rem', color: '#6B7280', marginTop: '0.25rem' }}>
                                                    执行优先按「代码生成」中的用例（解析 Playwright 代码得到），与代码里的 test 数量一致；解析不到时按「测试计划」用例执行。
                                                </p>
                                                <pre
                                                    style={{
                                                        marginTop: '0.5rem',
                                                        whiteSpace: 'pre-wrap',
                                                        fontSize: '0.8rem',
                                                    }}
                                                >
                                                    {JSON.stringify(result.phase4_result.case_results || [], null, 2)}
                                                </pre>
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
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
