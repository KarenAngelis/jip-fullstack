from enum import Enum

class Profissao(str, Enum):
    """
    Enum que representa as diferentes profissões mapeadas na aplicação.
    
    Herdar de 'str' e 'Enum' permite que os membros se comportem
    como strings, o que é ideal para APIs (ex: serialização para JSON).
    """
    ADVOGADO = "advogado"
    PSICOLOGO = "psicologo"
    ESTETICISTA = "esteticista"
    NUTRICIONISTA = "nutricionista"
    MEDICO = "medico"
    INFLUENCER = "influencer"
    ENGENHEIRO = "engenheiro"
    PROFESSOR = "professor"
    FINANCEIRO = "financeiro"
    PERSONAL = "personal_trainer"
    VETERINARIO = "veterinario"
    ARQUITETO = "arquiteto"
    COACH = "coach"
    DENTISTA = "dentista"