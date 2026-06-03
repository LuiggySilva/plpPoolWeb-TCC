import json

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from django.utils.safestring import mark_safe

from user.models import AssistentStudent, SystemSetting

from .models import Period, ProgrammingLanguages, Question, Tag

FK_FIELDS = {
    "author": AssistentStudent,
    "period": Period,
}

M2M_FIELDS = {
    "tags": Tag,
}


def get_code_highlighted(name, code):
    """Retorna o código formatado com destaque de sintaxe usando Pygments."""
    if name not in [opt for opt, _ in ProgrammingLanguages.choices]:
        try:
            lexer = get_lexer_by_name("textfmts", stripall=True)
        except ClassNotFound:
            lexer = get_lexer_by_name("text", stripall=True)
    else:
        lexer = (
            get_lexer_by_name("cpp", stripall=True)
            if name == "cpluplus"
            else get_lexer_by_name(name, stripall=True)
        )

    formatter = HtmlFormatter(style="monokai", full=True, linenos=True)
    highlighted_code = highlight(code, lexer, formatter)
    return mark_safe(highlighted_code)


def get_default_days():
    """Obtém o número padrão de dias para o filtro, garantindo que seja um valor válido."""
    return 30


def get_days_from_request(request):
    """Extrai e valida o filtro de dias de forma segura."""
    default_days = get_default_days()
    try:
        days = int(request.GET.get("days", default_days))
        return days if days in [30, 60, 150] else default_days
    except ValueError:
        return default_days


def get_field_labels():
    """Constrói um dicionário de rótulos de campos para Question e SystemSetting, incluindo campos personalizados."""
    field_labels = {}

    for field in Question._meta.fields:
        field_labels[field.name] = field.verbose_name.capitalize()

    for field in SystemSetting._meta.fields:
        field_labels[field.name] = field.verbose_name.capitalize()

    field_labels.update({"tags": "Tags", "tag": "Tag"})

    return field_labels


def resolve_fk_value(field, value):
    """Resolve o valor de uma chave estrangeira para exibição legível."""
    if not value:
        return "—"
    model = FK_FIELDS.get(field)
    if not model:
        return value
    obj = model.objects.filter(pk=value).first()

    return str(obj) if obj else value


def resolve_m2m_value(field, value):
    """Resolve o valor de uma relação muitos-para-muitos para exibição legível."""
    if not value:
        return "—"
    model = M2M_FIELDS.get(field)
    if not model:
        return value
    ids = []
    if isinstance(value, str):
        ids = [v.strip()["tag"] for v in value.split(",") if v.strip()]
    elif isinstance(value, list):
        ids = [list(item.values())[1] for item in value]
    objs = model.objects.filter(pk__in=ids)

    return ", ".join(str(obj) for obj in objs) or "—"


def get_history_with_diff(instance, history_qs):
    """Processa o histórico de um objeto, calculando as diferenças entre as versões e formatando os dados para exibição. Agrupa mudanças semelhantes feitas em um curto período de tempo para melhorar a legibilidade."""
    records = []
    field_labels = get_field_labels()
    history_qs = list(history_qs)

    # Itera sobre o histórico, calculando as diferenças entre cada versão e a anterior, e formatando os dados para exibição.
    for i, record in enumerate(history_qs):
        prev_record = history_qs[i + 1] if i + 1 < len(history_qs) else None
        delta = record.diff_against(prev_record) if prev_record else None
        changes_list = []

        # Processa as mudanças detectadas, resolvendo valores de chaves estrangeiras e relações muitos-para-muitos para exibição legível, e adicionando informações sobre os casos de teste se disponíveis.
        if delta:
            for change in delta.changes:
                field = change.field
                old, new = change.old, change.new

                if field in FK_FIELDS:
                    old, new = resolve_fk_value(field, old), resolve_fk_value(field, new)
                elif field in M2M_FIELDS:
                    old, new = resolve_m2m_value(field, old), resolve_m2m_value(field, new)

                changes_list.append(
                    {
                        "field": field_labels.get(field, field),
                        "old": old,
                        "new": new,
                        "is_textarea": field in ["description", "code", "tags"],
                    }
                )

        # Adiciona informações sobre os casos de teste se disponíveis, tentando decodificar o motivo da mudança como JSON e extraindo os dados relevantes.
        if record.history_change_reason:
            try:
                reason_data = json.loads(record.history_change_reason)
                tests_data = reason_data.get("tests")

                if tests_data:
                    created = tests_data.get("created", 0)
                    updated = tests_data.get("updated", 0)
                    deleted = tests_data.get("deleted", 0)

                    summary_old, summary_new = [], []

                    if deleted:
                        summary_old.append(f"{deleted} removido(s)")
                    if created:
                        summary_new.append(f"{created} criado(s)")
                    if updated:
                        summary_new.append(f"{updated} atualizado(s)")

                    changes_list.append(
                        {
                            "field": "Casos de teste",
                            "old": ", ".join(summary_old) or "—",
                            "new": ", ".join(summary_new) or "—",
                            "is_textarea": False,
                        }
                    )
            except json.JSONDecodeError:
                pass

        record.changes_list = changes_list
        records.append(record)

    # Agrupa mudanças semelhantes feitas em um curto período de tempo para melhorar a legibilidade, verificando se as mudanças foram feitas pelo mesmo usuário, do mesmo tipo, com o mesmo motivo e em um intervalo de tempo próximo, e combinando as mudanças em um único registro quando apropriado.
    merged_records = []
    for record in records:
        if not merged_records:
            merged_records.append(record)
            continue

        last = merged_records[-1]

        same_user = last.history_user_id == record.history_user_id
        same_type = last.history_type == record.history_type
        same_reason = last.history_change_reason == record.history_change_reason

        # Considera mudanças feitas em um intervalo de tempo próximo (menos de 10 segundos) como parte do mesmo grupo, para evitar fragmentação excessiva do histórico devido a múltiplas mudanças feitas em rápida sucessão.
        close_time = abs((last.history_date - record.history_date).total_seconds()) < 10

        if same_user and same_type and same_reason and close_time:
            existing = {(c["field"], str(c["old"]), str(c["new"])) for c in last.changes_list}

            for change in record.changes_list:
                identifier = (change["field"], str(change["old"]), str(change["new"]))
                if identifier not in existing:
                    last.changes_list.append(change)
        else:
            merged_records.append(record)

    return merged_records


def htmx_modal_response(request, response_function, target, modal_id, modal_list_id):
    """Padroniza a resposta de fechamento de modal e atualização de tabela."""
    response = response_function(request)
    instructions = {"closeModal": {"target": target, "modal": modal_id, "listModal": modal_list_id}}
    response["HX-Trigger"] = json.dumps(instructions)
    return response
