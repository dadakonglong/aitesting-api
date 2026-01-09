package config

import (
	"log"
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	// 服务配置
	Port string

	// 数据库配置
	DatabaseURL string

	// Redis配置
	RedisURL string

	// RabbitMQ配置
	RabbitMQURL string

	// AI服务配置
	AIServiceURL string

	// 知识图谱服务配置
	KGServiceURL string
}

func Load() *Config {
	// 加载.env文件
	if err := godotenv.Load(); err != nil {
		log.Println("未找到.env文件，使用环境变量")
	}

	return &Config{
		Port:         getEnv("SCENARIO_SERVICE_PORT", "8081"),
		DatabaseURL:  getEnv("DATABASE_URL", ""),
		RedisURL:     getEnv("REDIS_URL", "redis://localhost:6379"),
		RabbitMQURL:  getEnv("RABBITMQ_URL", "amqp://admin:password@localhost:5672"),
		AIServiceURL: getEnv("AI_SERVICE_URL", "http://localhost:8000"),
		KGServiceURL: getEnv("KG_SERVICE_URL", "http://localhost:8082"),
	}
}

func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}
