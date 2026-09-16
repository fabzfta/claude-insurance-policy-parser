"""
Wrapper fino sobre o SDK oficial da Anthropic: envia o PDF, força o uso da
tool de extração, devolve o resultado já como dict Python.

Fica em arquivo separado de claude_tool_schema.py (schema) e do código que
vai persistir o resultado no banco (próximo bloco) -- cada arquivo com uma
responsabilidade só: "schema", "chamar a API", "salvar no banco".
"""
import base64
import os
import logging

import anthropic

logger = logging.getLogger(__name__)
_client = None

CAMPOS_OBRIGATORIOS_TOPO = ("cliente", "apolice", "veiculo", "coberturas")


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
    return _client


class ExtracaoSemToolUseError(Exception):
    pass


def _chamar_claude(client, model, pdf_b64, tool_schema, system_prompt, tool_name, max_tokens):
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64},
                },
                {"type": "text", "text": "Extraia os dados desta apólice usando a tool disponível."},
            ],
        }],
    )

    logger.info(
        "Claude extraction: model=%s stop_reason=%s input_tokens=%s output_tokens=%s",
        model, response.stop_reason, response.usage.input_tokens, response.usage.output_tokens,
    )

    if response.stop_reason == "max_tokens":
        raise ExtracaoSemToolUseError(
            f"Resposta cortada por limite de tokens (max_tokens={max_tokens}, "
            f"output_tokens usados={response.usage.output_tokens})."
        )

    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input

    raise ExtracaoSemToolUseError(
        f"Resposta sem tool_use '{tool_name}'. stop_reason={response.stop_reason}"
    )


def extrair_dados_do_pdf(pdf_bytes: bytes, tool_schema: dict, system_prompt: str,
                          tool_name: str, max_tokens: int = 16000, max_tentativas: int = 3) -> dict:
    client = _get_client()
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    ultimo_faltando = None

    for tentativa in range(1, max_tentativas + 1):
        dados = _chamar_claude(client, model, pdf_b64, tool_schema, system_prompt, tool_name, max_tokens)

        faltando = [c for c in CAMPOS_OBRIGATORIOS_TOPO if c not in dados]
        if not faltando:
            logger.info("Extração completa na tentativa %d/%d.", tentativa, max_tentativas)
            return dados

        ultimo_faltando = faltando
        logger.warning(
            "Tentativa %d/%d incompleta -- faltando %s. Chaves recebidas: %s. Tentando de novo.",
            tentativa, max_tentativas, faltando, list(dados.keys()),
        )

    raise ExtracaoSemToolUseError(
        f"Resposta incompleta após {max_tentativas} tentativas. "
        f"Campos ainda faltando na última tentativa: {ultimo_faltando}"
    )