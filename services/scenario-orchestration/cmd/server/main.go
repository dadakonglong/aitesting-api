package main

import (
	"log"

	"github.com/aitesting/scenario-orchestration/internal/config"
	"github.com/aitesting/scenario-orchestration/internal/database"
	"github.com/aitesting/scenario-orchestration/internal/handlers"
	"github.com/aitesting/scenario-orchestration/internal/services"
	"github.com/gin-gonic/gin"
)

func main() {
	// 加载配置
	cfg := config.Load()

	// 初始化数据库
	if err := database.Init(cfg.DatabaseURL); err != nil {
		log.Fatal("数据库初始化失败:", err)
	}

	// 初始化服务
	db := database.GetDB()
	scenarioService := services.NewScenarioService(db, cfg.AIServiceURL)

	// 初始化处理器
	scenarioHandler := handlers.NewScenarioHandler(scenarioService)

	// 创建Gin路由
	r := gin.Default()

	// 健康检查
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status": "healthy",
			"service": "scenario-orchestration",
		})
	})

	// API路由
	api := r.Group("/api/v1")
	{
		// 场景相关
		scenarios := api.Group("/scenarios")
		{
			scenarios.POST("", scenarioHandler.CreateScenario)
			scenarios.GET("", scenarioHandler.ListScenarios)
			scenarios.GET("/:id", scenarioHandler.GetScenario)
			scenarios.POST("/:id/generate-case", scenarioHandler.GenerateTestCase)
		}
	}

	// 启动服务
	log.Printf("场景编排服务启动在端口 %s", cfg.Port)
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatal("服务启动失败:", err)
	}
}
