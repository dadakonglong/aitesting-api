# AI分析依赖逻辑通俗版

## 一、什么时候用AI分析？

**时机**：当知识图谱没有记录时，系统会用AI分析来判断是否需要前置依赖。

**流程**：
```
知识图谱查询
    ↓
知识图谱回答："没记录，不知道"
    ↓
系统用AI分析判断是否需要前置依赖
```

---

## 二、AI分析的完整流程

### 第一步：RAG检索（找相关接口）

**目的**：在项目的所有接口中，找到可能与目标接口相关的接口。

**怎么找？**

系统会做两件事：

**1. 基础检索**
- 用目标接口的信息（方法、路径、描述）作为关键词
- 在项目的接口库中搜索匹配的接口
- 比如：目标接口是"GET /api/user/profile"，系统会搜索包含"user"、"profile"等关键词的接口

**2. 智能扩展检索**

系统会"聪明地"根据目标接口的特征，添加额外的搜索关键词：

**情况A：检测到需要鉴权**
- 如果目标接口的请求头里有"Authorization"或"auth"
- 或者参数里有"token"
- 系统会额外搜索："登录 认证 token 鉴权 auth login"
- **目的**：找到登录接口

**情况B：检测到需要session**
- 如果目标接口的参数里有"sessionId"或"session"
- 系统会额外搜索："开台 创建会话 session 房间"
- **目的**：找到创建session的接口

**情况C：检测到需要order**
- 如果目标接口的参数里有"orderId"或"booking"
- 系统会额外搜索："订单 预订 booking order"
- **目的**：找到创建订单的接口

**示例**：
```
目标接口：POST /api/orders
参数：{"sessionId": "...", "roomId": "..."}
    ↓
系统检测：
  - 有sessionId → 需要session
  - 有order → 需要订单相关
    ↓
系统搜索：
  1. 基础搜索："POST orders"
  2. 扩展搜索："开台 创建会话 session 房间"
  3. 扩展搜索："订单 预订 booking order"
    ↓
找到相关接口：
  - POST /api/login（登录接口）
  - POST /api/sessions（创建会话接口）
  - GET /api/rooms（获取房间接口）
```

### 第二步：准备给AI的信息

**系统会把以下信息整理好，传给AI**：

**1. 目标接口的信息**
```json
{
  "path": "/api/user/profile",
  "method": "GET",
  "summary": "获取用户信息",
  "headers_keys": ["Authorization"],  // 请求头里有什么字段
  "params_keys": [],                   // 参数里有什么字段
  "has_authorization": true            // 是否需要鉴权
}
```

**2. 关联接口列表**
```json
[
  {
    "path": "/api/login",
    "method": "POST",
    "summary": "用户登录"
  },
  {
    "path": "/api/sessions",
    "method": "POST",
    "summary": "创建会话"
  }
]
```

### 第三步：AI分析判断

**系统把信息传给AI，AI会按照以下规则分析**：

#### 规则1：Authorization依赖判断

**AI会检查**：
- 目标接口的请求头里有没有"Authorization"或"auth"？
- 目标接口的参数里有没有"token"？

**如果检测到需要鉴权**：
- AI会在关联接口列表中找登录/认证类接口
- 比如：找到"POST /api/login"
- AI判断：需要先调用登录接口获取token

**示例**：
```
目标接口：GET /api/user/profile
请求头：{"Authorization": "Bearer ..."}
    ↓
AI分析：
  "这个接口需要Authorization，说明需要鉴权"
  "关联接口列表里有登录接口"
  "所以需要先调用登录接口获取token"
    ↓
AI返回：
  needs_deps: true
  dependency_chain: [
    {
      "api_path": "/api/login",
      "api_method": "POST",
      "reason": "获取token",
      "provides": [
        {
          "from_field": "data.token",
          "to_field": "Authorization",
          "to_type": "headers",
          "prefix": "Bearer "
        }
      ]
    }
  ]
```

#### 规则2：业务参数依赖判断

**AI会检查**：
- 目标接口的参数里有没有动态ID？
- 比如：sessionId、orderId、roomId等

**如果检测到需要动态ID**：
- AI会在关联接口列表中找能提供这些ID的接口
- 比如：找到"POST /api/sessions"（创建会话接口）
- AI判断：需要先调用创建会话接口获取sessionId

