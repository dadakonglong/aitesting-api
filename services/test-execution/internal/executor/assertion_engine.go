package executor

import (
	"fmt"
	"regexp"
	"strings"
)

// AssertionEngine 断言引擎
type AssertionEngine struct{}

func NewAssertionEngine() *AssertionEngine {
	return &AssertionEngine{}
}

// Verify 验证断言
func (e *AssertionEngine) Verify(
	statusCode int,
	assertions []Assertion,
	responseBody map[string]interface{},
) []AssertionResult {
	var results []AssertionResult

	for _, assertion := range assertions {
		result := e.verifyAssertion(statusCode, assertion, responseBody)
		results = append(results, result)
	}

	return results
}

// verifyAssertion 验证单个断言
func (e *AssertionEngine) verifyAssertion(
	statusCode int,
	assertion Assertion,
	responseBody map[string]interface{},
) AssertionResult {
	result := AssertionResult{
		Assertion: assertion,
	}

	switch assertion.Type {
	case "status_code":
		result.ActualValue = statusCode
		result.Passed = e.compareValues(statusCode, assertion.Operator, assertion.ExpectedValue)

	case "response_schema":
		actualValue := e.getFieldValue(responseBody, assertion.Field)
		result.ActualValue = actualValue
		result.Passed = e.compareValues(actualValue, assertion.Operator, assertion.ExpectedValue)

	case "business_logic":
		actualValue := e.getFieldValue(responseBody, assertion.Field)
		result.ActualValue = actualValue
		result.Passed = e.compareValues(actualValue, assertion.Operator, assertion.ExpectedValue)

	default:
		result.Passed = false
		result.ErrorMsg = fmt.Sprintf("不支持的断言类型: %s", assertion.Type)
	}

	if !result.Passed && result.ErrorMsg == "" {
		result.ErrorMsg = fmt.Sprintf("断言失败: 期望%v %s %v, 实际值为%v",
			assertion.Field, assertion.Operator, assertion.ExpectedValue, result.ActualValue)
	}

	return result
}

// compareValues 比较值
func (e *AssertionEngine) compareValues(actual interface{}, operator string, expected interface{}) bool {
	switch operator {
	case "==":
		return fmt.Sprintf("%v", actual) == fmt.Sprintf("%v", expected)
	case "!=":
		return fmt.Sprintf("%v", actual) != fmt.Sprintf("%v", expected)
	case ">":
		return e.compareNumeric(actual, expected, ">")
	case "<":
		return e.compareNumeric(actual, expected, "<")
	case ">=":
		return e.compareNumeric(actual, expected, ">=")
	case "<=":
		return e.compareNumeric(actual, expected, "<=")
	case "contains":
		return e.contains(actual, expected)
	case "matches":
		return e.matches(actual, expected)
	case "exists":
		return actual != nil
	default:
		return false
	}
}

// compareNumeric 数值比较
func (e *AssertionEngine) compareNumeric(actual, expected interface{}, operator string) bool {
	actualFloat, ok1 := toFloat64(actual)
	expectedFloat, ok2 := toFloat64(expected)

	if !ok1 || !ok2 {
		return false
	}

	switch operator {
	case ">":
		return actualFloat > expectedFloat
	case "<":
		return actualFloat < expectedFloat
	case ">=":
		return actualFloat >= expectedFloat
	case "<=":
		return actualFloat <= expectedFloat
	default:
		return false
	}
}

// contains 包含检查
func (e *AssertionEngine) contains(actual, expected interface{}) bool {
	actualStr := fmt.Sprintf("%v", actual)
	expectedStr := fmt.Sprintf("%v", expected)
	return strings.Contains(actualStr, expectedStr)
}

// matches 正则匹配
func (e *AssertionEngine) matches(actual, expected interface{}) bool {
	actualStr := fmt.Sprintf("%v", actual)
	pattern := fmt.Sprintf("%v", expected)
	matched, _ := regexp.MatchString(pattern, actualStr)
	return matched
}

// getFieldValue 获取字段值
func (e *AssertionEngine) getFieldValue(data map[string]interface{}, path string) interface{} {
	if path == "" {
		return data
	}

	parts := strings.Split(path, ".")
	if parts[0] == "response" {
		parts = parts[1:]
	}

	current := interface{}(data)
	for _, part := range parts {
		if m, ok := current.(map[string]interface{}); ok {
			current = m[part]
		} else {
			return nil
		}
	}

	return current
}

// toFloat64 转换为float64
func toFloat64(v interface{}) (float64, bool) {
	switch val := v.(type) {
	case float64:
		return val, true
	case float32:
		return float64(val), true
	case int:
		return float64(val), true
	case int64:
		return float64(val), true
	case int32:
		return float64(val), true
	default:
		return 0, false
	}
}
