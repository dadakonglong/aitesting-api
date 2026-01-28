'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function TestsRedirect() {
    const router = useRouter()

    useEffect(() => {
        // tests页面重定向到测试中心的测试场景Tab
        router.replace('/testing?tab=scenarios')
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
