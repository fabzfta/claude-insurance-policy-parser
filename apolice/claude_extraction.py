"""
Aplica o dict retornado por claude_client.extrair_dados_do_pdf() nos models
de verdade.
"""
from django.utils import timezone

from .models import (
    Apolice,
    AvaliacaoRisco,
    CoberturaApolice,
    CoberturaExtraApolice,
    CondutorPrincipal,
    Segurado,
    Veiculo,
)

CAMPOS_ENDERECO = ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")


def _aplicar_endereco(obj, endereco: dict | None, prefixo: str = ""):
    endereco = endereco or {}
    for campo in CAMPOS_ENDERECO:
        valor = endereco.get(campo)
        if valor is None:
            continue
        max_length = obj._meta.get_field(f"{prefixo}{campo}").max_length
        if max_length and len(valor) > max_length:
            continue
        setattr(obj, f"{prefixo}{campo}", valor)


def _upsert_segurado(dados_cliente: dict) -> Segurado:
    segurado, _ = Segurado.objects.get_or_create(
        cpf_cnpj=dados_cliente["cpf_cnpj"],
        defaults={
            "nome_completo": dados_cliente["nome_completo"],
            "tipo_documento": dados_cliente["tipo_documento"],
        },
    )
    segurado.nome_completo = dados_cliente["nome_completo"]
    segurado.tipo_documento = dados_cliente["tipo_documento"]
    segurado.data_nascimento = dados_cliente.get("data_nascimento") or None
    segurado.profissao = dados_cliente.get("profissao")
    segurado.sexo = dados_cliente.get("sexo")
    segurado.estado_civil = dados_cliente.get("estado_civil")
    segurado.eh_condutor_principal = dados_cliente["eh_condutor_principal"]
    _aplicar_endereco(segurado, dados_cliente.get("endereco"))
    segurado.save()
    return segurado


def _upsert_condutor_principal(apolice: Apolice, dados_cliente: dict):
    """CondutorPrincipal agora é por Apolice, não por Segurado -- essa
    função roda depois que `apolice` já existe e está salva, diferente da
    versão anterior (que criava o condutor dentro de _upsert_segurado)."""
    eh_condutor_principal = dados_cliente["eh_condutor_principal"]
    cp_dados = dados_cliente.get("condutor_principal")

    if eh_condutor_principal or not cp_dados or not (cp_dados.get("nome_completo") and cp_dados.get("cpf")):
        # Sem condutor separado necessário (ou dado incompleto demais pra
        # confiar) -- limpa qualquer CondutorPrincipal de um reprocessamento
        # anterior, pra não deixar dado desatualizado/inconsistente parado.
        CondutorPrincipal.objects.filter(apolice=apolice).delete()
        return

    condutor, _ = CondutorPrincipal.objects.get_or_create(
        apolice=apolice,
        defaults={"nome_completo": cp_dados["nome_completo"], "cpf": cp_dados["cpf"]},
    )
    condutor.nome_completo = cp_dados["nome_completo"]
    condutor.cpf = cp_dados["cpf"]
    condutor.profissao = cp_dados.get("profissao")
    condutor.sexo = cp_dados.get("sexo")
    condutor.estado_civil = cp_dados.get("estado_civil")
    condutor.save()


def _upsert_veiculo(dados_veiculo: dict) -> Veiculo:
    veiculo, _ = Veiculo.objects.get_or_create(
        placa=dados_veiculo["placa"], defaults={"chassi": dados_veiculo["chassi"]}
    )
    veiculo.chassi = dados_veiculo["chassi"]
    veiculo.marca = dados_veiculo.get("marca")
    veiculo.modelo = dados_veiculo.get("modelo")
    veiculo.zero_km = dados_veiculo.get("zero_km", False)
    veiculo.ano_fabricacao = dados_veiculo.get("ano_fabricacao")
    veiculo.ano_modelo = dados_veiculo.get("ano_modelo")
    veiculo.tipo_veiculo = dados_veiculo.get("tipo_veiculo")
    veiculo.combustivel = dados_veiculo.get("combustivel")
    veiculo.blindado = dados_veiculo.get("blindado", False)
    veiculo.save()
    return veiculo


