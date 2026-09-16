from django.shortcuts import render, redirect

from .claude_client import ExtracaoSemToolUseError, extrair_dados_do_pdf
from .claude_extraction import processar_extracao
from .claude_tool_schema import EXTRAIR_APOLICE_TOOL, SYSTEM_PROMPT_EXTRACAO

from .forms import (
    CondutorPrincipalNovoForm,
    PernoiteVeiculoNovoForm,
    SeguradoNovoForm,
    VeiculoNovoForm
)
from .models import Apolice

# Create your views here.


def escolher_tipo_operacao(request):
    """Landing page -- the very first decision point of the whole workflow.

    Pure navigation, no form and no model interaction here: just two links
    to the two paths (NOVO vs RENOVACAO), each handled by its own view
    further down this file.
    """
    return render(request, "apolice/escolher_tipo_operacao.html")


def upload_renovacao(request):
    """Creates the Apolice record for a RENOVACAO request and stores the
    uploaded PDF. Does NOT run the Claude extraction yet -- that's a
    separate future step. For now, status stays EXTRAINDO as a placeholder
    signal that "there's a PDF here, waiting to be processed"."""

    if request.method == "POST":
        form = UploadRenovacaoForm(request.POST, request.FILES)
        if form.is_valid():
            apolice = form.save(commit=False)
            apolice.tipo_operacao = Apolice.TipoOperacao.RENOVACAO
            apolice.status = Apolice.Status.EXTRAINDO
            apolice.nome_arquivo_original = apolice.pdf_file.name
            apolice.save()
            return redirect("admin:apolice_apolice_change", apolice.id)
    else:
        form = UploadRenovacaoForm()

    return render(request, "apolice/upload_renovacao.html", {"form": form})

def upload_novo(request):
    """Creates Segurado (+ address), optionally CondutorPrincipal, Veiculo,
    and Apolice (+ pernoite address) all from one intake form -- used for
    tipo_operacao == NOVO, where there's no PDF to extract any of this
    from.
    """
    if request.method == "POST":
        segurado_form = SeguradoNovoForm(request.POST)
        veiculo_form = VeiculoNovoForm(request.POST)
        pernoite_form = PernoiteVeiculoNovoForm(request.POST)
        condutor_form = CondutorPrincipalNovoForm(request.POST)

        # HTML checkboxes are only present in POST data when checked, so
        # the key being absent means "não, não sou o condutor principal" --
        # the one case where CondutorPrincipal is actually required.
        precisa_condutor = "eh_condutor_principal" not in request.POST
        condutor_form.fields["nome_completo"].required = precisa_condutor
        condutor_form.fields["cpf"].required = precisa_condutor

        if (
            segurado_form.is_valid()
            and veiculo_form.is_valid()
            and pernoite_form.is_valid()
            and condutor_form.is_valid()
        ):
            segurado = segurado_form.save()

            if precisa_condutor:
                condutor = condutor_form.save(commit=False)
                condutor.segurado = segurado
                condutor.save()

            veiculo = veiculo_form.save()

            apolice = pernoite_form.save(commit=False)
            apolice.tipo_operacao = Apolice.TipoOperacao.NOVO
            apolice.status = Apolice.Status.DADOS_INCOMPLETOS
            apolice.segurado = segurado
            apolice.veiculo = veiculo
            apolice.save()

            return redirect("admin:apolice_apolice_change", apolice.id)
    else:
        segurado_form = SeguradoNovoForm()
        veiculo_form = VeiculoNovoForm()
        pernoite_form = PernoiteVeiculoNovoForm()
        condutor_form = CondutorPrincipalNovoForm()
        condutor_form.fields["nome_completo"].required = False
        condutor_form.fields["cpf"].required = False

    return render(request, "apolice/upload_novo.html", {
        "segurado_form": segurado_form,
        "veiculo_form": veiculo_form,
        "condutor_form": condutor_form,
        "pernoite_form": pernoite_form,
    })

