package models

import "time"

// APINode 表示一个API节点
type APINode struct {
	ID             string                 `json:"id"`
	Name           string                 `json:"name"`
	Method         string                 `json:"method"`
	Path           string                 `json:"path"`
	ProjectID      string                 `json:"project_id"`
	Description    string                 `json:"description,omitempty"`
	RequestSchema  map[string]interface{} `json:"request_schema,omitempty"`
	ResponseSchema map[string]interface{} `json:"response_schema,omitempty"`
	Tags           []string               `json:"tags,omitempty"`
	CreatedAt      time.Time              `json:"created_at"`
	UpdatedAt      time.Time              `json:"updated_at"`
}

// CreateAPINodeInput 创建API节点的输入
type CreateAPINodeInput struct {
	Name           string                 `json:"name" binding:"required"`
	Method         string                 `json:"method" binding:"required"`
	Path           string                 `json:"path" binding:"required"`
	ProjectID      string                 `json:"project_id" binding:"required"`
	Description    string                 `json:"description"`
	RequestSchema  map[string]interface{} `json:"request_schema"`
	ResponseSchema map[string]interface{} `json:"response_schema"`
	Tags           []string               `json:"tags"`
}

// UpdateAPINodeInput 更新API节点的输入
type UpdateAPINodeInput struct {
	Name           string                 `json:"name"`
	Description    string                 `json:"description"`
	RequestSchema  map[string]interface{} `json:"request_schema"`
	ResponseSchema map[string]interface{} `json:"response_schema"`
	Tags           []string               `json:"tags"`
}
