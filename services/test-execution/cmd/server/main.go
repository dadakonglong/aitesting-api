package main

import (
	"log"
	"os"

	"github.com/aitesting/test-execution/internal/handlers"
	"github.com/aitesting/test-execution/internal/services"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func main() {
	// 加载环境变量
	godotenv.Load()

	// 初始化数据库
	databaseURL := os.Getenv("DATABASE_URL")
	db, err := gorm.Open(postgres.Open(databaseURL), &gorm.Config{})
	if err != nil {
		log.Fatal("数据库连接失败:", err)
	}

	// 自动迁移
	db.AutoMigrate(&services.TestExecution{})

	// 初始化服务
	executionService := services.NewExecutionService(db)

	// 初始化处理器
	executionHandler := handlers.NewExecutionHandler(executionService)

	// 创建Gin路由
	r := gin.Default()

	// 健康检查
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":  "healthy",
			"service": "test-execution",
		})
	})

	// API路由
	api := r.Group("/api/v1")
	{
		// 执行相关
		executions := api.Group("/executions")
		{
			executions.POST("", executionHandler.ExecuteTestCase)
			executions.GET("", executionHandler.ListExecutions)
			executions.GET("/:id", executionHandler.GetExecution)
		}
	}

	// 启动服务
	port := os.Getenv("EXECUTION_SERVICE_PORT")
	if port == "" {
		port = "8083"
	}

	log.Printf("测试执行服务启动在端口 %s", port)
	if err := r.Run(":" + port); err != nil {
		log.Fatal("服务启动失败:", err)
	}
}
