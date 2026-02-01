'use client'

import { useState, useEffect } from 'react'
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

    const handleGenerate = async () => {
        if (mode === 'scenario') {
            if (!scenario.trim()) {
                alert('请输入测试场景')
                return
            }
            setLoading(true)
            setResult(null)
            try {
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
                const caseRes = await fetch(
                    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/scenarios/${scenarioData.id}/generate-case`,
                    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ data_strategy: 'smart' }) }
                )
                if (!caseRes.ok) {
                    const errorData = await caseRes.json().catch(() => ({}))
                    throw new Error(errorData.detail || errorData.message || '生成测试用例失败')
                }
                const caseData = await caseRes.json()
                setResult({ scenario: scenarioData, testCase: caseData })
            } catch (error: any) {
                alert(`错误: ${error.message}`)
            } finally {
                setLoading(false)
            }
            return
        }

        // 接口测试：生成后把结果交给「接口测试」Tab 并切过去
        if (!singleApiInput.trim()) {
            alert('请输入接口测试描述，例如：为登录接口生成完整测试')
            return
        }
        setLoading(true)
        setResult(null)
        try {
            // 获取 base_url：优先用选中项，否则从环境列表取
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

            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/single-api/full-pipeline`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    natural_language_input: singleApiInput.trim(),
                    project_id: currentProject,
                    base_url: baseUrl,
                    environment: 'test',
                    run_execution: true,
                }),
            })
            if (!res.ok) {
                const err = await res.json().catch(() => ({}))
                throw new Error(err.detail || err.message || '单接口流水线失败')
            }
            let data = await res.json()

            // 若流水线未执行（无 base_url 或后端未找到），自动补跑 execute + analyze
            if (data.phase2_plan?.endpoints?.length && !data.phase4_result) {
                let runBaseUrl = baseUrl
                if (!runBaseUrl && environments.length > 0) {
                    const env = environments.find((e) => e.is_default === 1) || environments[0]
                    runBaseUrl = (env?.base_url || '').trim()
                }
                if (!runBaseUrl) {
                    const envRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/projects/${encodeURIComponent(currentProject)}/environments`)
                    if (envRes.ok) {
                        const envList: EnvItem[] = await envRes.json()
                        if (Array.isArray(envList) && envList.length > 0) {
                            runBaseUrl = ((envList.find((e) => e.is_default === 1) || envList[0])?.base_url || '').trim()
                        }
                    }
                }
                if (runBaseUrl) {
                    try {
                        const execRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/single-api/execute`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                project_id: currentProject,
                                base_url: runBaseUrl,
                                environment: 'test',
                                plan: data.phase2_plan,
                                generated_code: data.phase3_code || undefined,
                            }),
                        })
                        if (execRes.ok) {
                            const suiteResult = await execRes.json()
                            const analyzeRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/single-api/analyze`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ suite_result: suiteResult }),
                            })
                            if (analyzeRes.ok) {
                                const analyzeData = await analyzeRes.json()
                                data = {
                                    ...data,
                                    phase4_result: suiteResult,
                                    phase5_report: analyzeData.report ?? null,
                                    phase5_chart_data: analyzeData.chart_data ?? null,
                                }
                                const timeStr = new Date().toISOString().slice(0, 19).replace('T', ' ')
                                const reportName = `${getSingleApiDisplayName(data)}-${timeStr}`
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
                                            payload: { phase2_plan: data.phase2_plan, phase4_result: suiteResult, phase5_report: analyzeData.report, phase5_chart_data: analyzeData.chart_data },
                                        }),
                                    })
                                    data._reportSaved = true
                                } catch (_e) {
                                    /* 保存报告失败不影响主流程 */
                                }
                            } else {
                                data = { ...data, phase4_result: suiteResult, phase5_report: null, phase5_chart_data: null }
                            }
                        }
                    } catch (_e) {
                        /* 补跑失败时仍返回原始数据 */
                    }
                }
            }

            if (data.phase4_result && data.phase2_plan && !data._reportSaved) {
                const timeStr = new Date().toISOString().slice(0, 19).replace('T', ' ')
                const reportName = `${getSingleApiDisplayName(data)}-${timeStr}`
                try {
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
                } catch (_e) {
                    /* 保存报告失败不影响主流程 */
                }
            }

            if (onSingleApiGenerated) {
                onSingleApiGenerated(data)
            } else {
                setResult(data)
            }
        } catch (error: any) {
            alert(`错误: ${error.message}`)
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

            {/* 仅测试场景模式在此展示结果；单接口测试结果在「单接口测试」Tab */}
            {mode === 'scenario' && result && (
                <div style={{ background: 'white', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', borderRadius: '0.5rem', padding: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem' }}>
                        <CheckCircle2 style={{ color: '#10B981', marginRight: '0.5rem' }} size={24} />
                        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#111827', flex: 1 }}>生成成功！</h2>
                        <Link
                            href="/tests"
                            style={{
                                display: 'flex', alignItems: 'center', gap: '0.5rem',
                                padding: '0.5rem 1.25rem', background: 'linear-gradient(to right, #10B981, #059669)',
                                color: 'white', borderRadius: '0.5rem', textDecoration: 'none',
                                fontWeight: '600', fontSize: '0.875rem', boxShadow: '0 4px 6px -1px rgba(16, 185, 129, 0.3)'
                            }}
                        >
                            去执行场景 <ArrowRight size={16} />
                        </Link>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.375rem' }}>
                            <p style={{ fontSize: '0.875rem', color: '#4B5563' }}><span style={{ fontWeight: '500' }}>场景名称：</span>{result.scenario.name}</p>
                            <p style={{ fontSize: '0.875rem', color: '#4B5563', marginTop: '0.25rem' }}><span style={{ fontWeight: '500' }}>描述：</span>{result.scenario.description}</p>
                        </div>
                        <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.375rem' }}>
                            <p style={{ fontSize: '0.875rem', color: '#4B5563' }}><span style={{ fontWeight: '500' }}>用例名称：</span>{result.testCase.name}</p>
                            <p style={{ fontSize: '0.875rem', color: '#4B5563', marginTop: '0.25rem' }}><span style={{ fontWeight: '500' }}>测试步骤：</span>{result.testCase.steps?.length || 0} 个</p>
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