def _aplicar_cobertura(apolice: Apolice, dados_cob: dict):
    cobertura, _ = CoberturaApolice.objects.get_or_create(
        apolice=apolice, defaults={"tipo_cobertura": dados_cob["tipo_cobertura"]}
    )
    campos = [
        "tipo_cobertura", "franquia_valor", "franquia_percentual",
        "assistencia_24h_contratada", "assistencia_24h_plano", "assistencia_24h_premio",
        "vidros_contratado", "vidros_plano", "vidros_lmi", "vidros_premio",
        "vidros_franquias_detalhe",
        "carro_reserva_contratado", "carro_reserva_dias", "carro_reserva_tipo",
        "carro_reserva_premio",
        "rcf_danos_materiais_lmi", "rcf_danos_materiais_premio",
        "rcf_danos_corporais_lmi", "rcf_danos_corporais_premio",
        "rcf_danos_morais_lmi", "rcf_danos_morais_premio",
        "app_contratado", "app_morte_lmi", "app_invalidez_lmi", "app_premio",
        "despesas_extraordinarias_contratada", "despesas_extraordinarias_lmi",
        "despesas_extraordinarias_premio",
        "despesas_medico_hospitalares_contratada", "despesas_medico_hospitalares_lmi",
        "despesas_medico_hospitalares_premio",
        "blindagem_contratada", "blindagem_lmi", "blindagem_premio",
    ]
    for campo in campos:
        if campo in dados_cob:
            setattr(cobertura, campo, dados_cob[campo])
    cobertura.save()


def _aplicar_coberturas_extra(apolice: Apolice, lista_extra: list):
    apolice.coberturas_extra.all().delete()
    for item in lista_extra or []:
        CoberturaExtraApolice.objects.create(
            apolice=apolice,
            descricao=item["descricao"],
            lmi=item.get("lmi"),
            franquia=item.get("franquia"),
            premio=item.get("premio"),
        )


def processar_extracao(apolice: Apolice, dados: dict) -> None:
    campos_obrigatorios = ("cliente", "apolice", "veiculo", "coberturas")
    faltando = [campo for campo in campos_obrigatorios if campo not in dados]
    if faltando:
        raise ValueError(
            f"Resposta do Claude sem os campos obrigatórios {faltando}. "
            f"Campos presentes: {list(dados.keys())}"
        )

    segurado = _upsert_segurado(dados["cliente"])
    veiculo = _upsert_veiculo(dados["veiculo"])

    dados_apolice = dados["apolice"]
    apolice.segurado = segurado
    apolice.veiculo = veiculo
    apolice.numero_apolice = dados_apolice.get("numero_apolice")
    apolice.numero_proposta = dados_apolice.get("numero_proposta")
    apolice.numero_cotacao = dados_apolice.get("numero_cotacao")
    apolice.bonus = dados_apolice.get("bonus")
    apolice.ci = dados_apolice.get("ci")
    apolice.seguradora = dados_apolice["seguradora"]
    apolice.corretora = dados_apolice.get("corretora")
    apolice.data_inicio_vigencia = dados_apolice["data_inicio_vigencia"]
    apolice.data_fim_vigencia = dados_apolice["data_fim_vigencia"]
    apolice.premio_total = dados_apolice.get("premio_total")
    _aplicar_endereco(apolice, dados_apolice.get("pernoite"), prefixo="pernoite_")

    apolice.extraido_em = timezone.now()
    apolice.status = Apolice.Status.DADOS_INCOMPLETOS
    apolice.save()

    # Precisa rodar DEPOIS do apolice.save() acima -- get_or_create do
    # condutor exige que `apolice` já tenha uma PK persistida no banco.
    _upsert_condutor_principal(apolice, dados["cliente"])

    _aplicar_cobertura(apolice, dados["coberturas"])
    _aplicar_coberturas_extra(apolice, dados.get("coberturas_extra"))

    AvaliacaoRisco.objects.get_or_create(apolice=apolice)