**示例**：
```
目标接口：POST /api/orders
参数：{"sessionId": "...", "roomId": "..."}
    ↓
AI分析：
  "这个接口需要sessionId和roomId"
  "关联接口列表里有创建会话接口和获取房间接口"
  "所以需要先调用这两个接口"
    ↓
AI返回：
  needs_deps: true
  dependency_chain: [
    {
      "api_path": "/api/sessions",
      "api_method": "POST",
      "reason": "获取sessionId",
      "provides": [
        {
          "from_field": "data.sessionId",
          "to_field": "sessionId",
          "to_type": "params"
        }
      ]
    },
    {
      "api_path": "/api/rooms",
      "api_method": "GET",
      "reason": "获取roomId",
      "provides": [
        {
          "from_field": "data[0].id",
          "to_field": "roomId",
          "to_type": "params"
        }
      ]
    }
  ]
```

#### 规则3：跳过登录类接口

**AI会检查**：
- 目标接口本身是不是登录/认证类接口？

**如果是登录接口**：
- AI判断：不需要前置依赖
- 因为登录接口通常是第一个被调用的，不需要依赖其他接口

**示例**：
```
目标接口：POST /api/login
    ↓
AI分析：
  "这是登录接口本身"
  "登录接口不需要前置依赖"
    ↓
AI返回：
  needs_deps: false
  reason: "接口可独立执行"
  dependency_chain: []
```

#### 规则4：限制依赖链长度

**AI会限制**：
- 依赖链的总长度不超过3（包括目标接口）
- 比如：最多2个前置依赖 + 1个目标接口 = 3个

**目的**：避免依赖链太长，执行时间过长

---

## 三、AI分析的完整示例

### 示例1：需要登录的接口

**场景**：用户要测试"获取用户信息"接口

**流程**：

```
【步骤1：知识图谱查询】
知识图谱回答："没记录，不知道"
    ↓
【步骤2：RAG检索】
系统搜索相关接口：
  - 基础搜索："GET /api/user/profile"
  - 扩展搜索："登录 认证 token"（因为检测到需要Authorization）
    ↓
找到相关接口：
  - POST /api/login（登录接口）
  - GET /api/user/profile（目标接口本身）
    ↓
【步骤3：准备给AI的信息】
目标接口：
  {
    "path": "/api/user/profile",
    "method": "GET",
    "has_authorization": true  // 需要鉴权
  }
关联接口：
  [
    {"path": "/api/login", "method": "POST", "summary": "用户登录"}
  ]
    ↓
【步骤4：AI分析】
AI分析：
  "目标接口需要Authorization，说明需要鉴权"
  "关联接口列表里有登录接口"
  "所以需要先调用登录接口获取token"
    ↓
AI返回：
  {
    "needs_deps": true,
    "reason": "获取用户信息需要先登录获取token",
    "dependency_chain": [
      {
        "api_path": "/api/login",
        "api_method": "POST",
        "reason": "获取token",
        "provides": [
          {
            "from_field": "data.token",
            "to_field": "Authorization",
            "to_type": "headers",
            "prefix": "Bearer "
          }
        ]
      }
    ]
  }
    ↓
【步骤5：应用依赖链】
系统自动插入登录步骤：
  步骤1：POST /api/login（AI分析出的前置依赖）
  步骤2：GET /api/user/profile（用户要测试的）
```

### 示例2：需要多个前置依赖的接口

**场景**：用户要测试"创建订单"接口

**流程**：

