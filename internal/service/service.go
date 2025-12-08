package service

import (
	"firebird-web-admin/internal/domain"
	"firebird-web-admin/internal/repository"
)

type Service struct {
	repo repository.Repository
}

func NewService(repo repository.Repository) *Service {
	return &Service{repo: repo}
}

func (s *Service) Connect(params domain.ConnectionParams) error {
	return s.repo.TestConnection(params)
}

func (s *Service) ListTables(params domain.ConnectionParams) ([]domain.Table, error) {
	return s.repo.ListTables(params)
}

func (s *Service) GetData(params domain.ConnectionParams, tableName string) ([]map[string]interface{}, error) {
	return s.repo.GetData(params, tableName)
}
