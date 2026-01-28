'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function ImportRedirect() {
    const router = useRouter()

    useEffect(() => {
        // import页面重定向到API管理的数据导入Tab
        router.replace('/apis?tab=import')
    }, [router])

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            color: '#6B7280'
        }}>
            <p>正在跳转到API管理...</p>
        </div>
    )
}
