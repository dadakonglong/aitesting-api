package services

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/aitesting/test-execution/internal/executor"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

// TestCase 测试用例（简化版，从数据库读取）
type TestCase struct {
	ID           uuid.UUID              `json:"id"`
	ScenarioID   uuid.UUID              `json:"scenario_id"`
	Name         string                 `json:"name"`
	Description  string                 `json:"description"`
	Steps        []executor.TestStep    `json:"steps"`
	DataStrategy string                 `json:"data_strategy"`
	Tags         []string               `json:"tags"`
	Enabled      bool                   `json:"enabled"`
}

// TestExecution 测试执行记录
type TestExecution struct {
	ID         uuid.UUID              `gorm:"type:uuid;primary_key" json:"id"`
	TestCaseID uuid.UUID              `gorm:"type:uuid;index" json:"test_case_id"`
	Environment string                `gorm:"size:50" json:"environment"`
	Status     string                 `gorm:"size:50" json:"status"`
	StartTime  time.Time              `json:"start_time"`
	EndTime    *time.Time             `json:"end_time,omitempty"`
	DurationMs int64                  `json:"duration_ms"`
	Result     string                 `gorm:"type:text" json:"-"`
	ResultJSON map[string]interface{} `gorm:"-" json:"result"`
	ErrorMsg   string                 `gorm:"type:text" json:"error_msg,omitempty"`
	CreatedAt  time.Time              `json:"created_at"`
}

// BeforeCreate GORM钩子
func (te *TestExecution) BeforeCreate(tx *gorm.DB) error {
	if te.ID == uuid.Nil {
		te.ID = uuid.New()
	}
	return nil
}

// AfterFind GORM钩子 - 查询后解析JSON
func (te *TestExecution) AfterFind(tx *gorm.DB) error {
	if te.Result != "" {
		return json.Unmarshal([]byte(te.Result), &te.ResultJSON)
	}
	return nil
}

// BeforeSave GORM钩子 - 保存前序列化JSON
func (te *TestExecution) BeforeSave(tx *gorm.DB) error {
	if te.ResultJSON != nil {
		data, err := json.Marshal(te.ResultJSON)
		if err != nil {
			return err
		}
		te.Result = string(data)
	}
	return nil
}

// ExecutionService 执行服务
type ExecutionService struct {
	db *gorm.DB
}

func NewExecutionService(db *gorm.DB) *ExecutionService {
	return &ExecutionService{db: db}
}

// ExecuteTestCase 执行测试用例
func (s *ExecutionService) ExecuteTestCase(
	testCaseID uuid.UUID,
	environment string,
	baseURL string,
) (*TestExecution, error) {
	// 1. 获取测试用例
	var testCase TestCase
	if err := s.db.Table("test_cases").First(&testCase, "id = ?", testCaseID).Error; err != nil {
		return nil, fmt.Errorf("测试用例不存在: %w", err)
	}

	// 2. 创建执行记录
	execution := &TestExecution{
		TestCaseID:  testCaseID,
		Environment: environment,
		Status:      "running",
		StartTime:   time.Now(),
	}

	if err := s.db.Create(execution).Error; err != nil {
		return nil, err
	}

	// 3. 执行测试
	go s.executeAsync(execution.ID, testCase, baseURL)

	return execution, nil
}

// executeAsync 异步执行测试
func (s *ExecutionService) executeAsync(executionID uuid.UUID, testCase TestCase, baseURL string) {
	// 创建执行器
	testExecutor := executor.NewTestExecutor(baseURL)

	// 执行测试步骤
	stepResults, err := testExecutor.Execute(testCase.Steps)

	// 更新执行记录
	var execution TestExecution
	s.db.First(&execution, "id = ?", executionID)

	endTime := time.Now()
	execution.EndTime = &endTime
	execution.DurationMs = endTime.Sub(execution.StartTime).Milliseconds()

	if err != nil {
		execution.Status = "failed"
		execution.ErrorMsg = err.Error()
	} else {
		// 判断是否所有步骤都成功
		allSuccess := true
		for _, result := range stepResults {
			if !result.Success {
				allSuccess = false
				break
			}
		}

		if allSuccess {
			execution.Status = "success"
		} else {
			execution.Status = "failed"
		}
	}

	// 保存结果
	execution.ResultJSON = map[string]interface{}{
		"steps": stepResults,
		"summary": s.generateSummary(stepResults),
	}

	s.db.Save(&execution)
}

// GetExecution 获取执行记录
func (s *ExecutionService) GetExecution(id uuid.UUID) (*TestExecution, error) {
	var execution TestExecution
	if err := s.db.First(&execution, "id = ?", id).Error; err != nil {
		return nil, err
	}
	return &execution, nil
}

// ListExecutions 列出执行记录
func (s *ExecutionService) ListExecutions(testCaseID uuid.UUID, page, pageSize int) ([]TestExecution, int64, error) {
	var executions []TestExecution
	var total int64

	query := s.db.Model(&TestExecution{})
	if testCaseID != uuid.Nil {
		query = query.Where("test_case_id = ?", testCaseID)
	}

	query.Count(&total)

	offset := (page - 1) * pageSize
	if err := query.Offset(offset).Limit(pageSize).Order("created_at DESC").Find(&executions).Error; err != nil {
		return nil, 0, err
	}

	return executions, total, nil
}

// generateSummary 生成执行摘要
func (s *ExecutionService) generateSummary(stepResults []executor.StepResult) map[string]interface{} {
	totalSteps := len(stepResults)
	successSteps := 0
	failedSteps := 0
	totalAssertions := 0
	passedAssertions := 0

	for _, step := range stepResults {
		if step.Success {
			successSteps++
		} else {
			failedSteps++
		}

		for _, assertion := range step.Assertions {
			totalAssertions++
			if assertion.Passed {
				passedAssertions++
			}
		}
	}

	successRate := 0.0
	if totalAssertions > 0 {
		successRate = float64(passedAssertions) / float64(totalAssertions) * 100
	}

	return map[string]interface{}{
		"total_steps":       totalSteps,
		"success_steps":     successSteps,
		"failed_steps":      failedSteps,
		"total_assertions":  totalAssertions,
		"passed_assertions": passedAssertions,
		"failed_assertions": totalAssertions - passedAssertions,
		"success_rate":      successRate,
	}
}
