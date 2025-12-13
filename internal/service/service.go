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

func (s *Service) GetData(params domain.ConnectionParams, tableName string, limit, offset int, sortField string, sortOrder string) ([]map[string]interface{}, []domain.Column, int, error) {
	data, cols, err := s.repo.GetData(params, tableName, limit, offset, sortField, sortOrder)
	if err != nil {
		return nil, nil, 0, err
	}
	count, err := s.repo.GetTotalCount(params, tableName)
	if err != nil {
		return nil, nil, 0, err
	}
	return data, cols, count, nil
}

func (s *Service) UpdateData(params domain.ConnectionParams, tableName string, dbKey string, data map[string]interface{}) error {
	return s.repo.UpdateData(params, tableName, dbKey, data)
}

func (s *Service) ListViews(params domain.ConnectionParams) ([]domain.Table, error) {
	return s.repo.ListViews(params)
}

func (s *Service) ListProcedures(params domain.ConnectionParams) ([]domain.Table, error) {
	return s.repo.ListProcedures(params)
}

func (s *Service) GetProcedureSource(params domain.ConnectionParams, procName string) (string, error) {
	return s.repo.GetProcedureSource(params, procName)
}
