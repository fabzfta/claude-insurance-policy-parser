from datetime import timedelta

from django.contrib import admin
from django.db import transaction
from django.utils import timezone

from .claude_client import ExtracaoSemToolUseError, extrair_dados_do_pdf
from .claude_extraction import processar_extracao
from .claude_tool_schema import EXTRAIR_APOLICE_TOOL, SYSTEM_PROMPT_EXTRACAO
from .models import (
    Apolice,
    AvaliacaoRisco,
    CoberturaApolice,
    CoberturaExtraApolice,
    CondutorPrincipal,
    DadosCalculoRenovacao,
    Segurado,
    Veiculo,
)


@admin.register(Segurado)
class SeguradoAdmin(admin.ModelAdmin):
    # CondutorPrincipalInline saiu daqui -- agora mora em ApoliceAdmin,
    # já que o condutor principal é por apólice/veículo, não por segurado
    # (ver docstring de CondutorPrincipal em models.py).
    list_display = ("nome_completo", "cpf_cnpj", "tipo_documento", "cidade", "uf")
    list_filter = ("tipo_documento", "eh_condutor_principal", "uf")
    search_fields = ("nome_completo", "cpf_cnpj")

    fieldsets = (
        ("Dados pessoais", {
            "fields": (
                "nome_completo", "tipo_documento", "cpf_cnpj",
                "data_nascimento", "profissao", "sexo", "estado_civil",
                "eh_condutor_principal",
            )
        }),
        ("Endereço", {
            "fields": ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")
        }),
    )


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ("placa", "marca", "modelo", "ano_modelo", "tipo_veiculo", "blindado")
    list_filter = ("tipo_veiculo", "combustivel", "blindado", "zero_km")
    search_fields = ("placa", "chassi", "marca", "modelo")


class CondutorPrincipalInline(admin.StackedInline):
    """Moved here from SeguradoAdmin: CondutorPrincipal is now a OneToOne
    with Apolice, not Segurado (a policyholder can have multiple policies,
    each potentially driven by a different person -- see models.py)."""

    model = CondutorPrincipal
    extra = 0


class CoberturaApoliceInline(admin.StackedInline):
    model = CoberturaApolice
    extra = 0
    fieldsets = (
        (None, {"fields": ("tipo_cobertura", "franquia_valor", "franquia_percentual")}),
        ("Assistência 24h", {
            "fields": ("assistencia_24h_contratada", "assistencia_24h_plano", "assistencia_24h_premio")
        }),
        ("Vidros", {
            "fields": (
                "vidros_contratado", "vidros_plano", "vidros_lmi",
                "vidros_premio", "vidros_franquias_detalhe",
            )
        }),
        ("Carro reserva", {
            "fields": (
                "carro_reserva_contratado", "carro_reserva_dias",
                "carro_reserva_tipo", "carro_reserva_premio",
            )
        }),
        ("RCF", {
            "fields": (
                "rcf_danos_materiais_lmi", "rcf_danos_materiais_premio",
                "rcf_danos_corporais_lmi", "rcf_danos_corporais_premio",
                "rcf_danos_morais_lmi", "rcf_danos_morais_premio",
            )
        }),
        ("APP", {"fields": ("app_contratado", "app_morte_lmi", "app_invalidez_lmi", "app_premio")}),
        ("Despesas extraordinárias", {
            "classes": ("collapse",),
            "fields": (
                "despesas_extraordinarias_contratada",
                "despesas_extraordinarias_lmi", "despesas_extraordinarias_premio",
            ),
        }),
        ("Despesas médico-hospitalares", {
            "classes": ("collapse",),
            "fields": (
                "despesas_medico_hospitalares_contratada",
                "despesas_medico_hospitalares_lmi", "despesas_medico_hospitalares_premio",
            ),
        }),
        ("Blindagem", {
            "classes": ("collapse",),
            "fields": ("blindagem_contratada", "blindagem_lmi", "blindagem_premio"),
        }),
    )


class AvaliacaoRiscoInline(admin.StackedInline):
    model = AvaliacaoRisco
    extra = 0
    readonly_fields = ("completo",)


class CoberturaExtraApoliceInline(admin.TabularInline):
    model = CoberturaExtraApolice
    extra = 1
    fields = ("descricao", "lmi", "franquia", "premio")


