'use client'

import { useState } from 'react'
import { Sparkles, Loader2, CheckCircle2, ArrowRight, Target } from 'lucide-react'
import Link from 'next/link'
import { useProject } from '../../contexts/ProjectContext'

type Mode = 'scenario' | 'single-api'

type Props = {
    /** 单接口测试生成成功后调用，结果会放到「单接口测试」Tab 并自动切过去 */
    onSingleApiGenerated?: (data: any) => void
}

export default function AIGenerationTab({ onSingleApiGenerated }: Props) {
    const { currentProject } = useProject()
    const [mode, setMode] = useState<Mode>('scenario')
    const [scenario, setScenario] = useState('')
    const [singleApiInput, setSingleApiInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<any>(null)

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

        // 单接口测试：生成后把结果交给「单接口测试」Tab 并切过去
        if (!singleApiInput.trim()) {
            alert('请输入单接口测试描述，例如：为登录接口生成完整测试')
            return
        }
        setLoading(true)
        setResult(null)
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/single-api/full-pipeline`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    natural_language_input: singleApiInput.trim(),
                    project_id: currentProject,
                    base_url: '',
                    environment: 'test',
                    run_execution: true,
                }),
            })
            if (!res.ok) {
                const err = await res.json().catch(() => ({}))
                throw new Error(err.detail || err.message || '单接口流水线失败')
            }
            const data = await res.json()
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
                    单接口测试
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
                                💬 单接口测试描述
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
                                placeholder="例如：为登录接口生成完整测试&#10;为手机登录接口生成测试用例"
                            />
                        </div>
                        <p style={{ fontSize: '0.75rem', color: '#6B7280', textAlign: 'center', marginBottom: '1rem' }}>
                            💡 生成后将自动跳转到「单接口测试」Tab 查看结果并执行、分析
                        </p>
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
                            <span>{mode === 'scenario' ? 'AI正在分析场景...' : 'AI 正在生成单接口测试...'}</span>
                        </>
                    ) : (
                        <>
                            <Sparkles className="mr-2" size={22} />
                            <span>{mode === 'scenario' ? '✨ 一键生成测试用例' : '✨ 生成单接口测试（结果在单接口测试 Tab）'}</span>
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
