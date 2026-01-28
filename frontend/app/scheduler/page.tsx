'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function SchedulerRedirect() {
    const router = useRouter()

    useEffect(() => {
        // scheduler页面重定向到测试中心的定时任务Tab
        router.replace('/testing?tab=scheduler')
    }, [router])

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            color: '#6B7280'
        }}>
            <p>正在跳转到测试中心...</p>
        </div>
    )
}
