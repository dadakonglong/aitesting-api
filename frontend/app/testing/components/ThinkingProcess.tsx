'use client'

import { useState, useEffect } from 'react'
import { Brain, Sparkles, CheckCircle2 } from 'lucide-react'

interface ThinkingStep {
    id: string
    title: string
    status: 'thinking' | 'completed'
    details?: string[]
    timestamp?: number
}

interface ThinkingProcessProps {
    phase: string
    steps: ThinkingStep[]
    isActive: boolean
}

export default function ThinkingProcess({ phase, steps, isActive }: ThinkingProcessProps) {
    const [displayedSteps, setDisplayedSteps] = useState<ThinkingStep[]>([])

    useEffect(() => {
        if (!isActive || !steps || steps.length === 0) {
            setDisplayedSteps([])
            return
        }

        // 重置显示步骤，开始新的阶段（使用phase作为key，确保阶段切换时完全重置）
        setDisplayedSteps([])
        
        // 逐步显示思考步骤，模拟AI思考过程
        let currentIndex = 0
        const interval = setInterval(() => {
            // 添加安全检查：确保 currentIndex 在有效范围内且步骤存在
            if (currentIndex < steps.length && steps[currentIndex] && steps[currentIndex].id) {
                const currentStep = steps[currentIndex]
                setDisplayedSteps((prev) => {
                    // 如果步骤已存在，更新状态；否则添加新步骤
                    const existingIndex = prev.findIndex((s) => s.id === currentStep.id)
                    if (existingIndex >= 0) {
                        const updated = [...prev]
                        updated[existingIndex] = { ...currentStep, timestamp: Date.now() }
                        return updated
                    } else {
                        return [...prev, { ...currentStep, timestamp: Date.now() }]
                    }
                })
                currentIndex++
            } else {
                clearInterval(interval)
            }
        }, 800) // 每800ms显示一个步骤，让用户能看到每个步骤

        return () => clearInterval(interval)
    }, [phase]) // 只依赖phase，确保阶段切换时完全重置，避免重复显示

    // 更新步骤状态（当steps的status变化时）
    useEffect(() => {
        if (!isActive || !steps || steps.length === 0) return

        steps.forEach((step) => {
            // 添加安全检查
            if (!step || !step.id) return
            
            setDisplayedSteps((prev) => {
                const displayedStep = prev.find((s) => s.id === step.id)
                // 如果步骤已显示且状态需要更新
                if (displayedStep && step.status !== displayedStep.status) {
                    return prev.map((s) => (s.id === step.id ? { ...step, timestamp: Date.now() } : s))
                }
                return prev
            })
        })
    }, [steps, isActive]) // 移除displayedSteps依赖，避免循环更新

    // 添加安全检查：确保有有效的步骤数据
    if (!isActive || !steps || steps.length === 0 || displayedSteps.length === 0) {
        return null
    }

    return (
        <div
            style={{
                background: 'linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%)',
                border: '1px solid #e0e4f5',
                borderRadius: '0.75rem',
                padding: '1.25rem',
                marginTop: '1rem',
                marginBottom: '1rem',
                boxShadow: '0 2px 8px rgba(102, 126, 234, 0.08)',
                animation: 'fadeIn 0.3s ease-in',
            }}
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                <div style={{ 
                    width: '32px', 
                    height: '32px', 
                    borderRadius: '50%', 
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 4px 6px rgba(102, 126, 234, 0.2)',
                }}>
                    <Brain size={18} style={{ color: 'white' }} />
                </div>
                <div>
                    <span style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', display: 'block' }}>
                        {phase}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#6B7280' }}>
                        AI正在思考中...
                    </span>
                </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {displayedSteps.map((step, index) => {
                    const isThinking = step.status === 'thinking'
                    const isCompleted = step.status === 'completed'

                    return (
                        <div
                            key={step.id}
                            style={{
                                background: isThinking 
                                    ? 'linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%)' 
                                    : isCompleted 
                                    ? 'linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%)'
                                    : 'white',
                                borderRadius: '0.5rem',
                                padding: '0.875rem',
                                border: isThinking 
                                    ? '1px solid #667eea' 
                                    : isCompleted 
                                    ? '1px solid #10b981'
                                    : '1px solid #e5e7eb',
                                opacity: isThinking ? 0.95 : 1,
                                transition: 'all 0.4s ease',
                                transform: isThinking ? 'translateX(4px)' : 'translateX(0)',
                                boxShadow: isThinking 
                                    ? '0 2px 8px rgba(102, 126, 234, 0.15)' 
                                    : isCompleted 
                                    ? '0 2px 8px rgba(16, 185, 129, 0.1)'
                                    : '0 1px 3px rgba(0, 0, 0, 0.05)',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: step.details ? '0.5rem' : 0 }}>
                                {isThinking ? (
                                    <div style={{ position: 'relative' }}>
                                        <div
                                            style={{
                                                width: '18px',
                                                height: '18px',
                                                border: '2.5px solid #e0e7ff',
                                                borderTopColor: '#667eea',
                                                borderRadius: '50%',
                                                animation: 'spin 0.8s linear infinite',
                                            }}
                                        />
                                        <div
                                            style={{
                                                position: 'absolute',
                                                top: '50%',
                                                left: '50%',
                                                transform: 'translate(-50%, -50%)',
                                                width: '6px',
                                                height: '6px',
                                                background: '#667eea',
                                                borderRadius: '50%',
                                                animation: 'pulse 1.5s ease-in-out infinite',
                                            }}
                                        />
                                    </div>
                                ) : isCompleted ? (
                                    <div style={{
                                        width: '20px',
                                        height: '20px',
                                        borderRadius: '50%',
                                        background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        boxShadow: '0 2px 4px rgba(16, 185, 129, 0.3)',
                                    }}>
                                        <CheckCircle2 size={12} style={{ color: 'white' }} />
                                    </div>
                                ) : (
                                    <Sparkles size={16} style={{ color: '#667eea', opacity: 0.7 }} />
                                )}
                                <span
                                    style={{
                                        fontSize: '0.8125rem',
                                        fontWeight: isThinking ? '600' : isCompleted ? '500' : '500',
                                        color: isCompleted ? '#059669' : isThinking ? '#667eea' : '#374151',
                                        transition: 'all 0.3s ease',
                                    }}
                                >
                                    {step.title}
                                </span>
                            </div>

                            {step.details && step.details.length > 0 && (
                                <div style={{ marginLeft: '1.5rem', marginTop: '0.5rem' }}>
                                    {step.details.map((detail, detailIndex) => (
                                        <div
                                            key={detailIndex}
                                            style={{
                                                fontSize: '0.75rem',
                                                color: '#6B7280',
                                                lineHeight: '1.6',
                                                marginTop: '0.25rem',
                                            }}
                                        >
                                            • {detail}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>

            <style jsx>{`
                @keyframes spin {
                    from {
                        transform: rotate(0deg);
                    }
                    to {
                        transform: rotate(360deg);
                    }
                }
                @keyframes pulse {
                    0%, 100% {
                        opacity: 1;
                        transform: translate(-50%, -50%) scale(1);
                    }
                    50% {
                        opacity: 0.5;
                        transform: translate(-50%, -50%) scale(0.8);
                    }
                }
                @keyframes fadeIn {
                    from {
                        opacity: 0;
                        transform: translateY(-10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
            `}</style>
        </div>
    )
}
