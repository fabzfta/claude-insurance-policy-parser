"""
Domain models for the insurance-policy renewal management system.
"""

import uuid

from django.db import models


class EnderecoMixin(models.Model):
    """Reusable set of Brazilian address fields. Abstract: each concrete
    model that inherits this gets its OWN database columns."""

    cep = models.CharField("CEP", max_length=9, null=True, blank=True)
    logradouro = models.CharField("Logradouro", max_length=255, null=True, blank=True)
    numero = models.CharField("Número", max_length=20, null=True, blank=True)
    complemento = models.CharField("Complemento", max_length=100, null=True, blank=True)
    bairro = models.CharField("Bairro", max_length=100, null=True, blank=True)
    cidade = models.CharField("Cidade", max_length=100, null=True, blank=True)
    uf = models.CharField("UF", max_length=2, null=True, blank=True)

    class Meta:
        abstract = True


class Segurado(EnderecoMixin, models.Model):
    """The policyholder — the person or company the insurance is issued to."""

    class TipoDocumento(models.TextChoices):
        CPF = "CPF", "CPF"
        CNPJ = "CNPJ", "CNPJ"

    class Sexo(models.TextChoices):
        M = "M", "Masculino"
        F = "F", "Feminino"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome_completo = models.CharField("Nome completo", max_length=255)
    tipo_documento = models.CharField(
        "Tipo de documento", max_length=4, choices=TipoDocumento.choices
    )
    cpf_cnpj = models.CharField("CPF/CNPJ", max_length=18, unique=True)

    data_nascimento = models.DateField("Data de nascimento", null=True, blank=True)
    profissao = models.CharField("Profissão", max_length=255, null=True, blank=True)
    sexo = models.CharField("Sexo", max_length=1, choices=Sexo.choices, null=True, blank=True)
    estado_civil = models.CharField("Estado civil", max_length=50, null=True, blank=True)

    # NOTE: no longer tied to CondutorPrincipal (see that model, now
    # attached to Apolice instead) -- this flag is still meaningful as "is
    # this policyholder, as a person, generally the one driving", but the
    # actual per-policy driver record lives on Apolice now.
    eh_condutor_principal = models.BooleanField("É o condutor principal?", default=True)

    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Segurado"
        verbose_name_plural = "Segurados"

    def __str__(self):
        return f"{self.nome_completo} ({self.cpf_cnpj})"


class Veiculo(models.Model):
    """The insured vehicle — physical/fixed attributes only."""

    class TipoVeiculo(models.TextChoices):
        PARTICULAR = "particular", "Particular"
        COMERCIAL = "comercial", "Comercial"

    class Combustivel(models.TextChoices):
        ALCOOL = "alcool", "Álcool"
        DIESEL = "diesel", "Diesel"
        ELETRICO = "eletrico", "Elétrico"
        FLEX = "flex", "Flex"
        HIBRIDO = "hibrido", "Híbrido"
        GASOLINA = "gasolina", "Gasolina"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    placa = models.CharField("Placa", max_length=10, unique=True)
    chassi = models.CharField("Chassi", max_length=20, unique=True)
    marca = models.CharField("Marca", max_length=100, null=True, blank=True)
    modelo = models.CharField("Modelo", max_length=255, null=True, blank=True)
    zero_km = models.BooleanField("Zero KM?", default=False)
    ano_fabricacao = models.IntegerField("Ano de fabricação", null=True, blank=True)
    ano_modelo = models.IntegerField("Ano do modelo", null=True, blank=True)
    tipo_veiculo = models.CharField(
        "Tipo de veículo", max_length=10, choices=TipoVeiculo.choices, null=True, blank=True
    )
    combustivel = models.CharField(
        "Combustível", max_length=10, choices=Combustivel.choices, null=True, blank=True
    )
    blindado = models.BooleanField("Blindado?", default=False)

    class Meta:
        verbose_name = "Veículo"
        verbose_name_plural = "Veículos"

    def __str__(self):
        marca_modelo = f"{self.marca or ''} {self.modelo or ''}".strip()
        return f"{marca_modelo} - {self.placa}" if marca_modelo else self.placa