@admin.register(Apolice)
class ApoliceAdmin(admin.ModelAdmin):
    list_display = (
        "__str__", "segurado", "tipo_operacao", "status",
        "data_fim_vigencia", "dias_para_vencer", "premio_total",
    )
    list_filter = ("tipo_operacao", "status", "seguradora")
    search_fields = (
        "numero_apolice", "numero_proposta", "numero_cotacao",
        "segurado__nome_completo", "segurado__cpf_cnpj", "veiculo__placa",
        "condutor_principal__nome_completo", "condutor_principal__cpf",
    )
    date_hierarchy = "data_fim_vigencia"
    autocomplete_fields = ("segurado", "veiculo")
    readonly_fields = ("criado_em", "atualizado_em", "extraido_em")
    inlines = [
        CondutorPrincipalInline,
        CoberturaApoliceInline,
        AvaliacaoRiscoInline,
        CoberturaExtraApoliceInline,
    ]
    actions = ["marcar_como_vencendo"]

    fieldsets = (
        ("Operação", {"fields": ("tipo_operacao", "status")}),
        ("Identificação", {
            "fields": (
                "segurado", "veiculo", "numero_apolice", "numero_proposta",
                "numero_cotacao", "bonus", "ci", "seguradora", "corretora",
            )
        }),
        ("Vigência e prêmio", {
            "fields": ("data_inicio_vigencia", "data_fim_vigencia", "premio_total")
        }),
        ("Endereço de pernoite do veículo", {
            "fields": (
                "pernoite_cep", "pernoite_logradouro", "pernoite_numero",
                "pernoite_complemento", "pernoite_bairro", "pernoite_cidade", "pernoite_uf",
            )
        }),
        ("Arquivo (apenas renovação)", {
            "fields": ("pdf_file", "nome_arquivo_original", "erro_extracao_detalhe", "extraido_em"),
        }),
        ("Timestamps", {"fields": ("criado_em", "atualizado_em"), "classes": ("collapse",)}),
    )

    @admin.display(description="Dias p/ vencer")
    def dias_para_vencer(self, obj):
        if not obj.data_fim_vigencia:
            return "—"
        dias = (obj.data_fim_vigencia - timezone.now().date()).days
        if dias < 0:
            return f"Vencida há {abs(dias)} dias"
        return f"{dias} dias"

    @admin.action(description="Marcar selecionadas como 'Vencendo'")
    def marcar_como_vencendo(self, request, queryset):
        limite = timezone.now().date() + timedelta(days=45)
        atualizadas = queryset.filter(
            data_fim_vigencia__lte=limite, status=Apolice.Status.ATIVA
        ).update(status=Apolice.Status.VENCENDO)
        self.message_user(request, f"{atualizadas} apólice(s) marcada(s) como Vencendo.")

    def save_model(self, request, obj, form, change):
        eh_nova_renovacao_com_pdf = (
            not change
            and obj.tipo_operacao == Apolice.TipoOperacao.RENOVACAO
            and obj.pdf_file
        )
        super().save_model(request, obj, form, change)

        if not eh_nova_renovacao_com_pdf:
            return

        obj.status = Apolice.Status.EXTRAINDO
        obj.nome_arquivo_original = obj.pdf_file.name
        obj.save()

        with obj.pdf_file.open("rb") as arquivo:
            pdf_bytes = arquivo.read()

        try:
            dados = extrair_dados_do_pdf(
                pdf_bytes=pdf_bytes,
                tool_schema=EXTRAIR_APOLICE_TOOL,
                system_prompt=SYSTEM_PROMPT_EXTRACAO,
                tool_name="extrair_dados_apolice",
            )
            with transaction.atomic():
                processar_extracao(obj, dados)
            self.message_user(request, "PDF extraído com sucesso.")
        except (ExtracaoSemToolUseError, Exception) as exc:
            obj.status = Apolice.Status.ERRO_EXTRACAO
            obj.erro_extracao_detalhe = str(exc)[:2000]
            obj.save()
            self.message_user(request, f"Falha na extração: {exc}", level="error")


@admin.register(DadosCalculoRenovacao)
class DadosCalculoRenovacaoAdmin(admin.ModelAdmin):
    list_display = ("apolice_origem", "status", "gerado_em")
    list_filter = ("status",)
    readonly_fields = ("apolice_origem", "payload_calculo", "status", "gerado_em")

    def has_add_permission(self, request):
        return False