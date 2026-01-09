package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/aitesting/scenario-orchestration/internal/models"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type ScenarioService struct {
	db           *gorm.DB
	aiServiceURL string
}

func NewScenarioService(db *gorm.DB, aiServiceURL string) *ScenarioService {
	return &ScenarioService{
		db:           db,
		aiServiceURL: aiServiceURL,
	}
}

// CreateScenarioRequest 创建场景请求
type CreateScenarioRequest struct {
	ProjectID            string `json:"project_id"`
	NaturalLanguageInput string `json:"natural_language_input"`
}

// CreateScenario 创建场景
func (s *ScenarioService) CreateScenario(req *CreateScenarioRequest) (*models.Scenario, error) {
	// 1. 调用AI服务进行RAG增强理解
	enhanceResp, err := s.callAIEnhance(req.NaturalLanguageInput, req.ProjectID)
	if err != nil {
		return nil, fmt.Errorf("AI增强理解失败: %w", err)
	}

	// 2. 提取理解结果
	understanding := enhanceResp["understanding"].(map[string]interface{})
	
	// 3. 调用AI服务解析场景
	parseResp, err := s.callAIParse(understanding, req.ProjectID)
	if err != nil {
		return nil, fmt.Errorf("场景解析失败: %w", err)
	}

	// 4. 创建场景记录
	projectUUID, _ := uuid.Parse(req.ProjectID)
	scenario := &models.Scenario{
		ProjectID:            projectUUID,
		Name:                 parseResp["scenario_name"].(string),
		Description:          parseResp["description"].(string),
		NaturalLanguageInput: req.NaturalLanguageInput,
		ParsedStructure:      parseResp,
		Status:               "draft",
	}

	if err := s.db.Create(scenario).Error; err != nil {
		return nil, err
	}

	return scenario, nil
}

// GenerateTestCase 生成测试用例
func (s *ScenarioService) GenerateTestCase(scenarioID uuid.UUID, dataStrategy string) (*models.TestCase, error) {
	// 1. 获取场景
	var scenario models.Scenario
	if err := s.db.First(&scenario, "id = ?", scenarioID).Error; err != nil {
		return nil, err
	}

	// 2. 解析场景结构
	steps := scenario.ParsedStructure["steps"].([]interface{})
	
	// 3. 为每个步骤生成测试数据和断言
	var testSteps []models.TestStep
	
	for i, stepData := range steps {
		stepMap := stepData.(map[string]interface{})
		
		// 调用AI生成测试数据
		testData, err := s.callAIGenerateData(stepMap, dataStrategy)
		if err != nil {
			return nil, fmt.Errorf("生成测试数据失败: %w", err)
		}

		// 调用AI生成断言
		assertions, err := s.callAIGenerateAssertions(stepMap)
		if err != nil {
			return nil, fmt.Errorf("生成断言失败: %w", err)
		}

		testStep := models.TestStep{
			ID:             uuid.New().String(),
			StepOrder:      i + 1,
			APIID:          stepMap["api_id"].(string),
			APIName:        stepMap["api_name"].(string),
			APIPath:        stepMap["api_path"].(string),
			APIMethod:      stepMap["api_method"].(string),
			Description:    stepMap["description"].(string),
			Params:         testData,
			Assertions:     assertions,
			ExpectedStatus: 200,
			Timeout:        30000,
		}

		testSteps = append(testSteps, testStep)
	}

	// 4. 创建测试用例
	testCase := &models.TestCase{
		ScenarioID:   scenarioID,
		Name:         scenario.Name + " - " + dataStrategy,
		Description:  scenario.Description,
		Steps:        testSteps,
		DataStrategy: dataStrategy,
		Enabled:      true,
	}

	if err := s.db.Create(testCase).Error; err != nil {
		return nil, err
	}

	return testCase, nil
}

// GetScenario 获取场景
func (s *ScenarioService) GetScenario(id uuid.UUID) (*models.Scenario, error) {
	var scenario models.Scenario
	if err := s.db.First(&scenario, "id = ?", id).Error; err != nil {
		return nil, err
	}
	return &scenario, nil
}

// ListScenarios 列出场景
func (s *ScenarioService) ListScenarios(projectID uuid.UUID, page, pageSize int) ([]models.Scenario, int64, error) {
	var scenarios []models.Scenario
	var total int64

	query := s.db.Model(&models.Scenario{})
	if projectID != uuid.Nil {
		query = query.Where("project_id = ?", projectID)
	}

	// 获取总数
	query.Count(&total)

	// 分页查询
	offset := (page - 1) * pageSize
	if err := query.Offset(offset).Limit(pageSize).Order("created_at DESC").Find(&scenarios).Error; err != nil {
		return nil, 0, err
	}

	return scenarios, total, nil
}

// AI服务调用辅助方法

func (s *ScenarioService) callAIEnhance(description, projectID string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/rag/enhance-scenario", s.aiServiceURL)
	
	payload := map[string]string{
		"description": description,
		"project_id":  projectID,
	}

	return s.callAIService(url, payload)
}

func (s *ScenarioService) callAIParse(nluResult map[string]interface{}, projectID string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/ai/parse-scenario", s.aiServiceURL)
	
	payload := map[string]interface{}{
		"nlu_result": nluResult,
		"project_id": projectID,
	}

	return s.callAIService(url, payload)
}

func (s *ScenarioService) callAIGenerateData(stepInfo map[string]interface{}, strategy string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/v1/ai/generate-data", s.aiServiceURL)
	
	payload := map[string]interface{}{
		"param_schema": stepInfo["params"],
		"strategy":     strategy,
		"count":        1,
	}

	resp, err := s.callAIService(url, payload)
	if err != nil {
		return nil, err
	}

	// 提取第一组数据
	data := resp["data"].([]interface{})
	if len(data) > 0 {
		return data[0].(map[string]interface{}), nil
	}

	return make(map[string]interface{}), nil
}

func (s *ScenarioService) callAIGenerateAssertions(stepInfo map[string]interface{}) ([]models.Assertion, error) {
	url := fmt.Sprintf("%s/api/v1/ai/generate-assertions", s.aiServiceURL)
	
	payload := map[string]interface{}{
		"api_info": stepInfo,
	}

	resp, err := s.callAIService(url, payload)
	if err != nil {
		return nil, err
	}

	// 解析断言
	assertionsData := resp["assertions"].([]interface{})
	var assertions []models.Assertion

	for _, a := range assertionsData {
		aMap := a.(map[string]interface{})
		assertion := models.Assertion{
			Type:          aMap["type"].(string),
			Field:         aMap["field"].(string),
			Operator:      aMap["operator"].(string),
			ExpectedValue: aMap["expected_value"],
			Description:   aMap["description"].(string),
		}
		assertions = append(assertions, assertion)
	}

	return assertions, nil
}

func (s *ScenarioService) callAIService(url string, payload interface{}) (map[string]interface{}, error) {
	jsonData, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("AI服务返回错误: %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return result, nil
}
