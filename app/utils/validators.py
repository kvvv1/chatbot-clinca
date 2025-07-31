import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)

def validar_cpf(cpf: str) -> bool:
    """
    Valida CPF brasileiro usando algoritmo oficial
    
    Args:
        cpf: String contendo o CPF (com ou sem formatação)
    
    Returns:
        bool: True se CPF é válido, False caso contrário
    """
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', cpf)
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais (CPF inválido)
    if cpf == cpf[0] * 11:
        return False
    
    # Calcula primeiro dígito verificador
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    
    resto = soma % 11
    if resto < 2:
        digito1 = 0
    else:
        digito1 = 11 - resto
    
    # Calcula segundo dígito verificador
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    
    resto = soma % 11
    if resto < 2:
        digito2 = 0
    else:
        digito2 = 11 - resto
    
    # Verifica se os dígitos calculados são iguais aos do CPF
    return cpf[-2:] == f"{digito1}{digito2}"

def validar_telefone(telefone: str) -> bool:
    """
    Valida telefone brasileiro
    
    Args:
        telefone: String contendo o telefone
    
    Returns:
        bool: True se telefone é válido, False caso contrário
    """
    # Remove caracteres não numéricos
    clean = re.sub(r'[^0-9]', '', telefone)
    
    # Verifica se tem entre 10 e 13 dígitos (com código do país)
    if len(clean) < 10 or len(clean) > 13:
        return False
    
    # Se tem 13 dígitos, deve começar com 55 (Brasil)
    if len(clean) == 13 and not clean.startswith('55'):
        return False
    
    # Se tem 12 dígitos, deve começar com 55
    if len(clean) == 12 and not clean.startswith('55'):
        return False
    
    # Remove código do país para validação
    if clean.startswith('55'):
        clean = clean[2:]
    
    # Agora deve ter 10 ou 11 dígitos
    if len(clean) not in [10, 11]:
        return False
    
    # DDD válido (11-99)
    ddd = int(clean[:2])
    if ddd < 11 or ddd > 99:
        return False
    
    return True

def validar_data(data_str: str) -> Optional[datetime]:
    """
    Valida data no formato brasileiro DD/MM/YYYY
    
    Args:
        data_str: String contendo a data
    
    Returns:
        datetime: Objeto datetime se válido, None caso contrário
    """
    try:
        # Verifica formato
        if not re.match(r'^\d{2}/\d{2}/\d{4}$', data_str):
            return None
        
        # Converte para datetime
        data = datetime.strptime(data_str, '%d/%m/%Y')
        
        # Verifica se é data futura
        if data.date() < datetime.now().date():
            return None
        
        # Verifica se não é muito distante (máximo 1 ano)
        if data.date() > (datetime.now() + timedelta(days=365)).date():
            return None
        
        return data
        
    except ValueError:
        return None

def validar_horario(horario_str: str) -> Optional[str]:
    """
    Valida horário no formato HH:MM
    
    Args:
        horario_str: String contendo o horário
    
    Returns:
        str: Horário formatado se válido, None caso contrário
    """
    try:
        # Verifica formato
        if not re.match(r'^\d{2}:\d{2}$', horario_str):
            return None
        
        # Converte para verificar
        hora, minuto = map(int, horario_str.split(':'))
        
        # Validações
        if hora < 0 or hora > 23:
            return None
        
        if minuto < 0 or minuto > 59:
            return None
        
        # Horário comercial (8h às 18h)
        if hora < 8 or hora >= 18:
            return None
        
        return horario_str
        
    except ValueError:
        return None

def formatar_cpf(cpf: str) -> str:
    """
    Formata CPF para o padrão XXX.XXX.XXX-XX
    
    Args:
        cpf: String contendo o CPF
    
    Returns:
        str: CPF formatado
    """
    # Remove caracteres não numéricos
    clean = re.sub(r'[^0-9]', '', cpf)
    
    if len(clean) != 11:
        raise ValueError("CPF deve ter 11 dígitos")
    
    return f"{clean[:3]}.{clean[3:6]}.{clean[6:9]}-{clean[9:]}"

def formatar_telefone(telefone: str) -> str:
    """
    Formata telefone brasileiro
    
    Args:
        telefone: String contendo o telefone
    
    Returns:
        str: Telefone formatado
    """
    # Remove caracteres não numéricos
    clean = re.sub(r'[^0-9]', '', telefone)
    
    # Remove código do país se presente
    if clean.startswith('55'):
        clean = clean[2:]
    
    # Formata baseado no número de dígitos
    if len(clean) == 11:  # Celular
        return f"({clean[:2]}) {clean[2:7]}-{clean[7:]}"
    elif len(clean) == 10:  # Fixo
        return f"({clean[:2]}) {clean[2:6]}-{clean[6:]}"
    else:
        raise ValueError("Telefone inválido")

def formatar_data(data: datetime) -> str:
    """
    Formata data para o padrão brasileiro DD/MM/YYYY
    
    Args:
        data: Objeto datetime
    
    Returns:
        str: Data formatada
    """
    return data.strftime('%d/%m/%Y')

def formatar_data_hora(data: datetime) -> str:
    """
    Formata data e hora para o padrão brasileiro
    
    Args:
        data: Objeto datetime
    
    Returns:
        str: Data e hora formatada
    """
    return data.strftime('%d/%m/%Y às %H:%M')

def extrair_cpf_da_mensagem(mensagem: str) -> Optional[str]:
    """
    Extrai CPF de uma mensagem de texto
    
    Args:
        mensagem: Texto da mensagem
    
    Returns:
        str: CPF encontrado ou None
    """
    # Padrões para CPF
    padroes = [
        r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b',  # XXX.XXX.XXX-XX
        r'\b\d{11}\b',  # 11 dígitos consecutivos
    ]
    
    for padrao in padroes:
        match = re.search(padrao, mensagem)
        if match:
            cpf = match.group()
            # Remove formatação para validação
            cpf_limpo = re.sub(r'[^0-9]', '', cpf)
            if validar_cpf(cpf_limpo):
                return cpf_limpo
    
    return None

def extrair_telefone_da_mensagem(mensagem: str) -> Optional[str]:
    """
    Extrai telefone de uma mensagem de texto
    
    Args:
        mensagem: Texto da mensagem
    
    Returns:
        str: Telefone encontrado ou None
    """
    # Padrões para telefone
    padroes = [
        r'\b\d{2}\s\d{4,5}-\d{4}\b',  # (XX) XXXXX-XXXX
        r'\b\d{11}\b',  # 11 dígitos consecutivos
        r'\b\d{10}\b',  # 10 dígitos consecutivos
    ]
    
    for padrao in padroes:
        match = re.search(padrao, mensagem)
        if match:
            telefone = match.group()
            # Remove formatação para validação
            telefone_limpo = re.sub(r'[^0-9]', '', telefone)
            if validar_telefone(telefone_limpo):
                return telefone_limpo
    
    return None

def mascarar_dados_sensiveis(texto: str) -> str:
    """
    Mascara dados sensíveis em logs
    
    Args:
        texto: Texto que pode conter dados sensíveis
    
    Returns:
        str: Texto com dados mascarados
    """
    # Mascara CPF
    texto = re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', '***.***.***-**', texto)
    texto = re.sub(r'\b\d{11}\b', '***********', texto)
    
    # Mascara telefone
    texto = re.sub(r'\b\d{2}\s\d{4,5}-\d{4}\b', '(**) ****-****', texto)
    
    return texto 