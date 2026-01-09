package models

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// Scenario 测试场景
type Scenario struct {
	ID                  uuid.UUID              `gorm:"type:uuid;primary_key" json:"id"`
	ProjectID           uuid.UUID              `gorm:"type:uuid;index" json:"project_id"`
	Name                string                 `gorm:"size:255" json:"name"`
	Description         string                 `gorm:"type:text" json:"description"`
	NaturalLanguageInput string                `gorm:"type:text" json:"natural_language_input"`
	ParsedStructure     map[string]interface{} `gorm:"type:jsonb;serializer:json" json:"parsed_structure"`
	Status              string                 `gorm:"size:50;default:'draft'" json:"status"`
	CreatedBy           uuid.UUID              `gorm:"type:uuid" json:"created_by"`
	CreatedAt           time.Time              `json:"created_at"`
	UpdatedAt           time.Time              `json:"updated_at"`
}

// TestCase 测试用例
type TestCase struct {
	ID           uuid.UUID  `gorm:"type:uuid;primary_key" json:"id"`
	ScenarioID   uuid.UUID  `gorm:"type:uuid;index" json:"scenario_id"`
	Name         string     `gorm:"size:255" json:"name"`
	Description  string     `gorm:"type:text" json:"description"`
	Steps        []TestStep `gorm:"type:jsonb;serializer:json" json:"steps"`
	DataStrategy string     `gorm:"size:50" json:"data_strategy"`
	Tags         []string   `gorm:"type:jsonb;serializer:json" json:"tags"`
	Enabled      bool       `gorm:"default:true" json:"enabled"`
	CreatedAt    time.Time  `json:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at"`
}

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

// TestExecution 测试执行记录
type TestExecution struct {
	ID         uuid.UUID              `gorm:"type:uuid;primary_key" json:"id"`
	TestCaseID uuid.UUID              `gorm:"type:uuid;index" json:"test_case_id"`
	Environment string                `gorm:"size:50" json:"environment"`
	Status     string                 `gorm:"size:50" json:"status"`
	StartTime  time.Time              `json:"start_time"`
	EndTime    *time.Time             `json:"end_time,omitempty"`
	DurationMs int64                  `json:"duration_ms"`
	Result     map[string]interface{} `gorm:"type:jsonb;serializer:json" json:"result"`
	ErrorMsg   string                 `gorm:"type:text" json:"error_msg,omitempty"`
	CreatedBy  uuid.UUID              `gorm:"type:uuid" json:"created_by"`
	CreatedAt  time.Time              `json:"created_at"`
}

// BeforeCreate GORM钩子 - 创建前生成UUID
func (s *Scenario) BeforeCreate(tx *gorm.DB) error {
	if s.ID == uuid.Nil {
		s.ID = uuid.New()
	}
	return nil
}

func (tc *TestCase) BeforeCreate(tx *gorm.DB) error {
	if tc.ID == uuid.Nil {
		tc.ID = uuid.New()
	}
	return nil
}

func (te *TestExecution) BeforeCreate(tx *gorm.DB) error {
	if te.ID == uuid.Nil {
		te.ID = uuid.New()
	}
	return nil
}
