'use client'

import { useState, useEffect, useRef } from 'react'
import { Sparkles, Loader2, CheckCircle2, ArrowRight, Target } from 'lucide-react'
import Link from 'next/link'
import { useProject } from '../../contexts/ProjectContext'
import { getSingleApiDisplayName } from '../utils'
import ThinkingProcess from './ThinkingProcess'

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
    // 将进度同时存入 ref，便于生成完成后整体保存到后端
    const progressRef = useRef<string[]>([])
    // 测试场景模式：环境配置（生成后自动执行用）
    const [scenarioEnvs, setScenarioEnvs] = useState<EnvItem[]>([])
    const [scenarioSelectedEnvId, setScenarioSelectedEnvId] = useState<number | 'custom' | null>(null)
    const [scenarioExecBaseUrl, setScenarioExecBaseUrl] = useState('')
    // 思考过程状态
    const [thinkingPhase, setThinkingPhase] = useState<string>('')
    const [thinkingSteps, setThinkingSteps] = useState<Array<{ id: string; title: string; status: 'thinking' | 'completed'; details?: string[] }>>([])
    // 跟踪所有思考阶段是否完成（用于控制进度面板的显示）
    const [allThinkingCompleted, setAllThinkingCompleted] = useState(false)
    const allThinkingCompletedRef = useRef(false) // 使用ref确保在闭包中能访问到最新值

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
            setAllThinkingCompleted(false) // 重置思考完成状态
            allThinkingCompletedRef.current = false // 同时更新ref
            const initialLines: string[] = [] // 初始不显示进度面板
            progressRef.current = initialLines
            setProgressLines(initialLines)

            const appendProgress = (...lines: string[]) => {
                if (allThinkingCompletedRef.current) {
                    setProgressLines((prev) => {
                        const next = [...prev, ...lines]
                        progressRef.current = next
                        return next
                    })
                    setTimeout(() => progressEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
                } else {
                    // 思考过程中，先保存到ref，等思考完成后再显示
                    progressRef.current = [...(progressRef.current || []), ...lines]
                }
            }

            try {
                // ---------- 阶段一：创建测试场景 ----------
                appendProgress('创建测试场景...')

                // 展示思考过程 - 阶段一：场景理解
                setThinkingPhase('场景理解')
                setThinkingSteps([
                    { id: '1', title: '分析用户描述的业务场景', status: 'thinking', details: ['解析自然语言描述', '识别测试意图和目标'] },
                    { id: '2', title: '提取关键实体和动作', status: 'thinking', details: ['识别涉及的接口', '提取业务动作序列'] },
                    { id: '3', title: '确定预期结果', status: 'thinking', details: ['分析业务目标', '定义成功标准'] },
                ])

                // 等待思考步骤显示出来（给用户时间看到思考过程）
                await new Promise(resolve => setTimeout(resolve, 1000))

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

                // API请求完成后，更新思考步骤状态为completed
                setThinkingSteps([
                    { id: '1', title: '分析用户描述的业务场景', status: 'completed', details: ['解析自然语言描述', '识别测试意图和目标'] },
                    { id: '2', title: '提取关键实体和动作', status: 'completed', details: ['识别涉及的接口', '提取业务动作序列'] },
                    { id: '3', title: '确定预期结果', status: 'completed', details: ['分析业务目标', '定义成功标准'] },
                ])

                // 等待用户看到完成状态
                await new Promise(resolve => setTimeout(resolve, 1000))

                appendProgress('   ✓ 提取意图与实体')

                // 结构化展示意图分析结果（意图 / 实体 / 动作 / 预期），直接作为生成过程的一部分
                try {
                    let nlu: any = scenarioData.nlu_result
                    if (nlu && typeof nlu === 'string') {
                        try {
                            nlu = JSON.parse(nlu)
                        } catch {
                            // ignore
                        }
                    }
                    if (nlu && typeof nlu === 'object') {
                        if (nlu.intent) {
                            appendProgress(`   意图：${nlu.intent}`)
                        }
                        const entitiesRaw = Array.isArray(nlu.entities) ? nlu.entities : []
                        const entities = entitiesRaw
                            .map((e: any) => {
                                if (typeof e === 'string') return e
                                if (!e || typeof e !== 'object') return ''
                                return e.name || e.type || e.label || ''
                            })
                            .filter((x: string) => x)
                        if (entities.length > 0) {
                            appendProgress(`   关键实体：${entities.join('，')}`)
                        }
                        const actionsRaw = Array.isArray(nlu.actions) ? nlu.actions : []
                        if (actionsRaw.length > 0) {
                            appendProgress('   动作拆解：')
                            actionsRaw.forEach((a: any, idx: number) => {
                                let text = ''
                                if (typeof a === 'string') text = a
                                else if (a && typeof a === 'object') text = a.name || a.action || a.description || ''
                                appendProgress(`      ${idx + 1}. ${text || '（未命名动作）'}`)
                            })
                        }
                        const expectedRaw = Array.isArray(nlu.expected_results) ? nlu.expected_results : []
                        if (expectedRaw.length > 0) {
                            appendProgress('   预期结果：')
                            expectedRaw.forEach((r: any, idx: number) => {
                                let text = ''
                                if (typeof r === 'string') text = r
                                else if (r && typeof r === 'object') text = r.description || r.expectation || ''
                                appendProgress(`      ${idx + 1}. ${text || '（未描述）'}`)
                            })
                        }
                    }
                } catch {
                    // 意图展示失败不影响主流程
                }

                appendProgress('   ✓ 场景已保存')
                appendProgress('')

                // 等待一小段时间，让用户看到阶段一完成
                await new Promise(resolve => setTimeout(resolve, 500))

                // 清除阶段一的思考过程
                setThinkingPhase('')
                setThinkingSteps([])
                await new Promise(resolve => setTimeout(resolve, 300))

                // ---------- 阶段二：生成测试用例（展示与后端一致的子步骤） ----------
                appendProgress('生成测试用例...')

                // 展示思考过程 - 阶段二：场景编排
                setThinkingPhase('场景编排')
                setThinkingSteps([
                    { id: '4', title: '检索相关API接口', status: 'thinking', details: ['使用向量语义检索', '匹配业务场景相关的接口'] },
                    { id: '5', title: '分析接口依赖关系', status: 'thinking', details: ['查询知识图谱', '识别接口调用顺序'] },
                    { id: '6', title: '编排测试步骤序列', status: 'thinking', details: ['生成步骤顺序', '配置参数映射关系'] },
                    { id: '7', title: '优化参数传递', status: 'thinking', details: ['提取Token和Session', '配置动态头映射'] },
                ])

                // 等待思考步骤显示出来（给用户时间看到思考过程）
                await new Promise(resolve => setTimeout(resolve, 2000))

                appendProgress('   · 检索项目接口...')
                const caseResPromise = fetch(
                    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/scenarios/${scenarioData.id}/generate-case`,
                    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ data_strategy: 'smart' }) }
                )
                // 在请求进行中按顺序更新思考步骤状态（与后端处理时间对应）
                const t1 = setTimeout(() => {
                    appendProgress('   ✓ 检索项目接口')
                    setThinkingSteps((prev) => prev.map((s) => s.id === '4' ? { ...s, status: 'completed' } : s))
                    appendProgress('   · 查找接口依赖关系...')
                }, 1500)
                const t2 = setTimeout(() => {
                    appendProgress('   ✓ 查找接口依赖关系')
                    setThinkingSteps((prev) => prev.map((s) => s.id === '5' ? { ...s, status: 'completed' } : s))
                    appendProgress('   · 编排测试步骤与断言...')
                }, 3000)
                const t3 = setTimeout(() => {
                    appendProgress('   ✓ 编排测试步骤与断言')
                    setThinkingSteps((prev) => prev.map((s) => s.id === '6' ? { ...s, status: 'completed' } : s))
                    appendProgress('   · 提取参数与映射...')
                }, 5000)
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

                // API请求完成后，完成所有思考步骤
                setThinkingSteps((prev) => prev.map((s) => ({ ...s, status: 'completed' as const })))

                // 等待用户看到完成状态
                await new Promise(resolve => setTimeout(resolve, 1000))

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
                    const name = s.description || s.api_name || s.name || ''
                    appendProgress(`   ${i + 1}. ${method} ${path}${name ? `（${name}）` : ''}`)

                    // 显示参数映射
                    const paramMappings = s.param_mappings || []
                    if (paramMappings.length > 0) {
                        appendProgress(`      参数映射（${paramMappings.length} 个）：`)
                        paramMappings.forEach((mapping: any) => {
                            const fromStep = mapping.from_step || '?'
                            const fromField = mapping.from_field || '?'
                            const toField = mapping.to_field || '?'
                            const toType = mapping.to_type || 'params'
                            const toTypeLabel = toType === 'headers' ? '请求头' : toType === 'params' ? '请求参数' : 'URL参数'
                            appendProgress(`        步骤${fromStep}.${fromField} → ${toTypeLabel}.${toField}`)
                        })
                    } else {
                        appendProgress(`      参数映射：无`)
                    }
                })
                appendProgress('')

                // 等待用户看到阶段二完成
                await new Promise(resolve => setTimeout(resolve, 1000))

                // 清除阶段二的思考过程
                setThinkingPhase('')
                setThinkingSteps([])
                await new Promise(resolve => setTimeout(resolve, 300))

                // ---------- 阶段三：自动执行场景 ----------
                appendProgress('执行场景...')

                // 展示思考过程 - 阶段三：测试执行与结果分析
                setThinkingPhase('测试执行与结果分析')
                setThinkingSteps([
                    { id: '8', title: '执行测试步骤', status: 'thinking', details: ['按顺序执行接口调用', '处理参数映射'] },
                    { id: '9', title: '分析执行结果', status: 'thinking', details: ['检查HTTP状态码', '验证业务状态码'] },
                    { id: '10', title: '生成分析报告', status: 'thinking', details: ['分析失败原因', '提供改进建议'] },
                ])

                // 等待思考步骤显示出来
                await new Promise(resolve => setTimeout(resolve, 1000))

                // 调试：打印返回的数据
                console.log('场景生成返回数据:', JSON.stringify(caseData, null, 2))
                console.log('execution存在:', !!caseData.execution)
                console.log('analysis存在:', !!caseData.analysis)

                // 使用后端返回的执行结果和分析结果（如果存在）
                // 注意：即使执行失败，后端也应该返回execution和analysis，避免重复执行
                if (caseData.execution && caseData.analysis) {
                    const execData = caseData.execution
                    const analysisData = caseData.analysis

                    // 执行完成后，更新思考步骤状态 - 阶段三
                    setThinkingSteps((prev) => prev.map((s) => {
                        if (s.id === '8') return { ...s, status: 'completed' }
                        if (s.id === '9') return { ...s, status: 'completed' }
                        if (s.id === '10') return { ...s, status: 'completed' }
                        return s
                    }))

                    // 等待用户看到完成状态
                    await new Promise(resolve => setTimeout(resolve, 1000))

                    // 显示执行结果
                    const status = execData.status === 'success' ? '全部通过' : '存在失败'
                    appendProgress(`   ✓ 执行完成：${status}`)
                    appendProgress('')
                    appendProgress('执行结果：')
                    appendProgress(`   总步骤数：${analysisData.total_steps || 0}`)
                    appendProgress(`   通过步骤：${analysisData.passed_steps || 0}`)
                    appendProgress(`   失败步骤：${analysisData.failed_steps || 0}`)

                    // 显示每个步骤的执行结果
                    if (analysisData.analysis && analysisData.analysis.length > 0) {
                        appendProgress('')
                        appendProgress('步骤详情：')
                        analysisData.analysis.forEach((stepAnalysis: any) => {
                            const stepStatus = stepAnalysis.status === 'passed' ? '✓' : '✗'
                            const stepStatusText = stepAnalysis.status === 'passed' ? '通过' : '失败'
                            appendProgress(`   ${stepStatus} 步骤${stepAnalysis.step_order}：${stepAnalysis.api_path || '—'}`)
                            appendProgress(`     状态：${stepStatusText}`)
                            if (stepAnalysis.http_status) {
                                appendProgress(`     HTTP状态码：${stepAnalysis.http_status}`)
                            }
                            if (stepAnalysis.business_code !== null && stepAnalysis.business_code !== undefined) {
                                appendProgress(`     业务状态码：${stepAnalysis.business_code}`)
                            }
                            if (stepAnalysis.message) {
                                appendProgress(`     消息：${stepAnalysis.message}`)
                            }
                            if (stepAnalysis.failure_reason) {
                                appendProgress(`     失败原因：${stepAnalysis.failure_reason}`)
                            }
                        })
                    }

                    // 显示结果分析摘要
                    if (analysisData.summary) {
                        appendProgress('')
                        appendProgress('结果分析：')
                        appendProgress(`   ${analysisData.summary}`)
                    }

                    // 显示大模型深度分析结果
                    if (analysisData.ai_analysis) {
                        const aiAnalysis = analysisData.ai_analysis
                        appendProgress('')
                        appendProgress('AI深度分析：')

                        if (aiAnalysis.overview) {
                            appendProgress(`   执行概览：${aiAnalysis.overview}`)
                        }

                        if (aiAnalysis.failed_analysis && aiAnalysis.failed_analysis.length > 0) {
                            appendProgress('')
                            appendProgress('   失败步骤深度分析：')
                            aiAnalysis.failed_analysis.forEach((failed: any) => {
                                appendProgress(`     步骤${failed.step_order}（${failed.api_path || '—'}）：`)
                                if (failed.root_cause) {
                                    appendProgress(`       根因：${failed.root_cause}`)
                                }
                                if (failed.suggestions) {
                                    appendProgress(`       建议：${failed.suggestions}`)
                                }
                            })
                        }

                        if (aiAnalysis.success_evaluation) {
                            appendProgress('')
                            appendProgress(`   成功步骤评估：${aiAnalysis.success_evaluation}`)
                        }

                        if (aiAnalysis.business_flow_completeness) {
                            appendProgress('')
                            appendProgress(`   业务流程完整性：${aiAnalysis.business_flow_completeness}`)
                        }

                        if (aiAnalysis.improvement_suggestions && aiAnalysis.improvement_suggestions.length > 0) {
                            appendProgress('')
                            appendProgress('   改进建议：')
                            aiAnalysis.improvement_suggestions.forEach((suggestion: string, idx: number) => {
                                appendProgress(`     ${idx + 1}. ${suggestion}`)
                            })
                        }
                    }

                    // 等待一小段时间，让用户看到阶段三完成
                    await new Promise(resolve => setTimeout(resolve, 500))

                    // 清除阶段三的思考过程
                    setThinkingPhase('')
                    setThinkingSteps([])
                    await new Promise(resolve => setTimeout(resolve, 300))

                    // 如果有自愈结果，显示自愈信息 - 阶段四：自愈修复
                    if (caseData.heal) {
                        appendProgress('')
                        appendProgress('自愈修复：')

                        // 展示思考过程 - 阶段四：自愈修复
                        setThinkingPhase('自愈修复')
                        setThinkingSteps([
                            { id: '11', title: '分析失败原因', status: 'thinking', details: ['识别失败类型', '定位问题根因'] },
                            { id: '12', title: '判断是否可自愈', status: 'thinking', details: ['评估修复可行性', '确定修复策略'] },
                            { id: '13', title: '执行自动修复', status: 'thinking', details: ['更新测试用例', '优化参数配置'] },
                        ])

                        if (caseData.heal.status === 'healed') {
                            // 更新思考步骤状态 - 阶段四完成
                            setThinkingSteps((prev) => prev.map((s) => ({ ...s, status: 'completed' as const })))

                            appendProgress('   ✓ 已自动修复测试用例')
                            if (caseData.heal.message) {
                                appendProgress(`   ${caseData.heal.message}`)
                            }
                            if (caseData.heal.changes && caseData.heal.changes.length > 0) {
                                appendProgress('   修复内容：')
                                caseData.heal.changes.forEach((change: any) => {
                                    appendProgress(`     步骤${change.step_order}：`)
                                    if (change.changes) {
                                        change.changes.forEach((c: any) => {
                                            appendProgress(`       - ${c.field}：${c.old} → ${c.new}`)
                                        })
                                    }
                                })
                            }
                        } else if (caseData.heal.status === 'cannot_heal') {
                            // 更新思考步骤状态 - 阶段四无法自愈
                            setThinkingSteps((prev) => prev.map((s) => {
                                if (s.id === '11') return { ...s, status: 'completed' }
                                if (s.id === '12') return { ...s, status: 'completed' }
                                return s
                            }))

                            appendProgress('   ⚠ 无法自动修复，需要人工介入')
                            if (caseData.heal.message) {
                                appendProgress(`   ${caseData.heal.message}`)
                            }
                        }
                    }

                    // 自动保存场景测试报告
                    try {
                        const now = new Date()
                        const timeStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
                        const reportName = `${scenarioData.name || '场景测试'}-${timeStr}`
                        const apiBase = process.env.NEXT_PUBLIC_AI_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
                        const reportRes = await fetch(`${apiBase}/api/v1/test-reports`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                project_id: currentProject,
                                name: reportName,
                                report_type: '场景测试',
                                trigger_method: 'AI自动执行',
                                status: execData.status === 'success' ? 'success' : 'error',
                                payload: {
                                    scenario: scenarioData,
                                    execution: execData,
                                    analysis: analysisData,
                                    total_steps: analysisData.total_steps ?? 0,
                                    failed_steps: analysisData.failed_steps ?? 0,
                                },
                            }),
                        })
                        if (reportRes.ok) {
                            const saved = await reportRes.json().catch(() => ({}))
                            console.log('[AI场景测试报告] 保存成功, id:', saved.id)
                        } else {
                            console.error('[AI场景测试报告] 保存失败:', reportRes.status)
                        }
                    } catch (e) {
                        console.error('[AI场景测试报告] 网络错误:', e)
                    }
                } else {
                    // 如果后端没有返回执行结果，清除阶段三的思考过程
                    setThinkingPhase('')
                    setThinkingSteps([])

                    // 如果后端没有返回执行结果，说明后端可能没有执行或者执行失败
                    // 为了避免重复执行导致"请求频繁"的问题，这里只显示提示信息
                    appendProgress('   ⚠ 后端未返回执行结果，请手动执行测试')
                    appendProgress('   提示：后端已在生成时执行过一次，为避免重复执行，请到场景列表手动执行')
                }
                appendProgress('')
                appendProgress('处理完成！')

                // 所有思考阶段完成，现在显示进度面板
                allThinkingCompletedRef.current = true
                setAllThinkingCompleted(true)
                setProgressLines([...progressRef.current])

                // 清除所有思考过程
                setTimeout(() => {
                    setThinkingPhase('')
                    setThinkingSteps([])
                }, 2000)

                setResult({ scenario: scenarioData, testCase: caseData })

                // 将本次生成过程保存到后端，便于在场景列表中回看
                // 注意：确保在所有内容都添加到 progressRef 后再保存
                // 使用 setTimeout 确保所有 appendProgress 调用都已完成
                setTimeout(async () => {
                    try {
                        const apiUrl = process.env.NEXT_PUBLIC_AI_API_URL || process.env.NEXT_PUBLIC_API_URL
                        const logContent = (progressRef.current || []).join('\n')
                        console.log('保存生成过程，内容长度:', logContent.length)
                        await fetch(`${apiUrl}/api/v1/scenarios/${scenarioData.id}/generation-log`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                log: logContent,
                            }),
                        })
                    } catch (e) {
                        console.error('保存生成过程失败:', e)
                    }
                }, 100)
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
        setAllThinkingCompleted(false) // 重置思考完成状态
        allThinkingCompletedRef.current = false // 同时更新ref
        setProgressLines([]) // 初始不显示进度面板

        // 辅助函数：追加进度行（单接口模式下实时显示）
        const appendProgress = (...lines: string[]) => {
            setProgressLines((prev) => {
                const next = [...prev, ...lines]
                progressRef.current = next
                return next
            })
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

            // 展示思考过程
            setThinkingPhase('需求理解')
            setThinkingSteps([
                { id: '1', title: '分析接口功能需求', status: 'thinking', details: ['理解用户测试意图', '识别目标接口'] },
                { id: '2', title: '检索相关API文档', status: 'thinking', details: ['向量语义检索', '匹配接口定义'] },
                { id: '3', title: '提取接口关键信息', status: 'thinking', details: ['解析请求参数', '分析响应结构'] },
            ])
            // 让“思考中”状态停留一小段时间
            await new Promise((resolve) => setTimeout(resolve, 400))

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

            // 更新思考步骤状态为完成
            setThinkingSteps([
                { id: '1', title: '分析接口功能需求', status: 'completed', details: ['理解用户测试意图', '识别目标接口'] },
                { id: '2', title: '检索相关API文档', status: 'completed', details: ['向量语义检索', '匹配接口定义'] },
                { id: '3', title: '提取接口关键信息', status: 'completed', details: ['解析请求参数', '分析响应结构'] },
            ])
            // 给“完成”状态一点展示时间
            await new Promise((resolve) => setTimeout(resolve, 400))

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

            // 展示思考过程
            setThinkingPhase('测试计划')
            setThinkingSteps([
                { id: '4', title: '评估测试策略', status: 'thinking', details: ['分析接口特性', '确定测试类型'] },
                { id: '5', title: '设计测试用例', status: 'thinking', details: ['正向用例', '边界用例', '异常用例', '安全用例'] },
                { id: '6', title: '生成测试计划文档', status: 'thinking', details: ['整理测试范围', '定义验收标准'] },
            ])
            await new Promise((resolve) => setTimeout(resolve, 400))

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

            // 更新思考步骤状态
            setThinkingSteps([
                { id: '4', title: '评估测试策略', status: 'completed', details: ['分析接口特性', '确定测试类型'] },
                { id: '5', title: '设计测试用例', status: 'completed', details: ['正向用例', '边界用例', '异常用例', '安全用例'] },
                { id: '6', title: '生成测试计划文档', status: 'completed', details: ['整理测试范围', '定义验收标准'] },
            ])
            await new Promise((resolve) => setTimeout(resolve, 400))

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

            // 展示思考过程
            setThinkingPhase('代码生成')
            setThinkingSteps([
                { id: '7', title: '选择测试框架', status: 'thinking', details: ['评估框架适用性', '确定代码风格'] },
                { id: '8', title: '生成测试代码', status: 'thinking', details: ['编写测试函数', '配置断言逻辑'] },
                { id: '9', title: '优化代码质量', status: 'thinking', details: ['检查代码规范', '确保可执行性'] },
            ])
            await new Promise((resolve) => setTimeout(resolve, 400))

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

            // 更新思考步骤状态
            setThinkingSteps([
                { id: '7', title: '选择测试框架', status: 'completed', details: ['评估框架适用性', '确定代码风格'] },
                { id: '8', title: '生成测试代码', status: 'completed', details: ['编写测试函数', '配置断言逻辑'] },
                { id: '9', title: '优化代码质量', status: 'completed', details: ['检查代码规范', '确保可执行性'] },
            ])
            await new Promise((resolve) => setTimeout(resolve, 400))

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

            // 所有思考阶段完成，现在显示进度面板
            allThinkingCompletedRef.current = true
            setAllThinkingCompleted(true)
            setProgressLines([...progressRef.current])

            // 清除思考过程
            setTimeout(() => {
                setThinkingPhase('')
                setThinkingSteps([])
            }, 2000)

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
            setThinkingPhase('')
            setThinkingSteps([])
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

            {/* AI思考过程展示 - 显示在进度面板上方 */}
            {thinkingPhase && thinkingSteps.length > 0 && (
                <ThinkingProcess
                    phase={thinkingPhase}
                    steps={thinkingSteps}
                    isActive={loading}
                />
            )}

            {/* 实时进度展示面板（测试场景 + 接口测试 共用）
                - 场景模式：全部思考完成后显示
                - 单接口模式：生成过程中实时显示 */}
            {((mode === 'scenario' && allThinkingCompleted) || mode === 'single-api') && progressLines.length > 0 && (
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
