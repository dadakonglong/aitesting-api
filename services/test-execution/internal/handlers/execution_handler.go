package handlers

import (
	"net/http"

	"github.com/aitesting/test-execution/internal/services"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type ExecutionHandler struct {
	service *services.ExecutionService
}

func NewExecutionHandler(service *services.ExecutionService) *ExecutionHandler {
	return &ExecutionHandler{service: service}
}

// ExecuteTestCase 执行测试用例
func (h *ExecutionHandler) ExecuteTestCase(c *gin.Context) {
	var req struct {
		TestCaseID  string `json:"test_case_id" binding:"required"`
		Environment string `json:"environment" binding:"required"`
		BaseURL     string `json:"base_url" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	testCaseID, err := uuid.Parse(req.TestCaseID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的测试用例ID"})
		return
	}

	execution, err := h.service.ExecuteTestCase(testCaseID, req.Environment, req.BaseURL)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, execution)
}

// GetExecution 获取执行记录
func (h *ExecutionHandler) GetExecution(c *gin.Context) {
	idStr := c.Param("id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的ID"})
		return
	}

	execution, err := h.service.GetExecution(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "执行记录不存在"})
		return
	}

	c.JSON(http.StatusOK, execution)
}

// ListExecutions 列出执行记录
func (h *ExecutionHandler) ListExecutions(c *gin.Context) {
	testCaseIDStr := c.Query("test_case_id")
	page := 1
	pageSize := 10

	var testCaseID uuid.UUID
	if testCaseIDStr != "" {
		var err error
		testCaseID, err = uuid.Parse(testCaseIDStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "无效的测试用例ID"})
			return
		}
	}

	executions, total, err := h.service.ListExecutions(testCaseID, page, pageSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"data":      executions,
		"total":     total,
		"page":      page,
		"page_size": pageSize,
	})
}
