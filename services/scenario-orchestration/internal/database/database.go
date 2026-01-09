package database

import (
	"log"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"github.com/aitesting/scenario-orchestration/internal/models"
)

var DB *gorm.DB

// Init 初始化数据库连接
func Init(databaseURL string) error {
	var err error
	
	DB, err = gorm.Open(postgres.Open(databaseURL), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
	})
	
	if err != nil {
		return err
	}

	// 自动迁移
	err = DB.AutoMigrate(
		&models.Scenario{},
		&models.TestCase{},
		&models.TestExecution{},
	)
	
	if err != nil {
		return err
	}

	log.Println("数据库连接成功")
	return nil
}

// GetDB 获取数据库实例
func GetDB() *gorm.DB {
	return DB
}
