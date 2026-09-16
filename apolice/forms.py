from django import forms

from .models import Apolice, Segurado, Veiculo, CondutorPrincipal



class SeguradoNovoForm(forms.ModelForm):
    """Covers Segurado's personal data + the address fields it inherits
    from EnderecoMixin. Used only in the NOVO flow -- RENOVACAO never shows
    this form, since that data comes from PDF extraction instead."""

    class Meta:
        model = Segurado
        fields = [
            "nome_completo", "tipo_documento", "cpf_cnpj",
            "data_nascimento", "profissao", "sexo", "estado_civil",
            "eh_condutor_principal",
            "cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf",
        ]

class VeiculoNovoForm(forms.ModelForm):
    """Straightforward -- Veiculo has no nested structure like Segurado's
    address, so this is a plain field-for-field mirror of the model."""

    class Meta:
        model = Veiculo
        fields = [
            "placa", "chassi", "marca", "modelo", "zero_km",
            "ano_fabricacao", "ano_modelo", "tipo_veiculo", "combustivel", "blindado",
        ]

class CondutorPrincipalNovoForm(forms.ModelForm):
    """Only used when the policyholder answers 'não' to 'você é o condutor
    principal?' on the Segurado form. The view decides whether to even
    instantiate/validate this form based on that answer -- see next step."""

    class Meta:
        model = CondutorPrincipal
        fields = ["nome_completo", "cpf", "profissao", "sexo", "estado_civil"]


class PernoiteVeiculoNovoForm(forms.ModelForm):
    """Covers only the pernoite_* fields on Apolice -- NOT the whole model
    (Apolice has ~25 other fields that either get set programmatically by
    the view, like tipo_operacao/status, or don't apply to NOVO at all,
    like the PDF-related ones)."""

    class Meta:
        model = Apolice
        fields = [
            "pernoite_cep", "pernoite_logradouro", "pernoite_numero",
            "pernoite_complemento", "pernoite_bairro", "pernoite_cidade", "pernoite_uf",
        ]
        labels = {
            "pernoite_cep": "CEP",
            "pernoite_logradouro": "Logradouro",
            "pernoite_numero": "Número",
            "pernoite_complemento": "Complemento",
            "pernoite_bairro": "Bairro",
            "pernoite_cidade": "Cidade",
            "pernoite_uf": "UF",
        }