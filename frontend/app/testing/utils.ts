/** 从流水线结果中提取展示名，单接口如「登录接口测试用例」，多接口如「登录、注册、忘记密码 接口测试用例」 */
export function getSingleApiDisplayName(data: any): string {
    if (!data?.phase2_plan?.endpoints?.length) return '未命名接口测试用例'
    const endpoints = data.phase2_plan.endpoints
    const parts = endpoints.slice(0, 5).map((ep: any) => {
        const summary = (ep?.summary || ep?.name || '').toString().trim()
        const path = (ep?.path || '').toString()
        const pathPart = path ? (path.replace(/^\//, '').split('/').filter(Boolean).pop() || '') : ''
        const raw = summary || pathPart || '接口'
        return raw.replace(/接口$/, '') || raw
    })
    const name = [...new Set(parts)].filter(Boolean).join('、') || '接口'
    return name + (name.endsWith('接口') ? '测试用例' : '接口测试用例')
}

export type SingleApiCaseItem = { id: string; name: string; data: any; createdAt: number }
