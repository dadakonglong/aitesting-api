'use client'

import { useState } from 'react'
import { Sparkles, Loader2, CheckCircle2, ArrowRight } from 'lucide-react'
import Link from 'next/link'
import { useProject } from '../../contexts/ProjectContext'

export default function AIGenerationTab() {
    const { currentProject } = useProject()
    const [scenario, setScenario] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<any>(null)

    const handleGenerate = async () => {
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
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ data_strategy: 'smart' }),
                }
            )

            if (!caseRes.ok) throw new Error('生成测试用例失败')
            const caseData = await caseRes.json()

            setResult({
                scenario: scenarioData,
                testCase: caseData,
            })
        } catch (error: any) {
            alert(`错误: ${error.message}`)
        } finally {
            setLoading(false)
        }
    }

    return (
        <>
            {/* 输入区域 */}
            <div style={{
                background: 'rgba(255, 255, 255, 0.8)',
                backdropFilter: 'blur(10px)',
                borderRadius: '1rem',
                padding: '2rem',
                marginBottom: '2rem',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
                border: '1px solid rgba(255, 255, 255, 0.2)'
            }}>
                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', color: '#374151', marginBottom: '0.75rem' }}>
                        💬 测试场景描述
                    </label>
                    <div style={{ position: 'relative' }}>
                        <textarea
                            value={scenario}
                            onChange={(e) => setScenario(e.target.value)}
                            rows={5}
                            style={{
                                width: '100%',
                                padding: '0.75rem 1rem',
                                background: 'rgba(255, 255, 255, 0.9)',
                                border: '2px solid #E5E7EB',
                                borderRadius: '0.75rem',
                                outline: 'none',
                                resize: 'none',
                                transition: 'all 0.2s'
                            }}
                            placeholder="例如：测试用户登录后查询商品列表并添加到购物车&#10;&#10;💡 提示：用自然语言描述即可，AI会自动理解"
                            onFocus={(e) => {
                                e.target.style.borderColor = '#3B82F6'
                                e.target.style.boxShadow = '0 0 0 4px rgba(59, 130, 246, 0.1)'
                            }}
                            onBlur={(e) => {
                                e.target.style.borderColor = '#E5E7EB'
                                e.target.style.boxShadow = 'none'
                            }}
                        />
                        <div style={{ position: 'absolute', bottom: '0.75rem', right: '0.75rem', fontSize: '0.75rem', color: '#9CA3AF' }}>
                            {scenario.length} 字符
                        </div>
                    </div>
                </div>

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
                        transition: 'all 0.2s',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}
                    onMouseEnter={(e) => {
                        if (!loading) {
                            e.currentTarget.style.transform = 'translateY(-2px)'
                            e.currentTarget.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
                        }
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)'
                        e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)'
                    }}
                >
                    {loading ? (
                        <>
                            <Loader2 className="animate-spin mr-2" size={22} />
                            <span>AI正在分析场景...</span>
                        </>
                    ) : (
                        <>
                            <Sparkles className="mr-2" size={22} />
                            <span>✨ 一键生成测试用例</span>
                        </>
                    )}
                </button>

                <p style={{ fontSize: '0.75rem', color: '#6B7280', textAlign: 'center', marginTop: '1rem' }}>
                    💡 AI会自动理解场景、检索相关API、生成测试数据和断言
                </p>
            </div>

            {/* 结果展示 */}
            {result && (
                <div style={{
                    background: 'white',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                    borderRadius: '0.5rem',
                    padding: '1.5rem'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem' }}>
                        <CheckCircle2 style={{ color: '#10B981', marginRight: '0.5rem' }} size={24} />
                        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#111827', flex: 1 }}>
                            生成成功！
                        </h2>
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
                        <div>
                            <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#1F2937', marginBottom: '0.5rem' }}>
                                场景信息
                            </h3>
                            <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.375rem' }}>
                                <p style={{ fontSize: '0.875rem', color: '#4B5563' }}>
                                    <span style={{ fontWeight: '500' }}>场景名称：</span>
                                    {result.scenario.name}
                                </p>
                                <p style={{ fontSize: '0.875rem', color: '#4B5563', marginTop: '0.25rem' }}>
                                    <span style={{ fontWeight: '500' }}>描述：</span>
                                    {result.scenario.description}
                                </p>
                            </div>
                        </div>

                        <div>
                            <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#1F2937', marginBottom: '0.5rem' }}>
                                测试用例
                            </h3>
                            <div style={{ background: '#F9FAFB', padding: '1rem', borderRadius: '0.375rem' }}>
                                <p style={{ fontSize: '0.875rem', color: '#4B5563' }}>
                                    <span style={{ fontWeight: '500' }}>用例名称：</span>
                                    {result.testCase.name}
                                </p>
                                <p style={{ fontSize: '0.875rem', color: '#4B5563', marginTop: '0.25rem' }}>
                                    <span style={{ fontWeight: '500' }}>测试步骤：</span>
                                    {result.testCase.steps?.length || 0} 个
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
