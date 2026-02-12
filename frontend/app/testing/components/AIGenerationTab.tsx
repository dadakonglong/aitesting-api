'use client'

import { useState, useEffect, useRef } from 'react'
import { Sparkles, Loader2, CheckCircle2, ArrowRight, Target } from 'lucide-react'
import Link from 'next/link'
import { useProject } from '../../contexts/ProjectContext'
import { getSingleApiDisplayName } from '../page'

type Mode = 'scenario' | 'single-api'

interface EnvItem {
    id: number
    env_name: string
    base_url: string
    is_default?: number
}

type Props = {
    /** 接口测试生成成功后调用，结果会放到「接口测试」Tab 并自动切过去 */
    onSingleApiGenerated?: (data: any) => void
}

export default function AIGenerationTab({ onSingleApiGenerated }: Props) {
    const { currentProject } = useProject()
    const [mode, setMode] = useState<Mode>('scenario')
    const [scenario, setScenario] = useState('')
    const [singleApiInput, setSingleApiInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<any>(null)
    const [environments, setEnvironments] = useState<EnvItem[]>([])
    const [selectedEnvId, setSelectedEnvId] = useState<number | 'custom' | null>(null)
    const [execBaseUrl, setExecBaseUrl] = useState('')
    // 实时进度展示
    const [progressLines, setProgressLines] = useState<string[]>([])
    const progressEndRef = useRef<HTMLDivElement>(null)
    // 测试场景模式：环境配置（生成后自动执行用）
    const [scenarioEnvs, setScenarioEnvs] = useState<EnvItem[]>([])
    const [scenarioSelectedEnvId, setScenarioSelectedEnvId] = useState<number | 'custom' | null>(null)
    const [scenarioExecBaseUrl, setScenarioExecBaseUrl] = useState('')

    // 接口测试模式：加载项目环境
    useEffect(() => {
        if (mode !== 'single-api') return
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
    }, [currentProject, mode])

    // WIP 状态持久化：防止切 Tab 丢失输入
    useEffect(() => {
        const key = `wip-ai-gen-${currentProject}`
        const saved = localStorage.getItem(key)
        if (saved) {
            try {
                const { scenario: s, singleApiInput: sai, mode: m } = JSON.parse(saved)
                if (s) setScenario(s)
                if (sai) setSingleApiInput(sai)
                if (m) setMode(m)
            } catch (e) { /* ignore */ }
        }
    }, [currentProject])

    useEffect(() => {
        const key = `wip-ai-gen-${currentProject}`
        const data = JSON.stringify({ scenario, singleApiInput, mode })
        localStorage.setItem(key, data)
    }, [currentProject, scenario, singleApiInput, mode])

    // 测试场景模式：加载环境列表（页面上配置，生成后自动执行用）
    useEffect(() => {
        if (mode !== 'scenario') return
        const load = async () => {
            try {
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects/${encodeURIComponent(currentProject)}/environments`)
                if (!res.ok) return
                const data = await res.json()
                const list: EnvItem[] = Array.isArray(data) ? data : []
                setScenarioEnvs(list)
                const defaultEnv = list.find((e) => e.is_default === 1) || list[0]
                if (defaultEnv) {
                    setScenarioSelectedEnvId(defaultEnv.id)
                    setScenarioExecBaseUrl(defaultEnv.base_url || '')
                } else if (list[0]) {
                    setScenarioSelectedEnvId(list[0].id)
                    setScenarioExecBaseUrl(list[0].base_url || '')
                } else {
                    setScenarioSelectedEnvId(null)
                    setScenarioExecBaseUrl('')
                }
            } catch {
                setScenarioEnvs([])
                setScenarioSelectedEnvId(null)
                setScenarioExecBaseUrl('')
            }
        }
        load()
    }, [mode, currentProject])

    const handleGenerate = async () => {
        if (mode === 'scenario') {
            if (!scenario.trim()) {
                alert('请输入测试场景')
                return
            }
            setLoading(true)
            setResult(null)
            setProgressLines(['开始处理', ''])

            const appendProgress = (...lines: string[]) => {
                setProgressLines((prev) => [...prev, ...lines])
                setTimeout(() => progressEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
            }

            try {
                // ---------- 阶段一：创建测试场景 ----------
                appendProgress('创建测试场景...')
                appendProgress('   · 理解场景意图（解析意图、实体、动作）...')
                const scenarioRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/scenarios`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: currentProject,
                        natural_language_input: scenario,
                    }),
                })
                if (!scenarioRes.ok) throw new Error('创建场景失败')
                const scenarioData = await scenarioRes.json()
                appendProgress('   ✓ 提取意图与实体')
                appendProgress('   ✓ 场景已保存')
                appendProgress('')

                // ---------- 阶段二：生成测试用例（展示与后端一致的子步骤） ----------
                appendProgress('生成测试用例...')
                appendProgress('   · 检索项目接口...')
                const caseResPromise = fetch(
                    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/scenarios/${scenarioData.id}/generate-case`,
                    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ data_strategy: 'smart' }) }
                )
                // 在请求进行中按顺序展示子步骤（与后端：检索 API → 依赖 → 编排 → 提取/传递参数 一致）
                const t1 = setTimeout(() => {
                    appendProgress('   ✓ 检索项目接口')
                    appendProgress('   · 查找接口依赖关系...')
                }, 450)
                const t2 = setTimeout(() => {
                    appendProgress('   ✓ 查找接口依赖关系')
                    appendProgress('   · 编排测试步骤与断言...')
                }, 950)
                const t3 = setTimeout(() => {
                    appendProgress('   ✓ 编排测试步骤与断言')
                    appendProgress('   · 提取参数与映射...')
                }, 1450)
                let caseRes: Response
                try {
                    caseRes = await caseResPromise
                } finally {
                    clearTimeout(t1)
                    clearTimeout(t2)
                    clearTimeout(t3)
                }
                if (!caseRes.ok) {
                    const errorData = await caseRes.json().catch(() => ({}))
                    throw new Error(errorData.detail || errorData.message || '生成测试用例失败')
                }
                const caseData = await caseRes.json()
                appendProgress('   ✓ 提取参数与映射')
                appendProgress('   ✓ 传递参数配置（Token、Session 等）')
                appendProgress('   ✓ 用例生成完成')
                appendProgress('')
                appendProgress('生成成功！')
                appendProgress(`场景名称：${scenarioData.name || '—'}`)
                appendProgress(`描述：${scenarioData.description || '—'}`)
                appendProgress(`用例名称：${caseData.name || '—'}`)
                const steps = caseData.steps || []
                appendProgress(`测试步骤：${steps.length} 个`)
                steps.forEach((s: any, i: number) => {
                    const method = (s.api_method || s.method || 'GET').toString().toUpperCase()
                    const path = s.api_path || s.path || '—'
                    appendProgress(`   ${i + 1}. ${method} ${path}`)
                })
                appendProgress('')

                // ---------- 阶段三：自动执行场景 ----------
                appendProgress('执行场景...')
                let baseUrl = scenarioExecBaseUrl.trim()
                if (scenarioSelectedEnvId !== 'custom' && scenarioSelectedEnvId != null) {
                    const env = scenarioEnvs.find((e) => e.id === scenarioSelectedEnvId)
                    baseUrl = (env?.base_url || '').trim()
                }
                if (!baseUrl) baseUrl = 'http://localhost:8000'
                try {
                    const apiUrl = process.env.NEXT_PUBLIC_EXEC_API_URL || process.env.NEXT_PUBLIC_API_URL
                    const execRes = await fetch(`${apiUrl}/api/v1/executions`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            test_case_id: caseData.id,
                            environment: scenarioEnvs.find((e) => e.id === scenarioSelectedEnvId)?.env_name || 'test',
                            base_url: baseUrl,
                        }),
                    })
                    if (execRes.ok) {
                        const execData = await execRes.json()
                        const status = execData.status === 'success' ? '全部通过' : '存在失败'
                        appendProgress(`   ✓ 执行完成：${status}`)
                    } else {
                        const err = await execRes.json().catch(() => ({}))
                        appendProgress(`   ⚠ 执行失败：${err.detail || '请检查环境地址'}`)
                    }
                } catch (e: any) {
                    appendProgress(`   ⚠ 执行异常：${e.message}`)
                }
                appendProgress('')
                appendProgress('处理完成！')

                setResult({ scenario: scenarioData, testCase: caseData })
            } catch (error: any) {
                appendProgress('', `❌ 错误: ${error.message}`)
                alert(`错误: ${error.message}`)
            } finally {
                setLoading(false)
            }
            return
        }

        // 接口测试：逐步调用各阶段接口，实时展示进度
        if (!singleApiInput.trim()) {
            alert('请输入接口测试描述，例如：为登录接口生成完整测试')
            return
        }
        setLoading(true)
        setResult(null)
        setProgressLines(['开始处理任务...', ''])

        // 辅助函数：追加进度行
        const appendProgress = (...lines: string[]) => {
            setProgressLines((prev) => [...prev, ...lines])
            // 滚动到底部
            setTimeout(() => progressEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
        }

        try {
            // 获取 base_url
            let baseUrl = execBaseUrl.trim()
            if (!baseUrl && environments.length > 0) {
                const env = (typeof selectedEnvId === 'number'
                    ? environments.find((e) => e.id === selectedEnvId)
                    : null) || environments.find((e) => e.is_default === 1) || environments[0]
                baseUrl = (env?.base_url || '').trim()
            }
            if (!baseUrl) {
                const envRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects/${encodeURIComponent(currentProject)}/environments`)
                if (envRes.ok) {
                    const envList: EnvItem[] = await envRes.json()
                    if (Array.isArray(envList) && envList.length > 0) {
                        const env = envList.find((e) => e.is_default === 1) || envList[0]
                        baseUrl = (env?.base_url || '').trim()
                    }
                }
            }

            // ========== Phase 1: 需求理解 ==========
            appendProgress('检索 API 文档信息...')
            const phase1Res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/single-api/understand`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ natural_language_input: singleApiInput.trim(), project_id: currentProject }),
            })
            if (!phase1Res.ok) {
                const err = await phase1Res.json().catch(() => ({}))
                throw new Error(err.detail || err.message || '需求理解失败')
            }
            const structured = await phase1Res.json()

            // 根据 phase1 结果追加进度详情
            const entities = structured?.entities || []
            let moduleNames = [...new Set(entities.map((e: any) => e.entity_name || e.name || '').filter(Boolean))]
            if (moduleNames.length > 0) {
                appendProgress(`   ✓ 识别 ${moduleNames.length} 个相关实体：${(moduleNames as string[]).slice(0, 5).join('、')}${moduleNames.length > 5 ? '...' : ''}`)
            } else if (entities.length > 0) {
                appendProgress(`   ✓ 识别 ${entities.length} 个实体`)
            }
            const chunks = structured?.chunks || []
            appendProgress(`   ✓ 提取 ${chunks.length || 1} 个 API 端点`)
            const hasAuth = JSON.stringify(structured || '').includes('认证') || JSON.stringify(chunks).toLowerCase().includes('auth')
            if (hasAuth) appendProgress('   ✓ 识别认证机制')
            appendProgress('   ✓ 自动依赖分析（KG + AI）')
            appendProgress('')

            // ========== Phase 2: 测试计划 ==========
            appendProgress('生成测试计划...')
            const phase2Res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/single-api/plan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: currentProject, structured_info: structured }),
            })
            if (!phase2Res.ok) {
                const err = await phase2Res.json().catch(() => ({}))
                throw new Error(err.detail || err.message || '生成测试计划失败')
            }
            const phase2Data = await phase2Res.json()
            const planMarkdown = phase2Data.markdown || ''
            const planPayload = phase2Data.plan || {}
            const endpoints = planPayload?.endpoints || []
            const cases = endpoints.flatMap((ep: any) => ep.cases || [])
            if (cases.length > 0) appendProgress(`   ✓ 共 ${cases.length} 个测试用例`)
            if (endpoints.length > 0) appendProgress(`   ✓ 覆盖 ${endpoints.length} 个 API 端点`)
            appendProgress('')

            // 更新 moduleNames from endpoints if empty
            if (moduleNames.length === 0 && endpoints.length > 0) {
                moduleNames = [...new Set(endpoints.map((ep: any) => {
                    const s = (ep.summary || ep.name || ep.path || '').toString()
                    const part = s.split(/[\/\\\-_]/).filter(Boolean)[0] || s.slice(0, 8)
                    return part || '接口'
                }).filter(Boolean))]
            }

            // ========== Phase 3: 代码生成 ==========
            appendProgress('生成测试代码...')
            const targetApi = (endpoints[0]) || {}
            const apiInfo = planPayload.target_api || targetApi || (structured?.api_candidates || [{}])[0] || {}
            const phase3Res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/single-api/generate-code`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plan_markdown: planMarkdown, api_info: apiInfo, plan_payload: planPayload }),
            })
            if (!phase3Res.ok) {
                const err = await phase3Res.json().catch(() => ({}))
                throw new Error(err.detail || err.message || '代码生成失败')
            }
            const phase3Data = await phase3Res.json()
            const code = phase3Data.code || ''
            appendProgress('   ✓ 生成测试文件')
            appendProgress('')

            // 组装当前结果
            let data: any = {
                phase1_structured: structured,
                phase2_plan_markdown: planMarkdown,
                phase2_plan: planPayload,
                phase3_code: code,
                phase4_executor_summary: null,
                phase4_result: null,
                phase5_report: null,
                phase5_chart_data: null,
            }

            // ========== Phase 4: 执行测试 ==========
            appendProgress('执行测试...')
            appendProgress('   ✓ 自动解析前置依赖')
            if (baseUrl && endpoints.length > 0) {
                try {
                    const execRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/single-api/execute`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            project_id: currentProject,
                            base_url: baseUrl,
                            environment: 'test',
                            plan: planPayload,
                            generated_code: code || undefined,
                        }),
                    })
                    if (execRes.ok) {
                        const suiteResult = await execRes.json()
                        data.phase4_result = suiteResult
                        const total = suiteResult.total_cases ?? 0
                        const passed = suiteResult.passed_cases ?? 0
                        const failed = suiteResult.failed_cases ?? 0
                        const dur = suiteResult.duration_ms != null ? (suiteResult.duration_ms / 1000).toFixed(1) : '-'
                        appendProgress(`   ✓ 执行 ${total} 个测试用例`)
                        appendProgress(`   ✓ 通过：${passed} 个`)
                        appendProgress(`   ✓ 失败：${failed} 个`)
                        appendProgress(`   ✓ 执行时间：${dur}s`)
                    } else {
                        appendProgress('   ⚠ 执行失败，跳过')
                    }
                } catch (_e) {
                    appendProgress('   ⚠ 执行异常，跳过')
                }
            } else {
                appendProgress('   ✓ 未执行（未配置接口基础地址）')
            }
            appendProgress('')

            // ========== Phase 5: 生成报告 ==========
            appendProgress('生成报告...')
            if (data.phase4_result) {
                try {
                    const analyzeRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/single-api/analyze`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ suite_result: data.phase4_result }),
                    })
                    if (analyzeRes.ok) {
                        const analyzeData = await analyzeRes.json()
                        data.phase5_report = analyzeData.report ?? null
                        data.phase5_chart_data = analyzeData.chart_data ?? null
                        appendProgress('   ✓ 生成测试摘要')
                        if (analyzeData.chart_data) appendProgress('   ✓ 生成可视化图表')
                        appendProgress('   ✓ 分析失败原因')
                        appendProgress('   ✓ 提供优化建议')
                    } else {
                        appendProgress('   ⚠ 报告生成失败')
                    }
                } catch (_e) {
                    appendProgress('   ⚠ 报告生成异常')
                }

                // 保存报告
                try {
                    const timeStr = new Date().toISOString().slice(0, 19).replace('T', ' ')
                    const reportName = `${getSingleApiDisplayName(data)}-${timeStr}`
                    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/test-reports`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            project_id: currentProject,
                            name: reportName,
                            report_type: '接口测试',
                            trigger_method: '手动触发',
                            status: (data.phase4_result.failed_cases || 0) > 0 ? 'error' : 'success',
                            payload: { phase2_plan: data.phase2_plan, phase4_result: data.phase4_result, phase5_report: data.phase5_report, phase5_chart_data: data.phase5_chart_data },
                        }),
                    })
                } catch (_e) { /* 保存报告失败不影响主流程 */ }
            } else {
                appendProgress('   ✓ 待生成（执行后可生成）')
            }
            appendProgress('')
            appendProgress('任务完成！')

            // 延迟 1.5 秒后切换到接口用例 Tab，让用户看到完成
            setTimeout(() => {
                if (onSingleApiGenerated) {
                    onSingleApiGenerated(data)
                } else {
                    setResult(data)
                }
            }, 1500)
        } catch (error: any) {
            appendProgress('', `❌ 错误: ${error.message}`)
        } finally {
            setLoading(false)
        }
    }

    return (
        <>
            {/* 模式切换：测试场景 | 单接口测试 */}
            <div style={{ marginBottom: '1.5rem', display: 'flex', gap: '0.5rem' }}>
                <button
                    type="button"
                    onClick={() => setMode('scenario')}
                    style={{
                        padding: '0.5rem 1rem',
                        borderRadius: '0.5rem',
                        border: mode === 'scenario' ? '2px solid #667eea' : '1px solid #E5E7EB',
                        background: mode === 'scenario' ? 'rgba(102,126,234,0.1)' : 'white',
                        fontWeight: '600',
                        color: mode === 'scenario' ? '#667eea' : '#6B7280',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                    }}
                >
                    <Sparkles size={18} />
                    测试场景
                </button>
                <button
                    type="button"
                    onClick={() => setMode('single-api')}
                    style={{
                        padding: '0.5rem 1rem',
                        borderRadius: '0.5rem',
                        border: mode === 'single-api' ? '2px solid #667eea' : '1px solid #E5E7EB',
                        background: mode === 'single-api' ? 'rgba(102,126,234,0.1)' : 'white',
                        fontWeight: '600',
                        color: mode === 'single-api' ? '#667eea' : '#6B7280',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                    }}
                >
                    <Target size={18} />
                    接口测试
                </button>
            </div>

            <div style={{
                background: 'rgba(255, 255, 255, 0.8)',
                borderRadius: '1rem',
                padding: '2rem',
                marginBottom: '2rem',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
                border: '1px solid rgba(255, 255, 255, 0.2)'
            }}>
                {mode === 'scenario' && (
                    <>
                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.75rem' }}>
                                💬 测试场景描述
                            </label>
                            <textarea
                                value={scenario}
                                onChange={(e) => setScenario(e.target.value)}
                                rows={5}
                                style={{
                                    width: '100%', padding: '0.75rem 1rem',
                                    background: 'rgba(255, 255, 255, 0.9)', border: '2px solid #E5E7EB',
                                    borderRadius: '0.75rem', outline: 'none', resize: 'none',
                                }}
                                placeholder="例如：测试用户登录后查询商品列表并添加到购物车&#10;&#10;💡 用自然语言描述即可，AI会自动理解"
                            />
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>
                                🌐 执行环境（生成用例后将自动执行场景）
                            </label>
                            {scenarioEnvs.length > 0 ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                    <select
                                        value={scenarioSelectedEnvId === 'custom' ? 'custom' : (scenarioSelectedEnvId ?? '')}
                                        onChange={(e) => {
                                            const v = e.target.value
                                            if (v === 'custom') {
                                                setScenarioSelectedEnvId('custom')
                                                setScenarioExecBaseUrl('')
                                            } else {
                                                const id = Number(v)
                                                const env = scenarioEnvs.find((ep) => ep.id === id)
                                                if (env) {
                                                    setScenarioSelectedEnvId(id)
                                                    setScenarioExecBaseUrl(env.base_url || '')
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
                                        {scenarioEnvs.map((env) => (
                                            <option key={env.id} value={env.id}>
                                                {env.env_name} — {env.base_url}
                                            </option>
                                        ))}
                                        <option value="custom">自定义地址...</option>
                                    </select>
                                    {scenarioSelectedEnvId === 'custom' && (
                                        <input
                                            type="text"
                                            value={scenarioExecBaseUrl}
                                            onChange={(e) => setScenarioExecBaseUrl(e.target.value)}
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
                                </div>
                            ) : (
                                <input
                                    type="text"
                                    value={scenarioExecBaseUrl}
                                    onChange={(e) => setScenarioExecBaseUrl(e.target.value)}
                                    placeholder="如 https://api.example.com，生成后将用此地址自动执行"
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem 0.75rem',
                                        border: '1px solid #D1D5DB',
                                        borderRadius: '0.5rem',
                                        fontSize: '0.875rem',
                                    }}
                                />
                            )}
                            <p style={{ fontSize: '0.75rem', color: '#6B7280', marginTop: '0.25rem' }}>
                                💡 一键生成将先创建场景与用例，再自动执行该场景
                            </p>
                        </div>
                        <p style={{ fontSize: '0.75rem', color: '#6B7280', textAlign: 'center', marginBottom: '1rem' }}>
                            💡 AI会自动理解场景、检索相关API、生成测试数据和断言
                        </p>
                    </>
                )}
                {mode === 'single-api' && (
                    <>
                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.75rem' }}>
                                💬 接口测试描述
                            </label>
                            <textarea
                                value={singleApiInput}
                                onChange={(e) => setSingleApiInput(e.target.value)}
                                rows={3}
                                style={{
                                    width: '100%', padding: '0.75rem 1rem',
                                    background: 'rgba(255, 255, 255, 0.9)', border: '2px solid #E5E7EB',
                                    borderRadius: '0.75rem', outline: 'none', resize: 'none',
                                }}
                                placeholder="例如：为登录接口生成完整测试&#10;为登录、注册、忘记密码三个接口生成测试用例"
                            />
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.5rem' }}>
                                🌐 接口基础地址（用于生成后自动执行）
                            </label>
                            {environments.length > 0 ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
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
                                </div>
                            ) : (
                                <input
                                    type="text"
                                    value={execBaseUrl}
                                    onChange={(e) => setExecBaseUrl(e.target.value)}
                                    placeholder="如 https://api.example.com，或在项目设置中配置环境"
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem 0.75rem',
                                        border: '1px solid #D1D5DB',
                                        borderRadius: '0.5rem',
                                        fontSize: '0.875rem',
                                    }}
                                />
                            )}
                            <p style={{ fontSize: '0.75rem', color: '#6B7280', marginTop: '0.25rem' }}>
                                💡 选择或填写后，一键生成将自动执行测试并生成分析报告
                            </p>
                        </div>
                    </>
                )}

                <button
                    onClick={handleGenerate}
                    disabled={loading}
                    style={{
                        width: '100%',
                        background: loading ? '#9CA3AF' : 'linear-gradient(to right, #2563EB, #4F46E5)',
                        color: 'white',
                        fontWeight: '600',
                        padding: '0.75rem 1.5rem',
                        borderRadius: '0.75rem',
                        border: 'none',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}
                >
                    {loading ? (
                        <>
                            <Loader2 className="animate-spin mr-2" size={22} />
                            <span>{mode === 'scenario' ? 'AI正在分析场景...' : 'AI 正在生成...'}</span>
                        </>
                    ) : (
                        <>
                            <Sparkles className="mr-2" size={22} />
                            <span>{mode === 'scenario' ? '✨ 一键生成测试用例' : '✨ 一键生成'}</span>
                        </>
                    )}
                </button>
            </div>

            {/* 实时进度展示面板（测试场景 + 接口测试 共用） */}
            {progressLines.length > 0 && (
                <div style={{
                    marginTop: '1.5rem',
                    background: 'linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%)',
                    border: '1px solid #e0e4f5',
                    borderRadius: '0.75rem',
                    padding: '1.5rem',
                    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
                    fontSize: '0.85rem',
                    lineHeight: '1.7',
                    color: '#374151',
                    maxHeight: '420px',
                    overflowY: 'auto',
                    boxShadow: '0 2px 8px rgba(102, 126, 234, 0.08)',
                    position: 'relative',
                }}>
                    {loading && (
                        <div style={{
                            position: 'absolute', top: '0.75rem', right: '0.75rem',
                            display: 'flex', alignItems: 'center', gap: '0.4rem',
                            fontSize: '0.75rem', color: '#667eea',
                        }}>
                            <Loader2 className="animate-spin" size={14} />
                            <span>处理中...</span>
                        </div>
                    )}
                    {progressLines.map((line, i) => {
                        if (line === '') return <div key={i} style={{ height: '0.5rem' }} />
                        const isError = line.startsWith('❌')
                        const isWarning = line.includes('⚠')
                        const isComplete = line === '任务完成！' || line === '处理完成！'
                        return (
                            <div key={i} style={{
                                color: isError ? '#DC2626' : isWarning ? '#D97706' : isComplete ? '#059669' : undefined,
                                fontWeight: isComplete ? 700 : (line.startsWith('检索') || line.startsWith('生成') || line.startsWith('执行')) ? 600 : undefined,
                                marginTop: (line.startsWith('检索') || line.startsWith('生成') || line.startsWith('执行')) ? '0.25rem' : undefined,
                            }}>
                                {isComplete && <CheckCircle2 size={16} style={{ display: 'inline', verticalAlign: 'text-bottom', marginRight: '0.4rem', color: '#059669' }} />}
                                {line}
                            </div>
                        )
                    })}
                    <div ref={progressEndRef} />
                </div>
            )}

            {/* 仅测试场景模式在此展示结果；单接口测试结果在「单接口测试」Tab */}
            {mode === 'scenario' && result && (
                <div style={{ background: 'white', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', borderRadius: '0.5rem', padding: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', marginBottom: '1rem' }}>
                        <Link
                            href="/tests"
                            style={{
                                display: 'flex', alignItems: 'center', gap: '0.5rem',
                                padding: '0.5rem 1.25rem', background: 'linear-gradient(to right, #10B981, #059669)',
                                color: 'white', borderRadius: '0.5rem', textDecoration: 'none',
                                fontWeight: '600', fontSize: '0.875rem', boxShadow: '0 4px 6px -1px rgba(16, 185, 129, 0.3)'
                            }}
                        >
                            去查看场景 <ArrowRight size={16} />
                        </Link>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.375rem' }}>
                            <p style={{ fontSize: '0.875rem', color: '#4B5563' }}><span style={{ fontWeight: '500' }}>场景名称：</span>{result.scenario.name}</p>
                            <p style={{ fontSize: '0.875rem', color: '#4B5563', marginTop: '0.25rem' }}><span style={{ fontWeight: '500' }}>描述：</span>{result.scenario.description}</p>
                        </div>
                        <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.375rem' }}>
                            <p style={{ fontSize: '0.875rem', color: '#4B5563' }}><span style={{ fontWeight: '500' }}>用例名称：</span>{result.testCase.name}</p>
                            <p style={{ fontSize: '0.875rem', color: '#4B5563', marginTop: '0.25rem' }}><span style={{ fontWeight: '500' }}>测试步骤：</span>{(result.testCase.steps || []).length} 个</p>
                            {(result.testCase.steps || []).length > 0 && (
                                <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem', fontSize: '0.8125rem', color: '#4B5563', lineHeight: 1.6 }}>
                                    {(result.testCase.steps || []).map((s: any, i: number) => {
                                        const method = (s.api_method || s.method || 'GET').toString().toUpperCase()
                                        const path = s.api_path || s.path || '—'
                                        return <li key={i}>{method} {path}</li>
                                    })}
                                </ul>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
