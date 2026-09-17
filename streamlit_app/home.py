"""
Single-file Streamlit front-end: landing cards + renewal upload/processing,
all on one page. The renewal uploader and its result metrics are rendered
full-width, OUTSIDE the two-column card row -- nesting metric columns
inside a half-width column is what caused the overlapping layout.
"""
import math
from datetime import date, timedelta

import django_setup  # noqa: F401 -- import side effect only, must run first

import streamlit as st
from django.core.files.base import ContentFile
from django.db import transaction

from apolice.claude_client import ExtracaoSemToolUseError, extrair_dados_do_pdf
from apolice.claude_extraction import processar_extracao
from apolice.claude_tool_schema import EXTRAIR_APOLICE_TOOL, SYSTEM_PROMPT_EXTRACAO
from apolice.models import Apolice

st.set_page_config(page_title="Policy System", page_icon="📋")

st.title("📋 Policy System")
st.write("Choose what you need to do.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔄 Renewal")
    st.write("Upload the current policy's PDF below and let AI extract the data.")

with col2:
    st.subheader("🆕 New Policy")
    st.write("No prior policy — coming in the next step.")
    st.button("Go to New Policy", disabled=True)

st.divider()

st.subheader("Process an Insurance Policy")

uploaded_file = st.file_uploader("Policy PDF", type="pdf")

if uploaded_file and st.button("Process an Insurance Policy", type="primary"):
    pdf_bytes = uploaded_file.getvalue()

    policy = Apolice(
        tipo_operacao=Apolice.TipoOperacao.RENOVACAO,
        status=Apolice.Status.EXTRAINDO,
        nome_arquivo_original=uploaded_file.name,
    )
    policy.pdf_file.save(uploaded_file.name, ContentFile(pdf_bytes), save=False)
    policy.save()

    with st.spinner("Extracting policy data via AI... this takes a few seconds."):
        try:
            extracted_data = extrair_dados_do_pdf(
                pdf_bytes=pdf_bytes,
                tool_schema=EXTRAIR_APOLICE_TOOL,
                system_prompt=SYSTEM_PROMPT_EXTRACAO,
                tool_name="extrair_dados_apolice",
            )
            with transaction.atomic():
                processar_extracao(policy, extracted_data)
            success = True
        except (ExtracaoSemToolUseError, Exception) as exc:
            policy.status = Apolice.Status.ERRO_EXTRACAO
            policy.erro_extracao_detalhe = str(exc)[:2000]
            policy.save()
            success = False

    if success:
        policy.refresh_from_db()
        st.success("Policy processed successfully!")

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Policyholder", policy.segurado.nome_completo if policy.segurado else "—")
        col_b.metric("Insurer", policy.seguradora or "—")
        col_c.metric("Total premium", f"R$ {policy.premio_total or 0:,.2f}")

        col_d, col_e = st.columns(2)
        col_d.metric("Vehicle plate", policy.veiculo.placa if policy.veiculo else "—")
        col_e.metric(
            "Coverage period",
            f"{policy.data_inicio_vigencia:%d/%m/%Y} to {policy.data_fim_vigencia:%d/%m/%Y}"
            if policy.data_fim_vigencia
            else "—",
        )

        if policy.status == Apolice.Status.DADOS_INCOMPLETOS:
            st.info(
                "This policy's risk assessment is still incomplete. "
                "Complete it in the Django Admin before calculating the renewal."
            )
    else:
        st.error(f"Extraction failed: {policy.erro_extracao_detalhe}")
        st.write("You can retry with the same file or check whether the PDF is readable.")

st.divider()

total_policies = Apolice.objects.count()


today = date.today()
in_30_days = today + timedelta(days=30)

expiring_soon = Apolice.objects.filter(
    data_fim_vigencia__gte=today, data_fim_vigencia__lte=in_30_days
).count()

metric_col1, metric_col2 = st.columns(2)
metric_col1.metric("Policies in the system", total_policies)
metric_col2.metric("Expiring in the next 30 days", expiring_soon)

# --- Registered policies list: filterable by expiration date range,
# sorted by expiration date (newest first), paginated 10 per page. ---
st.subheader("Registered policies")

date_range = st.date_input(
    "Filter by expiration date range",
    value=(),
    key="policies_date_filter",
)

# st.date_input with a tuple value returns a partial tuple while the user
# is still picking the second date -- handle 0/1/2 selected dates safely.
start_date = end_date = None
if isinstance(date_range, tuple):
    if len(date_range) == 2:
        start_date, end_date = date_range
    elif len(date_range) == 1:
        start_date = date_range[0]

policies_qs = (
    Apolice.objects.select_related("segurado", "veiculo")
    .order_by("-data_fim_vigencia")
)

if start_date:
    policies_qs = policies_qs.filter(data_fim_vigencia__gte=start_date)
if end_date:
    policies_qs = policies_qs.filter(data_fim_vigencia__lte=end_date)

PAGE_SIZE = 10
total_matching = policies_qs.count()
total_pages = max(1, math.ceil(total_matching / PAGE_SIZE))

if "policies_page" not in st.session_state:
    st.session_state.policies_page = 1

# Keep the current page valid if a filter change shrinks the result set.
st.session_state.policies_page = min(st.session_state.policies_page, total_pages)
current_page = st.session_state.policies_page

offset = (current_page - 1) * PAGE_SIZE
page_policies = policies_qs[offset : offset + PAGE_SIZE]

if not page_policies:
    st.write("No policies match this filter.")
else:
    header = st.columns([3, 3, 2, 2, 2])
    header[0].markdown("**Policyholder**")
    header[1].markdown("**Insurer**")
    header[2].markdown("**Plate**")
    header[3].markdown("**Expires on**")
    header[4].markdown("**Action**")


    for policy in page_policies:
        row = st.columns([3, 3, 2, 2, 2])
        row[0].write(policy.segurado.nome_completo if policy.segurado else "—")
        row[1].write(policy.seguradora or "—")
        row[2].write(policy.veiculo.placa if policy.veiculo else "—")
        row[3].write(
            policy.data_fim_vigencia.strftime("%d/%m/%Y") if policy.data_fim_vigencia else "—"
        )
        row[4].button(
            "🧮 Renewal",
            key=f"calc_renewal_{policy.pk}",
            disabled=True,
        )

    nav_prev, nav_label, nav_next = st.columns([1, 2, 1])
    with nav_prev:
        if st.button("← Previous", disabled=(current_page <= 1)):
            st.session_state.policies_page -= 1
            st.rerun()
    with nav_label:
        st.write(f"Page {current_page} of {total_pages} ({total_matching} policies)")
    with nav_next:
        if st.button("Next →", disabled=(current_page >= total_pages)):
            st.session_state.policies_page += 1
            st.rerun()