```
【步骤1：知识图谱查询】
知识图谱回答："没记录，不知道"
    ↓
【步骤2：RAG检索】
系统检测目标接口：
  - 参数里有"sessionId" → 需要session
  - 参数里有"roomId" → 需要room
  - 请求头里有"Authorization" → 需要鉴权
    ↓
系统搜索：
  - 基础搜索："POST /api/orders"
  - 扩展搜索："登录 认证 token"
  - 扩展搜索："开台 创建会话 session"
  - 扩展搜索："订单 预订 booking"
    ↓
找到相关接口：
  - POST /api/login（登录接口）
  - POST /api/sessions（创建会话接口）
  - GET /api/rooms（获取房间接口）
  - POST /api/orders（目标接口本身）
    ↓
【步骤3：AI分析】
AI分析：
  "目标接口需要Authorization、sessionId、roomId"
  "关联接口列表里有登录、创建会话、获取房间接口"
  "所以需要先调用这三个接口"
    ↓
AI返回：
  {
    "needs_deps": true,
    "reason": "创建订单需要先登录、创建会话、获取房间",
    "dependency_chain": [
      {
        "api_path": "/api/login",
        "api_method": "POST",
        "reason": "获取token"
      },
      {
        "api_path": "/api/sessions",
        "api_method": "POST",
        "reason": "获取sessionId"
      },
      {
        "api_path": "/api/rooms",
        "api_method": "GET",
        "reason": "获取roomId"
      }
    ]
  }
    ↓
【步骤4：应用依赖链】
系统自动插入前置步骤：
  步骤1：POST /api/login
  步骤2：POST /api/sessions
  步骤3：GET /api/rooms
  步骤4：POST /api/orders（用户要测试的）
```

### 示例3：不需要前置依赖的接口

**场景**：用户要测试"登录"接口本身

**流程**：

```
【步骤1：知识图谱查询】
知识图谱回答："没记录，不知道"
    ↓
【步骤2：RAG检索】
系统搜索相关接口
    ↓
【步骤3：AI分析】
AI分析：
  "这是登录接口本身"
  "登录接口不需要前置依赖"
    ↓
AI返回：
  {
    "needs_deps": false,
    "reason": "接口可独立执行",
    "dependency_chain": []
  }
    ↓
【步骤4：直接执行】
系统直接执行登录接口，不插入前置步骤
```

---

## 四、AI分析的判断规则总结

### 规则1：Authorization依赖
- **检查**：目标接口的请求头或参数里有没有"Authorization"、"auth"、"token"
- **判断**：如果有，需要找登录接口
- **结果**：插入登录步骤

### 规则2：业务参数依赖
- **检查**：目标接口的参数里有没有动态ID（sessionId、orderId、roomId等）
- **判断**：如果有，需要找能提供这些ID的接口
- **结果**：插入相应的前置步骤

### 规则3：跳过登录类接口
- **检查**：目标接口本身是不是登录/认证类接口
- **判断**：如果是，不需要前置依赖
- **结果**：不插入前置步骤

### 规则4：限制依赖链长度
- **限制**：依赖链总长度不超过3
- **目的**：避免依赖链太长

---

## 五、AI分析 vs 知识图谱

### 对比

| 对比项 | 知识图谱 | AI分析 |
|--------|---------|--------|
| **数据来源** | 历史执行记录 | 接口特征分析 |
| **准确性** | 高（基于真实数据） | 中等（基于AI推理） |
| **速度** | 快（查文件） | 慢（调用AI） |
| **成本** | 低（本地查询） | 高（AI调用） |
| **适用场景** | 有历史记录时 | 第一次使用或知识图谱无记录时 |

### 优先级

```
查询知识图谱（优先）
    ↓
有记录？
    ├─ 是 → 直接使用，不再问AI
    └─ 否 → 用AI分析判断
```

**为什么这样设计？**
- 知识图谱基于历史真实数据，更准确
- 知识图谱查询快，成本低
- AI分析作为"兜底方案"，确保即使没有历史记录也能工作

---

## 六、总结

### AI分析的逻辑

1. **RAG检索**：根据目标接口的特征，智能搜索相关接口
2. **准备信息**：整理目标接口和关联接口的信息
3. **AI分析**：根据规则判断是否需要前置依赖
4. **应用结果**：如果AI判断需要，自动插入前置步骤

### 关键点

1. **智能搜索**：根据接口特征（Authorization、sessionId等）扩展搜索关键词
2. **规则判断**：AI按照明确的规则（Authorization依赖、业务参数依赖等）判断
3. **兜底方案**：当知识图谱没有记录时，AI分析确保系统仍能工作
4. **优先级**：知识图谱优先，AI分析作为补充

---

**说明**：本文档用通俗语言描述AI分析依赖的逻辑，重点说明"当知识图谱没有记录时，AI是怎么判断是否需要前置依赖的"。
