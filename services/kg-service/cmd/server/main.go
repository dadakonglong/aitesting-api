package main

import (
	"log"
	"net/http"

	"github.com/aitesting/kg-service/internal/config"
	"github.com/aitesting/kg-service/internal/database"
	"github.com/gin-gonic/gin"
)

func main() {
	// 加载配置
	cfg := config.Load()

	// 初始化数据库连接
	db, err := database.NewNeo4jDB(cfg)
	if err != nil {
		log.Fatalf("无法连接到 Neo4j: %v", err)
	}
	defer db.Close()

	// 初始化路由
	r := gin.Default()

	// 健康检查
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service": "kg-service",
			"status":  "healthy",
		})
	})

	// 基础路由
	r.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"message": "AI Testing API Knowledge Graph Service",
		})
	})

	// 启动服务器
	log.Printf("知识图谱服务启动在端口 %s...", cfg.ServerPort)
	if err := r.Run(":" + cfg.ServerPort); err != nil {
		log.Fatalf("服务启动失败: %v", err)
	}
}
