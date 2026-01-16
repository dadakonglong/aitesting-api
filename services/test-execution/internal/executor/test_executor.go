package executor

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/go-resty/resty/v2"
)

// TestStep 测试步骤
type TestStep struct {
	ID             string                 `json:"id"`
	StepOrder      int                    `json:"step_order"`
	APIID          string                 `json:"api_id"`
	APIName        string                 `json:"api_name"`
	APIPath        string                 `json:"api_path"`
	APIMethod      string                 `json:"api_method"`
	Description    string                 `json:"description"`
	Params         map[string]interface{} `json:"params"`
	Headers        map[string]string      `json:"headers"`
	ParamMappings  []ParamMapping         `json:"param_mappings"`
	Assertions     []Assertion            `json:"assertions"`
	ExpectedStatus int                    `json:"expected_status"`
	Timeout        int                    `json:"timeout"`
}

// ParamMapping 参数映射
type ParamMapping struct {
	FromStep  int    `json:"from_step"`
	FromField string `json:"from_field"`
	ToField   string `json:"to_field"`
}

// Assertion 断言
type Assertion struct {
	Type          string      `json:"type"`
	Field         string      `json:"field,omitempty"`
	Operator      string      `json:"operator"`
	ExpectedValue interface{} `json:"expected_value"`
	Description   string      `json:"description"`
}

// ExecutionContext 执行上下文
type ExecutionContext struct {
	data map[string]interface{}
}

func NewExecutionContext() *ExecutionContext {
	return &ExecutionContext{
		data: make(map[string]interface{}),
	}
}

func (ctx *ExecutionContext) Set(key string, value interface{}) {
	ctx.data[key] = value
}

func (ctx *ExecutionContext) Get(key string) (interface{}, bool) {
	val, ok := ctx.data[key]
	return val, ok
}

// StepResult 步骤执行结果
type StepResult struct {
	StepID          string                 `json:"step_id"`
	StepOrder       int                    `json:"step_order"`
	Success         bool                   `json:"success"`
	StatusCode      int                    `json:"status_code"`
	Request         map[string]interface{} `json:"request"`
	Response        map[string]interface{} `json:"response"`
	ResponseHeaders map[string][]string    `json:"response_headers"`
	ResponseTime    int64                  `json:"response_time_ms"`
	Assertions      []AssertionResult      `json:"assertions"`
	Extractions     []ExtractionRecord     `json:"extractions"`
	ErrorMsg        string                 `json:"error_msg,omitempty"`
}

// AssertionResult 断言结果
type AssertionResult struct {
	Assertion   Assertion   `json:"assertion"`
	Passed      bool        `json:"passed"`
	ActualValue interface{} `json:"actual_value,omitempty"`
	ErrorMsg    string      `json:"error_msg,omitempty"`
}

// ExtractionRecord 提取记录 - 展示AI自动识别的接口依赖关系
type ExtractionRecord struct {
	FromStep       int         `json:"from_step"`
	FromField      string      `json:"from_field"`
	ToField        string      `json:"to_field"`
	ExtractedValue interface{} `json:"extracted_value"`
	Success        bool        `json:"success"`
	ErrorMsg       string      `json:"error_msg,omitempty"`
}

// TestExecutor 测试执行器
type TestExecutor struct {
	httpClient      *resty.Client
	assertionEngine *AssertionEngine
	baseURL         string
}

func NewTestExecutor(baseURL string) *TestExecutor {
	client := resty.New()
	client.SetTimeout(60 * time.Second)

	return &TestExecutor{
		httpClient:      client,
		assertionEngine: NewAssertionEngine(),
		baseURL:         baseURL,
	}
}

// Execute 执行测试步骤序列
func (e *TestExecutor) Execute(steps []TestStep) ([]StepResult, error) {
	execCtx := NewExecutionContext()
	var stepResults []StepResult

	for _, step := range steps {
		result := e.executeStep(&step, execCtx)
		stepResults = append(stepResults, *result)

		if !result.Success {
			break
		}

		// 保存响应到上下文
		execCtx.Set(fmt.Sprintf("step_%d", step.StepOrder), result.Response)
	}

	return stepResults, nil
}

