"""
Schema da tool usada para extrair dados de um PDF de apólice via Claude.

Mantido em arquivo separado (não dentro de views.py ou de um services.py
maior) porque é um dicionário grande e praticamente estático -- separar
deixa claude_extraction.py (o próximo arquivo que vamos escrever) focado
na lógica de chamada e persistência, sem 200 linhas de schema no meio.
"""

UF_VALIDAS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
]

ENDERECO_PROPERTIES = {
    "cep": {"type": ["string", "null"]},
    "logradouro": {"type": ["string", "null"]},
    "numero": {"type": ["string", "null"]},
    "complemento": {"type": ["string", "null"]},
    "bairro": {"type": ["string", "null"]},
    "cidade": {"type": ["string", "null"]},
    "uf": {
        "type": ["string", "null"],
        "enum": UF_VALIDAS + [None],
        "description": "Sigla de 2 letras do estado (ex.: CE, SP) -- nunca o nome completo.",
    },
}

EXTRAIR_APOLICE_TOOL = {
    "name": "extrair_dados_apolice",
    "description": (
        "Extrai todos os dados estruturados de um PDF de apólice/orçamento "
        "de seguro auto. Preencha apenas o que estiver literalmente escrito "
        "no documento. NUNCA infira, estime ou copie valores de outros "
        "campos para preencher uma lacuna -- quando um dado não aparecer no "
        "PDF, retorne null nesse campo."
    ),
    "input_schema": {
        "type": "object",
        "required": ["cliente", "apolice", "veiculo", "coberturas"],
        "properties": {
            "cliente": {
                "type": "object",
                "required": [
                    "nome_completo", "tipo_documento", "cpf_cnpj", "eh_condutor_principal",
                ],
                "properties": {
                    "nome_completo": {"type": "string"},
                    "tipo_documento": {"type": "string", "enum": ["CPF", "CNPJ"]},
                    "cpf_cnpj": {"type": "string"},
                    "data_nascimento": {"type": ["string", "null"], "format": "date"},
                    "profissao": {"type": ["string", "null"]},
                    "sexo": {"type": ["string", "null"], "enum": ["M", "F", None]},
                    "estado_civil": {"type": ["string", "null"]},
                    "eh_condutor_principal": {"type": "boolean"},
                    "endereco": {
                        "type": "object",
                        "description": "Endereço de correspondência do segurado.",
                        "properties": ENDERECO_PROPERTIES,
                    },
                    "condutor_principal": {
                        "type": ["object", "null"],
                        "description": "Preencher somente se eh_condutor_principal = false.",
                        "required": ["nome_completo", "cpf"],
                        "properties": {
                            "nome_completo": {"type": "string"},
                            "cpf": {"type": "string"},
                            "profissao": {"type": ["string", "null"]},
                            "sexo": {"type": ["string", "null"], "enum": ["M", "F", None]},
                            "estado_civil": {"type": ["string", "null"]},
                        },
                    },
                },
            },
            "apolice": {
                "type": "object",
                "required": ["seguradora", "data_inicio_vigencia", "data_fim_vigencia"],
                "properties": {
                    "numero_apolice": {"type": ["string", "null"]},
                    "numero_proposta": {"type": ["string", "null"]},
                    "numero_cotacao": {"type": ["string", "null"]},
                    "bonus": {"type": ["integer", "null"]},
                    "ci": {"type": ["string", "null"]},
                    "seguradora": {"type": "string"},
                    "corretora": {"type": ["string", "null"]},
                    "data_inicio_vigencia": {"type": "string", "format": "date"},
                    "data_fim_vigencia": {"type": "string", "format": "date"},
                    "premio_total": {"type": ["number", "null"]},
                    "pernoite": {
                        "type": "object",
                        "description": "Endereço onde o veículo pernoita.",
                        "properties": ENDERECO_PROPERTIES,
                    },
                },
            },
            "veiculo": {
                "type": "object",
                "required": ["placa", "chassi"],
                "properties": {
                    "placa": {"type": "string"},
                    "chassi": {"type": "string"},
                    "marca": {"type": ["string", "null"]},
                    "modelo": {"type": ["string", "null"]},
                    "zero_km": {"type": "boolean"},
                    "ano_fabricacao": {"type": ["integer", "null"]},
                    "ano_modelo": {"type": ["integer", "null"]},
                    "tipo_veiculo": {
                        "type": ["string", "null"], "enum": ["particular", "comercial", None]
                    },
                    "combustivel": {
                        "type": ["string", "null"],
                        "enum": ["alcool", "diesel", "eletrico", "flex", "hibrido", "gasolina", None],
                    },
                    "blindado": {"type": "boolean"},
                },
            },
            "coberturas": {
                "type": "object",
                "required": ["tipo_cobertura"],
                "properties": {
                    "tipo_cobertura": {"type": "string", "enum": ["compreensiva", "rcf"]},
                    "franquia_valor": {"type": ["number", "null"]},
                    "franquia_percentual": {"type": ["number", "null"]},
                    "assistencia_24h_contratada": {"type": "boolean"},
                    "assistencia_24h_plano": {"type": ["string", "null"]},
                    "assistencia_24h_premio": {"type": ["number", "null"]},
                    "vidros_contratado": {"type": "boolean"},
                    "vidros_plano": {"type": ["string", "null"]},
                    "vidros_lmi": {"type": ["number", "null"]},
                    "vidros_premio": {"type": ["number", "null"]},
                    "vidros_franquias_detalhe": {"type": ["object", "null"]},
                    "carro_reserva_contratado": {"type": "boolean"},
                    "carro_reserva_dias": {"type": ["integer", "null"]},
                    "carro_reserva_tipo": {"type": ["string", "null"]},
                    "carro_reserva_premio": {"type": ["number", "null"]},
                    "rcf_danos_materiais_lmi": {"type": ["number", "null"]},
                    "rcf_danos_materiais_premio": {"type": ["number", "null"]},
                    "rcf_danos_corporais_lmi": {"type": ["number", "null"]},
                    "rcf_danos_corporais_premio": {"type": ["number", "null"]},
                    "rcf_danos_morais_lmi": {"type": ["number", "null"]},
                    "rcf_danos_morais_premio": {"type": ["number", "null"]},
                    "app_contratado": {"type": "boolean"},
                    "app_morte_lmi": {"type": ["number", "null"]},
                    "app_invalidez_lmi": {"type": ["number", "null"]},
                    "app_premio": {"type": ["number", "null"]},
                    "despesas_extraordinarias_contratada": {"type": "boolean"},
                    "despesas_extraordinarias_lmi": {"type": ["number", "null"]},
                    "despesas_extraordinarias_premio": {"type": ["number", "null"]},
                    "despesas_medico_hospitalares_contratada": {"type": "boolean"},
                    "despesas_medico_hospitalares_lmi": {"type": ["number", "null"]},
                    "despesas_medico_hospitalares_premio": {"type": ["number", "null"]},
                    "blindagem_contratada": {"type": "boolean"},
                    "blindagem_lmi": {"type": ["number", "null"]},
                    "blindagem_premio": {"type": ["number", "null"]},
                },
            },
            "coberturas_extra": {
                "type": "array",
                "description": "Itens de cobertura/serviço fora dos campos fixos acima.",
                "items": {
                    "type": "object",
                    "required": ["descricao"],
                    "properties": {
                        "descricao": {"type": "string"},
                        "lmi": {"type": ["number", "null"]},
                        "franquia": {"type": ["number", "null"]},
                        "premio": {"type": ["number", "null"]},
                    },
                },
            },
        },
    },
}

SYSTEM_PROMPT_EXTRACAO = """\
Você é um extrator de dados de apólices de seguro auto brasileiras.

Regras obrigatórias:
1. Use exclusivamente a tool `extrair_dados_apolice` para responder -- nunca \
responda em texto livre.
2. Extraia apenas o que está literalmente escrito no documento. Nunca infira, \
estime, arredonde ou copie de outro campo para preencher uma lacuna.
3. Quando um campo não existir no documento, retorne null explicitamente.
4. Datas sempre no formato YYYY-MM-DD.
5. Valores monetários como número (sem "R$", sem separador de milhar), \
usando ponto como separador decimal.
6. Se o mesmo tipo de informação aparecer mais de uma vez no PDF (ex.: \
franquias diferentes por página), use o valor da tabela de resumo/coberturas \
contratadas, não de exemplos ou simulações de pagamento.
"""