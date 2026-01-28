'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function ProjectsRedirect() {
    const router = useRouter()

    useEffect(() => {
        // projects页面重定向到项目设置的项目管理Tab
        router.replace('/settings?tab=projects')
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
