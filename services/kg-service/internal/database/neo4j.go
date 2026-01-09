package database

import (
	"context"
	"fmt"

	"github.com/aitesting/kg-service/internal/config"
	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

type Neo4jDB struct {
	Driver neo4j.DriverWithContext
}

func NewNeo4jDB(cfg *config.Config) (*Neo4jDB, error) {
	driver, err := neo4j.NewDriverWithContext(
		cfg.Neo4jURI,
		neo4j.BasicAuth(cfg.Neo4jUser, cfg.Neo4jPass, ""),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create driver: %w", err)
	}

	// 验证连接
	ctx := context.Background()
	if err := driver.VerifyConnectivity(ctx); err != nil {
		return nil, fmt.Errorf("failed to verify connectivity: %w", err)
	}

	return &Neo4jDB{Driver: driver}, nil
}

func (db *Neo4jDB) Close(ctx context.Context) error {
	return db.Driver.Close(ctx)
}

// ExecuteWrite 执行写操作
func (db *Neo4jDB) ExecuteWrite(ctx context.Context, query string, params map[string]interface{}) (interface{}, error) {
	session := db.Driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	result, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (interface{}, error) {
		result, err := tx.Run(ctx, query, params)
		if err != nil {
			return nil, err
		}

		if result.Next(ctx) {
			return result.Record().AsMap(), nil
		}

		return nil, result.Err()
	})

	return result, err
}

// ExecuteRead 执行读操作
func (db *Neo4jDB) ExecuteRead(ctx context.Context, query string, params map[string]interface{}) ([]map[string]interface{}, error) {
	session := db.Driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)

	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (interface{}, error) {
		result, err := tx.Run(ctx, query, params)
		if err != nil {
			return nil, err
		}

		var records []map[string]interface{}
		for result.Next(ctx) {
			records = append(records, result.Record().AsMap())
		}

		if err := result.Err(); err != nil {
			return nil, err
		}

		return records, nil
	})

	if err != nil {
		return nil, err
	}

	return result.([]map[string]interface{}), nil
}
