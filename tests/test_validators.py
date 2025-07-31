import pytest
from app.utils.validators import (
    validar_cpf, validar_telefone, validar_data, validar_horario,
    formatar_cpf, formatar_telefone, formatar_data,
    extrair_cpf_da_mensagem, extrair_telefone_da_mensagem
)
from datetime import datetime, timedelta

class TestCPFValidator:
    """Testes para validação de CPF"""
    
    def test_cpf_valido(self):
        """Testa CPFs válidos"""
        cpfs_validos = [
            "12345678909",
            "11144477735",
            "123.456.789-09",
            "111.444.777-35"
        ]
        
        for cpf in cpfs_validos:
            assert validar_cpf(cpf) == True
    
    def test_cpf_invalido(self):
        """Testa CPFs inválidos"""
        cpfs_invalidos = [
            "12345678901",  # Dígitos verificadores incorretos
            "11111111111",  # Todos iguais
            "00000000000",  # Todos zeros
            "1234567890",   # Menos de 11 dígitos
            "123456789012", # Mais de 11 dígitos
            "abc123def45",  # Caracteres não numéricos
            ""              # Vazio
        ]
        
        for cpf in cpfs_invalidos:
            assert validar_cpf(cpf) == False
    
    def test_formatar_cpf(self):
        """Testa formatação de CPF"""
        cpf_limpo = "12345678909"
        cpf_formatado = formatar_cpf(cpf_limpo)
        assert cpf_formatado == "123.456.789-09"
    
    def test_extrair_cpf_da_mensagem(self):
        """Testa extração de CPF de mensagem"""
        mensagens = [
            "Meu CPF é 123.456.789-09",
            "CPF: 12345678909",
            "Informe seu CPF: 111.444.777-35",
            "Não tem CPF aqui"
        ]
        
        cpfs_esperados = [
            "12345678909",
            "12345678909", 
            "11144477735",
            None
        ]
        
        for mensagem, cpf_esperado in zip(mensagens, cpfs_esperados):
            resultado = extrair_cpf_da_mensagem(mensagem)
            assert resultado == cpf_esperado

class TestTelefoneValidator:
    """Testes para validação de telefone"""
    
    def test_telefone_valido(self):
        """Testa telefones válidos"""
        telefones_validos = [
            "11999999999",      # Celular SP
            "31987654321",      # Celular MG
            "1133334444",       # Fixo SP
            "3133334444",       # Fixo MG
            "5511999999999",    # Com código do país
            "5531987654321",    # Com código do país
            "(11) 99999-9999",  # Formatado
            "(31) 3333-4444"    # Formatado
        ]
        
        for telefone in telefones_validos:
            assert validar_telefone(telefone) == True
    
    def test_telefone_invalido(self):
        """Testa telefones inválidos"""
        telefones_invalidos = [
            "123456789",        # Muito curto
            "123456789012345",  # Muito longo
            "00999999999",      # DDD inválido
            "99999999999",      # DDD inválido
            "abc123def45",      # Caracteres não numéricos
            ""                  # Vazio
        ]
        
        for telefone in telefones_invalidos:
            assert validar_telefone(telefone) == False
    
    def test_formatar_telefone(self):
        """Testa formatação de telefone"""
        # Celular
        celular = "11999999999"
        celular_formatado = formatar_telefone(celular)
        assert celular_formatado == "(11) 99999-9999"
        
        # Fixo
        fixo = "1133334444"
        fixo_formatado = formatar_telefone(fixo)
        assert fixo_formatado == "(11) 3333-4444"
    
    def test_extrair_telefone_da_mensagem(self):
        """Testa extração de telefone de mensagem"""
        mensagens = [
            "Meu telefone é (11) 99999-9999",
            "Tel: 11999999999",
            "Ligue: 31 3333-4444",
            "Não tem telefone aqui"
        ]
        
        telefones_esperados = [
            "11999999999",
            "11999999999",
            "3133334444", 
            None
        ]
        
        for mensagem, telefone_esperado in zip(mensagens, telefones_esperados):
            resultado = extrair_telefone_da_mensagem(mensagem)
            assert resultado == telefone_esperado

class TestDataValidator:
    """Testes para validação de data"""
    
    def test_data_valida(self):
        """Testa datas válidas"""
        # Data futura válida
        data_futura = (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")
        assert validar_data(data_futura) is not None
    
    def test_data_invalida(self):
        """Testa datas inválidas"""
        datas_invalidas = [
            "32/12/2024",       # Dia inválido
            "15/13/2024",       # Mês inválido
            "15/12/2020",       # Data passada
            "15/12/2026",       # Muito distante
            "15-12-2024",       # Formato incorreto
            "abc/def/ghij",     # Caracteres não numéricos
            ""                  # Vazio
        ]
        
        for data in datas_invalidas:
            assert validar_data(data) is None
    
    def test_formatar_data(self):
        """Testa formatação de data"""
        data = datetime(2024, 12, 15)
        data_formatada = formatar_data(data)
        assert data_formatada == "15/12/2024"

class TestHorarioValidator:
    """Testes para validação de horário"""
    
    def test_horario_valido(self):
        """Testa horários válidos"""
        horarios_validos = [
            "08:00",
            "09:30", 
            "14:15",
            "17:45"
        ]
        
        for horario in horarios_validos:
            assert validar_horario(horario) == horario
    
    def test_horario_invalido(self):
        """Testa horários inválidos"""
        horarios_invalidos = [
            "07:00",    # Antes do horário comercial
            "19:00",    # Depois do horário comercial
            "25:00",    # Hora inválida
            "12:60",    # Minuto inválido
            "8:30",     # Formato incorreto
            "abc:def",  # Caracteres não numéricos
            ""          # Vazio
        ]
        
        for horario in horarios_invalidos:
            assert validar_horario(horario) is None 