// executeStep 执行单个步骤
func (e *TestExecutor) executeStep(step *TestStep, execCtx *ExecutionContext) *StepResult {
	result := &StepResult{
		StepID:    step.ID,
		StepOrder: step.StepOrder,
	}

	startTime := time.Now()

	// 1. 解析参数（替换变量引用）并记录提取过程
	params, extractions, err := e.resolveParams(step.Params, step.ParamMappings, execCtx)
	if err != nil {
		result.Success = false
		result.ErrorMsg = fmt.Sprintf("解析参数失败: %v", err)
		return result
	}
	result.Extractions = extractions

	// 2. 构建完整URL
	fullURL := e.baseURL + step.APIPath

	// 3. 发送HTTP请求
	resp, err := e.sendRequest(step.APIMethod, fullURL, params, step.Headers, step.Timeout)
	if err != nil {
		result.Success = false
		result.ErrorMsg = fmt.Sprintf("请求失败: %v", err)
		return result
	}

	result.ResponseTime = time.Since(startTime).Milliseconds()
	result.StatusCode = resp.StatusCode()
	result.Request = params
	// 保存响应头
	result.ResponseHeaders = resp.Header()

	// 4. 解析响应
	var responseBody map[string]interface{}
	if err := json.Unmarshal(resp.Body(), &responseBody); err != nil {
		responseBody = map[string]interface{}{
			"raw": string(resp.Body()),
		}
	}
	result.Response = responseBody

	// 5. 执行断言
	assertionResults := e.assertionEngine.Verify(resp.StatusCode(), step.Assertions, responseBody)
	result.Assertions = assertionResults

	// 6. 判断是否成功
	result.Success = e.isStepSuccess(result, step)

	return result
}

// resolveParams 解析参数并记录提取过程
func (e *TestExecutor) resolveParams(
	params map[string]interface{},
	mappings []ParamMapping,
	execCtx *ExecutionContext,
) (map[string]interface{}, []ExtractionRecord, error) {
	resolved := make(map[string]interface{})
	var extractions []ExtractionRecord

	// 复制原始参数
	for k, v := range params {
		resolved[k] = v
	}

	// 应用参数映射并记录提取过程
	for _, mapping := range mappings {
		extraction := ExtractionRecord{
			FromStep:  mapping.FromStep,
			FromField: mapping.FromField,
			ToField:   mapping.ToField,
			Success:   false,
		}

		stepKey := fmt.Sprintf("step_%d", mapping.FromStep)
		stepData, ok := execCtx.Get(stepKey)
		if !ok {
			extraction.ErrorMsg = fmt.Sprintf("步骤%d的数据不存在", mapping.FromStep)
			extractions = append(extractions, extraction)
			return nil, extractions, fmt.Errorf("步骤%d的数据不存在", mapping.FromStep)
		}

		// 提取字段值
		value, err := extractFieldValue(stepData, mapping.FromField)
		if err != nil {
			extraction.ErrorMsg = err.Error()
			extractions = append(extractions, extraction)
			return nil, extractions, err
		}

		// 记录提取的值
		extraction.ExtractedValue = value
		extraction.Success = true

		// 设置到目标字段
		if err := setFieldValue(resolved, mapping.ToField, value); err != nil {
			extraction.Success = false
			extraction.ErrorMsg = err.Error()
			extractions = append(extractions, extraction)
			return nil, extractions, err
		}

		extractions = append(extractions, extraction)
	}

	return resolved, extractions, nil
}

// sendRequest 发送HTTP请求
func (e *TestExecutor) sendRequest(
	method string,
	url string,
	params map[string]interface{},
	headers map[string]string,
	timeout int,
) (*resty.Response, error) {
	req := e.httpClient.R().
		SetHeaders(headers)

	switch strings.ToUpper(method) {
	case "GET":
		req.SetQueryParams(convertToStringMap(params))
		return req.Get(url)
	case "POST":
		req.SetBody(params)
		return req.Post(url)
	case "PUT":
		req.SetBody(params)
		return req.Put(url)
	case "DELETE":
		return req.Delete(url)
	case "PATCH":
		req.SetBody(params)
		return req.Patch(url)
	default:
		return nil, fmt.Errorf("不支持的HTTP方法: %s", method)
	}
}

// isStepSuccess 判断步骤是否成功
func (e *TestExecutor) isStepSuccess(result *StepResult, step *TestStep) bool {
	// 检查状态码
	if result.StatusCode != step.ExpectedStatus {
		return false
	}

	// 检查所有断言是否通过
	for _, assertion := range result.Assertions {
		if !assertion.Passed {
			return false
		}
	}

	return true
}

// 辅助函数

func extractFieldValue(data interface{}, path string) (interface{}, error) {
	parts := strings.Split(path, ".")
	current := data

	for _, part := range parts {
		if part == "response" || part == "request" {
			continue
		}

		if m, ok := current.(map[string]interface{}); ok {
			current = m[part]
		} else {
			return nil, fmt.Errorf("无法提取字段: %s", path)
		}
	}

	return current, nil
}

func setFieldValue(data map[string]interface{}, path string, value interface{}) error {
	parts := strings.Split(path, ".")
	if parts[0] == "request" {
		parts = parts[1:]
	}

	if len(parts) == 1 {
		data[parts[0]] = value
		return nil
	}

	// 处理嵌套路径
	current := data
	for i := 0; i < len(parts)-1; i++ {
		if _, ok := current[parts[i]]; !ok {
			current[parts[i]] = make(map[string]interface{})
		}
		current = current[parts[i]].(map[string]interface{})
	}
	current[parts[len(parts)-1]] = value

	return nil
}

func convertToStringMap(params map[string]interface{}) map[string]string {
	result := make(map[string]string)
	for k, v := range params {
		result[k] = fmt.Sprintf("%v", v)
	}
	return result
}
