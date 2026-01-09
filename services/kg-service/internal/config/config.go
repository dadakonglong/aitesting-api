package config

import (
	"os"
)

type Config struct {
	ServerPort string
	Neo4jURI   string
	Neo4jUser  string
	Neo4jPass  string
}

func Load() *Config {
	return &Config{
		ServerPort: getEnv("KG_SERVICE_PORT", "8082"),
		Neo4jURI:   getEnv("NEO4J_URI", "bolt://localhost:7687"),
		Neo4jUser:  getEnv("NEO4J_USER", "neo4j"),
		Neo4jPass:  getEnv("NEO4J_PASSWORD", "password"),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