class Apolice(models.Model):
    """The insurance policy/quote request — the central entity of this system."""

    class TipoOperacao(models.TextChoices):
        NOVO = "novo", "Seguro novo"
        RENOVACAO = "renovacao", "Renovação"

    class Status(models.TextChoices):
        EXTRAINDO = "extraindo", "Extraindo dados do PDF"
        ERRO_EXTRACAO = "erro_extracao", "Erro na extração do PDF"
        COLETANDO_DADOS = "coletando_dados", "Coletando dados do segurado/veículo"
        DADOS_INCOMPLETOS = "dados_incompletos", "Avaliação de risco incompleta"
        ATIVA = "ativa", "Ativa"
        VENCENDO = "vencendo", "Vencendo"
        VENCIDA = "vencida", "Vencida"
        RENOVADA = "renovada", "Renovada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo_operacao = models.CharField(
        "Tipo de operação", max_length=10, choices=TipoOperacao.choices
    )
    status = models.CharField(
        "Status", max_length=20, choices=Status.choices, default=Status.COLETANDO_DADOS
    )

    segurado = models.ForeignKey(
        Segurado, on_delete=models.CASCADE, related_name="apolices", null=True, blank=True
    )
    veiculo = models.ForeignKey(
        Veiculo, on_delete=models.CASCADE, related_name="apolices", null=True, blank=True
    )

    numero_apolice = models.CharField("Número da apólice", max_length=100, null=True, blank=True)
    numero_proposta = models.CharField("Número da proposta", max_length=100, null=True, blank=True)
    numero_cotacao = models.CharField("Número da cotação", max_length=100, null=True, blank=True)
    bonus = models.IntegerField("Classe de bônus", null=True, blank=True)
    ci = models.CharField("Código CI", max_length=50, null=True, blank=True)
    seguradora = models.CharField("Seguradora", max_length=255, null=True, blank=True)
    corretora = models.CharField("Corretora", max_length=255, null=True, blank=True)

    data_inicio_vigencia = models.DateField("Início de vigência", null=True, blank=True)
    data_fim_vigencia = models.DateField("Fim de vigência", null=True, blank=True, db_index=True)

    premio_total = models.DecimalField(
        "Prêmio total", max_digits=10, decimal_places=2, null=True, blank=True
    )

    pernoite_cep = models.CharField("CEP de pernoite", max_length=9, null=True, blank=True)
    pernoite_logradouro = models.CharField(
        "Logradouro de pernoite", max_length=255, null=True, blank=True
    )
    pernoite_numero = models.CharField("Número de pernoite", max_length=20, null=True, blank=True)
    pernoite_complemento = models.CharField(
        "Complemento de pernoite", max_length=100, null=True, blank=True
    )
    pernoite_bairro = models.CharField("Bairro de pernoite", max_length=100, null=True, blank=True)
    pernoite_cidade = models.CharField("Cidade de pernoite", max_length=100, null=True, blank=True)
    pernoite_uf = models.CharField("UF de pernoite", max_length=2, null=True, blank=True)

    pdf_file = models.FileField("Arquivo PDF", upload_to="apolices/%Y/%m/", null=True, blank=True)
    nome_arquivo_original = models.CharField(
        "Nome do arquivo original", max_length=255, null=True, blank=True
    )
    erro_extracao_detalhe = models.TextField("Detalhe do erro de extração", null=True, blank=True)
    extraido_em = models.DateTimeField("Extraído em", null=True, blank=True)

    criado_em = models.DateTimeField("Criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Apólice"
        verbose_name_plural = "Apólices"
        ordering = ["data_fim_vigencia"]

    def __str__(self):
        referencia = self.numero_apolice or self.numero_cotacao or str(self.id)[:8]
        return f"{referencia} - {self.seguradora or self.get_tipo_operacao_display()}"


class CondutorPrincipal(models.Model):
    """The vehicle's main driver for a SPECIFIC policy, when different from
    the policyholder.

    Tied to Apolice (not Segurado): a policyholder can have multiple
    policies -- e.g. a company insuring a fleet of vehicles -- each
    potentially driven by a different person. Tying this to Segurado would
    force a single "main driver" across every policy that segurado ever
    has, which breaks for exactly that fleet scenario (confirmed by a real
    case: COMABEM SUPERMERCADOS LTDA, a company, with a named employee as
    the actual driver of one specific insured vehicle).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    apolice = models.OneToOneField(
        Apolice, on_delete=models.CASCADE, related_name="condutor_principal"
    )
    nome_completo = models.CharField("Nome completo", max_length=255)
    cpf = models.CharField("CPF", max_length=14)
    profissao = models.CharField("Profissão", max_length=255, null=True, blank=True)
    sexo = models.CharField(
        "Sexo", max_length=1, choices=Segurado.Sexo.choices, null=True, blank=True
    )
    estado_civil = models.CharField("Estado civil", max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = "Condutor Principal"
        verbose_name_plural = "Condutores Principais"

    def __str__(self):
        return self.nome_completo


class CoberturaApolice(models.Model):
    """The policy's coverage details — one-to-one with Apolice."""

    class TipoCobertura(models.TextChoices):
        COMPREENSIVA = "compreensiva", "Compreensiva"
        RCF = "rcf", "RCF (Responsabilidade Civil Facultativa)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    apolice = models.OneToOneField(Apolice, on_delete=models.CASCADE, related_name="cobertura")

    tipo_cobertura = models.CharField(
        "Tipo de cobertura", max_length=15, choices=TipoCobertura.choices
    )

    franquia_valor = models.DecimalField(
        "Franquia (valor)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    franquia_percentual = models.DecimalField(
        "Franquia (%)", max_digits=5, decimal_places=2, null=True, blank=True
    )

    assistencia_24h_contratada = models.BooleanField("Assistência 24h contratada?", default=False)
    assistencia_24h_plano = models.CharField(
        "Plano de assistência 24h", max_length=100, null=True, blank=True
    )
    assistencia_24h_premio = models.DecimalField(
        "Prêmio da assistência 24h", max_digits=10, decimal_places=2, null=True, blank=True
    )

    vidros_contratado = models.BooleanField("Cobertura de vidros contratada?", default=False)
    vidros_plano = models.CharField("Plano de vidros", max_length=100, null=True, blank=True)
    vidros_lmi = models.DecimalField(
        "LMI de vidros", max_digits=12, decimal_places=2, null=True, blank=True
    )
    vidros_premio = models.DecimalField(
        "Prêmio de vidros", max_digits=10, decimal_places=2, null=True, blank=True
    )
    vidros_franquias_detalhe = models.JSONField(
        "Franquias de vidros (detalhe)", null=True, blank=True
    )

    carro_reserva_contratado = models.BooleanField("Carro reserva contratado?", default=False)
    carro_reserva_dias = models.IntegerField("Dias de carro reserva", null=True, blank=True)
    carro_reserva_tipo = models.CharField(
        "Tipo de carro reserva", max_length=50, null=True, blank=True
    )
    carro_reserva_premio = models.DecimalField(
        "Prêmio de carro reserva", max_digits=10, decimal_places=2, null=True, blank=True
    )

    rcf_danos_materiais_lmi = models.DecimalField(
        "RCF danos materiais (LMI)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    rcf_danos_materiais_premio = models.DecimalField(
        "RCF danos materiais (prêmio)", max_digits=10, decimal_places=2, null=True, blank=True
    )
    rcf_danos_corporais_lmi = models.DecimalField(
        "RCF danos corporais (LMI)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    rcf_danos_corporais_premio = models.DecimalField(
        "RCF danos corporais (prêmio)", max_digits=10, decimal_places=2, null=True, blank=True
    )
    rcf_danos_morais_lmi = models.DecimalField(
        "RCF danos morais (LMI)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    rcf_danos_morais_premio = models.DecimalField(
        "RCF danos morais (prêmio)", max_digits=10, decimal_places=2, null=True, blank=True
    )

    app_contratado = models.BooleanField("APP contratado?", default=False)
    app_morte_lmi = models.DecimalField(
        "APP morte (LMI)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    app_invalidez_lmi = models.DecimalField(
        "APP invalidez (LMI)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    app_premio = models.DecimalField(
        "Prêmio do APP", max_digits=10, decimal_places=2, null=True, blank=True
    )

    despesas_extraordinarias_contratada = models.BooleanField(
        "Despesas extraordinárias contratadas?", default=False
    )
    despesas_extraordinarias_lmi = models.DecimalField(
        "Despesas extraordinárias (LMI)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    despesas_extraordinarias_premio = models.DecimalField(
        "Despesas extraordinárias (prêmio)", max_digits=10, decimal_places=2, null=True, blank=True
    )

    despesas_medico_hospitalares_contratada = models.BooleanField(
        "Despesas médico-hospitalares contratadas?", default=False
    )
    despesas_medico_hospitalares_lmi = models.DecimalField(
        "Despesas médico-hospitalares (LMI)",
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    despesas_medico_hospitalares_premio = models.DecimalField(
        "Despesas médico-hospitalares (prêmio)",
        max_digits=10, decimal_places=2, null=True, blank=True,
    )

    blindagem_contratada = models.BooleanField("Blindagem contratada?", default=False)
    blindagem_lmi = models.DecimalField(
        "Blindagem (LMI)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    blindagem_premio = models.DecimalField(
        "Blindagem (prêmio)", max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = "Cobertura"
        verbose_name_plural = "Coberturas"

    def __str__(self):
        return f"Cobertura de {self.apolice}"


class CoberturaExtraApolice(models.Model):
    """Generic fallback for any coverage/service line item that doesn't
    map to one of CoberturaApolice's fixed fields."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    apolice = models.ForeignKey(
        Apolice, on_delete=models.CASCADE, related_name="coberturas_extra"
    )
    descricao = models.CharField("Descrição", max_length=255)
    lmi = models.DecimalField("LMI", max_digits=12, decimal_places=2, null=True, blank=True)
    franquia = models.DecimalField(
        "Franquia", max_digits=12, decimal_places=2, null=True, blank=True
    )
    premio = models.DecimalField("Prêmio", max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "Cobertura Extra"
        verbose_name_plural = "Coberturas Extras"

    def __str__(self):
        return self.descricao


class AvaliacaoRisco(models.Model):
    """The risk-assessment questionnaire data — one-to-one with Apolice."""

    class Garagem(models.TextChoices):
        COM_PORTAO = "com_portao_eletronico", "Sim, com portão eletrônico"
        SEM_PORTAO = "sem_portao_eletronico", "Sim, sem portão eletrônico"
        NAO_POSSUI = "nao_possui", "Não possui"
        NAO_DEIXA = "nao_deixa_garagem", "Não deixa na garagem"

    class TipoUso(models.TextChoices):
        LOCOMOCAO_DIARIA = "locomocao_diaria", "Locomoção diária"
        USO_COMERCIAL = "uso_comercial", "Uso comercial"
        AMBOS = "locomocao_diaria_e_uso_comercial", "Locomoção diária e uso comercial"

    class ResideMenores(models.TextChoices):
        NAO_RESIDE = "nao_reside", "Não reside"
        SIM_MASCULINO = "sim_masculino", "Sim, masculino"
        SIM_FEMININO = "sim_feminino", "Sim, feminino"
        SIM_AMBOS = "sim_ambos", "Sim, ambos"
        SIM_MAS_NAO_UTILIZAM = "sim_mas_nao_utilizam", "Sim, mas não utilizam"

    class FaixaIdade(models.TextChoices):
        DE_18_A_24 = "18_a_24", "De 18 a 24 anos"
        MAIOR_24 = "maior_24", "Maior de 24 anos"

    CAMPOS_OBRIGATORIOS = (
        "garagem_residencia",
        "garagem_trabalho",
        "garagem_estudo",
        "tipo_uso",
        "reside_com_menores_26",
        "faixa_idade_condutor",
        "km_mensal",
        "distancia_trabalho_km",
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    apolice = models.OneToOneField(
        Apolice, on_delete=models.CASCADE, related_name="avaliacao_risco"
    )

    garagem_residencia = models.CharField(
        "Garagem na residência", max_length=25, choices=Garagem.choices, null=True, blank=True
    )
    garagem_trabalho = models.CharField(
        "Garagem no trabalho", max_length=25, choices=Garagem.choices, null=True, blank=True
    )
    garagem_estudo = models.CharField(
        "Garagem no estudo", max_length=25, choices=Garagem.choices, null=True, blank=True
    )
    tipo_uso = models.CharField(
        "Tipo de uso", max_length=35, choices=TipoUso.choices, null=True, blank=True
    )
    reside_com_menores_26 = models.CharField(
        "Reside com menores de 26 anos",
        max_length=25, choices=ResideMenores.choices, null=True, blank=True,
    )
    faixa_idade_condutor = models.CharField(
        "Faixa de idade do condutor",
        max_length=10, choices=FaixaIdade.choices, null=True, blank=True,
    )
    km_mensal = models.IntegerField("KM mensal", null=True, blank=True)
    distancia_trabalho_km = models.DecimalField(
        "Distância do trabalho (km)", max_digits=6, decimal_places=1, null=True, blank=True
    )

    completo = models.BooleanField("Avaliação completa?", default=False)

    class Meta:
        verbose_name = "Avaliação de Risco"
        verbose_name_plural = "Avaliações de Risco"

    def atualizar_completude(self) -> bool:
        completo = all(
            getattr(self, campo) is not None for campo in self.CAMPOS_OBRIGATORIOS
        )
        if completo != self.completo:
            self.completo = completo
            self.save(update_fields=["completo"])
        return completo

    def __str__(self):
        return f"Avaliação de risco de {self.apolice}"


class DadosCalculoRenovacao(models.Model):
    """Renewal-calculation payload, ready to eventually be sent to the
    Segfy quoting API."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    apolice_origem = models.ForeignKey(
        Apolice, on_delete=models.CASCADE, related_name="calculos_renovacao"
    )
    payload_calculo = models.JSONField("Payload de cálculo")
    status = models.CharField("Status", max_length=30, default="pronto_para_cotar")
    gerado_em = models.DateTimeField("Gerado em", auto_now_add=True)

    class Meta:
        verbose_name = "Dados de Cálculo de Renovação"
        verbose_name_plural = "Dados de Cálculo de Renovação"

    def __str__(self):
        return f"Cálculo de {self.apolice_origem} em {self.gerado_em:%d/%m/%Y}"