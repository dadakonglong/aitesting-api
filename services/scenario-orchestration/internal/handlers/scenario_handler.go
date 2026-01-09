package handlers

import (
	"net/http"
	"strconv"

	"github.com/aitesting/scenario-orchestration/internal/services"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type ScenarioHandler struct {
	service *services.ScenarioService
}

func NewScenarioHandler(service *services.ScenarioService) *ScenarioHandler {
	return &ScenarioHandler{service: service}
}

// CreateScenario 创建场景
// @Summary 创建测试场景
// @Description 通过自然语言描述创建测试场景
// @Tags scenarios
// @Accept json
// @Produce json
// @Param request body services.CreateScenarioRequest true "创建场景请求"
// @Success 200 {object} models.Scenario
// @Router /api/v1/scenarios [post]
func (h *ScenarioHandler) CreateScenario(c *gin.Context) {
	var req services.CreateScenarioRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	scenario, err := h.service.CreateScenario(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, scenario)
}

// GetScenario 获取场景
// @Summary 获取场景详情
// @Tags scenarios
// @Produce json
// @Param id path string true "场景ID"
// @Success 200 {object} models.Scenario
// @Router /api/v1/scenarios/{id} [get]
func (h *ScenarioHandler) GetScenario(c *gin.Context) {
	idStr := c.Param("id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的ID"})
		return
	}

	scenario, err := h.service.GetScenario(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "场景不存在"})
		return
	}

	c.JSON(http.StatusOK, scenario)
}

// ListScenarios 列出场景
// @Summary 列出场景
// @Tags scenarios
// @Produce json
// @Param project_id query string false "项目ID"
// @Param page query int false "页码" default(1)
// @Param page_size query int false "每页数量" default(10)
// @Success 200 {object} map[string]interface{}
// @Router /api/v1/scenarios [get]
func (h *ScenarioHandler) ListScenarios(c *gin.Context) {
	projectIDStr := c.Query("project_id")
	page := c.DefaultQuery("page", "1")
	pageSize := c.DefaultQuery("page_size", "10")

	var projectID uuid.UUID
	if projectIDStr != "" {
		var err error
		projectID, err = uuid.Parse(projectIDStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "无效的项目ID"})
			return
		}
	}

	pageInt, _ := strconv.Atoi(page)
	pageSizeInt, _ := strconv.Atoi(pageSize)

	scenarios, total, err := h.service.ListScenarios(projectID, pageInt, pageSizeInt)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"data":  scenarios,
		"total": total,
		"page":  pageInt,
		"page_size": pageSizeInt,
	})
}

// GenerateTestCase 生成测试用例
// @Summary 生成测试用例
// @Tags scenarios
// @Accept json
// @Produce json
// @Param id path string true "场景ID"
// @Param request body map[string]string true "生成请求"
// @Success 200 {object} models.TestCase
// @Router /api/v1/scenarios/{id}/generate-case [post]
func (h *ScenarioHandler) GenerateTestCase(c *gin.Context) {
	idStr := c.Param("id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的ID"})
		return
	}

	var req struct {
		DataStrategy string `json:"data_strategy" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	testCase, err := h.service.GenerateTestCase(id, req.DataStrategy)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, testCase)
}
