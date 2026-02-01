# `/vod/song/order` 参数错误问题分析与修复

## 问题现象

- **后台执行**：返回「参数错误」
- **Postman 执行**：成功

## 可能原因

### 1. 参数格式（parm 等嵌套字段）

当 `parm` 在 request_template.params 中存为 **对象** `{"vip":0,"isRecord":0,...}` 时，form 编码会错误地使用 Python 的 `str()`，得到 `{'vip': 0, ...}`（单引号），而非合法 JSON `{"vip":0,...}`。服务端解析失败会返回「参数错误」。

**修复**：在 form 编码前，对所有 dict/list 类型值使用 `json.dumps()` 转为合法 JSON 字符串。

### 2. Content-Type

接口需要 **`application/x-www-form-urlencoded`**。若 headers 中未指定或错误指定为 `application/json`，也会导致解析失败。

### 差异对比

| 项目 | Postman（成功） | 后台（修复前） |
|------|-----------------|----------------|
| Content-Type | `application/x-www-form-urlencoded` | `application/json` |
| Body 格式 | `ktvid=105497&unionid=xxx&...` | `{"ktvid":"105497",...}` |
| 服务端解析 | 按 form 解析 ✓ | 按 form 解析失败 ✗ |

## 代码修复

在 `_run_steps` 中，根据 `request_template.headers` 中的 Content-Type 选择请求体格式：

- **`application/x-www-form-urlencoded`** → 使用 `data=`（form 编码）
- **`application/json`** 或其他 → 使用 `json=`（JSON 编码）

## 使用说明

用例的 `request_template.headers` 中需要显式设置正确的 Content-Type，例如：

```json
{
  "request_template": {
    "params": {
      "ktvid": "105497",
      "unionid": "o6qE3twVuimSKKGHj0agds7YmiGA",
      "parm": "{\"vip\":0,\"isRecord\":0,\"isScore\":0,\"isForceJinhai\":0}"
    },
    "headers": {
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
  }
}
```

- 若 **未** 在 headers 中指定 Content-Type，默认仍为 `application/json`。
- 若 API 需要 form-urlencoded，必须在 headers 中写入 `Content-Type: application/x-www-form-urlencoded`。

## 建议

1. 在 API 定义或 Swagger 中明确该接口的 `requestBody.content-type`。
2. 导入 Swagger 时保留 `requestBody` 的 content-type，供用例生成使用。
3. 对 `/vod/song/order` 等已知为 form 的接口，在用例 `headers` 中设置 `Content-Type: application/x-www-form-urlencoded`。
