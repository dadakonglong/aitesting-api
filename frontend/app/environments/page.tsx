'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function EnvironmentsRedirect() {
    const router = useRouter()

    useEffect(() => {
        // environments页面重定向到项目设置的环境配置Tab
        router.replace('/settings?tab=environments')
    }, [router])

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            color: '#6B7280'
        }}>
            <p>正在跳转到项目设置...</p>
        </div>
    )
}
